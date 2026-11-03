# Running this line on Ignition (Maker Edition)

This guide connects the simulated line to **Inductive Automation Ignition** over OPC-UA and builds the HMI in **Perspective**. When you're done, the tags, alarms, history and screens all run on Ignition.

> Ignition Maker Edition is free for personal, non-commercial use. Ignition Standard Edition also runs free in 2-hour trial mode, which resets as often as you like.

## 0. What you need

- Ignition 8.1 or 8.3 (Maker Edition or trial) installed locally
- Python 3.10+ with `pip install -r requirements.txt`
- Docker, for PostgreSQL (tag history and alarm journal)

## 1. Start the OPC-UA server and database

```bash
python opcua_server.py          # opc.tcp://0.0.0.0:4841/linesim/
docker compose up -d            # PostgreSQL on localhost:5432
```

## 2. Connect Ignition to the OPC-UA server

Gateway webpage (`http://localhost:8088`) → **Config → OPC Client → OPC Connections → Create new OPC Connection**:

| Setting | Value |
|---|---|
| Type | OPC UA |
| Endpoint URL | `opc.tcp://localhost:4841/linesim/` |
| Security policy | None |
| **Name** | `LineSim` (must match, because the tag file uses this server name) |

Check that the status shows **Connected**. In the Designer's **OPC Browser** you should see `Objects → Line1 → FILLER / CAPPER / LABELER / LINE`.

## 3. Add the database (history + alarm journal)

1. **Config → Databases → Connections → Create new:** PostgreSQL, `jdbc:postgresql://localhost:5432/linehistory`, user/password `ignition`, named `LineDB`.
2. **Tag history:**
   - Ignition 8.1: a SQL history provider is created automatically for `LineDB`. Rename it to `LineHistory`, or change `historyProvider` in `ignition_tags.json`.
   - Ignition 8.3: create a historian named `LineHistory` that stores to `LineDB`, or use the built-in core historian and update `historyProvider` to match.
3. **Alarm journal:** **Config → Alarming → Journal → Create new** → Database journal, data source `LineDB`, name `LineJournal`.

## 4. Import the tags

Designer → **Tag Browser** → `default` provider → **⋮ → Import Tags** → select `ignition_tags.json`.

This creates:

```
Line1/
  FILLER/  State (String) · StateCode (Int4, alarm: Equality 2 → HIGH "FILLER faulted")
           Count (Int4, history) · MotorTemp (Float8, alarm: > 85 °C MEDIUM, history)
  CAPPER/  … same …
  LABELER/ … same …
  LINE/    Speed (Float8, history) · TankLevel (Float8, alarm: < 15 % MEDIUM, history)
```

All values should show **Good** quality and update every second. StateCode values are `0 = IDLE`, `1 = RUNNING`, `2 = FAULT`.

## 5. Build the Perspective screens

Create a Perspective project called `LineSim`.

### View 1: `Overview` (page URL `/`)

Root: **Flex Container**, direction `column`.

1. **Header (Flex row):** a Label `LINE 1 – Bottling`, then two Labels bound to tags:
   - `Speed: {value} bpm` → Tag binding `[default]Line1/LINE/Speed`, with an expression transform `"Speed: " + numberFormat({value}, "0") + " bpm"`
   - `Tank: {value} %` → `[default]Line1/LINE/TankLevel`
2. **Station cards (Flex row with 3 children):** for each station, a Flex column containing:
   - Label `FILLER`
   - Label with **text** bound to `[default]Line1/FILLER/State`
   - **style.backgroundColor** bound to `[default]Line1/FILLER/StateCode` with a **Map** transform: `0 → #F1C40F`, `1 → #2ECC71`, `2 → #E74C3C`
   - Label `Count: {Line1/FILLER/Count}`
   - **Linear Scale** or **Cylindrical Tank** for `MotorTemp` (0–120 °C)

   Tip: build one card as an embedded view with a `station` parameter and use indirect tag bindings (`[default]Line1/{view.params.station}/State`). Then reuse it three times, which is how real Ignition projects are built.
3. **Cylindrical Tank** component → `value` bound to `[default]Line1/LINE/TankLevel`.

### View 2: `Trends` (page URL `/trends`)

- **Power Chart** component. Add pens for `Line1/*/MotorTemp` and `Line1/LINE/TankLevel` from the `LineHistory` provider, with the range set to the last 15 minutes in realtime mode.

### View 3: `Alarms` (page URL `/alarms`)

- **Alarm Status Table** (Active tab): filter `source` like `*Line1*`. Operators can acknowledge alarms from here.
- **Alarm Journal Table**: journal `LineJournal`, last 24 hours.

### Navigation

Add a **docked top view** with a **Horizontal Menu** linking `/`, `/trends` and `/alarms`.

## 6. Verify

- Open `http://localhost:8088/data/perspective/client/LineSim`.
- Within a few minutes the simulator produces random faults and overheating, so you should see:
  - a station card turn red, with a HIGH alarm in the Alarm Status Table
  - acknowledging it in the table, then watching it clear when the station recovers
  - the event showing up in the Alarm Journal and the trend lines in the Power Chart

## 7. Add it to this repo

1. Designer → **File → Export** → export the `LineSim` project as a zip and add it to the repo.
2. Take screenshots of the Overview, Trends and Alarms views and add them to the README.
3. Export the tags again (Tag Browser → Export) if you changed anything.
