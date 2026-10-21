"""Hidden product data (extract.structured, the 'data' reader): JSON-LD, meta tags and Next.js data read
before brains where they agree with the brains, and JavaScript pages that need no window once the
hidden data covers every field."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from errand import engine as real, extract as x
from errand.browser import Pool
from errand.fetch import Polite
from tests.test_engine import wait
from tests.test_extract import fake_brain, product, truth

FIELDS = {'title': ('the product title', 'text'), 'price': ('the price', 'text'), 'stock': ('copies in stock', 'number')}


def ld(k, graph=False):
    item = {'@type': 'Product', 'name': f'Book {k}', 'offers': {'@type': 'Offer', 'price': f'£1{k}.00', 'inventoryLevel': k + 2},
            'aggregateRating': {'@type': 'AggregateRating', 'ratingValue': '4.7'}}
    block = {'@context': 'https://schema.org', '@graph': [{'@type': 'BreadcrumbList'}, item]} if graph else item
    return f'<script type="application/ld+json">{json.dumps(block)}</script>'


def test_hidden_data_is_labelled_by_type_not_place():
    a = x.structured(f'<html><head>{ld(3)}<meta property="og:title" content="Book 3"></head><body></body></html>')
    b = x.structured(f'<html><head>{ld(3, graph=True)}</head></html>')
    assert a['ld.Product.name'] == b['ld.Product.name'] == 'Book 3'  # same label inside a @graph or not
    assert a['ld.Product.offers.price'] == '£13.00' and a['meta.og:title'] == 'Book 3'
    nxt = '<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"item": {"title": "Lamp"}}}}</script>'
    assert x.structured(f'<html><body>{nxt}</body></html>')['next.pageProps.item.title'] == 'Lamp'
    assert x.structured('<script type="application/ld+json">{broken</script>') == {}  # bad JSON is skipped
    assert x.coerce('4.7', 'number') is None and x.coerce('12', 'number') == 12 and x.coerce('1,036', 'number') == 1036


def test_the_vote_reads_hidden_data_where_the_layout_moves():
    # the price moves down the page (notes=k), so no CSS spot holds it; the JSON-LD always does
    pages = [(product(f'Book {k}', f'£1{k}.00', k + 2, notes=k).replace('<head>', '<head>' + ld(k)), truth(f'Book {k}', k))
             for k in range(5)]
    recipe = x.learn_recipe(pages, FIELDS, focus='div.product')
    assert recipe['price'] == ('data', 'ld.Product.offers.price')
    assert recipe['stock'] == ('data', 'ld.Product.offers.inventoryLevel')  # a tie with the page goes to hidden data
    new = product('Book 9', '£19.00', 11, notes=3).replace('<head>', '<head>' + ld(9))
    assert x.replay(new, recipe, FIELDS) == {'title': 'Book 9', 'price': '£19.00', 'stock': 11}


def shell_with_data(k):
    """An app shell: empty until JavaScript runs, but its hidden data is already in the download."""
    inner = product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1).split('<body>')[1].split('</body>')[0]
    return (f'<html><head>{ld(k)}</head><body><div id="root"></div><script>document.getElementById("root").innerHTML = '
            f'{json.dumps(inner)};</script></body></html>')


class Shells(BaseHTTPRequestHandler):
    def do_GET(self):  # the same page for the plain download and for the browser window
        body = '' if self.path == '/robots.txt' else shell_with_data(int(self.path.split('/')[-1].split('.')[0]))
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


def test_javascript_pages_skip_the_window_once_hidden_data_covers_every_field(tmp_path):
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Shells)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    pool = Pool(size=2)
    renders = []
    real_render = pool.render
    pool.render = lambda url, ua, shot=True: renders.append(url) or real_render(url, ua, shot)
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(14)}
    eng = real.Engine(brain=fake_brain(said, []), results=tmp_path, remember=False, pool=pool,
                      fetcher=Polite(delay=(0.2, 0.25), allow_local=True))  # a real site's pause, so the recipe is learned between pages
    urls = [f'http://127.0.0.1:{httpd.server_port}/js/{k}.html' for k in range(14)]
    eng.start_job('Shells', urls, {f: d for f, (d, _) in FIELDS.items() if f != 'stock'} | {'stock': 'number: copies in stock'})
    s = wait(eng, 90)
    eng.close()
    httpd.shutdown()
    assert eng.groups[next(iter(eng.groups))]['recipe']['price'] == ('data', 'ld.Product.offers.price')
    assert all(eng.rows[u]['title'] == f'Book {k}' and eng.rows[u]['price'] == f'£1{k}.00' for k, u in enumerate(urls))
    assert len(renders) == real.SAMPLES  # the 10 samples in windows; the other 4 straight from the download
    assert s['by_code'] == 4
