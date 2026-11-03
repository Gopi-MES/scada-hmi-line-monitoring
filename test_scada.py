from line_simulator import LineSimulator, configure
from tags import TagDB


def make(tmp_path):
    db = TagDB(str(tmp_path / "a.db"))
    configure(db)
    return db


def test_alarm_lifecycle(tmp_path):
    db = make(tmp_path)
    db.write("FILLER.MotorTemp", 95.0)
    assert "FILLER_TEMP_HI" in db.snapshot()["alarms"][0]["name"]
    db.ack("FILLER_TEMP_HI")
    assert db.snapshot()["alarms"][0]["acked"]
    db.write("FILLER.MotorTemp", 60.0)
    assert not db.snapshot()["alarms"]
    events = [e["event"] for e in db.history()]
    assert events == ["CLEARED", "ACKED", "ACTIVE"]


def test_simulator_runs(tmp_path):
    db = make(tmp_path)
    sim = LineSimulator(db, seed=1)
    for _ in range(200):
        sim.step()
    snap = db.snapshot()["tags"]
    assert snap["FILLER.Count"]["value"] > 0
    assert len(db.trend("LINE.TankLevel")) == 200
    assert any(e["event"] == "ACTIVE" for e in db.history(500))   # some alarms happened
