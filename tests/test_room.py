"""The 3D room in demo mode (room spec section 8), driven in headless Chromium.

Starts its own `errand start` with a Python prompt standing in for Claude Code, so no test ever
starts the real Claude Code. Needs the internet for three.js, xterm.js and the fonts.
"""
import math
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time

import httpx
import pytest

sync_api = pytest.importorskip('playwright.sync_api')
expect = sync_api.expect

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = 'http://127.0.0.1:8765/'
RED, CYAN = '#FF5A52', '#8FF7FB'


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(('127.0.0.1', port)) == 0


@pytest.fixture(scope='module')
def errand():
    if port_open(8765) or port_open(8766):
        pytest.skip('Errand is already running: stop it to run the room tests')
    env = {**os.environ, 'ERRAND_CLAUDE': sys.executable}  # a Python prompt stands in for Claude Code
    p = subprocess.Popen([sys.executable, '-m', 'errand', 'start'], cwd=ROOT, env=env,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    for _ in range(100):
        if port_open(8765) and port_open(8766):
            break
        time.sleep(0.1)
    else:
        p.kill()
        pytest.fail('errand start did not come up')
    yield p
    p.send_signal(signal.CTRL_BREAK_EVENT)  # a clean stop, so the bridge closes its terminal program
    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        p.kill()


@pytest.fixture(scope='module')
def browser(errand):
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        yield b
        b.close()


def open_room(browser, width=1024, height=700):
    page = browser.new_page(viewport={'width': width, 'height': height})
    page.goto(URL)
    page.wait_for_function('window.__room && __room.webgl && __room.status', timeout=20000)
    return page


@pytest.fixture
def page(browser):
    p = open_room(browser)
    yield p
    p.close()


# Software 3D in headless Chromium draws few frames a second, so walking runs slow here:
# hold keys until something happens instead of for a fixed time.
def hold(page, keys, until=None, ms=12000):
    for k in keys:
        page.keyboard.down(k)
    if until:
        page.wait_for_function(until, timeout=ms)
    else:  # until you stop moving: 5 frames go by without moving, so something blocks you
        last, f0 = page.evaluate('[__room.pos, __room.frames]')
        t0 = time.time()
        while time.time() - t0 < ms / 1000:
            page.wait_for_timeout(300)
            p, f = page.evaluate('[__room.pos, __room.frames]')
            if p != last:
                last, f0 = p, f
            elif f - f0 >= 5:
                break
    for k in keys:
        page.keyboard.up(k)
    page.wait_for_function('!__room.gliding')
    page.wait_for_timeout(600)  # 0.3 s to stop, at a low frame rate
    return page.evaluate('__room.pos')


def free(page, p):
    r = page.evaluate('({WALL: __room.WALL, MARGIN: __room.MARGIN, BOXES: __room.BOXES})')
    for i in range(8):
        a = i * math.pi / 4
        if p['x'] * math.sin(a) - p['z'] * math.cos(a) > r['WALL'] + 1e-6:
            return False
    for b in r['BOXES']:
        dx, dz, c, s = p['x'] - b['x'], p['z'] - b['z'], math.cos(b['r']), math.sin(b['r'])
        if abs(dx * c - dz * s) < b['hx'] + r['MARGIN'] - 1e-6 and abs(dx * s + dz * c) < b['hz'] + r['MARGIN'] - 1e-6:
            return False
    return True


def test_walking_cannot_leave_the_room(page):
    p = hold(page, ['KeyD'])
    assert p['x'] == pytest.approx(4.6, abs=0.01)  # stopped 0.6 from the right wall
    for keys in (['KeyW'], ['KeyA', 'KeyW'], ['KeyS'], ['KeyA'], ['KeyS', 'KeyD'], ['KeyW', 'KeyD']):
        p = hold(page, keys)
        assert free(page, p), (keys, p)


def test_walking_cannot_pass_through_the_console(page):
    hold(page, ['KeyA'], until='__room.pos.x < -1.0')  # step to the left of the chair
    p = hold(page, ['KeyW'])  # and walk at the console
    assert free(page, p)
    assert -1.11 <= p['z'] < -0.9, p  # stopped at its edge: the front at -1.45 plus the 0.35 margin


def test_sit_esc_reaches_the_terminal_and_stand_up(page):
    hold(page, ['KeyW'])  # walk up to the chair; the chair stops you
    assert page.evaluate('__room.nearChair')
    page.wait_for_function("getComputedStyle(document.getElementById('hint')).opacity === '1'")
    expect(page.locator('#hint')).to_have_text('Press E to sit')
    page.keyboard.press('KeyE')
    page.wait_for_function('__room.seated && __room.panelOpen', timeout=5000)
    rows = page.frame_locator('#term').locator('.xterm-rows')
    expect(rows).to_contain_text('>>>', timeout=20000)  # the stand-in Python prompt is up
    page.wait_for_function("document.activeElement.id === 'term'")
    page.keyboard.type('abc')
    page.keyboard.press('Escape')
    page.wait_for_timeout(400)
    assert page.evaluate('__room.seated && __room.panelOpen')  # Esc did not stand you up
    page.keyboard.type('6*7')
    page.keyboard.press('Enter')
    expect(rows).to_contain_text('42')  # Esc reached the terminal: it cleared "abc"
    page.click('#stand')
    page.wait_for_function('!__room.seated && !__room.panelOpen', timeout=5000)
    hold(page, ['KeyS'], until='__room.pos.z > 1.0')  # walking works again after standing up


def test_terminal_paste_non_english_emoji_esc_and_ctrl_c(browser):
    page = browser.new_page()
    page.goto('http://127.0.0.1:8766/')
    rows = page.locator('.xterm-rows')
    expect(rows).to_contain_text('>>>', timeout=20000)
    page.evaluate("""() => {
        const dt = new DataTransfer();
        dt.setData('text/plain', "print('héllo ñ 日本 ' + chr(0x1F44B) + ' 👋')");
        document.querySelector('.xterm-helper-textarea').dispatchEvent(
            new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    }""")
    page.keyboard.press('Enter')
    expect(rows).to_contain_text('héllo ñ 日本 👋 👋')
    # Claude Code reads keys raw, so Esc and Ctrl+C reach it as plain keys: read two keys raw the same way
    page.keyboard.type("import msvcrt; print('keys:', repr(msvcrt.getwch() + msvcrt.getwch()))")
    page.keyboard.press('Enter')
    page.wait_for_timeout(500)
    page.keyboard.press('Escape')
    page.wait_for_timeout(300)  # a lone Esc, not the start of Alt+key
    page.keyboard.press('Control+C')
    expect(rows).to_contain_text(r"keys: '\x1b\x03'")
    page.close()


def test_problems_tv_is_red_only_above_zero(page):
    tv = page.evaluate('__room.tv.prob')
    assert tv['val'] > 0 and tv['color'] == RED  # the demo opens with 2 problems
    token = (pathlib.Path.home() / '.errand' / 'token').read_text(encoding='utf-8').strip()
    with httpx.Client(base_url='http://127.0.0.1:8765', headers={'Authorization': f'Bearer {token}'}) as api:
        for _ in range(20):
            for a in api.get('/api/agents', params={'state': 'needs_you'}).json():
                api.post(f"/api/problems/{a['n']}", json={'approve': True})
            page.wait_for_timeout(1000)
            tv = page.evaluate('__room.tv.prob')
            assert tv['color'] == (RED if tv['val'] > 0 else CYAN), tv
            if tv['val'] == 0:
                return
    pytest.fail('PROBLEMS never reached 0')


def test_tv_numbers_at_700px(browser):
    page = open_room(browser, 700, 500)
    page.wait_for_timeout(2000)  # fonts in, first numbers drawn
    tv = page.evaluate('__room.tv')
    assert all(tv[k]['val'] is not None for k in ('done', 'hand', 'prob'))
    out = ROOT / 'tests' / 'out'
    out.mkdir(exist_ok=True)
    page.screenshot(path=str(out / 'room-700px.png'))  # look at it: all three numbers must be legible
    page.close()
