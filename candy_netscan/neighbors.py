"""Read the OS neighbour (ARP) table: IP -> MAC.

Tries, in order: /proc/net/arp (Linux), ``ip neigh`` (Linux),
``arp -a`` (Windows, macOS, BSD). Output is parsed with a generic regex,
so it does not depend on the system language or exact column layout.

Android 10+ blocks all of these for normal apps (Pydroid, Termux)
without root; :class:`NeighborTableUnavailable` is raised then.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List

_IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
_MAC_RE = re.compile(r"\b([0-9A-Fa-f]{1,2}(?:[:-][0-9A-Fa-f]{1,2}){5})\b")
_INVALID_MACS = {"00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"}
_COMMANDS: List[List[str]] = [["ip", "neigh", "show"], ["arp", "-a"]]


class NeighborTableUnavailable(RuntimeError):
    pass


def normalize_mac(mac: str) -> str:
    """'0-1A-2b-3:4:5' -> '00:1a:2b:03:04:05'."""
    parts = re.split(r"[:-]", mac)
    return ":".join(p.zfill(2).lower() for p in parts)


def parse_neighbor_output(text: str) -> Dict[str, str]:
    """Extract IP -> MAC pairs from any ARP/neighbour table dump."""
    table: Dict[str, str] = {}
    for line in text.splitlines():
        ip_match = _IP_RE.search(line)
        mac_match = _MAC_RE.search(line)
        if not ip_match or not mac_match:
            continue
        mac = normalize_mac(mac_match.group(1))
        if mac in _INVALID_MACS:
            continue
        table[ip_match.group(1)] = mac
    return table


def _run(cmd: List[str]) -> str:
    completed = subprocess.run(cmd, capture_output=True, timeout=10,
                               check=True)
    return completed.stdout.decode("utf-8", errors="replace")


def read_neighbors() -> Dict[str, str]:
    errors: List[str] = []

    proc_arp = Path("/proc/net/arp")
    try:
        table = parse_neighbor_output(proc_arp.read_text())
        if table:
            return table
    except OSError as exc:
        errors.append(f"{proc_arp}: {exc.strerror or exc}")

    for cmd in _COMMANDS:
        try:
            table = parse_neighbor_output(_run(cmd))
            if table:
                return table
            errors.append(f"{' '.join(cmd)}: empty")
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{' '.join(cmd)}: {exc}")

    raise NeighborTableUnavailable(
        "Cannot read the ARP table (" + "; ".join(errors) + "). "
        "On Android 10+ this is blocked for apps without root - "
        "run the scan on a PC, or check MAC addresses in the router.")
