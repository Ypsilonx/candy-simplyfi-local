"""Low-level client for a Candy simply-Fi appliance (local HTTP, XOR "encryption").

Shared by candy_watch, send and the ovladac server. Standard library only,
Python 3.8+ (runs in Pydroid too). See docs/protokol.md for the protocol.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Dict

READ_PATH = "/http-read.json?encrypted=1"
WRITE_PATH = "/http-write.json?encrypted=1&data="


def _xor(data: bytes, key: str) -> bytes:
    """XOR ``data`` with the ASCII ``key`` repeated over its whole length."""
    k = key.encode("ascii")
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(data))


def xor_encrypt(text: str, key: str) -> str:
    """Encrypt plaintext the way the app does: XOR with the key, uppercase hex."""
    return _xor(text.encode("ascii"), key).hex().upper()


def xor_decrypt(hex_payload: str, key: str) -> str:
    """Decrypt a hex payload from the appliance back to plaintext."""
    return _xor(bytes.fromhex(hex_payload.strip()), key).decode()


def _get(url: str, timeout: float) -> str:
    """Perform one GET and return the body as text."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("ascii", errors="replace")


def parse_status(text: str) -> Dict[str, str]:
    """Parse the decrypted status document, return its fields (values as strings).

    The document has a single top-level object, e.g. ``{"statusDWash": {...}}``.
    The firmware does not escape backslashes: during autoclean it sends
    ``"r9":"H_2 \\"`` (seen in experiment P12), which breaks a strict JSON
    parser. Its values never contain real escapes, so every backslash is
    taken literally.
    """
    doc = json.loads(text.replace("\\", "\\\\"))
    (_, fields), = doc.items()
    return {k: str(v) for k, v in fields.items()}


def read_status(ip: str, key: str, timeout: float = 8.0) -> Dict[str, str]:
    """Read and decrypt the status, return its fields (all values as strings)."""
    return parse_status(xor_decrypt(_get(f"http://{ip}{READ_PATH}", timeout), key))


def send_params(ip: str, key: str, params: str, timeout: float = 8.0) -> str:
    """Send a plaintext ``k=v&...`` command, return the decrypted response.

    The module answers SUCCESS even to commands it ignores - verify the effect
    by reading the status afterwards.
    """
    body = _get(f"http://{ip}{WRITE_PATH}{xor_encrypt(params, key)}", timeout)
    try:
        return xor_decrypt(body, key)
    except ValueError:  # not hex - return as is so the caller sees what came
        return body
