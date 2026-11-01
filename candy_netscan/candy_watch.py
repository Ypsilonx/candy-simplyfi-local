#!/usr/bin/env python3
"""Poll a Candy simply-Fi appliance and print only the fields that change.

Reads http://<ip>/http-read.json?encrypted=1, decrypts the repeating-XOR
payload with the device key and diffs consecutive readings. Use it to map
field meanings: change one thing (program, option, door...) and watch.

Standard library only. Python 3.8+.

IP and key are taken from arguments, or from CANDY_IP / CANDY_KEY in the
environment or in the project's .env file (never commit the key).

Usage:
    python candy_netscan/candy_watch.py
    python candy_netscan/candy_watch.py --interval 5 --log data/watch/x.jsonl
    python candy_netscan/candy_watch.py <ip> <key>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

READ_PATH = "/http-read.json?encrypted=1"
DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_dotenv(path: Path = DOTENV_PATH) -> None:
    """Load KEY=VALUE lines from ``path`` into os.environ (no overrides).

    Minimal parser on purpose: the project stays standard-library only.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip())


def xor_decrypt(hex_payload: str, key: bytes) -> str:
    data = bytes.fromhex(hex_payload.strip())
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).decode()


def read_status(ip: str, key: bytes, timeout: float) -> Dict[str, str]:
    url = f"http://{ip}{READ_PATH}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        payload = resp.read().decode("ascii", errors="replace")
    doc = json.loads(xor_decrypt(payload, key))
    # Single top-level object, e.g. {"statusDWash": {...}}
    (_, fields), = doc.items()
    return {k: str(v) for k, v in fields.items()}


def diff(old: Dict[str, str], new: Dict[str, str]) -> Dict[str, tuple]:
    keys = old.keys() | new.keys()
    return {k: (old.get(k), new.get(k)) for k in sorted(keys)
            if old.get(k) != new.get(k)}


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("ip", nargs="?", default=os.environ.get("CANDY_IP"),
                   help="appliance IP (default: CANDY_IP)")
    p.add_argument("key", nargs="?", default=os.environ.get("CANDY_KEY"),
                   help="16-character XOR key (default: CANDY_KEY)")
    p.add_argument("--interval", type=float, default=3.0,
                   help="seconds between reads (default: 3)")
    p.add_argument("--timeout", type=float, default=8.0)
    p.add_argument("--log", type=Path,
                   help="append every reading as a JSON line")
    args = p.parse_args(argv)
    if not args.ip or not args.key:
        p.error("IP and key are required (arguments or CANDY_IP/CANDY_KEY)")
    return args


def main(argv) -> int:
    load_dotenv()
    args = parse_args(argv)
    key = args.key.encode("ascii")
    previous: Optional[Dict[str, str]] = None
    print("Watching... change something in the app or on the dishwasher. "
          "Ctrl+C to stop.")
    try:
        while True:
            stamp = datetime.now().strftime("%H:%M:%S")
            try:
                current = read_status(args.ip, key, args.timeout)
            except (OSError, ValueError) as exc:  # network / bad payload
                print(f"[{stamp}] read failed: {exc}")
                time.sleep(args.interval)
                continue

            if previous is None:
                print(f"[{stamp}] initial state:")
                for k, v in current.items():
                    print(f"    {k:<14} {v}")
            else:
                for k, (old, new) in diff(previous, current).items():
                    print(f"[{stamp}] {k:<14} {old} -> {new}")

            if args.log:
                with args.log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"t": stamp, **current}) + "\n")
            previous = current
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))