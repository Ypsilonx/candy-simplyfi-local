"""Build, show and (optionally) send a command to a Candy simply-Fi dishwasher.

Commands follow the simply-Fi app 3.14.1 ("nautilus" dishwasher family), see
docs/protokol.md. Default is a dry run: the plaintext and encrypted payload are
printed, nothing is sent. With --send the remote-control flag is checked
first (StatoWiFi=1), the command is sent and the status is read back.

Usage (from the project root):
    python -m candy_netscan.send start P12
    python -m candy_netscan.send start P2 --extradry --delay 4 --send
    python -m candy_netscan.send stop --send
    python -m candy_netscan.send raw "BM=1"
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
from typing import Dict

from .candy_watch import diff, load_dotenv, read_status

WRITE_PATH = "/http-write.json?encrypted=1&data="

# Program code -> panel position (w1 / r1), measured in experiment P4.
# App-only programs (P9, P16, P17, P20) have no known position yet: use --w1.
PANEL_POSITIONS = {"P2": 1, "P5": 2, "P8": 3, "P12": 4, "P19": 5}

# Option bitmask used by the app (OpzProg), see CandyDishWasher.getOptions.
OPT_EXTRADRY, OPT_HALFLOAD, OPT_ECO, OPT_TAB, OPT_OPENDOOR = 1, 2, 4, 8, 16


def xor_encrypt(plaintext: str, key: bytes) -> str:
    """Return the app-compatible payload: XOR with the key, uppercase hex."""
    data = plaintext.encode("ascii")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).hex().upper()


def start_params(program: str, w1: int, delay: int, mask: int) -> str:
    """Build the start command exactly in the order the app uses.

    ``delay`` is in half-hours for appliances with r15 > 0 (ours), max 48.
    """
    flag = lambda bit: "1" if mask & bit else "0"  # noqa: E731
    return (f"DelayStart={delay}&ExtraDry={flag(OPT_EXTRADRY)}"
            f"&OpenDoorOpt={flag(OPT_OPENDOOR)}&TreinUno={flag(OPT_TAB)}"
            f"&Program={program}&MetaCarico={flag(OPT_HALFLOAD)}"
            f"&OpzProg={mask}&w1={w1}&StartStop=1&Eco={flag(OPT_ECO)}")


# Pause (Pa=1/0) is answered with SUCCESS but ignored by our model (P8).
SIMPLE_COMMANDS = {"stop": "Reset=1"}


def build_params(args: argparse.Namespace) -> str:
    """Translate parsed CLI arguments into the plaintext parameter string."""
    if args.action in SIMPLE_COMMANDS:
        return SIMPLE_COMMANDS[args.action]
    if args.action == "raw":
        return args.params
    program = args.program.upper()
    w1 = args.w1 if args.w1 is not None else PANEL_POSITIONS.get(program)
    if w1 is None:
        sys.exit(f"Unknown panel position for {program}, pass --w1.")
    mask = ((OPT_EXTRADRY if args.extradry else 0)
            | (OPT_HALFLOAD if args.halfload else 0)
            | (OPT_ECO if args.eco else 0)
            | (OPT_TAB if args.tab else 0)
            | (OPT_OPENDOOR if args.opendoor else 0))
    return start_params(program, w1, args.delay, mask)


def send(ip: str, payload: str, timeout: float) -> str:
    """Send the encrypted payload, return the raw HTTP body."""
    with urllib.request.urlopen(f"http://{ip}{WRITE_PATH}{payload}",
                                timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_args(argv) -> argparse.Namespace:
    """Define the CLI: start/stop/raw + common flags."""
    # Common flags live in a parent parser so they work after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--send", action="store_true",
                        help="really send (default: dry run)")
    common.add_argument("--timeout", type=float, default=8.0)
    common.add_argument("--wait", type=float, default=5.0,
                        help="seconds before reading the status back")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="action", required=True)
    st = sub.add_parser("start", parents=[common], help="start a program")
    st.add_argument("program", help="e.g. P2, P5, P8, P12, P19")
    st.add_argument("--w1", type=int, help="panel position override")
    st.add_argument("--delay", type=int, default=0, choices=range(49),
                    metavar="0-48", help="delayed start in half-hours")
    for opt in ("extradry", "halfload", "eco", "tab", "opendoor"):
        st.add_argument(f"--{opt}", action="store_true")
    for name in SIMPLE_COMMANDS:
        sub.add_parser(name, parents=[common])
    raw = sub.add_parser("raw", parents=[common],
                         help="send a raw parameter string")
    raw.add_argument("params")
    return p.parse_args(argv)


def main(argv) -> int:
    """Dry-run or send one command and show what changed on the appliance."""
    load_dotenv()
    args = parse_args(argv)
    ip, key = os.environ.get("CANDY_IP"), os.environ.get("CANDY_KEY")
    if not ip or not key:
        sys.exit("CANDY_IP / CANDY_KEY missing (.env)")
    params = build_params(args)
    payload = xor_encrypt(params, key.encode("ascii"))
    print(f"plaintext: {params}\npayload:   {payload}")
    if not args.send:
        print("dry run - nothing sent (add --send)")
        return 0

    before = read_status(ip, key.encode("ascii"), args.timeout)
    if before.get("StatoWiFi") != "1":
        sys.exit("Remote control is off (StatoWiFi != 1) - enable it on the "
                 "dishwasher first.")
    print(f"response:  {send(ip, payload, args.timeout)}")
    time.sleep(args.wait)
    after: Dict[str, str] = read_status(ip, key.encode("ascii"), args.timeout)
    changes = diff(before, after)
    for k, (old, new) in changes.items():
        print(f"    {k:<14} {old} -> {new}")
    if not changes:
        print("    (no change - command ignored or not applied yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
