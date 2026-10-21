"""Terminal bridge (room spec section 5.1): runs Claude Code in a Windows pseudo-terminal
and streams it to the chief's computer.

Listens on 127.0.0.1:8766 only. `tailscale serve` exposes 8765, never this port, so the phone
can't reach it. Every request must also pass the Host, Origin and token locks (spec section 6).
"""
import asyncio
import glob
import json
import os
import secrets
import shutil
import threading
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse

PORT = 8766
HOSTS = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
ORIGINS = {f'http://{h}' for h in HOSTS}
# Only the room may frame the terminal. Otherwise any website could frame it and trick your
# typing into Claude Code: the frame's own origin passes the Origin lock.
FRAME_ANCESTORS = 'frame-ancestors http://127.0.0.1:8765 http://localhost:8765'
TOKEN = secrets.token_urlsafe(32)  # new each start, embedded only in this server's own page
SCROLLBACK_LINES = 2000
def child_env(env):
    """The environment for the room's Claude Code. If Errand was started from inside a Claude session
    (the desktop app, or Claude starting it for you), that session's settings are dropped: Claude Code
    would refuse to start "nested", or run on the parent's proxy and login instead of your own."""
    if 'CLAUDECODE' not in env and 'CLAUDE_CODE_ENTRYPOINT' not in env:
        return dict(env)
    return {k: v for k, v in env.items() if not k.upper().startswith(('CLAUDE', 'ANTHROPIC', 'MCP_'))}


def find_claude():
    path = os.environ.get('ERRAND_CLAUDE') or shutil.which('claude')
    if path:
        return path
    # The Claude desktop app bundles Claude Code; use its newest copy (it moved to Roaming in October 2026).
    found = [p for pattern in (r'%APPDATA%\Claude\claude-code\*\*\claude.exe',
                               r'%LOCALAPPDATA%\Claude-Data\*\claude-code\*\*\claude.exe')
             for p in glob.glob(os.path.expandvars(pattern))]
    return max(found, key=os.path.getmtime) if found else None


def host_ok(headers):
    return headers.get('host') in HOSTS


def ws_ok(ws):
    return host_ok(ws.headers) and ws.headers.get('origin') in ORIGINS and \
        secrets.compare_digest(ws.query_params.get('token', ''), TOKEN)


class Session:
    """The one Claude Code session. It outlives page reloads; clients come and go.

    shortcut: every open page answers the terminal's live queries, so with two pages open at once
    Claude Code gets each answer twice. Fine for one room tab; let only the newest page answer if it bites.
    """

    def __init__(self):
        self.proc = None
        self.chunks = deque()  # recent output, trimmed to about SCROLLBACK_LINES lines
        self.lines = 0
        self.clients = set()
        self.size = (30, 100)  # rows, cols

    def alive(self):
        return self.proc is not None and self.proc.isalive()

    def start(self, loop):
        from winpty import PtyProcess  # Windows only; imported here so tests of the locks run anywhere
        exe = find_claude()
        if not exe:
            return False
        env = child_env(os.environ)
        self.chunks.clear()
        self.lines = 0
        self.proc = PtyProcess.spawn([exe], cwd=os.path.expanduser('~'), env=env, dimensions=self.size)
        threading.Thread(target=self._pump, args=(self.proc, loop), daemon=True).start()
        return True

    def _pump(self, proc, loop):
        while True:
            try:
                data = proc.read(65536)
            except EOFError:
                break
            if data:
                asyncio.run_coroutine_threadsafe(self._out(data), loop)
        asyncio.run_coroutine_threadsafe(self._send_all({'t': 'exit'}), loop)

    async def _out(self, data):
        self.chunks.append(data)
        self.lines += data.count('\n')
        while self.lines > SCROLLBACK_LINES and len(self.chunks) > 1:
            self.lines -= self.chunks.popleft().count('\n')
        await self._send_all({'t': 'out', 'd': data})

    async def _send_all(self, msg):
        for ws in list(self.clients):
            try:
                await ws.send_text(json.dumps(msg))
            except Exception:
                self.clients.discard(ws)

    def resize(self, rows, cols):
        self.size = (max(5, rows), max(20, cols))
        if self.alive():
            self.proc.setwinsize(*self.size)


session = Session()


@asynccontextmanager
async def lifespan(app):
    yield
    if session.alive():
        session.proc.terminate(force=True)  # don't leave Claude Code running after Errand stops


app = FastAPI(lifespan=lifespan)


