"""Phone access (errand/phone.py, server.py): from a Tailscale host everything needs the PIN first;
5 wrong PINs lock it; the phone gets the list view, never the room or its terminal."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from errand import phone, server

PHONE = '100.64.0.7:8765'


@pytest.fixture
def setup(tmp_path, monkeypatch):
    clock = [1000.0]
    lock = phone.Lock(tmp_path / 'phone.json', clock=lambda: clock[0])
    pin = phone.set_pin(tmp_path / 'phone.json')
    monkeypatch.setattr(server, 'lock', lock)
    monkeypatch.setattr(server, 'HOSTS', server.HOSTS | {PHONE})
    monkeypatch.setattr(server, 'PHONE_HOSTS', {PHONE})
    monkeypatch.setattr(server, 'TOKEN_FILE', tmp_path / 'token')
    with TestClient(server.app, base_url=f'http://{PHONE}') as c:
        yield c, pin, clock


AUTH = {'Authorization': f'Bearer {server.TOKEN}'}


def test_the_phone_needs_the_pin_before_anything(setup):
    c, pin, _ = setup
    assert c.get('/', follow_redirects=False).headers['location'] == '/login'
    assert c.get('/list', follow_redirects=False).status_code == 303
    assert c.get('/api/status', headers=AUTH).status_code == 401  # even with the token
    assert c.post('/login', data={'pin': 'wrong'}).status_code == 401
    r = c.post('/login', data={'pin': pin}, follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'] == '/list'
    assert 'httponly' in r.headers['set-cookie'].lower() and 'samesite=strict' in r.headers['set-cookie'].lower()
    page = c.get('/list')
    assert page.status_code == 200 and server.TOKEN in page.text and 'Needs you' in page.text
    assert c.get('/api/status', headers=AUTH).status_code == 200
    assert c.get('/', follow_redirects=False).headers['location'] == '/list'  # the 3D room and terminal stay home


def test_five_wrong_pins_lock_it_for_ten_minutes(setup):
    c, pin, clock = setup
    for _ in range(phone.TRIES):
        assert c.post('/login', data={'pin': '000001'}).status_code == 401
    assert c.post('/login', data={'pin': pin}).status_code == 429  # locked, even for the right PIN
    clock[0] += phone.LOCK + 1
    assert c.post('/login', data={'pin': pin}, follow_redirects=False).status_code == 303


def test_the_live_feed_needs_the_pin_too(setup):
    c, pin, _ = setup
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect(f'/ws?token={server.TOKEN}', headers={'origin': f'http://{PHONE}', 'host': PHONE}) as ws:
            ws.receive_text()
    c.post('/login', data={'pin': pin})
    cookie = f'{phone.COOKIE}={c.cookies.get(phone.COOKIE)}'  # a browser sends it with the WebSocket; the test client doesn't
    with c.websocket_connect(f'/ws?token={server.TOKEN}',
                             headers={'origin': f'http://{PHONE}', 'host': PHONE, 'cookie': cookie}) as ws:
        assert '"t": "state"' in ws.receive_text()


def test_the_laptop_needs_no_pin_and_no_pin_means_no_entry(tmp_path):
    with TestClient(server.app, base_url='http://127.0.0.1:8765') as c:
        assert c.get('/list').status_code == 200
    assert phone.Lock(tmp_path / 'none.json').login('123456') is None  # no PIN made yet: nobody gets in
    saved = (tmp_path / 'p.json')
    pin = phone.set_pin(saved)
    assert pin not in saved.read_text()  # only a salted hash is kept
