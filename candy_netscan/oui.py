"""MAC vendor lookup using the official IEEE OUI registry (MA-L, 24-bit).

The CSV (~6 MB) is downloaded once and cached; later runs work offline.
Smaller MA-M / MA-S blocks are not covered: such devices show the
organisation that owns the parent block, or nothing.
"""

from __future__ import annotations

import csv
import urllib.request
from pathlib import Path
from typing import Dict, Optional

IEEE_OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"
_USER_AGENT = "candy-netscan/0.2 (python urllib)"


def default_cache_path() -> Path:
    return Path.home() / ".cache" / "candy_netscan" / "oui.csv"


def ensure_database(path: Path, refresh: bool = False,
                    timeout: float = 30.0) -> Path:
    """Download the registry to ``path`` unless it is already there."""
    if path.exists() and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(IEEE_OUI_URL,
                                     headers={"User-Agent": _USER_AGENT})
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        tmp.write_bytes(resp.read())
    tmp.replace(path)  # atomic: no half-written cache on failure
    return path


def load_database(path: Path) -> Dict[str, str]:
    """Return {'AABBCC': 'Organization Name'}."""
    db: Dict[str, str] = {}
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            prefix = (row.get("Assignment") or "").strip().upper()
            name = (row.get("Organization Name") or "").strip()
            if len(prefix) == 6 and name:
                db[prefix] = name
    return db


def is_locally_administered(mac: str) -> bool:
    """True for randomised/private MACs (phones, laptops with privacy on).

    Such addresses are not registered, so they have no vendor.
    """
    return bool(int(mac.split(":")[0], 16) & 0x02)


def lookup(db: Dict[str, str], mac: str) -> Optional[str]:
    return db.get(mac.replace(":", "")[:6].upper())
