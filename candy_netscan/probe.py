"""HTTP probe of the simply-Fi local status endpoint.

Probing every host also makes the OS resolve its MAC address, which
fills the ARP table read afterwards by :mod:`neighbors`.
"""

from __future__ import annotations

import ipaddress
import json
import string
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Dict, Optional

ENDPOINT = "/http-read.json"
MAX_BODY_BYTES = 64 * 1024
HEX_CHARS = frozenset(string.hexdigits)


@dataclass(frozen=True)
class HttpResult:
    status: int
    kind: str  # "json" | "encrypted-hex" | "other" | "error"
    preview: str


def classify(body: str) -> str:
    text = body.strip()
    try:
        json.loads(text)
        return "json"
    except ValueError:
        pass
    if text and len(text) % 2 == 0 and set(text) <= HEX_CHARS:
        return "encrypted-hex"
    return "other"


def _preview(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    return " ".join(text.split())[:120]


def probe(ip: str, port: int, timeout: float) -> Optional[HttpResult]:
    """Return the HTTP answer of ``ip``, or None if nothing answered."""
    url = f"http://{ip}:{port}{ENDPOINT}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read(MAX_BODY_BYTES)
            body = raw.decode("utf-8", errors="replace")
            return HttpResult(resp.status, classify(body), _preview(raw))
    except urllib.error.HTTPError as exc:  # must precede URLError
        return HttpResult(exc.code, "error", str(exc.reason)[:120])
    except (urllib.error.URLError, OSError, ValueError):
        return None


def probe_network(network: ipaddress.IPv4Network, port: int, timeout: float,
                  workers: int,
                  on_progress: Optional[Callable[[int, int], None]] = None,
                  ) -> Dict[str, HttpResult]:
    hosts = [str(h) for h in network.hosts()]
    results: Dict[str, HttpResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(probe, ip, port, timeout): ip for ip in hosts}
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result is not None:
                results[futures[future]] = result
            if on_progress:
                on_progress(done, len(hosts))
    return results
