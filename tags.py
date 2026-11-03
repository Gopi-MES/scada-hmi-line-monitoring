"""Tag database + alarm manager (the 'SCADA core').

Tags hold the latest value/quality/timestamp. Alarm definitions are evaluated on
every tag write; alarms go ACTIVE -> (ACKED) -> CLEARED and are logged to SQLite.
"""
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Tag:
    name: str
    value: object = None
    unit: str = ""
    quality: str = "GOOD"
    ts: float = 0.0
    history: deque = field(default_factory=lambda: deque(maxlen=300))  # (ts, value) for trends


@dataclass
class AlarmDef:
    name: str
    tag: str
    condition: str          # "gt", "lt", "eq"
    setpoint: object
    priority: str           # HIGH / MEDIUM / LOW
    message: str


class TagDB:
    def __init__(self, db_path="alarms.db"):
        self.tags: dict[str, Tag] = {}
        self.alarm_defs: list[AlarmDef] = []
        self.active: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.db = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.db.execute("""CREATE TABLE IF NOT EXISTS alarm_history (
            id INTEGER PRIMARY KEY, alarm TEXT, priority TEXT, message TEXT, value TEXT,
            event TEXT, ts REAL)""")

    def define(self, name, unit="", value=None):
        self.tags[name] = Tag(name, value, unit)

    def add_alarm(self, *args):
        self.alarm_defs.append(AlarmDef(*args))

    def write(self, name, value, quality="GOOD"):
        with self.lock:
            t = self.tags[name]
            t.value, t.quality, t.ts = value, quality, time.time()
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                t.history.append((t.ts, value))
            self._evaluate(name)

    def _evaluate(self, tag_name):
        for a in (a for a in self.alarm_defs if a.tag == tag_name):
            v = self.tags[tag_name].value
            hit = {"gt": lambda: v > a.setpoint, "lt": lambda: v < a.setpoint,
                   "eq": lambda: v == a.setpoint}[a.condition]()
            if hit and a.name not in self.active:
                self.active[a.name] = {"name": a.name, "priority": a.priority, "message": a.message,
                                       "value": v, "ts": time.time(), "acked": False}
                self._log(a, v, "ACTIVE")
            elif not hit and a.name in self.active:
                self.active.pop(a.name)
                self._log(a, v, "CLEARED")

    def ack(self, alarm_name):
        with self.lock:
            if alarm_name in self.active:
                self.active[alarm_name]["acked"] = True
                a = next(d for d in self.alarm_defs if d.name == alarm_name)
                self._log(a, self.active[alarm_name]["value"], "ACKED")

    def _log(self, a, v, event):
        self.db.execute("INSERT INTO alarm_history (alarm, priority, message, value, event, ts)"
                        " VALUES (?,?,?,?,?,?)", (a.name, a.priority, a.message, str(v), event, time.time()))

    def history(self, limit=50):
        cur = self.db.execute("SELECT alarm, priority, message, value, event, ts FROM alarm_history"
                              " ORDER BY id DESC LIMIT ?", (limit,))
        cols = ["alarm", "priority", "message", "value", "event", "ts"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def snapshot(self):
        with self.lock:
            return {
                "tags": {n: {"value": t.value, "unit": t.unit, "quality": t.quality, "ts": t.ts}
                         for n, t in self.tags.items()},
                "alarms": sorted(self.active.values(), key=lambda a: a["ts"], reverse=True),
            }

    def trend(self, name):
        with self.lock:
            return list(self.tags[name].history)
