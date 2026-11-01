"""Společné fixtures: načítání skutečných řádků z logů v data/watch/."""

import json
from pathlib import Path

import pytest

WATCH_DIR = Path(__file__).resolve().parent.parent / "data" / "watch"


def load_log(name: str) -> list[dict[str, str]]:
    """Načte JSONL log pokusu, vynechá časovou značku ``t``."""
    rows = []
    for line in (WATCH_DIR / name).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        row.pop("t", None)
        rows.append(row)
    return rows


@pytest.fixture(scope="session")
def p2_log() -> list[dict[str, str]]:
    """Celý cyklus P2 s ExtraDry a 3v1 (pokus P1)."""
    return load_log("2026-11-01_P2_extradry.jsonl")


@pytest.fixture(scope="session")
def panel_log() -> list[dict[str, str]]:
    """Přepínání programů na panelu bez startu (pokus P4)."""
    return load_log("2026-11-01_mapa-programu.jsonl")
