"""Simulated 3-station bottling line feeding the tag database.

Stations: FILLER -> CAPPER -> LABELER. Each has a state (RUNNING/IDLE/FAULT),
part counter and motor temperature. Faults happen at random and auto-reset after
a repair time; the downstream station starves when upstream is faulted.
"""
import random
import threading
import time

STATIONS = ["FILLER", "CAPPER", "LABELER"]


def configure(db):
    for s in STATIONS:
        db.define(f"{s}.State", value="IDLE")
        db.define(f"{s}.Count", "pcs", 0)
        db.define(f"{s}.MotorTemp", "°C", 40.0)
        db.add_alarm(f"{s}_FAULT", f"{s}.State", "eq", "FAULT", "HIGH", f"{s} faulted")
        db.add_alarm(f"{s}_TEMP_HI", f"{s}.MotorTemp", "gt", 85.0, "MEDIUM", f"{s} motor temperature high")
    db.define("LINE.Speed", "bpm", 0.0)
    db.define("LINE.TankLevel", "%", 80.0)
    db.add_alarm("TANK_LOW", "LINE.TankLevel", "lt", 15.0, "MEDIUM", "Product tank level low")


class LineSimulator(threading.Thread):
    def __init__(self, db, period=1.0, seed=None):
        super().__init__(daemon=True)
        self.db, self.period = db, period
        self.rng = random.Random(seed)
        self.fault_timer = {s: 0 for s in STATIONS}
        self.temp = {s: 40.0 for s in STATIONS}
        self.counts = {s: 0 for s in STATIONS}
        self.tank = 80.0

    def step(self):
        upstream_ok = self.tank > 5
        speed = 0.0
        for s in STATIONS:
            if self.fault_timer[s] > 0:
                self.fault_timer[s] -= 1
                state = "FAULT"
            elif self.rng.random() < 0.01:
                self.fault_timer[s] = self.rng.randint(5, 15)
                state = "FAULT"
            elif not upstream_ok:
                state = "IDLE"          # starved
            else:
                state = "RUNNING"

            if state == "RUNNING":
                made = self.rng.randint(1, 3)
                self.counts[s] += made
                speed = max(speed, made * 60 / self.period)
                self.temp[s] += self.rng.uniform(-0.5, 1.2) + (60 - self.temp[s]) * 0.05
                if self.rng.random() < 0.01:
                    self.temp[s] += 30          # overheating event
            else:
                self.temp[s] += (35 - self.temp[s]) * 0.08
            upstream_ok = upstream_ok and state == "RUNNING"

            self.db.write(f"{s}.State", state)
            self.db.write(f"{s}.Count", self.counts[s])
            self.db.write(f"{s}.MotorTemp", round(self.temp[s], 1))

        self.tank -= 0.6 if speed else 0
        if self.tank < 10 or self.rng.random() < 0.02:
            self.tank = min(100.0, self.tank + 40)      # refill
        self.db.write("LINE.TankLevel", round(self.tank, 1))
        self.db.write("LINE.Speed", round(speed, 1))

    def run(self):
        while True:
            self.step()
            time.sleep(self.period)
