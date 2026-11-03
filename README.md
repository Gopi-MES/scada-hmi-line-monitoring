# SCADA / HMI Production Line Monitoring Simulation

A SCADA-style **HMI** for a simulated 3-station bottling line: live station status, trend charts, an alarm banner, alarm acknowledgement and alarm history. The tag and alarm model is designed the way SCADA platforms like Ignition work.

![HMI screenshot](hmi_screenshot.png)

## How it works

```
line_simulator.py  ──writes──►  tags.py (Tag DB + Alarm manager)  ◄──REST──  hmi_app.py (web HMI)
 FILLER → CAPPER → LABELER        • latest value, quality, timestamp           • line overview
 states, counts, motor temps      • trend history buffer                       • trends
 random faults, overheating,      • alarm rules (gt / lt / eq)                 • alarm banner + Ack
 tank level, starvation           • ACTIVE → ACKED → CLEARED → SQLite log      • alarm history
```

### Tags

| Tag | Description |
|---|---|
| `FILLER/CAPPER/LABELER.State` | RUNNING / IDLE (starved) / FAULT |
| `*.Count` | Part counter |
| `*.MotorTemp` | Motor temperature (°C) |
| `LINE.Speed`, `LINE.TankLevel` | Line speed (bpm) and product tank level (%) |

### Alarms

| Alarm | Condition | Priority |
|---|---|---|
| `<STATION>_FAULT` | State = FAULT | HIGH |
| `<STATION>_TEMP_HI` | MotorTemp > 85 °C | MEDIUM |
| `TANK_LOW` | TankLevel < 15 % | MEDIUM |

Every alarm transition (ACTIVE, ACKED, CLEARED) is stored in `alarms.db`, which gives you an alarm journal for troubleshooting.

## Run it

```bash
pip install -r requirements.txt
python hmi_app.py        # open http://localhost:5000
pytest -q
```

## REST API

| Endpoint | Purpose |
|---|---|
| `GET /api/snapshot` | All tag values + active alarms |
| `GET /api/trend/<tag>` | Trend history for a tag |
| `POST /api/ack` `{"alarm": "FILLER_FAULT"}` | Acknowledge an alarm |
| `GET /api/history` | Alarm journal |

## Tech

Python · Flask · SQLite · HTML5 canvas trends · SCADA concepts (tags, quality, alarm priorities, acknowledgement)
