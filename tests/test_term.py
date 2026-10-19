"""The terminal bridge's four locks (room spec section 6). No test here starts Claude Code."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from errand import term

BASE = 'http://127.0.0.1:8766'
GOOD = f'/term?token={term.TOKEN}'
HOST = '127.0.0.1:8766'  # the test client sends "testserver" on WebSockets unless told


@pytest.fixture
def client():
    return TestClient(term.app, base_url=BASE)


def refused(client, url, host=HOST, **headers):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(url, headers={'host': host, **headers}) as ws:
            ws.receive_text()


def test_page_needs_the_right_host_and_only_the_room_may_frame_it(client):
    assert client.get('/', headers={'host': 'evil.com:8766'}).status_code == 403
    r = client.get('/')
    assert r.status_code == 200 and term.TOKEN in r.text
    assert r.headers['content-security-policy'] == term.FRAME_ANCESTORS


def test_wrong_host_refused(client):
    refused(client, GOOD, host='evil.com:8766', origin=BASE)


def test_wrong_origin_refused(client):
    refused(client, GOOD, origin='http://evil.com')
    refused(client, GOOD, origin='http://127.0.0.1:8765')  # not even the room's own page


def test_missing_or_wrong_token_refused(client):
    refused(client, '/term', origin=BASE)
    refused(client, '/term?token=wrong', origin=BASE)


def test_all_four_locks_pass(client):
    with client.websocket_connect(GOOD, headers={'host': HOST, 'origin': BASE}) as ws:
        assert ws.receive_json() == {'t': 'reset'}
    with client.websocket_connect(GOOD, headers={'host': 'localhost:8766', 'origin': 'http://localhost:8766'}) as ws:
        assert ws.receive_json() == {'t': 'reset'}
