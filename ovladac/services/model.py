"""Převod surového stavu myčky (``statusDWash``) na čitelný stav pro UI a historii.

Významy polí viz docs/protokol.md. Čisté funkce, bez síťové komunikace.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .programs import CATALOG, OPTIONS

# StatoDWash → (kód stavu, český popis).
STATES: dict[str, tuple[str, str]] = {
    "0": ("nic", "Neznámý stav"),
    "1": ("reset", "Ruší se program"),
    "2": ("vyber", "Připraveno"),
    "3": ("beh", "Myje"),
    "4": ("pauza", "Pozastaveno"),
    "5": ("konec", "Dokončeno"),
    "6": ("chyba", "Chyba"),
    "99": ("odlozeno", "Čeká na odložený start"),
}

# Myčka myje (pauza = otevřená dvířka během mytí, cyklus pokračuje).
RUNNING = ("beh", "pauza")
# Myčka má program „rozjetý“ – nový start ani nastavení programu nedávají smysl.
ACTIVE = (*RUNNING, "odlozeno")

# r2 → český název fáze.
PHASES = {"0": "", "1": "Předmytí", "2": "Mytí", "3": "Oplach", "4": "Sušení",
          "5": "Konec", "9": "Pauza"}


@dataclass
class Nastaveni:
    """Nastavení uložená v myčce (přežijí restart)."""

    zvuk: bool          # r6 (BM)
    tvrdost: int        # r7 (HL), index 0–5
    posledni_cyklus: bool  # r8 (LC)


@dataclass
class Stav:
    """Čitelný stav myčky.

    ``faze`` je prázdná mimo běh (``r2`` tam drží starou hodnotu),
    ``zbyva_min`` mimo běh = jmenovitá délka vybraného programu,
    ``odlozeni_min`` = minuty do odloženého startu (0 = žádný).
    """

    stav: str
    popis: str
    faze: str
    program: str
    program_nazev: str
    zbyva_min: int
    odlozeni_min: int
    volby: list[str]
    aktivni: bool       # stav je v ACTIVE (myje, pauza, čeká na start)
    dalkove_ovladani: bool
    dvirka_otevrena: bool
    nastaveni: Nastaveni
    varovani: list[str] = field(default_factory=list)


def _int(raw: dict[str, str], name: str) -> int:
    """Vrátí číselné pole stavu, chybějící nebo nečíselné jako 0."""
    try:
        return int(raw.get(name, "0"))
    except ValueError:
        return 0


def interpret(raw: dict[str, str]) -> Stav:
    """Převede surový stav (hodnoty jako stringy) na ``Stav``."""
    code, label = STATES.get(raw.get("StatoDWash", "0"), STATES["0"])
    delay = _int(raw, "DelayStart")
    # Čekající odložený start hlásí myčka jako běh (3), s otevřenými dvířky asi jako pauzu (4).
    if code in RUNNING and delay > 0:
        code, label = STATES["99"]
    running = code in RUNNING

    program = raw.get("Program", "")
    catalog_entry = CATALOG.get(program)
    volby = [name for name, (_, fld, _) in OPTIONS.items() if raw.get(fld) == "1"]

    warnings = []
    if raw.get("MissSalt") == "1":
        warnings.append("Doplňte sůl")
    if raw.get("MissRinse") == "1":
        warnings.append("Doplňte leštidlo")
    error = raw.get("CodiceErrore", "E0")
    if error not in ("E0", ""):
        warnings.append(f"Chyba myčky {error}")

    return Stav(
        stav=code,
        popis=label,
        faze=PHASES.get(raw.get("r2", "0"), "") if running else "",
        program=program,
        program_nazev=catalog_entry.nazev if catalog_entry else program,
        zbyva_min=_int(raw, "RemTime"),
        # Mimo čekání drží myčka v DelayStart starou hodnotu (viděno ve stavu výběr).
        odlozeni_min=delay if code == "odlozeno" else 0,
        volby=volby,
        aktivni=code in ACTIVE,
        dalkove_ovladani=raw.get("StatoWiFi") == "1",
        dvirka_otevrena=raw.get("OpenDoor") == "1",
        nastaveni=Nastaveni(
            zvuk=raw.get("r6") == "1",
            tvrdost=_int(raw, "r7"),
            posledni_cyklus=raw.get("r8") == "1",
        ),
        varovani=warnings,
    )
