"""ARCclaude App — beginner-friendly local web UI (`arcclaude app`).

Runs a localhost server and opens the browser. The user types plain English;
the agent core, ArcPy worker, provider calls, and Live Link detection all
happen automatically in the background. No terminal knowledge needed after
launch. Uses only packages ARCclaude already depends on (starlette/uvicorn/
sse-starlette ship with the MCP SDK).
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import webbrowser

import anyio
import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .agent import AgentSession, load_config, resolve_provider, save_config
from .live import listener_alive, paste_line

PORT = 8517

SESSION = AgentSession()
EVENTS: "queue.Queue[dict]" = queue.Queue()
BUSY = threading.Event()


def _pro_running() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ArcGISPro.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return "ArcGISPro.exe" in out
    except Exception:
        return False


async def home(_request):
    return HTMLResponse(PAGE)


async def status(_request):
    cfg = SESSION.cfg
    return JSONResponse({
        "configured": bool(resolve_provider(cfg)),
        "provider": resolve_provider(cfg),
        "model": SESSION.model if resolve_provider(cfg) else None,
        "engine": SESSION.bridge.alive,
        "engine_info": SESSION.bridge.ready_info.get("license"),
        "pro_running": _pro_running(),
        "live_link": listener_alive(),
        "busy": BUSY.is_set(),
    })


async def set_config(request):
    global SESSION
    body = await request.json()
    cfg = load_config()
    for key in ("provider", "api_key", "model", "base_url"):
        if body.get(key) is not None:
            cfg[key] = body[key] or None
    save_config(cfg)
    old_bridge = SESSION.bridge
    SESSION = AgentSession(cfg=cfg, bridge=old_bridge)  # keep the warm engine
    return JSONResponse({"ok": True, "provider": resolve_provider(cfg)})


async def live_line(_request):
    return JSONResponse({"line": paste_line(), "active": listener_alive()})


async def send(request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
    if BUSY.is_set():
        return JSONResponse({"ok": False, "error": "busy"}, status_code=409)
    BUSY.set()

    def work():
        try:
            SESSION.run_turn(text, EVENTS.put)
        except Exception as exc:  # never leave the UI hanging
            EVENTS.put({"kind": "error", "message": f"Unexpected error: {exc}"})
            EVENTS.put({"kind": "done"})
        finally:
            BUSY.clear()

    threading.Thread(target=work, daemon=True).start()
    return JSONResponse({"ok": True})


async def events(_request):
    async def gen():
        while True:
            ev = await anyio.to_thread.run_sync(EVENTS.get)
            yield {"data": json.dumps(ev, ensure_ascii=False)}
    return EventSourceResponse(gen())


app = Starlette(routes=[
    Route("/", home),
    Route("/api/status", status),
    Route("/api/config", set_config, methods=["POST"]),
    Route("/api/liveline", live_line),
    Route("/api/send", send, methods=["POST"]),
    Route("/api/events", events),
])


def main(port: int = PORT) -> None:
    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"ARCclaude App running at http://127.0.0.1:{port}  (Ctrl+C to quit)")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


# --------------------------------------------------------------------------
# The page. One file, no build step, no CDN — works offline.
# --------------------------------------------------------------------------

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>ARCclaude</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#0f1419;--panel:#1a2129;--panel2:#232c36;--text:#e6edf3;--dim:#8b98a5;
--accent:#4fa3ff;--green:#3fb950;--red:#f85149;--amber:#d29922;font-size:15px}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
display:flex;flex-direction:column;height:100vh}
header{display:flex;align-items:center;gap:14px;padding:10px 18px;background:var(--panel);
border-bottom:1px solid #2d3742}
header h1{font-size:1.05rem;font-weight:600}
header h1 span{color:var(--accent)}
.dots{display:flex;gap:14px;margin-left:auto;font-size:.8rem;color:var(--dim)}
.dot{display:flex;align-items:center;gap:5px}
.dot i{width:9px;height:9px;border-radius:50%;background:#555;display:inline-block}
.dot i.on{background:var(--green)} .dot i.warn{background:var(--amber)}
button{background:var(--panel2);color:var(--text);border:1px solid #2d3742;border-radius:8px;
padding:7px 14px;cursor:pointer;font-size:.85rem}
button:hover{border-color:var(--accent)}
button.primary{background:var(--accent);border-color:var(--accent);color:#04121f;font-weight:600}
#chat{flex:1;overflow-y:auto;padding:22px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:72%;padding:10px 14px;border-radius:12px;white-space:pre-wrap;line-height:1.45}
.user{align-self:flex-end;background:#1d4f82}
.ai{align-self:flex-start;background:var(--panel2)}
.chip{align-self:flex-start;font-size:.78rem;color:var(--dim);background:var(--panel);
border:1px solid #2d3742;border-radius:99px;padding:3px 12px}
.chip.ok{border-color:var(--green)} .chip.bad{border-color:var(--red)}
.err{align-self:flex-start;background:#3d1d20;border:1px solid var(--red)}
.hello{align-self:center;color:var(--dim);text-align:center;max-width:520px;margin-top:8vh}
.hello b{color:var(--text)}
footer{padding:12px 18px;background:var(--panel);border-top:1px solid #2d3742;display:flex;gap:10px}
textarea{flex:1;background:var(--panel2);border:1px solid #2d3742;border-radius:10px;color:var(--text);
padding:10px 12px;resize:none;font:inherit;height:46px}
textarea:focus{outline:1px solid var(--accent)}
.modal{position:fixed;inset:0;background:#000a;display:none;align-items:center;justify-content:center}
.modal.show{display:flex}
.card{background:var(--panel);border:1px solid #2d3742;border-radius:14px;padding:22px;width:430px;
display:flex;flex-direction:column;gap:10px}
.card h2{font-size:1rem} .card label{font-size:.8rem;color:var(--dim)}
.card input,.card select{background:var(--panel2);border:1px solid #2d3742;border-radius:8px;
color:var(--text);padding:8px 10px;font:inherit;width:100%}
.card code{background:var(--panel2);padding:8px;border-radius:8px;font-size:.75rem;word-break:break-all;
display:block}
.spin{display:inline-block;width:12px;height:12px;border:2px solid var(--dim);border-top-color:var(--accent);
border-radius:50%;animation:r 0.8s linear infinite;vertical-align:-2px}
@keyframes r{to{transform:rotate(360deg)}}
</style></head><body>
<header>
  <h1>ARC<span>claude</span></h1>
  <div class="dots">
    <span class="dot"><i id="d-eng"></i>Engine</span>
    <span class="dot"><i id="d-pro"></i>ArcGIS Pro</span>
    <span class="dot"><i id="d-live"></i>Live Link</span>
  </div>
  <button onclick="showLive()">Connect Pro</button>
  <button onclick="showSettings()">Settings</button>
</header>
<div id="chat">
  <div class="hello" id="hello">
    <b>Welcome to ARCclaude</b><br><br>
    Type what you want in plain English — like<br>
    <i>"make a shapefile of the 3 biggest parks in Vancouver"</i><br>
    <i>"describe the data in my project's geodatabase"</i><br><br>
    Everything runs automatically in the background. The first request takes
    about a minute while ArcGIS wakes up; after that it's fast.
  </div>
</div>
<footer>
  <textarea id="box" placeholder="Ask ARCclaude to do GIS work…"></textarea>
  <button class="primary" id="sendBtn" onclick="send()">Send</button>
</footer>

<div class="modal" id="settings"><div class="card">
  <h2>AI provider</h2>
  <label>Provider</label>
  <select id="s-provider" onchange="provChange()">
    <option value="anthropic">Anthropic (Claude)</option>
    <option value="openai">OpenAI-compatible (OpenAI / Gemini / Groq / Ollama)</option>
  </select>
  <label>API key</label><input id="s-key" type="password" placeholder="sk-ant-... (or blank for local Ollama)">
  <label>Model</label><input id="s-model" placeholder="claude-sonnet-5">
  <div id="s-baserow" style="display:none"><label>Base URL (Ollama: http://localhost:11434/v1)</label>
  <input id="s-base" placeholder="leave blank for api.openai.com"></div>
  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:6px">
    <button onclick="hide('settings')">Cancel</button>
    <button class="primary" onclick="saveSettings()">Save</button>
  </div>
</div></div>

<div class="modal" id="live"><div class="card">
  <h2>Connect your open ArcGIS Pro</h2>
  <p style="font-size:.85rem;color:var(--dim)">In ArcGIS Pro: <b>View ribbon → Python window</b>,
  paste this line, press Enter. Then leave that window alone — stop anytime from here.</p>
  <code id="liveline">…</code>
  <div style="display:flex;gap:8px;justify-content:flex-end">
    <button onclick="copyLine()">Copy line</button>
    <button class="primary" onclick="hide('live')">Done</button>
  </div>
</div></div>

<script>
const chat = document.getElementById('chat');
function el(cls, txt){const d=document.createElement('div');d.className=cls;d.textContent=txt;
  document.getElementById('hello')?.remove();chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
function hide(id){document.getElementById(id).classList.remove('show')}
function show(id){document.getElementById(id).classList.add('show')}

let spinChip=null;
const es = new EventSource('/api/events');
es.onmessage = e => {
  const ev = JSON.parse(e.data);
  if(ev.kind==='text') el('msg ai', ev.text);
  else if(ev.kind==='tool_start'){spinChip=el('chip','⚙ '+ev.tool+' ');
    const s=document.createElement('span');s.className='spin';spinChip.appendChild(s)}
  else if(ev.kind==='tool_end'&&spinChip){spinChip.textContent='⚙ '+ev.tool+(ev.ok?' ✓':' ⚠');
    spinChip.className='chip '+(ev.ok?'ok':'bad');spinChip=null}
  else if(ev.kind==='error') el('msg err', ev.message);
  else if(ev.kind==='done'){setBusy(false)}
};

function setBusy(b){document.getElementById('sendBtn').disabled=b;
  document.getElementById('sendBtn').textContent=b?'Working…':'Send'}

async function send(){
  const box=document.getElementById('box'); const t=box.value.trim(); if(!t)return;
  const st=await (await fetch('/api/status')).json();
  if(!st.configured){show('settings');return}
  el('msg user', t); box.value=''; setBusy(true);
  const r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:t})});
  if(!r.ok){setBusy(false); el('msg err','Could not send (engine busy?). Try again.')}
}
document.getElementById('box').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});

function provChange(){const p=document.getElementById('s-provider').value;
  document.getElementById('s-baserow').style.display=p==='openai'?'block':'none';
  document.getElementById('s-model').placeholder=p==='openai'?'gpt-4o or llama3.1':'claude-sonnet-5'}
function showSettings(){show('settings')}
async function saveSettings(){
  const p=document.getElementById('s-provider').value;
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({provider:p, api_key:document.getElementById('s-key').value||null,
      model:document.getElementById('s-model').value||null,
      base_url:p==='openai'?(document.getElementById('s-base').value||null):null})});
  hide('settings'); poll();
}
async function showLive(){const r=await (await fetch('/api/liveline')).json();
  document.getElementById('liveline').textContent=r.line; show('live')}
function copyLine(){navigator.clipboard.writeText(document.getElementById('liveline').textContent)}

async function poll(){
  try{
    const s=await (await fetch('/api/status')).json();
    document.getElementById('d-eng').className=s.engine?'on':'';
    document.getElementById('d-pro').className=s.pro_running?'on':'';
    document.getElementById('d-live').className=s.live_link?'on':(s.pro_running?'warn':'');
    if(!s.configured&&!window._askedSetup){window._askedSetup=true;show('settings')}
  }catch(e){}
}
poll(); setInterval(poll, 5000);
</script>
</body></html>"""
