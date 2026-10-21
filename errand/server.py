"""Mission control server (main spec section 17, room spec): serves the 3D room page, streams live
state over /ws, and offers the local API that the Errand connector (MCP) calls. It runs the real
engine (errand/engine.py); with ERRAND_DEMO=1 (`errand start --demo`, and the tests) the demo engine.

Listens on 127.0.0.1:8765 (and on this laptop's Tailscale address with `errand start --phone`).
Every request must carry the right Host (blocks DNS rebinding), and /api and /ws also need the
token, which is made at each start, embedded in the room page and written to ~/.errand/token for the
connector. Without the token no website can approve or stop anything. From the phone everything
also needs a session from the PIN (errand/phone.py).
"""
import asyncio
import json
import os
import pathlib
import secrets
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import Body, Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from . import demo, engine as real, phone
from .inbox import Inbox
from .schedule import Scheduler
from .telegram import Telegram

PORT = 8765
HOSTS = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
PHONE_HOSTS = set()  # this laptop's Tailscale names, added by `errand start --phone` (errand/phone.py)
TOKEN_FILE = pathlib.Path.home() / '.errand' / 'token'
ROOM = pathlib.Path(__file__).with_name('static') / 'room.html'
LIST = pathlib.Path(__file__).with_name('static') / 'list.html'
LOGIN = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,
initial-scale=1"><title>Errand</title><style>body{{margin:0;background:#021316;color:#CFF6F8;font:18px system-ui;
display:grid;place-items:center;min-height:100vh}}form{{display:grid;gap:12px;padding:16px;width:min(320px,100%)}}
input,button{{font:inherit;min-height:48px;border-radius:8px;border:1px solid #3FC8D0;background:#06262B;color:inherit;
padding:0 12px}}button{{background:#3FC8D0;color:#021316;font-weight:600}}</style></head><body><form method="post"
action="/login"><label for="pin">Errand PIN</label><input id="pin" name="pin" inputmode="numeric" autocomplete="one-time-code"
autofocus required><button type="submit">Open</button><p>{note}</p></form></body></html>'''

TOKEN = secrets.token_urlsafe(32)
DEMO = os.environ.get('ERRAND_DEMO') == '1'
engine = demo.DemoEngine() if DEMO else real.Engine(server_log=pathlib.Path.home() / '.errand' / 'llama-server.log')
scheduler = None if DEMO else Scheduler(engine, engine.store)
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
    if DEMO:
        engine.fast_forward(612, problems=2, huddles=1)  # demo: open mid-job with problems, like the mockup
    task = asyncio.create_task(clock())
    bot = Telegram(engine).start()  # does nothing until you give it a bot token (errand/telegram.py)
    if scheduler:
        scheduler.start()
        Inbox(engine).start()  # does nothing until the Cloudflare inbox is set up (errand/inbox.py)
    yield
    bot.stop.set()
    task.cancel()
    if not DEMO:
        engine.close()  # stops the agents and the brain server it started


app = FastAPI(lifespan=lifespan)
lock = phone.Lock()


@app.middleware('http')
async def phone_gate(request: Request, call_next):
    """From the phone (a Tailscale host) everything but the PIN page needs a session from the PIN."""
    if request.headers.get('host') in PHONE_HOSTS and request.url.path != '/login' and \
            not lock.ok(request.cookies.get(phone.COOKIE)):
        if request.url.path.startswith('/api'):
            return PlainTextResponse('enter your PIN first', status_code=401)
        return RedirectResponse('/login', status_code=303)
    return await call_next(request)


@app.get('/login')
def login_page():
    return HTMLResponse(LOGIN.format(note=''))


@app.post('/login')
async def login(request: Request):
    sid = lock.login(parse_qs((await request.body()).decode()).get('pin', [''])[0].strip())
    if sid == 'locked':
        return HTMLResponse(LOGIN.format(note='Too many wrong PINs. Try again in 10 minutes.'), status_code=429)
    if not sid:
        return HTMLResponse(LOGIN.format(note='Wrong PIN.'), status_code=401)
    r = RedirectResponse('/list', status_code=303)
    r.set_cookie(phone.COOKIE, sid, max_age=phone.DAYS * 86400, httponly=True, samesite='strict')
    return r


@app.get('/list')
def list_view(request: Request):
    """The phone layout: job, what needs you, problems, updates. No 3D, no terminal."""
    if request.headers.get('host') not in HOSTS:
        return PlainTextResponse('Forbidden', status_code=403)
    return HTMLResponse(LIST.read_text(encoding='utf-8').replace('__TOKEN__', TOKEN),
                        headers={'Content-Security-Policy': "frame-ancestors 'none'"})


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
    if request.headers.get('host') in PHONE_HOSTS:
        return RedirectResponse('/list', status_code=303)  # the 3D room and its terminal stay on the laptop
    # no other site may frame this page: it holds the token and the Approve buttons
    return HTMLResponse(ROOM.read_text(encoding='utf-8').replace('__TOKEN__', TOKEN),
                        headers={'Content-Security-Policy': "frame-ancestors 'none'"})


@app.websocket('/ws')
async def ws_live(ws: WebSocket):
    origin_ok = ws.headers.get('origin') in {f'http://{h}' for h in HOSTS}
    if ws.headers.get('host') not in HOSTS or not origin_ok or \
            not secrets.compare_digest(ws.query_params.get('token', ''), TOKEN) or \
            ws.headers.get('host') in PHONE_HOSTS and not lock.ok(ws.cookies.get(phone.COOKIE)):
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


@app.get('/api/agents/{n}/shot', dependencies=[api])
def agent_shot(n: int):
    """The last picture of the agent's browser window (JPEG), for its tile in the room."""
    a = None if DEMO else engine._agent(n)
    if a is None or a.shot is None:
        raise HTTPException(404, f'no window picture for agent #{n}')
    return Response(a.shot, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


@app.get('/api/board', dependencies=[api])
def board():
    return engine.board_view()


@app.get('/api/board/{pid}', dependencies=[api])
def board_problem(pid: str):
    p = engine.problem_detail(pid)
    if p is None:
        raise HTTPException(404, f'no problem {pid}')
    return p


@app.get('/api/history', dependencies=[api])
def history(limit: int = 20):
    return [] if DEMO else engine.history(limit)  # past jobs, newest first


@app.get('/api/updates', dependencies=[api])
def updates(since: int | None = None):
    return engine.updates.since(since)


@app.post('/api/jobs', dependencies=[api])
def start_job(body: dict = Body(...)):
    urls = [u for u in body.get('urls') or [] if isinstance(u, str)]
    if body.get('file'):
        path = pathlib.Path(os.path.expanduser(body['file']))
        if not path.is_file():
            raise HTTPException(400, f'file not found: {path}')
        urls += [line.strip() for line in path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
    if not urls:
        raise HTTPException(400, 'give urls or a file with one link per line')
    if DEMO:
        return engine.start_job(body.get('prompt', ''), len(urls))
    try:
        return engine.start_job(body.get('prompt', ''), urls, body.get('fields'), body.get('focus'),
                                bool(body.get('private')), body.get('steps'))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get('/api/schedules', dependencies=[api])
def schedules():
    return [] if DEMO else engine.store.schedules()


@app.post('/api/schedules', dependencies=[api])
def add_schedule(body: dict = Body(...)):
    if DEMO:
        raise HTTPException(400, 'schedules need the real engine')
    try:
        return {'id': scheduler.add(str(body.get('skill') or ''), body.get('urls'), str(body.get('every') or ''), body.get('values'))}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete('/api/schedules/{sid}', dependencies=[api])
def remove_schedule(sid: int):
    if DEMO or not engine.store.remove_schedule(sid):
        raise HTTPException(404, f'no schedule #{sid}')
    return {'ok': True}


@app.get('/api/skills', dependencies=[api])
def skills():
    return [] if DEMO else engine.store.skills()


@app.post('/api/skills', dependencies=[api])
def save_skill(body: dict = Body(...)):
    if DEMO:
        raise HTTPException(400, 'skills need the real engine')
    try:
        return engine.save_skill(str(body.get('name') or ''), str(body.get('description') or ''))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/api/skills/{name}/run', dependencies=[api])
def run_skill(name: str, body: dict = Body(...)):
    if DEMO:
        raise HTTPException(400, 'skills need the real engine')
    try:
        return engine.run_skill(name, [u for u in body.get('urls') or [] if isinstance(u, str)], body.get('values'))
    except ValueError as e:
        raise HTTPException(400, str(e))


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