@app.get('/')
async def page(request: Request):
    if not host_ok(request.headers):
        return PlainTextResponse('Forbidden', status_code=403)
    return HTMLResponse(PAGE.replace('__TOKEN__', TOKEN), headers={'Content-Security-Policy': FRAME_ANCESTORS})


@app.websocket('/term')
async def term(ws: WebSocket):
    if not ws_ok(ws):
        await ws.close(code=1008)
        return
    await ws.accept()
    session.clients.add(ws)
    await ws.send_text(json.dumps({'t': 'reset'}))
    for chunk in list(session.chunks):
        await ws.send_text(json.dumps({'t': 'out', 'd': chunk}))
    await ws.send_text(json.dumps({'t': 'ready'}))  # replay done
    if not session.alive() and session.proc is not None:
        await ws.send_text(json.dumps({'t': 'exit'}))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg['t'] == 'in' and session.alive():
                session.proc.write(msg['d'])
            elif msg['t'] == 'size':
                session.resize(int(msg['rows']), int(msg['cols']))
                if session.proc is None and not session.start(asyncio.get_running_loop()):
                    await ws.send_text(json.dumps({'t': 'missing'}))
            elif msg['t'] == 'start' and not session.alive():
                if not session.start(asyncio.get_running_loop()):
                    await ws.send_text(json.dumps({'t': 'missing'}))
    except Exception:
        pass
    finally:
        session.clients.discard(ws)


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Chief's terminal</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.css">
<style>html,body{margin:0;height:100%;background:#020E11;color:#CFF6F8;font:14px 'Share Tech Mono',Consolas,monospace}
#t{position:absolute;inset:6px}#msg{position:absolute;inset:0;display:none;align-items:center;justify-content:center;flex-direction:column;gap:12px;background:#020E11;text-align:center;padding:24px}
button{font:inherit;background:#0A1316;color:#5CE1E6;border:1px solid #1F5F66;border-radius:6px;padding:6px 14px;cursor:pointer}a{color:#5CE1E6}</style></head>
<body><div id="t"></div><div id="msg"></div>
<script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.js"></script>
<script>
const TOKEN='__TOKEN__',box=document.getElementById('t'),msg=document.getElementById('msg');
const term=new Terminal({fontFamily:'Cascadia Mono, Consolas, monospace',fontSize:14,cursorBlink:false,
  theme:{background:'#020E11',foreground:'#CFF6F8',cursor:'#5CE1E6',selectionBackground:'#1F5F66'}});
const fit=new FitAddon.FitAddon();term.loadAddon(fit);term.open(box);fit.fit();
let ws,replaying=false;const send=m=>ws&&ws.readyState===1&&ws.send(JSON.stringify(m));
function show(html){msg.innerHTML=html;msg.style.display=html?'flex':'none'}
function connect(){ws=new WebSocket('ws://'+location.host+'/term?token='+TOKEN);
  ws.onopen=()=>{show('');send({t:'size',rows:term.rows,cols:term.cols})};
  ws.onmessage=e=>{const m=JSON.parse(e.data);
    if(m.t==='out')term.write(m.d);else if(m.t==='reset'){term.reset();replaying=true}
    else if(m.t==='ready')term.write('',()=>{replaying=false});
    else if(m.t==='exit')show('Claude Code closed.<button onclick="restart()">Start again</button>');
    else if(m.t==='missing')show('Claude Code isn\\'t installed on this laptop.<a href="https://docs.claude.com/en/docs/claude-code/setup" target="_blank" rel="noopener">How to install it</a>')};
  ws.onclose=()=>setTimeout(reconnect,2000)}
// after Errand restarts this page's token is stale: reload to get the new one
function reconnect(){fetch('/').then(r=>r.text()).then(t=>t.includes(TOKEN)?connect():location.reload(),connect)}
function restart(){show('');send({t:'start'})}
// replayed output holds old terminal queries (Windows asks "what terminal are you?" at start);
// answering them again would type junk into Claude Code, so stay quiet until the replay is drawn
term.onData(d=>{if(!replaying)send({t:'in',d})});
addEventListener('message',e=>{if(e.data==='focus'&&/^http:\\/\\/(127\\.0\\.0\\.1|localhost):8765$/.test(e.origin))term.focus()});
new ResizeObserver(()=>{fit.fit();send({t:'size',rows:term.rows,cols:term.cols})}).observe(box);
connect();term.focus();
</script></body></html>"""
