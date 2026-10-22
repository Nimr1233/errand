"""Safe clicking (errand/clicks.py) in real headless Chromium on a fake shop: option buttons change the
price with JavaScript; a Buy button, an outside Register link and a do-nothing button must never
count as a good click. A stand-in chooser plays the brain."""
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from errand import clicks, engine as real
from errand.browser import Pool
from errand.fetch import Polite
from tests.test_engine import wait

FIELDS = {'title': 'the laptop name', 'price': 'the price with currency symbol'}


def shop_page(k):
    base = 300 + k
    return f'''<html><body><div class="product"><h1>Laptop {k}</h1><p class="price">${base}</p>
      <div class="swatches"><button type="button" class="btn swatch" value="128">128</button>
      <button type="button" class="btn swatch" value="256">256</button>
      <button type="button" class="btn swatch disabled" value="1024">1024</button></div>
      <button type="button" class="buy">Buy now</button><a href="https://cloud.example.com/register">Register</a>
      <button type="button" class="compare">Compare</button></div>
      <script>
        const prices = {{"128": {base}, "256": {base + 20}}};
        document.querySelectorAll('.swatch').forEach(b => b.onclick = () => {{
          document.querySelector('.price').textContent = '$' + prices[b.value]; }});
        document.querySelector('.buy').onclick = () => fetch('/bought');
      </script></body></html>'''


