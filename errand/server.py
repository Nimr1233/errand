"""Mission control server (main spec section 17, room spec): serves the 3D room page, streams live
state over /ws, and offers the local API that the Errand connector (MCP) calls.

Listens on 127.0.0.1:8765. Every request must carry the right Host (blocks DNS rebinding), and
/api and /ws also need the token, which is made at each start, embedded in the room page and written
to ~/.errand/token for the connector. Without the token no website can approve or stop anything.
"""
import asyncio
import json
import os
import pathlib
import secrets
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import demo

PORT = 8765
# shortcut: laptop only for now; the phone (Tailscale Host header + pairing, section 17) comes later
HOSTS = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
TOKEN_FILE = pathlib.Path.home() / '.errand' / 'token'
ROOM = pathlib.Path(__file__).with_name('static') / 'room.html'

TOKEN = secrets.token_urlsafe(32)
engine = demo.DemoEngine()
clients = set()


def write_token():
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(TOKEN, encoding='utf-8')


async def clock():
    sent = engine.updates.n
    while True:
        await asyncio.sleep(demo.STEP)
        engine.step()
        new = [u for u in engine.updates.since(sent)]
        sent = engine.updates.n
        await broadcast({'t': 'state', 'status': engine.status(), 'agents': engine.agents_view(), 'updates': new})


async def broadcast(msg):
    text = json.dumps(msg)
    for ws in list(clients):
        try:
            await ws.send_text(text)
        except Exception:
            clients.discard(ws)


@asynccontextmanager
async def lifespan(app):
    write_token()
    engine.fast_forward(612, problems=2)  # demo: open mid-job with 2 problems, like the approved mockup
    task = asyncio.create_task(clock())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


def guard(request: Request):
    if request.headers.get('host') not in HOSTS:
        raise HTTPException(403, 'wrong host')
    auth = request.headers.get('authorization', '')
    if not secrets.compare_digest(auth, f'Bearer {TOKEN}'):
        raise HTTPException(401, 'missing or wrong token')


@app.get('/')
async def room(request: Request):
    if request.headers.get('host') not in HOSTS:
        return PlainTextResponse('Forbidden', status_code=403)
    # no other site may frame this page: it holds the token and the Approve buttons
    return HTMLResponse(ROOM.read_text(encoding='utf-8').replace('__TOKEN__', TOKEN),
                        headers={'Content-Security-Policy': "frame-ancestors 'none'"})


@app.websocket('/ws')
async def ws_live(ws: WebSocket):
    origin_ok = ws.headers.get('origin') in {f'http://{h}' for h in HOSTS}
    if ws.headers.get('host') not in HOSTS or not origin_ok or \
            not secrets.compare_digest(ws.query_params.get('token', ''), TOKEN):
        await ws.close(code=1008)
        return
    await ws.accept()
    clients.add(ws)
    await ws.send_text(json.dumps({'t': 'state', 'status': engine.status(), 'agents': engine.agents_view(),
                                   'updates': engine.updates.since(None)}))
    try:
        while True:
            await ws.receive_text()  # the page only listens; actions go through /api
    except Exception:
        clients.discard(ws)


api = Depends(guard)


@app.get('/api/status', dependencies=[api])
def status():
    return engine.status()


@app.get('/api/agents', dependencies=[api])
def agents(state: str | None = None):
    return engine.agents_view(state)


@app.get('/api/agents/{n}', dependencies=[api])
def agent(n: int):
    d = engine.agent_detail(n)
    if d is None:
        raise HTTPException(404, f'no agent #{n}')
    return d


@app.get('/api/updates', dependencies=[api])
def updates(since: int | None = None):
    return engine.updates.since(since)


@app.post('/api/jobs', dependencies=[api])
def start_job(body: dict = Body(...)):
    urls = body.get('urls') or []
    count = len(urls)
    if body.get('file'):
        path = pathlib.Path(os.path.expanduser(body['file']))
        if not path.is_file():
            raise HTTPException(400, f'file not found: {path}')
        count = sum(1 for line in path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip())
    if not count:
        raise HTTPException(400, 'give urls or a file with one link per line')
    return engine.start_job(body.get('prompt', ''), count)


@app.post('/api/problems/{n}', dependencies=[api])
def answer_problem(n: int, body: dict = Body(...)):
    return engine.answer_problem(n, bool(body.get('approve')))


@app.post('/api/agents/{n}/stop', dependencies=[api])
def stop_agent(n: int):
    return engine.stop_agent(n)


@app.post('/api/pause', dependencies=[api])
def pause():
    return engine.pause_all()


@app.post('/api/resume', dependencies=[api])
def resume():
    return engine.resume_all()
