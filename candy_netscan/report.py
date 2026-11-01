"""Combine scan data into rows and judge how likely each host is Candy.

Evidence, strongest first:
  * answer on /http-read.json with JSON or hex  -> "CANDY (endpoint)"
  * vendor Candy / Hoover / Haier               -> "likely (vendor)"
  * vendor Espressif                            -> "possible (ESP module)"
    Community reports mention ESP-based Wi-Fi modules in some Candy
    appliances; this is a hint, not proof, and many IoT devices use ESP.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .oui import is_locally_administered, lookup
from .probe import HttpResult

CANDY_VENDOR_KEYWORDS = ("candy", "hoover", "haier")
MODULE_VENDOR_KEYWORDS = ("espressif",)


@dataclass(frozen=True)
class HostRow:
    ip: str
    mac: str
    vendor: str
    http: str
    verdict: str
    rank: int  # lower = more likely Candy


def _judge(vendor: str, http: Optional[HttpResult]) -> "tuple[int, str]":
    low = vendor.lower()
    if http and http.status == 200 and http.kind in ("json", "encrypted-hex"):
        return 0, "CANDY (endpoint)"
    if any(k in low for k in CANDY_VENDOR_KEYWORDS):
        return 1, "likely (vendor)"
    if any(k in low for k in MODULE_VENDOR_KEYWORDS):
        return 2, "possible (ESP module)"
    return 9, ""


def build_rows(ips: Iterable[str], neighbors: Dict[str, str],
               http: Dict[str, HttpResult],
               oui_db: Optional[Dict[str, str]]) -> List[HostRow]:
    rows: List[HostRow] = []
    for ip in ips:
        mac = neighbors.get(ip, "")
        if not mac:
            vendor = ""
        elif is_locally_administered(mac):
            vendor = "(random MAC - phone/PC)"
        elif oui_db is None:
            vendor = "(vendor DB unavailable)"
        else:
            vendor = lookup(oui_db, mac) or "(unknown)"
        result = http.get(ip)
        http_text = f"{result.status} {result.kind}" if result else "-"
        rank, verdict = _judge(vendor, result)
        rows.append(HostRow(ip, mac or "?", vendor, http_text, verdict, rank))
    return sorted(rows, key=lambda r: ipaddress.ip_address(r.ip))


def render(rows: List[HostRow], vendor_width: int = 28) -> str:
    header = f"{'IP':<15} {'MAC':<17} {'Vendor':<{vendor_width}} " \
             f"{'HTTP':<17} Verdict"
    lines = [header, "-" * len(header)]
    for r in rows:
        vendor = r.vendor[:vendor_width]
        lines.append(f"{r.ip:<15} {r.mac:<17} {vendor:<{vendor_width}} "
                     f"{r.http:<17} {r.verdict}")
    candidates = sorted((r for r in rows if r.rank < 9), key=lambda r: r.rank)
    lines.append("")
    if candidates:
        lines.append("Candidates (most likely first):")
        lines += [f"  {r.ip:<15} {r.verdict}" for r in candidates]
    else:
        lines.append("No Candy candidate found. Compare the list with the "
                     "dishwasher on/off (the host that disappears is it).")
    return "\n".join(lines)
