"""Benchmark step 1 (spec section 15): fetch and cache the test pages.

Set A: 105 product pages from books.toscrape.com (a scraping-practice site, no robots.txt).
Set B: scrapingcourse.com's Cloudflare and anti-bot practice pages (robots.txt allows them),
       plain download first, then Scrapling's stealth browser with CAPTCHA solving OFF.

Run:  python -X utf8 bench/fetch.py
"""
import json, pathlib, random, sys, time
from concurrent.futures import ThreadPoolExecutor
from scrapling.fetchers import Fetcher, StealthyFetcher

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))
from errand.fetch import CHALLENGE_MARKERS, challenged, text  # noqa: E402,F401  the engine's own checks
CACHE = ROOT / 'cache'
OUT = ROOT / 'fetch_results.json'
SET_B = ['https://www.scrapingcourse.com/cloudflare-challenge',
         'https://www.scrapingcourse.com/antibot-challenge']
B_TRIES = 10


def set_a_urls():
    urls = []
    for n in range(1, 7):  # 20 books per listing page; 6 pages -> 120, keep 105
        page = Fetcher.get(f'https://books.toscrape.com/catalogue/page-{n}.html', timeout=30)
        assert page.status == 200, f'listing page {n} -> HTTP {page.status}'
        urls += [page.urljoin(h) for h in page.css('article.product_pod h3 a::attr(href)').getall()]
        time.sleep(1)
    return urls[:105]


def fetch_a(i_url):
    i, url = i_url
    t = time.perf_counter()
    page = Fetcher.get(url, timeout=30)
    took = time.perf_counter() - t
    html = text(page)
    (CACHE / 'A' / f'{i:03d}.html').write_text(html, encoding='utf-8')
    time.sleep(1)  # per-domain politeness: 2 workers x 1 s pause
    return {'i': i, 'url': url, 'status': page.status, 'seconds': round(took, 3), 'bytes': len(html)}


def try_b(url, attempt):
    row = {'url': url, 'attempt': attempt}
    t = time.perf_counter()
    plain = Fetcher.get(url, timeout=30)
    row['plain_status'], row['plain_seconds'] = plain.status, round(time.perf_counter() - t, 2)
    row['plain_passed'] = not challenged(plain.status, text(plain))
    if not row['plain_passed']:
        t = time.perf_counter()
        # wait=10 s lets a passive "Just a moment" check finish like any visitor's browser would;
        # solve_cloudflare stays off, so an interactive CAPTCHA is never clicked through.
        page = StealthyFetcher.fetch(url, headless=True, solve_cloudflare=False, disable_resources=True,
                                     hide_canvas=True, block_webrtc=True, network_idle=True,
                                     wait=10000, timeout=60000)
        html = text(page)
        row['stealth_status'], row['stealth_seconds'] = page.status, round(time.perf_counter() - t, 2)
        row['stealth_title'] = (page.css('title::text').get() or '').strip()
        # page.status is the FIRST response (the challenge's 403); judge by the final page content
        row['stealth_passed'] = not challenged(200, html)
        name = url.rstrip('/').rsplit('/', 1)[-1]
        (CACHE / 'B' / f'{name}-{attempt:02d}.html').write_text(html, encoding='utf-8')
    return row


def main():
    for d in ('A', 'B'):
        (CACHE / d).mkdir(parents=True, exist_ok=True)

    if '--b-only' in sys.argv:  # Set A already cached: keep its earlier numbers
        set_a = json.loads(OUT.read_text(encoding='utf-8'))['set_a']
    else:
        urls = set_a_urls()
        assert len(urls) == 105, f'expected 105 product URLs, got {len(urls)}'
        t = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2) as pool:  # at most 2 requests to one domain at once
            a_rows = list(pool.map(fetch_a, enumerate(urls)))
        a_wall = time.perf_counter() - t
        a_ok = sum(r['status'] == 200 for r in a_rows)
        print(f'Set A: {a_ok}/105 OK in {a_wall:.1f} s (includes 1 s politeness pauses)', flush=True)
        set_a = {'wall_seconds': round(a_wall, 1), 'ok': a_ok, 'rows': a_rows}

    b_rows = []
    for url in SET_B:
        for attempt in range(1, B_TRIES + 1):
            row = try_b(url, attempt)
            b_rows.append(row)
            print(f"Set B {url.rsplit('/', 1)[-1]} #{attempt}: plain {row['plain_status']}"
                  f"{'' if row['plain_passed'] else ' blocked'}"
                  + (f", stealth {row['stealth_status']} {'PASSED' if row['stealth_passed'] else 'still blocked'}"
                     f" in {row['stealth_seconds']} s ('{row['stealth_title']}')" if 'stealth_status' in row else ''),
                  flush=True)
            time.sleep(random.uniform(3, 5))  # one page per domain at a time, 3-5 s apart

    OUT.write_text(json.dumps({'set_a': set_a, 'set_b': b_rows}, indent=2), encoding='utf-8')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
