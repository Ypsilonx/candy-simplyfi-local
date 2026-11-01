"""Detekce cyklů myčky ze sledu stavů, historie v JSONL a počítadla údržby.

Myčka sama žádné počítadlo cyklů lokálně nedává (statistiky jdou jen do cloudu),
proto se cykly odvozují z přechodů stavu a ukládají do ``data/historie.jsonl``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .model import RUNNING, Stav

FILTER_INTERVAL = 100
# Odvápnění po N cyklech podle tvrdosti vody r7 (index 0–5), z appky.
DESCALE_INTERVALS = [110, 105, 100, 95, 90, 85]
MAINTENANCE_KINDS = ("filtr", "odvapneni")


@dataclass
class Cycle:
    """Jeden zaznamenaný cyklus.

    ``start`` je první čtení, kdy myčka běžela (po restartu serveru uprostřed
    cyklu tedy pozdější než skutečný start), ``zbyva_na_startu`` je ``RemTime``
    v tu chvíli – z něj se doučí skutečná délka programu s volbami.
    ``faze`` = minuty strávené v jednotlivých fázích.
    """

    start: str
    konec: str
    program: str
    volby: list[str]
    delka_min: int
    zbyva_na_startu: int
    vysledek: str  # "dokonceno" | "zruseno"
    faze: dict[str, int] = field(default_factory=dict)
    cisteni: bool = False  # čisticí cyklus (odvápnění) – starší záznamy pole nemají


@dataclass
class Event:
    """Událost z ``CycleTracker``: ``start`` (cycle je None), ``konec`` nebo ``zruseno``."""

    kind: str
    cycle: Cycle | None = None


def _iso(ts: datetime) -> str:
    """ISO 8601 s offsetem na celé sekundy."""
    return ts.isoformat(timespec="seconds")


def _minutes(a: datetime, b: datetime) -> int:
    """Celé minuty mezi dvěma časy (zaokrouhleno)."""
    return round((b - a).total_seconds() / 60)


class CycleTracker:
    """Sleduje po sobě jdoucí stavy a hlásí začátek a konec cyklu.

    Čekání na odložený start se za cyklus nepočítá; cyklus začne až během.
    Pauza (otevřená dvířka, krátce po startu) cyklus nepřerušuje.
    """

    def __init__(self) -> None:
        """Začíná bez rozpracovaného cyklu."""
        self._start: datetime | None = None
        self._first: Stav | None = None
        self._phase: str = ""
        self._phase_since: datetime | None = None
        self._phases: dict[str, int] = {}

    def update(self, stav: Stav, ts: datetime) -> Event | None:
        """Zpracuje další čtení stavu (``ts`` s časovou zónou), vrátí událost nebo None."""
        running = stav.stav in RUNNING
        if self._start is None:
            if not running:
                return None
            self._start, self._first = ts, stav
            self._phase, self._phase_since, self._phases = stav.faze, ts, {}
            return Event("start")

        if running:
            if stav.faze and stav.faze != self._phase:
                self._close_phase(ts)
                self._phase, self._phase_since = stav.faze, ts
            return None

        self._close_phase(ts)
        cycle = Cycle(
            start=_iso(self._start),
            konec=_iso(ts),
            program=self._first.program,
            volby=self._first.volby,
            delka_min=_minutes(self._start, ts),
            zbyva_na_startu=self._first.zbyva_min,
            vysledek="dokonceno" if stav.stav == "konec" else "zruseno",
            faze=self._phases,
        )
        self._start = self._first = None
        return Event("konec" if cycle.vysledek == "dokonceno" else "zruseno", cycle)

    def _close_phase(self, ts: datetime) -> None:
        """Připočte čas právě končící fáze (pauza se počítá do fáze, ve které nastala)."""
        if self._phase and self._phase_since is not None:
            self._phases[self._phase] = (self._phases.get(self._phase, 0)
                                         + _minutes(self._phase_since, ts))


class History:
    """Historie cyklů a značek údržby v jednom JSONL souboru.

    Řádek je buď ``{"typ": "cyklus", ...Cycle}``, nebo
    ``{"typ": "udrzba", "druh": "filtr"|"odvapneni", "cas": ISO}``.
    """

    def __init__(self, path: Path) -> None:
        """``path`` = cesta k JSONL; složka se vytvoří při prvním zápisu."""
        self.path = path

    def _append(self, record: dict) -> None:
        """Připíše jeden záznam na konec souboru."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _records(self) -> list[dict]:
        """Načte všechny záznamy v pořadí zápisu (chybějící soubor = prázdno)."""
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def append(self, cycle: Cycle) -> None:
        """Uloží cyklus."""
        self._append({"typ": "cyklus", **asdict(cycle)})

    def list(self) -> list[Cycle]:
        """Všechny cykly od nejstaršího."""
        return [Cycle(**{k: v for k, v in r.items() if k != "typ"})
                for r in self._records() if r["typ"] == "cyklus"]

    def mark(self, kind: str, ts: datetime | None = None) -> None:
        """Zapíše provedenou údržbu (``filtr`` / ``odvapneni``), výchozí čas = teď."""
        if kind not in MAINTENANCE_KINDS:
            raise ValueError(f"Neznámý druh údržby: {kind}")
        ts = ts or datetime.now().astimezone()  # volající (server) předává čas v zóně domácnosti
        self._append({"typ": "udrzba", "druh": kind, "cas": _iso(ts)})

    def maintenance(self, hardness: int) -> dict:
        """Kolik dokončených cyklů zbývá do čištění filtru a odvápnění.

        Počítá se od poslední značky daného druhu (bez značky od začátku historie).
        Záporné číslo = údržba je po termínu o tolik cyklů. Vrací i čas poslední značky.
        """
        counts = {kind: 0 for kind in MAINTENANCE_KINDS}
        last: dict[str, str | None] = {kind: None for kind in MAINTENANCE_KINDS}
        for r in self._records():
            if r["typ"] == "udrzba":
                counts[r["druh"]], last[r["druh"]] = 0, r["cas"]
            elif r["vysledek"] == "dokonceno":
                for kind in counts:
                    counts[kind] += 1
        descale = DESCALE_INTERVALS[min(max(hardness, 0), len(DESCALE_INTERVALS) - 1)]
        return {
            "filtr_zbyva": FILTER_INTERVAL - counts["filtr"],
            "odvapneni_zbyva": descale - counts["odvapneni"],
            "filtr_posledni": last["filtr"],
            "odvapneni_posledni": last["odvapneni"],
        }
