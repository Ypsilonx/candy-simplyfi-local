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
from .history import CycleTracker, History
from .model import Stav, interpret

log = logging.getLogger(__name__)


class ApplianceError(Exception):
    """Příkaz nejde provést (myčka nedostupná, vypnuté dálkové ovládání …)."""


@dataclass
class CommandResult:
    """Výsledek příkazu: v dry-run jen plaintext, jinak i odpověď a změny stavu po ověření."""

    plaintext: str
    odeslano: bool
    odpoved: str | None = None
    zmeny: dict[str, tuple] | None = None


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
        self._lock = asyncio.Lock()

    async def _read(self) -> dict[str, str]:
        """Jedno čtení stavu z myčky (mimo event loop)."""
        s = self.settings
        return await asyncio.to_thread(read_status, s.candy_ip, s.candy_key, s.timeout_seconds)

    def _store(self, raw: dict[str, str]) -> None:
        """Uloží čtení do cache a předá ho trackeru; hotový cyklus zapíše do historie."""
        now = datetime.now().astimezone()
        self.raw, self.stav, self.updated, self.error = raw, interpret(raw), now, None
        event = self._tracker.update(self.stav, now)
        if event:
            log.info("cyklus: %s %s", event.kind, event.cycle or self.stav.program)
            if event.cycle:
                self.history.append(event.cycle)

    async def refresh(self) -> None:
        """Načte stav; chybu jen zaznamená (poslední stav zůstává, ``error`` ji popíše)."""
        async with self._lock:
            try:
                self._store(await self._read())
            except (OSError, ValueError) as exc:
                self.error = f"Myčka neodpovídá: {exc}"
                log.warning(self.error)

    async def run(self) -> None:
        """Nekonečná smyčka čtení; ruší se zrušením tasku při vypnutí serveru."""
        while True:
            await self.refresh()
            await asyncio.sleep(self.settings.poll_seconds)

    async def command(self, params: str) -> CommandResult:
        """Pošle plaintext příkaz (v dry-run jen vrátí), ověří ho čtením stavu.

        Před odesláním čerstvě přečte stav: příkaz jde jen při ``StatoWiFi=1``.
        """
        if self.settings.dry_run:
            log.info("dry-run, neodesláno: %s", params)
            return CommandResult(plaintext=params, odeslano=False)
        s = self.settings
        async with self._lock:
            try:
                before = await self._read()
                self._store(before)
                if before.get("StatoWiFi") != "1":
                    raise ApplianceError("Dálkové ovládání je vypnuté – zapněte ho tlačítkem Wi-Fi na myčce")
                log.info("příkaz: %s", params)
                answer = await asyncio.to_thread(
                    send_params, s.candy_ip, s.candy_key, params, s.timeout_seconds)
                await asyncio.sleep(s.verify_seconds)
                after = await self._read()
                self._store(after)
            except (OSError, ValueError) as exc:
                raise ApplianceError(f"Myčka neodpovídá: {exc}") from exc
        return CommandResult(plaintext=params, odeslano=True, odpoved=answer,
                             zmeny=diff(before, after))
