"""Testy detekce cyklů (přehrání skutečného logu) a počítadel údržby."""

from datetime import timedelta

from ovladac.services.history import Cycle, CycleTracker, History
from ovladac.services.model import interpret


def replay(rows):
    """Přehraje (čas, řádek) přes tracker, vrátí seznam událostí."""
    tracker = CycleTracker()
    events = [tracker.update(interpret(raw), ts) for ts, raw in rows]
    return [e for e in events if e]


def test_replay_p2_log_gives_one_finished_cycle(p2_timed):
    events = replay(p2_timed)
    assert [e.kind for e in events] == ["start", "konec"]
    c = events[1].cycle
    assert (c.program, c.volby, c.vysledek) == ("P2", ["extradry", "tab"], "dokonceno")
    assert 131 <= c.delka_min <= 133
    assert c.zbyva_na_startu == 134
    assert set(c.faze) == {"Mytí", "Oplach", "Sušení"}
    assert sum(c.faze.values()) == c.delka_min


def test_reset_during_run_is_cancelled(p2_timed):
    (t0, running), (t1, _) = p2_timed[0], p2_timed[1]
    reset = {**running, "StatoDWash": "1"}
    events = replay([(t0, running), (t1, {**running, "StatoDWash": "4"}),
                     (t1 + timedelta(minutes=3), reset)])
    assert [e.kind for e in events] == ["start", "zruseno"]
    assert events[1].cycle.vysledek == "zruseno"


def test_waiting_delayed_start_is_not_a_cycle(p2_timed):
    t0, running = p2_timed[0]
    waiting = {**running, "DelayStart": "60"}
    assert replay([(t0, waiting), (t0 + timedelta(minutes=1), {**waiting, "StatoDWash": "1"})]) == []


def _cycle(result="dokonceno"):
    return Cycle(start="2026-11-01T02:30:10+01:00", konec="2026-11-01T04:42:00+01:00",
                 program="P2", volby=[], delka_min=132, zbyva_na_startu=134, vysledek=result)


def test_history_roundtrip_and_maintenance(tmp_path, p2_timed):
    h = History(tmp_path / "historie.jsonl")
    for _ in range(3):
        h.append(_cycle())
    h.append(_cycle("zruseno"))
    assert len(h.list()) == 4 and h.list()[0] == _cycle()

    m = h.maintenance(hardness=2)
    assert (m["filtr_zbyva"], m["odvapneni_zbyva"]) == (97, 97)

    h.mark("filtr", p2_timed[0][0])
    h.append(_cycle())
    m = h.maintenance(hardness=5)
    assert (m["filtr_zbyva"], m["odvapneni_zbyva"]) == (99, 81)
    assert m["filtr_posledni"].startswith("2026-11-01T02:30:10")
    assert m["odvapneni_posledni"] is None


def test_door_opened_while_waiting_is_not_a_cycle(p2_timed):
    t0, running = p2_timed[0]
    waiting = {**running, "DelayStart": "60"}
    rows = [(t0, waiting), (t0 + timedelta(minutes=1), {**waiting, "StatoDWash": "4"}),
            (t0 + timedelta(minutes=2), waiting)]
    assert replay(rows) == []
