"""Testy převodu surového stavu na čitelný na skutečných logech."""

from ovladac.services.model import interpret


def test_running_p2_with_options(p2_log):
    s = interpret(p2_log[0])
    assert (s.stav, s.faze, s.program, s.zbyva_min) == ("beh", "Mytí", "P2", 134)
    assert s.program_nazev == "Intenzivní"
    assert s.volby == ["extradry", "tab"]
    assert s.dalkove_ovladani and not s.varovani
    assert s.nastaveni.tvrdost == 2 and not s.nastaveni.zvuk


def test_phases_follow_r2(p2_log):
    phases = {interpret(r).faze for r in p2_log if r["StatoDWash"] == "3"}
    assert phases == {"Mytí", "Oplach", "Sušení"}


def test_finished_has_no_phase(p2_log):
    s = interpret(p2_log[-1])
    assert (s.stav, s.faze) == ("konec", "")
    assert s.dvirka_otevrena


def test_panel_selection_without_remote(panel_log):
    s = interpret(panel_log[-1])
    assert (s.stav, s.program, s.zbyva_min) == ("vyber", "P12", 5)
    assert not s.dalkove_ovladani and s.volby == []


def test_delayed_start_and_warnings(p2_log):
    raw = {**p2_log[0], "DelayStart": "90", "MissSalt": "1", "CodiceErrore": "E5"}
    s = interpret(raw)
    assert (s.stav, s.odlozeni_min) == ("odlozeno", 90)
    assert s.varovani == ["Doplňte sůl", "Chyba myčky E5"]
