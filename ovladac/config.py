"""Nastavení ovladače z proměnných prostředí (v Dockeru) nebo ze souboru .env (vývoj)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurace serveru; názvy proměnných = názvy polí velkými písmeny (``CANDY_IP`` …).

    Proměnné prostředí mají přednost před ``.env`` – v kontejneru stačí ``environment``/``env_file``.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    candy_ip: str
    candy_key: str = Field(min_length=16, max_length=16)
    # Bezpečný výchozí stav: příkazy se jen sestaví, neodešlou. Ostrý provoz DRY_RUN=false.
    dry_run: bool = True
    # Modul je ESP – nečíst častěji než á 3 s (appka čte á 15 s).
    poll_seconds: float = Field(default=15.0, ge=3.0)
    timeout_seconds: float = 8.0
    # Po příkazu počkat, než se stav ověří čtením (myčka hlásí SUCCESS i na ignorované).
    verify_seconds: float = 5.0
    # Složka s historií; v Dockeru připojit jako volume (např. /data).
    data_dir: Path = Path("data")

    @property
    def history_path(self) -> Path:
        """Soubor s historií cyklů a údržby."""
        return self.data_dir / "historie.jsonl"
