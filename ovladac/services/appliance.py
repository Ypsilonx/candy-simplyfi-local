"""Jediný správce myčky: pravidelné čtení stavu, cache, sériové příkazy a zápis cyklů.

Server je jediný klient myčky (souběh spojení modul zasekává). Síťová volání
jsou synchronní (``urllib``), proto běží v ``asyncio.to_thread``; čtení i příkazy
se střídají přes jeden zámek.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from candy_netscan.candy_watch import diff
from candy_netscan.client import read_status, send_params

from ..config import Settings
from .history import Cycle, CycleTracker, History
from .model import Stav, interpret
from .programs import AUTOCLEAN_PROGRAM
from .rawlog import RawLog

log = logging.getLogger(__name__)


class ApplianceError(Exception):
    """Příkaz nejde provést (myčka nedostupná, vypnuté dálkové ovládání …)."""


class ApplianceBusy(ApplianceError):
    """Myčka už má program rozjetý – nový start by šel do běžícího cyklu."""


@dataclass
class CommandResult:
    """Výsledek příkazu: v dry-run jen plaintext, jinak i odpověď a změny stavu po ověření."""

    plaintext: str
    odeslano: bool
    odpoved: str | None = None
    zmeny: dict[str, tuple] | None = None
    varovani: str | None = None


class Appliance:
    """Drží poslední známý stav myčky a zprostředkuje všechny příkazy."""

    def __init__(self, settings: Settings, history: History) -> None:
        """Bez čtení – první stav přinese ``refresh`` / ``run``."""
        self.settings = settings
        self.history = history
        self.raw: dict[str, str] | None = None
        self.stav: Stav | None = None
        self.updated: datetime | None = None
        self.error: str | None = None
        self._tracker = CycleTracker()
        self._rawlog = RawLog(settings.raw_dir)
        # Čištění = jen cyklus spuštěný tlačítkem v ovladači. r9=H_ z myčky se nepoužívá:
        # drží se i po konci cyklu (P12), běžné mytí by se pak mohlo počítat jako odvápnění.
        self._cleaning_started = False
        self._lock = asyncio.Lock()

    async def _read(self) -> dict[str, str]:
        """Jedno čtení stavu z myčky (mimo event loop)."""
        s = self.settings
        return await asyncio.to_thread(read_status, s.candy_ip, s.candy_key, s.timeout_seconds)

    def _store(self, raw: dict[str, str]) -> None:
        """Uloží čtení do cache a předá ho trackeru; hotový cyklus zapíše do historie."""
        now = self.settings.now()
        self._rawlog.write(raw, now)  # před interpretací – zůstane i čtení, na kterém by model spadl
        self.raw, self.stav, self.updated, self.error = raw, interpret(raw), now, None
        event = self._tracker.update(self.stav, now)
        if event:
            log.info("cyklus: %s %s", event.kind, event.cycle or self.stav.program)
            if event.cycle:
                self._finish_cycle(event.cycle)

    def _finish_cycle(self, cycle: Cycle) -> None:
        """Zapíše cyklus; dokončené čištění zároveň zapíše jako odvápnění."""
        cycle.cisteni = self._cleaning_started and cycle.program == AUTOCLEAN_PROGRAM
        self._cleaning_started = False
        self.history.append(cycle)
        if cycle.cisteni and cycle.vysledek == "dokonceno":
            self.history.mark("odvapneni", datetime.fromisoformat(cycle.konec))
            log.info("čištění dokončeno – zapsáno odvápnění")

    @property
    def cleaning(self) -> bool:
        """Právě běží čisticí cyklus spuštěný z ovladače."""
        return self._cleaning_started and bool(self.stav and self.stav.aktivni)

    def cleaning_started(self) -> None:
        """Ovladač právě spustil čisticí cyklus a myčka běží – jeho konec se zapíše jako odvápnění."""
        if self.stav and self.stav.aktivni and self.stav.program == AUTOCLEAN_PROGRAM:
            self._cleaning_started = True

    async def refresh(self) -> None:
        """Načte stav; chybu jen zaznamená (poslední stav zůstává, ``error`` ji popíše).

        Zachytává vše: kromě ``OSError`` hází urllib i ``http.client.HTTPException``
        (useknutá odpověď z ESP) a nepropadlá výjimka by poller natrvalo zastavila.
        """
        async with self._lock:
            try:
                self._store(await self._read())
            except Exception as exc:  # noqa: BLE001 – poller nesmí spadnout
                self.error = f"Myčka neodpovídá: {exc!r}"
                log.warning(self.error)

    async def run(self) -> None:
        """Nekonečná smyčka čtení; ruší se zrušením tasku při vypnutí serveru."""
        while True:
            await self.refresh()
            await asyncio.sleep(self.settings.poll_seconds)

    async def command(self, params: str, require_idle: bool = False) -> CommandResult:
        """Pošle plaintext příkaz (v dry-run jen vrátí), ověří ho čtením stavu.

        Před odesláním pod zámkem čerstvě přečte stav: příkaz jde jen při
        ``StatoWiFi=1`` a s ``require_idle`` jen když myčka nemá rozjetý program
        (``ApplianceBusy``). Selhání kontrolního čtení po odeslání už není chyba
        příkazu – vrátí se jako ``varovani``, aby uživatel neposílal start podruhé.
        """
        s = self.settings
        if s.dry_run:
            if require_idle and self.stav and self.stav.aktivni:
                raise ApplianceBusy("Myčka už má spuštěný program – nejdřív ho zastavte")
            log.info("dry-run, neodesláno: %s", params)
            return CommandResult(plaintext=params, odeslano=False)
        async with self._lock:
            try:
                before = await self._read()
            except Exception as exc:  # noqa: BLE001
                raise ApplianceError(f"Myčka neodpovídá: {exc!r}") from exc
            self._store(before)
            if before.get("StatoWiFi") != "1":
                raise ApplianceError("Dálkové ovládání je vypnuté – zapněte ho tlačítkem Wi-Fi na myčce")
            if require_idle and self.stav.aktivni:
                raise ApplianceBusy("Myčka už má spuštěný program – nejdřív ho zastavte")

            log.info("příkaz: %s", params)
            try:
                answer = await asyncio.to_thread(
                    send_params, s.candy_ip, s.candy_key, params, s.timeout_seconds)
            except Exception as exc:  # noqa: BLE001
                # Nevíme, jestli příkaz došel – ať uživatel nejdřív zkontroluje stav.
                raise ApplianceError(
                    f"Odeslání selhalo ({exc!r}) – zkontrolujte stav, než to zkusíte znovu") from exc

            await asyncio.sleep(s.verify_seconds)
            try:
                after = await self._read()
            except Exception as exc:  # noqa: BLE001
                log.warning("ověření po příkazu selhalo: %r", exc)
                return CommandResult(plaintext=params, odeslano=True, odpoved=answer,
                                     varovani="Příkaz odešel, ale stav se nepodařilo ověřit – "
                                              "počkejte na další načtení")
            self._store(after)
        return CommandResult(plaintext=params, odeslano=True, odpoved=answer,
                             zmeny=diff(before, after))
