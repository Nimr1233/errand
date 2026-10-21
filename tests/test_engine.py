"""The real engine (errand/engine.py) on a small fake website served on this laptop, with a fake
brain. The fetching is real: Scrapling over HTTP, robots.txt, pauses, back-off."""
import csv
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from errand import demo, engine as real, mcp_server as m, server
from errand.fetch import Polite
from tests.test_extract import FIELDS, fake_brain, product, truth

FIELD_WORDS = {'title': 'the product title', 'price': 'the price', 'stock': 'number: copies in stock',
               'rating': 'number: stars', 'published': 'date: the first publication date'}
PAGES = 14


class Site(BaseHTTPRequestHandler):
    log, live, most, tries = [], 0, 0, {}
    lock = threading.Lock()

    def do_GET(self):
        with Site.lock:
            Site.live += 1
            Site.most = max(Site.most, Site.live)
            Site.log.append((self.path, time.monotonic()))
            Site.tries[self.path] = Site.tries.get(self.path, 0) + 1
        time.sleep(0.02)
        code, body = 200, ''
        if self.path == '/robots.txt':
            body = 'User-agent: *\nDisallow: /private/\n'
        elif self.path.startswith('/p/'):
            k = int(self.path[3:].split('.')[0])
            body = product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1)
        elif self.path == '/login.html':
            body = '<form><input name="user"><input type="password" name="pw"></form>'
        elif self.path == '/check.html':
            body = '<title>Just a moment...</title>'
        elif self.path == '/busy/x.html':
            code, body = (429, 'slow down') if Site.tries[self.path] == 1 else (200, product('Book 99'))
        else:
            code = 404
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode())
        with Site.lock:
            Site.live -= 1

    def log_message(self, *a):
        pass


@pytest.fixture
def site():
    Site.log, Site.live, Site.most, Site.tries = [], 0, 0, {}
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Site)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{httpd.server_port}'
    httpd.shutdown()


def make(tmp_path, calls=None, **kw):
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(100)}
    return real.Engine(brain=fake_brain(said, calls if calls is not None else []), results=tmp_path,
                       fetcher=Polite(delay=(0.05, 0.08), backoff=(0.3,), allow_local=True), pool=kw.pop('pool', None), **kw)


def wait(eng, secs=30):
    t = time.monotonic()
    while not eng.complete():
        assert time.monotonic() - t < secs, eng.status()
        time.sleep(0.05)
    time.sleep(0.6)  # let idle agents notice there is no work left
    return eng.status()


