import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from errand import server

BASE = 'http://127.0.0.1:8765'
AUTH = {'Authorization': f'Bearer {server.TOKEN}'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'TOKEN_FILE', tmp_path / 'token')  # leave the real token alone
    with TestClient(server.app, base_url=BASE) as c:
        yield c


def test_wrong_host_refused(client):
    assert client.get('/', headers={'host': 'evil.com'}).status_code == 403
    assert client.get('/api/status', headers={**AUTH, 'host': 'evil.com'}).status_code == 403


def test_token_needed(client):
    assert client.get('/api/status').status_code == 401
    assert client.get('/api/status', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    assert client.get('/api/status', headers=AUTH).status_code == 200


def test_room_page_has_the_token_and_cannot_be_framed(client):
    r = client.get('/')
    assert r.status_code == 200 and server.TOKEN in r.text and '__TOKEN__' not in r.text
    assert r.headers['content-security-policy'] == "frame-ancestors 'none'"


def test_answer_problem(client):
    a = next(a for a in server.engine.agents if a.state == 'needs_you')  # the demo opens with 2
    assert client.post(f'/api/problems/{a.n}', json={'approve': True}, headers=AUTH).json() == {'ok': True}
    assert a.state == 'working'
    assert client.post(f'/api/problems/{a.n}', json={'approve': True}, headers=AUTH).json()['ok'] is False


def test_start_job_needs_links(client):
    assert client.post('/api/jobs', json={'prompt': 'x'}, headers=AUTH).status_code == 400
    r = client.post('/api/jobs', json={'prompt': 'Two pages', 'urls': ['https://a', 'https://b']}, headers=AUTH)
    assert r.json() == {'job': 'Two pages', 'pages': 2}


def test_live_socket_locks(client):
    host = '127.0.0.1:8765'  # the test client sends "testserver" on WebSockets unless told
    for url, headers in ((f'/ws?token={server.TOKEN}', {'host': host, 'origin': 'http://evil.com'}),
                         ('/ws?token=wrong', {'host': host, 'origin': BASE}),
                         (f'/ws?token={server.TOKEN}', {'host': 'evil.com', 'origin': BASE})):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url, headers=headers) as ws:
                ws.receive_text()
    with client.websocket_connect(f'/ws?token={server.TOKEN}', headers={'host': host, 'origin': BASE}) as ws:
        m = ws.receive_json()
        assert m['t'] == 'state' and len(m['agents']) == 53 and 'problems' in m['status']


def test_terminal_is_not_served_here(client):
    assert client.get('/term').status_code == 404
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/term?token={server.TOKEN}', headers={'host': '127.0.0.1:8765', 'origin': BASE}) as ws:
            ws.receive_text()
