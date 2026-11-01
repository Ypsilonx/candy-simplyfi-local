"""Testy správce myčky bez sítě: síťové funkce jsou nahrazené v modulu appliance."""

import asyncio
import http.client

import pytest

from ovladac.config import Settings
from ovladac.services import appliance as appliance_mod
from ovladac.services.appliance import Appliance, ApplianceBusy
from ovladac.services.history import History


@pytest.fixture
def make(tmp_path, monkeypatch, panel_log, p2_log):
    """Vytvoří správce v ostrém režimu; ``reads`` = co postupně vrací čtení (výjimka se vyhodí)."""
    def factory(reads):
        it = iter(reads)

        def fake_read(ip, key, timeout):
            item = next(it)
            if isinstance(item, Exception):
                raise item
            return item

        monkeypatch.setattr(appliance_mod, "read_status", fake_read)
        monkeypatch.setattr(appliance_mod, "send_params", lambda *a: '{"response":"SUCCESS"}')
        settings = Settings(_env_file=None, candy_ip="127.0.0.1", candy_key="x" * 16,
                            dry_run=False, verify_seconds=0, data_dir=tmp_path)
        return Appliance(settings, History(settings.history_path))
    idle = {**panel_log[-1], "StatoWiFi": "1"}
    return factory, idle, p2_log[0]


def test_refresh_survives_truncated_response(make):
    factory, idle, _ = make
    a = factory([http.client.IncompleteRead(b""), idle])
    asyncio.run(a.refresh())
    assert a.error and a.stav is None
    asyncio.run(a.refresh())
    assert a.error is None and a.stav.stav == "vyber"


def test_failed_verification_still_reports_sent(make):
    factory, idle, _ = make
    a = factory([idle, TimeoutError("timed out")])
    res = asyncio.run(a.command("Reset=1"))
    assert res.odeslano and res.varovani and res.zmeny is None


def test_start_refused_when_fresh_read_shows_running(make):
    factory, idle, running = make
    a = factory([idle, running])
    asyncio.run(a.refresh())  # cache: připraveno
    with pytest.raises(ApplianceBusy):
        asyncio.run(a.command("StartStop=1", require_idle=True))


def _run_cycle(a, n):
    """Zavolá refresh n-krát (každé čtení = jeden řádek z ``reads``)."""
    for _ in range(n):
        asyncio.run(a.refresh())


def test_r9_alone_is_not_cleaning(make):
    """r9=H_2 zůstává po čištění i dál – bez tlačítka ovladače je P2 běžné mytí."""
    factory, idle, running = make
    done = {**running, "StatoDWash": "5", "r2": "5"}
    a = factory([idle, {**running, "r9": "H_2"}, {**done, "r9": "H_2"}])
    _run_cycle(a, 3)
    assert not a.history.list()[0].cisteni
    assert a.history.maintenance(2)["odvapneni_posledni"] is None


def test_cleaning_started_from_button(make):
    factory, idle, running = make
    done = {**running, "StatoDWash": "5", "r2": "5"}
    a = factory([idle, running, done])
    _run_cycle(a, 2)
    a.cleaning_started()
    assert a.cleaning
    _run_cycle(a, 1)
    assert a.history.list()[0].cisteni
    assert not a.cleaning
    assert a.history.maintenance(2)["odvapneni_zbyva"] == 100


def test_normal_cycle_does_not_mark_descaling(make):
    factory, idle, running = make
    a = factory([idle, running, {**running, "StatoDWash": "5"}])
    _run_cycle(a, 3)
    assert not a.history.list()[0].cisteni
    assert a.history.maintenance(2)["odvapneni_posledni"] is None