class Shop(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Shop.seen.append(self.path)
        body = 'User-agent: *\nAllow: /\n' if self.path == '/robots.txt' else \
            shop_page(int(self.path.split('/')[-1].split('.')[0])) if self.path.startswith('/laptop/') else ''
        self.send_response(200 if body else 404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def shop():
    Shop.seen = []
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Shop)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{httpd.server_port}'
    httpd.shutdown()


def reader(view, fields):  # a brain that copies the title and price lines
    get = lambda tag: (re.search(rf'^\[\d+\] {tag}: (.+)$', view, re.M) or [None, None])[1]
    return {'title': get('h1'), 'price': get('p class=price')}


def make(tmp_path, picks):
    def chooser(step, offered):
        picks.append((step, [clicks.name(c) for c in offered]))
        return '256' if '256' in step else 'Buy now' if 'buy' in step.lower() else 'Compare'
    return real.Engine(brain=reader, results=tmp_path, remember=False, pool=Pool(size=2), chooser=chooser,
                       fetcher=Polite(delay=(0.03, 0.05), allow_local=True))


def test_only_safe_things_are_ever_offered():
    c = lambda **k: {'tag': 'button', 'type': 'button', 'text': '', 'title': '', 'aria': '', 'value': '', 'href': '',
                     'role': '', 'disabled': False, 'form': False, 'cls': '', 'css': 'x', **k}
    url = 'https://shop.example/laptop/1'
    assert clicks.safe(c(text='256'), url) == (True, '')
    assert clicks.safe(c(text='Buy now'), url)[0] is False
    assert clicks.safe(c(text='Add to cart'), url)[0] is False
    assert clicks.safe(c(tag='a', text='Register', href='https://cloud.example.com/register'), url)[0] is False
    assert clicks.safe(c(tag='a', text='Reviews', href='https://other.example/reviews'), url) == (False, 'leaves the site')
    assert clicks.safe(c(tag='a', text='Next', href='https://shop.example/laptop/2'), url) == (True, '')
    assert clicks.safe(c(text='Go', form=True, type=''), url) == (False, 'sends a form')  # a form button submits
    assert clicks.safe(c(text='1024', disabled=True), url) == (False, 'disabled')
    assert clicks.fill('click the {size} option', {'size': '256'}) == 'click the 256 option'
    # found live: the 2B copied "256 (button)" from the menu; the menu now shows names only, and a copied label is ignored
    offered = [c(text='128'), c(text='256')]
    assert '(button)' not in clicks.choose_prompt('click 256', offered)
    assert clicks.find(offered, '256 (button)')[0]['text'] == '256'


def test_the_option_is_clicked_once_by_the_brain_then_replayed(shop, tmp_path):
    picks = []
    eng = make(tmp_path, picks)
    urls = [f'{shop}/laptop/{k}.html' for k in range(6)]
    eng.start_job('Laptops 256', urls, FIELDS, steps=['click the 256 option'])
    s = wait(eng, 90)
    assert all(eng.rows[u] == {'status': 'ok', 'title': f'Laptop {k}', 'price': f'${320 + k}'} for k, u in enumerate(urls))
    assert len(picks) == 1 and s['clicks_by_brain'] == 1 and s['clicks_replayed'] == 5  # the brain once, then no AI
    offered = picks[0][1]
    assert '256' in offered and not {'Buy now', 'Register', '1024'} & set(offered)  # unsafe things are never offered
    picks.clear()
    eng.start_job('Laptops again', urls[:2], FIELDS, steps=['click the 256 option'])
    wait(eng, 60)
    assert not picks and eng.rows[urls[1]]['price'] == '$321'  # the saved click works for the next job too
    eng.close()


def test_a_buy_click_never_happens_and_nothing_changing_is_a_failure(shop, tmp_path):
    eng = make(tmp_path, [])
    eng.start_job('Try to buy', [f'{shop}/laptop/1.html'], FIELDS, steps=['click the Buy button'])
    wait(eng, 60)
    assert eng.rows[f'{shop}/laptop/1.html']['status'] == 'click failed: nothing called "Buy now"'
    eng.start_job('Compare', [f'{shop}/laptop/2.html'], FIELDS, steps=['click compare'])
    wait(eng, 60)
    eng.close()
    assert eng.rows[f'{shop}/laptop/2.html']['status'] == 'click failed: clicking "Compare" changed nothing'
    assert '/bought' not in Shop.seen


def test_escalating_chooser_only_asks_the_senior_when_the_2b_misses():
    c = lambda t, href='': {'tag': 'button', 'type': 'button', 'text': t, 'title': '', 'aria': '', 'value': '',
                            'href': href, 'role': '', 'disabled': False, 'form': False, 'cls': '', 'css': 'x'}
    offered = [c('128'), c('256')]
    asked = []
    senior = lambda step, off: (asked.append(step), '256')[1]
    # the 2B names a real thing: the senior is never asked
    ch = clicks.escalating_chooser(lambda s, o: '128', senior, ready=lambda: True)
    assert ch('click 128', offered) == '128' and not asked
    # the 2B misses: the senior is asked and its valid pick is used
    ch = clicks.escalating_chooser(lambda s, o: 'nope', senior, ready=lambda: True)
    assert ch('click 256', offered) == '256' and asked == ['click 256']
    # the senior isn't ready yet: only the 2B is used (its pick stands, do_steps then reports the miss)
    asked.clear()
    ch = clicks.escalating_chooser(lambda s, o: 'nope', senior, ready=lambda: False)
    assert ch('click 256', offered) == 'nope' and not asked
    # both miss: the 2B's pick is returned
    ch = clicks.escalating_chooser(lambda s, o: 'nope', lambda s, o: 'also nope', ready=lambda: True)
    assert ch('click 256', offered) == 'nope'


def test_a_hard_click_choice_falls_to_the_senior(shop, tmp_path):
    picks = {'2b': [], 'senior': []}
    dumb = lambda step, off: (picks['2b'].append(step), 'the 256 GB variant')[1]  # names something not on the page
    senior = lambda step, off: (picks['senior'].append(step), '256')[1]  # the 4B names it right
    chooser = clicks.escalating_chooser(dumb, senior, ready=lambda: True)
    eng = real.Engine(brain=reader, results=tmp_path, remember=False, pool=Pool(size=2), chooser=chooser,
                      fetcher=Polite(delay=(0.03, 0.05), allow_local=True))
    u = f'{shop}/laptop/1.html'
    eng.start_job('Laptops 256', [u], FIELDS, steps=['click the 256 option'])
    wait(eng, 90)
    eng.close()
    assert eng.rows[u] == {'status': 'ok', 'title': 'Laptop 1', 'price': '$321'}  # 256 clicked (+$20) via the senior
    assert picks['2b'] and picks['senior'] == ['click the 256 option']  # 2B missed, senior settled it


def test_a_skill_fills_its_blanks(shop, tmp_path):
    picks = []
    eng = make(tmp_path, picks)
    eng.start_job('First', [f'{shop}/laptop/1.html'], FIELDS, steps=['click the {size} option'])
    wait(eng, 60)
    assert eng.save_skill('laptop price', 'a laptop price for one disk size') == {'ok': True, 'skill': 'laptop price'}
    eng.run_skill('laptop price', [f'{shop}/laptop/4.html'], {'size': '256'})
    wait(eng, 60)
    eng.close()
    assert eng.rows[f'{shop}/laptop/4.html']['price'] == '$324' and picks[-1][0] == 'click the 256 option'
    assert eng.store.skill('laptop price')['steps'] == ['click the {size} option']
