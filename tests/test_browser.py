"""Browser windows (errand/browser.py) in the real engine: JavaScript pages loaded in real headless
Chromium windows, the shelf when every window is busy, hand-offs, window pictures, and the stealth
step (stood in for, so no stealth browser starts). Two fake sites run on this laptop."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from errand import engine as real
from errand.browser import Pool
from errand.fetch import Polite
from tests.test_engine import FIELD_WORDS, wait
from tests.test_extract import fake_brain, product, truth


def app_shell(k):
    """A page that is empty until its JavaScript runs, like many shops built with React."""
    inner = product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1).split('<body>')[1].split('</body>')[0]
    return (f'<html><body><div id="root"></div><noscript>You need to enable JavaScript.</noscript>'
            f'<script>document.getElementById("root").innerHTML = {json.dumps(inner)};</script></body></html>')


class Shop(BaseHTTPRequestHandler):
    in_window = 0
    most = 0
    lock = threading.Lock()

    def do_GET(self):
        body = 'User-agent: *\nAllow: /\n' if self.path == '/robots.txt' else \
            app_shell(int(self.path.split('/')[-1].split('.')[0])) if self.path.startswith('/js/') else \
            '<title>Just a moment...</title>' if self.path == '/check.html' else ''
        self.send_response(200 if body else 404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def two_sites():
    servers = [ThreadingHTTPServer(('127.0.0.1', 0), Shop) for _ in range(2)]
    for s in servers:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    yield [f'http://127.0.0.1:{s.server_port}' for s in servers]
    for s in servers:
        s.shutdown()


def make(tmp_path, pool):
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(20)}
    return real.Engine(brain=fake_brain(said, []), results=tmp_path, remember=False, pool=pool,
                       fetcher=Polite(delay=(0.05, 0.08), allow_local=True))


def test_javascript_pages_are_read_in_shared_windows_with_hand_offs(two_sites, tmp_path):
    pool = Pool(size=1)  # one window for two sites: pages must wait on the shelf and be handed on
    eng = make(tmp_path, pool)
    most, stop = [0], threading.Event()

    def watch():
        while not stop.is_set():
            most[0] = max(most[0], pool.in_use)
            time.sleep(0.01)
    threading.Thread(target=watch, daemon=True).start()
    urls = [f'{base}/js/{k}.html' for base in two_sites for k in (3 * two_sites.index(base) + i for i in range(3))]
    eng.start_job('Shop', urls, FIELD_WORDS)
    s = wait(eng, 90)
    stop.set()
    assert all(eng.rows[u]['status'] == 'ok' for u in urls), {u: eng.rows[u] for u in urls}
    k = int(urls[4].split('/')[-1].split('.')[0])
    assert eng.rows[urls[4]] == {'status': 'ok', **truth(f'Book {k}', k)}  # read from the page JavaScript built
    assert most[0] == 1 and s['windows'] == 1 and s['windows_in_use'] == 0  # never more windows than the pool
    assert s['handoffs'] >= 1  # a window went straight from one page to the next one waiting
    shots = [a.shot for a in eng.agents if a.shot]
    assert shots and shots[0][:2] == b'\xff\xd8'  # a JPEG picture of the window, for the room
    eng.close()


def test_an_app_shell_is_spotted_even_with_a_few_links():
    """Found live: quotes.toscrape.com/js/page/3 has 104 characters of links and keeps its quotes in a
    script; a plain text-length rule missed it and the brains read an empty shell."""
    from errand.fetch import thin
    links = '<div>Quotes to Scrape</div><a>Login</a><a>← Previous</a><a>Next →</a><footer>Quotes by: GoodReads.com Made with love by Zyte</footer>'
    data = 'var data = [' + ','.join('{"text": "A long quote that only JavaScript will put on the page"}' for _ in range(10)) + '];'
    assert thin(f'<html><body>{links}<script>{data}</script></body></html>')
    assert not thin(product('Book 1'))  # a real page with its own small script is read as it is


def test_the_stealth_step_never_gets_past_a_bot_check(two_sites, tmp_path):
    pool = Pool(size=2)
    tried = []
    pool.stealth = lambda url: tried.append(url) or {'status': 'ok', 'code': 200, 'html': '<title>Just a moment...</title>'}
    eng = make(tmp_path, pool)
    eng.start_job('Checked', [f'{two_sites[0]}/check.html'], FIELD_WORDS)
    wait(eng, 60)
    assert tried and eng.rows[f'{two_sites[0]}/check.html']['status'] == 'blocked: bot check'
    eng.close()


def test_the_stealth_step_reads_a_page_the_download_was_refused(two_sites, tmp_path):
    pool = Pool(size=2)
    pool.stealth = lambda url: {'status': 'ok', 'code': 200, 'html': product('Book 7', '£17.00', 9, 3)}
    eng = make(tmp_path, pool)
    eng.start_job('Refused', [f'{two_sites[0]}/check.html'], FIELD_WORDS)
    wait(eng, 60)
    assert eng.rows[f'{two_sites[0]}/check.html']['title'] == 'Book 7'
    eng.close()
