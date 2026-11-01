"""Local subnet detection."""

from __future__ import annotations

import ipaddress
import socket


def detect_local_subnet(prefix: int = 24) -> ipaddress.IPv4Network:
    """Return the network of the interface used for outbound traffic.

    Connecting a UDP socket sends no packets; it only makes the OS pick
    the outgoing interface, whose address is then read. The prefix
    length cannot be read portably, so it is assumed (default /24).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("192.0.2.1", 80))  # TEST-NET-1, never routed
        local_ip = sock.getsockname()[0]
    return ipaddress.ip_network(f"{local_ip}/{prefix}", strict=False)
