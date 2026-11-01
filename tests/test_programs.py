"""Testy katalogu programů: povolené volby, vylučování, „konec v“, příkaz startu."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from ovladac.routers.api import _next_occurrence
from ovladac.services.programs import (allowed_options, autoclean_params,
                                       delay_for_end, start_params,
                                       validate_options)


def test_allowed_options_from_mask():
    assert allowed_options("P2") == {"extradry", "halfload", "eco", "tab"}
    assert allowed_options("P19") == {"eco", "tab"}
    assert allowed_options("P12") == {"tab"}


@pytest.mark.parametrize("opts", [{"extradry", "eco"}, {"halfload", "eco"},
                                  {"extradry", "halfload"}])
def test_exclusive_options_rejected(opts):
    with pytest.raises(ValueError, match="kombinovat"):
        validate_options("P2", opts)


def test_tab_combines_freely_and_mask_is_enforced():
    validate_options("P2", {"extradry", "tab"})
    with pytest.raises(ValueError, match="nepovoluje"):
        validate_options("P12", {"eco"})


def test_delay_for_end_rounds_to_half_hours():
    now = datetime(2026, 11, 1, 22, 0).astimezone()
    # P2 130 min, konec v 6:00 → čekat 5 h 50 min → 12 půlhodin, konec 6:10
    half_hours, end = delay_for_end(now, now + timedelta(hours=8), 130)
    assert half_hours == 12
    assert end == now + timedelta(hours=8, minutes=10)


def test_delay_for_end_rejects_impossible():
    now = datetime(2026, 11, 1, 22, 0).astimezone()
    with pytest.raises(ValueError, match="nestihne"):
        delay_for_end(now, now + timedelta(minutes=60), 130)
    with pytest.raises(ValueError, match="24 hodin"):
        delay_for_end(now, now + timedelta(hours=30), 130)


def test_start_params_matches_verified_command():
    # Přesně tento příkaz spustil P12 v pokusu P8.
    assert start_params("P12", set()) == (
        "DelayStart=0&ExtraDry=0&OpenDoorOpt=0&TreinUno=0&Program=P12"
        "&MetaCarico=0&OpzProg=0&w1=4&StartStop=1&Eco=0")
    assert "ExtraDry=1" in start_params("P2", {"extradry", "tab"}, 4)
    assert "OpzProg=9" in start_params("P2", {"extradry", "tab"}, 4)


def test_app_only_program_not_startable():
    with pytest.raises(ValueError, match="neumíme"):
        start_params("P9", set())


def test_delay_for_end_across_dst_change():
    prague = ZoneInfo("Europe/Prague")
    # Noc na 25. 10. 2026 má o hodinu víc (změna na zimní čas ve 3:00).
    now = datetime(2026, 10, 24, 22, 0, tzinfo=prague)
    konec = _next_occurrence(now, time(6, 0))
    assert (konec.day, konec.hour, konec.minute) == (25, 6, 0)
    half_hours, end = delay_for_end(now, konec, 130)
    assert half_hours == 14  # skutečně uběhne 9 h, ne 8 h
    assert (end.day, end.hour, end.minute) == (25, 6, 10)


def test_autoclean_params_like_app():
    assert autoclean_params() == (
        "DelayStart=0&ExtraDry=0&OpenDoorOpt=0&TreinUno=0&Program=P2"
        "&MetaCarico=0&OpzProg=0&w1=1&StartStop=1&Eco=0&w3=H_2")
