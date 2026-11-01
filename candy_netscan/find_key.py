"""Recover the 16-character XOR key of a Candy simply-Fi module (known-plaintext attack).

The status document always starts the same way (e.g. ``{\\r\\n\\t"statusDWash"``)
and the key is just XOR-ed over it, so XOR-ing the first 16 bytes of the
encrypted payload with that known start yields the key. Each module has its own
key; it is not sent anywhere, only read from the appliance's own answer.

Usage (from the project root):
    python -m candy_netscan.find_key <ip>
    python -m candy_netscan.find_key --hex <payload copied from /http-read.json?encrypted=1>
"""

from __future__ import annotations

import argparse
import string
import sys
from typing import Optional

from .client import READ_PATH, _get, _xor, parse_status

KEY_LEN = 16
# Known starts of the status document; firmwares differ in line endings/indentation.
KNOWN_PREFIXES = (
    '{\r\n\t"statusDWash":{',
    '{\n\t"statusDWash":{',
    '{\r\n"statusDWash":{',
    '{\n"statusDWash":{',
    '{"statusDWash":{',
)


def recover_key(hex_payload: str) -> Optional[str]:
    """Return the key that decrypts ``hex_payload`` into a valid status, or None.

    Each candidate key comes from one known prefix and is accepted only if it is
    printable ASCII and the whole payload then parses as a status document.
    """
    data = bytes.fromhex(hex_payload.strip())
    for prefix in KNOWN_PREFIXES:
        raw = bytes(c ^ p for c, p in zip(data, prefix[:KEY_LEN].encode("ascii")))
        candidate = raw.decode("latin-1")
        if len(candidate) != KEY_LEN or not all(ch in string.printable[:94] for ch in candidate):
            continue
        try:
            parse_status(_xor(data, candidate).decode())
        except ValueError:  # covers UnicodeDecodeError and JSONDecodeError
            continue
        return candidate
    return None


def main(argv=None) -> int:
    """CLI: read the encrypted status from the appliance (or take ``--hex``) and print the key."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("ip", nargs="?", help="appliance IP (one read of /http-read.json)")
    src.add_argument("--hex", help="encrypted payload instead of reading the appliance")
    p.add_argument("--timeout", type=float, default=8.0)
    args = p.parse_args(argv)

    payload = args.hex or _get(f"http://{args.ip}{READ_PATH}", args.timeout)
    key = recover_key(payload)
    if key is None:
        print("Key not found - the status does not start with any known prefix.", file=sys.stderr)
        return 1
    print(key)
    print("Put it into .env as CANDY_KEY (never commit it).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
