"""Společné fixtures: načítání skutečných řádků z logů v data/watch/."""

import json
from datetime import datetime
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


def load_timed_log(name: str, day: str) -> list[tuple[datetime, dict[str, str]]]:
    """Načte log jako (čas s místní zónou, řádek); log nese jen HH:MM:SS, den se doplní."""
    rows = []
    for line in (WATCH_DIR / name).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        ts = datetime.fromisoformat(f"{day}T{row.pop('t')}").astimezone()
        rows.append((ts, row))
    return rows


@pytest.fixture(scope="session")
def p2_timed() -> list[tuple[datetime, dict[str, str]]]:
    """Cyklus P2 z pokusu P1 s časovými značkami."""
    return load_timed_log("2026-11-01_P2_extradry.jsonl", "2026-11-01")


@pytest.fixture(scope="session")
def p2_log() -> list[dict[str, str]]:
    """Celý cyklus P2 s ExtraDry a 3v1 (pokus P1)."""
    return load_log("2026-11-01_P2_extradry.jsonl")


@pytest.fixture(scope="session")
def panel_log() -> list[dict[str, str]]:
    """Přepínání programů na panelu bez startu (pokus P4)."""
    return load_log("2026-11-01_mapa-programu.jsonl")
