"""CLI: python -m candy_netscan [--subnet CIDR] [...]"""

from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import oui
from .neighbors import NeighborTableUnavailable, read_neighbors
from .network import detect_local_subnet
from .probe import ENDPOINT, probe_network
from .report import build_rows, render


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="candy_netscan",
        description="List LAN hosts with MAC vendors and flag Candy "
                    "simply-Fi appliances.")
    p.add_argument("--subnet", help="e.g. 192.168.1.0/24 (default: auto /24)")
    p.add_argument("--port", type=int, default=80)
    p.add_argument("--timeout", type=float, default=2.0,
                   help="seconds per host (default: 2.0)")
    p.add_argument("--workers", type=int, default=64)
    p.add_argument("--oui-file", type=Path, default=oui.default_cache_path(),
                   help="IEEE oui.csv path (downloaded if missing)")
    p.add_argument("--refresh-oui", action="store_true",
                   help="re-download the vendor database")
    p.add_argument("--no-oui", action="store_true",
                   help="skip vendor lookup")
    return p.parse_args(argv)


def _progress(done: int, total: int) -> None:
    print(f"\rScanned {done}/{total}", end="", flush=True)


def _load_oui(args: argparse.Namespace) -> Optional[Dict[str, str]]:
    if args.no_oui:
        return None
    try:
        path = oui.ensure_database(args.oui_file, refresh=args.refresh_oui)
        return oui.load_database(path)
    except OSError as exc:  # URLError is an OSError subclass
        print(f"Warning: vendor database unavailable ({exc}).",
              file=sys.stderr)
        return None


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    try:
        network = (ipaddress.ip_network(args.subnet, strict=False)
                   if args.subnet else detect_local_subnet())
    except (ValueError, OSError) as exc:
        print(f"Cannot determine subnet: {exc}", file=sys.stderr)
        return 2

    print(f"Scanning {network} (port {args.port}, {ENDPOINT}) ...")
    http = probe_network(network, args.port, args.timeout, args.workers,
                         on_progress=_progress)
    print()

    try:
        neighbors = read_neighbors()
    except NeighborTableUnavailable as exc:
        print(f"Warning: {exc}", file=sys.stderr)
        neighbors = {}

    in_net = {ip for ip in neighbors
              if ipaddress.ip_address(ip) in network}
    hosts = sorted(in_net | set(http), key=ipaddress.ip_address)
    if not hosts:
        print("No hosts found. Check that you are on the same Wi-Fi "
              "(not a guest network) and that the subnet is right.")
        return 1

    oui_db = _load_oui(args) if neighbors else None
    print(render(build_rows(hosts, neighbors, http, oui_db)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