def test_a_job_reads_every_page_and_needs_brains_only_for_samples(site, tmp_path):
    calls = []
    eng = make(tmp_path, calls)
    urls = [f'{site}/p/{k}.html' for k in range(PAGES)] + \
           [f'{site}/private/x.html', f'{site}/login.html', f'{site}/check.html', f'{site}/busy/x.html']
    assert eng.start_job('Fake shop', urls, FIELD_WORDS) == {'job': 'Fake shop', 'pages': len(urls)}
    s = wait(eng)
    eng.close()
    assert s['complete'] and s['pages_done'] == len(urls) and s['finished'] == demo.N
    assert len(calls) == real.SAMPLES  # 10 samples, then code reads the rest (/busy/x.html is the same kind)
    assert s['by_code'] == PAGES - real.SAMPLES + 1 and s['recipes'] == 1
    assert eng.rows[f'{site}/p/12.html'] == {'status': 'ok', **truth('Book 12', 12)}
    assert eng.rows[f'{site}/private/x.html']['status'] == 'disallowed by robots.txt'
    assert eng.rows[f'{site}/login.html']['status'] == 'blocked: login page'  # Errand never logs in
    assert eng.rows[f'{site}/check.html']['status'] == 'blocked: bot check'  # never solved
    assert eng.rows[f'{site}/busy/x.html']['status'] == 'ok' and Site.tries['/busy/x.html'] == 2  # 429: paused, retried
    assert s['blocked'] == 3

    paths = [p for p, _ in Site.log]
    assert '/private/x.html' not in paths and paths.count('/robots.txt') == 1
    assert Site.most == 1  # one request to the site at a time
    starts = [t for _, t in Site.log]
    assert min(b - a for a, b in zip(starts, starts[1:])) >= 0.05  # and a pause between them

    with open(s['results'], encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    assert rows[0] == ['url', 'status', *FIELDS] and len(rows) == len(urls) + 1
    assert [f'{site}/p/3.html', 'ok', 'Book 3', '£13.00', '5', '4', 'October 18, 1851'] in rows
    assert set(demo.DemoEngine(seed=1).status()) <= set(s)  # everything the room and connector read


def test_results_are_never_overwritten(site, tmp_path):
    eng = make(tmp_path)
    for n in (1, 2):
        eng.start_job('Same name', [f'{site}/p/{n}.html'], FIELD_WORDS)
        wait(eng)
    eng.close()
    assert sorted(p.name for p in tmp_path.glob('*.csv')) == ['same-name-2.csv', 'same-name.csv']


def test_no_brains_ends_the_job_with_a_reason(site, tmp_path):
    class Broken:
        def start(self):
            raise RuntimeError('brains not installed: llama-server.exe is missing')

        def stop(self):
            pass
    eng = real.Engine(results=tmp_path, fetcher=Polite(delay=(0.05, 0.08), allow_local=True), pool=None)
    eng.server = Broken()
    eng.start_job('No brains', [f'{site}/p/{k}.html' for k in range(3)], FIELD_WORDS)
    s = wait(eng)
    eng.close()
    assert s['complete'] and {r['status'] for r in eng.rows.values()} == {'error: no brains'}
    assert any('could not start' in u['text'] for u in eng.updates.since(None))


def test_pause_holds_every_agent(site, tmp_path):
    eng = make(tmp_path)
    eng.pause_all()
    eng.start_job('Paused', [f'{site}/p/{k}.html' for k in range(3)], FIELD_WORDS)
    time.sleep(0.5)
    assert eng.status()['pages_done'] == 0 and not Site.log
    eng.resume_all()
    assert wait(eng)['pages_done'] == 3
    eng.close()


def test_links_to_this_laptop_or_odd_schemes_are_refused():
    p = Polite()  # the real rules: no allow_local
    for url, why in (('http://127.0.0.1:9/x', 'refused: a private network address'),
                     ('http://localhost/x', 'refused: this laptop'), ('file:///C:/x', 'refused: only http and https links')):
        assert p.take(url) and p.fetch(url)['status'] == why


def test_fields_and_their_kinds():
    assert real.parse_fields({'Price!': 'the price', 'stock': 'Number: copies', 'when': 'date:', 'x y': ''}) == {
        'Price': ('the price', 'text'), 'stock': ('copies', 'number'), 'when': ('when', 'date'), 'x_y': ('x_y', 'text')}
    assert real.kind_of_page('https://a.com/catalogue/b/index.html') == 'a.com/*/*/*'


def test_api_and_connector_start_a_real_job(site, tmp_path, monkeypatch):
    eng = make(tmp_path)
    monkeypatch.setattr(server, 'DEMO', False)
    monkeypatch.setattr(server, 'engine', eng)
    client = lambda: TestClient(server.app, base_url='http://127.0.0.1:8765',  # noqa: E731  the connector closes each one
                                headers={'Authorization': f'Bearer {server.TOKEN}'})
    monkeypatch.setattr(m, '_client', client)
    r = client().post('/api/jobs', json={'prompt': 'x', 'urls': [f'{site}/p/1.html']})
    assert r.status_code == 400 and 'which fields' in r.json()['detail']
    out = m.start_job('Shop', urls=[f'{site}/p/{k}.html' for k in range(2)], fields=FIELD_WORDS)
    assert out.startswith("Started job 'Shop' · 2 pages")
    wait(eng)
    status = m.job_status()
    assert "Job 'Shop': 2/2 pages · complete" in status and 'brain calls: 2' in status and 'recipes learned' in status
    eng.close()
