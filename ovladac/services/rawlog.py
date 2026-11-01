"""Surový log čtení myčky: celé čtení beze změn, ale jen když se liší od předchozího.

Formát jako ``candy_watch`` (jeden JSON na řádek, ``t`` + všechna pole tak, jak je myčka
poslala, i neznámá), soubor na den ``<YYYY-MM-DD>.jsonl``. Slouží k výzkumu – nic se nefiltruje.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class RawLog:
    """Zapisuje změněná čtení do ``<adresář>/<datum>.jsonl``."""

    def __init__(self, directory: Path) -> None:
        """``directory`` se vytvoří při prvním zápisu; první čtení po startu se zapíše vždy."""
        self.directory = directory
        self._last: dict[str, str] | None = None

    def write(self, raw: dict[str, str], ts: datetime) -> bool:
        """Zapíše čtení, pokud se od minulého změnilo; vrátí True, když zapsalo."""
        if raw == self._last:
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{ts.date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": ts.isoformat(timespec="seconds"), **raw}, ensure_ascii=False) + "\n")
        self._last = dict(raw)
        return True
