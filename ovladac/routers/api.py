"""REST API ovladače (``/api/...``). Stránky se ptají serveru, nikdy přímo myčky."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from ..services import programs
from ..services.appliance import Appliance, ApplianceBusy, ApplianceError, CommandResult
from ..services.history import MAINTENANCE_KINDS

router = APIRouter(prefix="/api")


def _appliance(request: Request) -> Appliance:
    """Správce myčky vytvořený v lifespan aplikace."""
    return request.app.state.appliance


async def _run(appliance: Appliance, params: str, require_idle: bool = False) -> dict:
    """Provede příkaz a převede chyby na HTTP odpovědi (rozjetý program 409, jinak 503)."""
    try:
        result: CommandResult = await appliance.command(params, require_idle)
    except ApplianceBusy as exc:
        raise HTTPException(409, str(exc)) from exc
    except ApplianceError as exc:
        raise HTTPException(503, str(exc)) from exc
    return asdict(result)


class StartRequest(BaseModel):
    """Start programu: hned, s odložením v půlhodinách, nebo „konec v HH:MM“."""

    program: str
    volby: list[str] = []
    odlozeni: int | None = Field(default=None, ge=0, le=programs.MAX_DELAY_HALF_HOURS)
    konec: time | None = None

    @model_validator(mode="after")
    def _one_timing(self) -> StartRequest:
        """Odložení a čas konce nejdou zadat současně."""
        if self.odlozeni is not None and self.konec is not None:
            raise ValueError("Zadejte buď odložení, nebo čas konce")
        return self


class SettingRequest(BaseModel):
    """Jedno nastavení myčky na požadavek (každé je ověřené samostatně, kombinace ne)."""

    zvuk: bool | None = None
    tvrdost: int | None = Field(default=None, ge=0, le=5)
    posledni_cyklus: bool | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> SettingRequest:
        """Právě jedna hodnota."""
        if sum(v is not None for v in (self.zvuk, self.tvrdost, self.posledni_cyklus)) != 1:
            raise ValueError("Zadejte právě jedno nastavení")
        return self

    def params(self) -> str:
        """Plaintext příkazu (BM → r6, HL → r7, LC → r8, ověřeno v P10)."""
        if self.zvuk is not None:
            return f"BM={int(self.zvuk)}"
        if self.tvrdost is not None:
            return f"HL={self.tvrdost}"
        return f"LC={int(self.posledni_cyklus)}"


class MaintenanceRequest(BaseModel):
    """Značka provedené údržby."""

    druh: Literal[MAINTENANCE_KINDS]  # type: ignore[valid-type]


def _next_occurrence(now: datetime, at: time) -> datetime:
    """Nejbližší budoucí okamžik s časem ``at`` (dnes, nebo zítra).

    ``now`` nese ``ZoneInfo`` – ``replace`` i ``+ 1 den`` pak drží čas na ručičkách
    i přes změnu letního času.
    """
    target = now.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


@router.get("/stav")
async def get_status(request: Request) -> dict:
    """Poslední známý stav myčky z cache (myčku nečte); ``chyba`` = poslední čtení selhalo."""
    a = _appliance(request)
    return {
        "stav": asdict(a.stav) if a.stav else None,
        "raw": a.raw,
        "aktualizovano": a.updated.isoformat(timespec="seconds") if a.updated else None,
        "chyba": a.error,
        "dry_run": a.settings.dry_run,
    }


@router.get("/programy")
async def get_programs() -> list[dict]:
    """Katalog programů s povolenými volbami, jejich českými názvy a volbami, které se vylučují."""
    result = []
    for p in programs.CATALOG.values():
        allowed = programs.allowed_options(p.kod)
        result.append({
            **asdict(p), "delka": p.delka, "spustitelny": p.spustitelny,
            "volby": [{"kod": o, "nazev": programs.OPTIONS[o][2]}
                      for o in programs.OPTIONS if o in allowed],
            "vylucne": sorted(allowed & programs.EXCLUSIVE),
        })
    return result


@router.post("/start")
async def start(body: StartRequest, request: Request) -> dict:
    """Spustí program; vrací výsledek příkazu a odhad konce."""
    a = _appliance(request)
    try:
        program = programs.get_program(body.program)
    except KeyError as exc:
        raise HTTPException(404, f"Neznámý program {body.program}") from exc
    now = a.settings.now()
    try:
        if body.konec is not None:
            delay, end = programs.delay_for_end(
                now, _next_occurrence(now, body.konec), program.delka)
        else:
            delay = body.odlozeni or 0
            end = now + timedelta(minutes=30 * delay + program.delka)
        params = programs.start_params(program.kod, set(body.volby), delay)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {**await _run(a, params, require_idle=True), "odlozeni": delay,
            "odhad_konce": end.isoformat(timespec="minutes")}


@router.post("/cisteni")
async def start_cleaning(request: Request) -> dict:
    """Spustí čisticí cyklus (odvápnění) s prázdnou myčkou; po dokončení se sám zapíše do údržby."""
    a = _appliance(request)
    result = await _run(a, programs.autoclean_params(), require_idle=True)
    if result["odeslano"]:
        a.cleaning_started()
    length = programs.get_program(programs.AUTOCLEAN_PROGRAM).delka
    end = a.settings.now() + timedelta(minutes=length)
    return {**result, "odhad_konce": end.isoformat(timespec="minutes")}


@router.post("/stop")
async def stop(request: Request) -> dict:
    """Zastaví program nebo zruší odložený start (``Reset=1``)."""
    return await _run(_appliance(request), "Reset=1")


@router.post("/nastaveni")
async def set_setting(body: SettingRequest, request: Request) -> dict:
    """Změní jedno nastavení myčky (zvuk, tvrdost vody, pamatovat poslední cyklus)."""
    return await _run(_appliance(request), body.params())


@router.get("/udrzba")
async def get_maintenance(request: Request) -> dict:
    """Počítadla údržby a historie cyklů (nejnovější první).

    Tvrdost vody se bere z posledního stavu myčky; dokud žádný není, 503.
    """
    a = _appliance(request)
    if a.stav is None:
        raise HTTPException(503, "Stav myčky zatím není načtený")
    return {**a.history.maintenance(a.stav.nastaveni.tvrdost),
            "historie": [asdict(c) for c in reversed(a.history.list())]}


@router.post("/udrzba")
async def mark_maintenance(body: MaintenanceRequest, request: Request) -> dict:
    """Zapíše provedenou údržbu a vrátí nová počítadla.

    Bez načteného stavu (neznámá tvrdost) se nic nezapíše – jinak by uživatel viděl
    chybu u uloženého záznamu a klikl znovu.
    """
    a = _appliance(request)
    if a.stav is None:
        raise HTTPException(503, "Stav myčky zatím není načtený – zkuste to za chvíli")
    a.history.mark(body.druh, a.settings.now())
    return await get_maintenance(request)
