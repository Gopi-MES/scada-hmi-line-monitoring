"""Web HMI: line overview, live trends, alarm banner/summary with acknowledge,
and alarm history. Run: python hmi_app.py  ->  http://localhost:5000
"""
from flask import Flask, jsonify, request

from line_simulator import LineSimulator, STATIONS, configure
from tags import TagDB

app = Flask(__name__)
db = TagDB()
configure(db)


@app.get("/api/snapshot")
def snapshot():
    return jsonify(db.snapshot())


@app.get("/api/trend/<path:tag>")
def trend(tag):
    return jsonify(db.trend(tag))


@app.post("/api/ack")
def ack():
    db.ack(request.json["alarm"])
    return jsonify(ok=True)


@app.get("/api/history")
def history():
    return jsonify(db.history())


@app.get("/")
def index():
    return PAGE.replace("__STATIONS__", ",".join(f'"{s}"' for s in STATIONS))


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Line 1 HMI</title>
<style>
body{margin:0;font-family:Segoe UI,Arial;background:#1e2329;color:#dde}
header{background:#111;padding:10px 20px;display:flex;justify-content:space-between}
#banner{padding:8px 20px;font-weight:600}
.ok{background:#1f3b2b}.bad{background:#8b1d1d;animation:b 1s infinite}@keyframes b{50%{opacity:.7}}
.wrap{padding:16px 20px;display:grid;gap:16px}
.line{display:flex;gap:16px;align-items:center}
.st{flex:1;background:#2a3038;border-radius:8px;padding:12px;border-left:8px solid #666}
.RUNNING{border-color:#2ecc71}.IDLE{border-color:#f1c40f}.FAULT{border-color:#e74c3c}
.arrow{font-size:28px;color:#678}
.big{font-size:26px;font-weight:700}
.card{background:#2a3038;border-radius:8px;padding:12px}
canvas{width:100%;height:160px;background:#20252b}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:4px 6px;border-bottom:1px solid #3a414a;text-align:left}
.HIGH{color:#ff6b6b}.MEDIUM{color:#f5b041}button{background:#456;color:#fff;border:0;padding:3px 10px;border-radius:4px;cursor:pointer}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
</style></head><body>
<header><b>LINE 1 – Bottling</b><span>Speed: <b id="speed">-</b> bpm · Tank: <b id="tank">-</b> %</span><span id="clock"></span></header>
<div id="banner" class="ok">No active alarms</div>
<div class="wrap">
 <div class="line" id="line"></div>
 <div class="grid2">
  <div class="card"><b>Motor temperature trend (°C)</b><canvas id="trend" width="600" height="160"></canvas></div>
  <div class="card"><b>Tank level trend (%)</b><canvas id="tank_trend" width="600" height="160"></canvas></div>
 </div>
 <div class="grid2">
  <div class="card"><b>Active alarms</b><table id="active"></table></div>
  <div class="card"><b>Alarm history</b><table id="hist"></table></div>
 </div>
</div>
<script>
const ST=[__STATIONS__], COLORS=["#5dade2","#f5b041","#af7ac5"];
const fmt=t=>new Date(t*1000).toLocaleTimeString();
async function j(u,o){return (await fetch(u,o)).json()}
function draw(id,series,lo,hi){const c=document.getElementById(id),x=c.getContext("2d");x.clearRect(0,0,c.width,c.height);
 series.forEach((s,i)=>{if(!s.length)return;const t0=s[0][0],t1=s[s.length-1][0]||t0+1;x.strokeStyle=COLORS[i];x.beginPath();
  s.forEach(([t,v],k)=>{const px=(t-t0)/(t1-t0||1)*c.width,py=c.height-(v-lo)/(hi-lo)*c.height;k?x.lineTo(px,py):x.moveTo(px,py)});x.stroke()});}
async function ack(a){await j("/api/ack",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({alarm:a})});tick()}
async function tick(){
 const s=await j("/api/snapshot"),T=s.tags;
 document.getElementById("clock").textContent=new Date().toLocaleTimeString();
 document.getElementById("speed").textContent=T["LINE.Speed"].value;
 document.getElementById("tank").textContent=T["LINE.TankLevel"].value;
 document.getElementById("line").innerHTML=ST.map((n,i)=>`${i?'<span class="arrow">➜</span>':''}<div class="st ${T[n+".State"].value}">
  <b>${n}</b><div class="big">${T[n+".State"].value}</div>Count: ${T[n+".Count"].value} · Motor: ${T[n+".MotorTemp"].value} °C</div>`).join("");
 const un=s.alarms.filter(a=>!a.acked), b=document.getElementById("banner");
 b.className=un.length?"bad":"ok"; b.textContent=un.length?`⚠ ${un.length} unacknowledged alarm(s): ${un[0].message}`:(s.alarms.length?`${s.alarms.length} active alarm(s), all acknowledged`:"No active alarms");
 document.getElementById("active").innerHTML="<tr><th>Time</th><th>Priority</th><th>Message</th><th></th></tr>"+s.alarms.map(a=>
  `<tr><td>${fmt(a.ts)}</td><td class="${a.priority}">${a.priority}</td><td>${a.message} (${a.value})</td><td>${a.acked?"ACKED":`<button onclick="ack('${a.name}')">Ack</button>`}</td></tr>`).join("");
 const h=await j("/api/history");
 document.getElementById("hist").innerHTML="<tr><th>Time</th><th>Event</th><th>Alarm</th><th>Value</th></tr>"+h.slice(0,12).map(e=>
  `<tr><td>${fmt(e.ts)}</td><td>${e.event}</td><td class="${e.priority}">${e.message}</td><td>${e.value}</td></tr>`).join("");
 draw("trend",await Promise.all(ST.map(n=>j("/api/trend/"+n+".MotorTemp"))),30,120);
 draw("tank_trend",[await j("/api/trend/LINE.TankLevel")],0,100);
}
setInterval(tick,1000);tick();
</script></body></html>"""


if __name__ == "__main__":
    LineSimulator(db).start()
    app.run(host="0.0.0.0", port=5000)
