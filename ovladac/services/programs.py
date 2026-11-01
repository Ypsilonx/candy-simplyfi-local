"""Katalog programů, pravidla voleb, výpočet „konec v“ a sestavení příkazu startu."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from candy_netscan import send

CATALOG_PATH = Path(__file__).with_name("programs.json")

# Volba → (bit masky OpzProg, pole ve stavu myčky, český název).
OPTIONS: dict[str, tuple[int, str, str]] = {
    "extradry": (send.OPT_EXTRADRY, "ExtraDry", "Extra sušení"),
    "halfload": (send.OPT_HALFLOAD, "MetaCarico", "½ náplň"),
    "eco": (send.OPT_ECO, "Eco", "Eco"),
    "tab": (send.OPT_TAB, "TreinUno", "Tablety 3v1"),
    "opendoor": (send.OPT_OPENDOOR, "OpenDoorOpt", "Otevření dvířek"),
}

# Volby, které se navzájem vylučují (podle appky: ExtraDry ↔ ½ náplň ↔ Eco).
EXCLUSIVE = {"extradry", "halfload", "eco"}

# Otevírání dvířek náš model asi nemá (neověřeno) – nenabízí se, dokud se neověří.
HIDDEN_OPTIONS = {"opendoor"}

MAX_DELAY_HALF_HOURS = 48


@dataclass(frozen=True)
class Program:
    """Jeden program myčky z katalogu.

    ``w1`` je pozice na panelu (None = jen z appky, zatím nespustitelný),
    ``delka_min`` naše změřená délka (None = neměřeno, použije se délka z appky).
    """

    kod: str
    nazev: str
    popis: str
    teplota: int | None
    w1: int | None
    delka_min: int | None
    delka_appka_min: int
    maska: int

    @property
    def delka(self) -> int:
        """Nejlepší známá délka programu v minutách."""
        return self.delka_min if self.delka_min is not None else self.delka_appka_min

    @property
    def spustitelny(self) -> bool:
        """True, pokud známe pozici na panelu a program jde poslat do myčky."""
        return self.w1 is not None


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Program]:
    """Načte katalog z JSON, vrátí slovník kód → Program (v pořadí souboru)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {p["kod"]: Program(**p) for p in data["programy"]}


CATALOG = load_catalog()


def get_program(code: str) -> Program:
    """Vrátí program podle kódu (např. ``P2``), neznámý kód → ``KeyError``."""
    return CATALOG[code.upper()]


def allowed_options(code: str) -> set[str]:
    """Volby, které program povoluje a které ovladač nabízí."""
    mask = get_program(code).maska
    return {name for name, (bit, _, _) in OPTIONS.items()
            if mask & bit and name not in HIDDEN_OPTIONS}


def validate_options(code: str, opts: set[str]) -> None:
    """Ověří kombinaci voleb pro program, při chybě vyhodí ``ValueError`` s českou zprávou."""
    unknown = opts - OPTIONS.keys()
    if unknown:
        raise ValueError(f"Neznámé volby: {', '.join(sorted(unknown))}")
    denied = opts - allowed_options(code)
    if denied:
        names = ", ".join(OPTIONS[o][2] for o in sorted(denied))
        raise ValueError(f"Program {code} nepovoluje: {names}")
    clash = opts & EXCLUSIVE
    if len(clash) > 1:
        names = " a ".join(OPTIONS[o][2] for o in sorted(clash))
        raise ValueError(f"Nelze kombinovat {names}")


def delay_for_end(now: datetime, konec: datetime,
                  delka_min: int) -> tuple[int, datetime]:
    """Spočítá odložení startu tak, aby program skončil co nejblíž ``konec``.

    Vrací (počet půlhodin pro ``DelayStart``, skutečný odhad konce). Odložení jde
    jen po 30 min, takže odhad se od přání liší až o ±15 min.
    ``ValueError``, když program do požadovaného času nestihne doběhnout
    nebo by odložení přesáhlo 24 h.
    """
    wait = konec - now - timedelta(minutes=delka_min)
    if wait < timedelta(0):
        raise ValueError("Program do požadovaného času nestihne doběhnout")
    half_hours = round(wait / timedelta(minutes=30))
    if half_hours > MAX_DELAY_HALF_HOURS:
        raise ValueError("Odložení startu může být nejvýš 24 hodin")
    estimate = now + timedelta(minutes=30 * half_hours + delka_min)
    return half_hours, estimate


def options_mask(opts: set[str]) -> int:
    """Převede množinu voleb na bitovou masku ``OpzProg``."""
    mask = 0
    for name in opts:
        mask |= OPTIONS[name][0]
    return mask


def start_params(code: str, opts: set[str], delay: int = 0) -> str:
    """Sestaví plaintext příkazu startu (pořadí parametrů jako appka).

    ``delay`` je v půlhodinách. Volby se ověří, program musí být spustitelný.
    """
    program = get_program(code)
    if not program.spustitelny:
        raise ValueError(f"Program {program.kod} zatím neumíme spustit (neznámá pozice)")
    validate_options(program.kod, opts)
    if not 0 <= delay <= MAX_DELAY_HALF_HOURS:
        raise ValueError("Odložení startu musí být 0–48 půlhodin")
    return send.start_params(program.kod, program.w1, delay, options_mask(opts))
