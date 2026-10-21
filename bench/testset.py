"""A multi-site test set (the council's step 1): 10 pages from each of 4 sites, each with answers
from a hand-written recipe, so brain changes are scored on more than one website.

Sites (robots.txt checked 2026-10-21):
- books.toscrape.com: scraping-practice site, no robots.txt. Reuses 10 pages of bench/cache/A.
- quotes.toscrape.com: scraping-practice site, no robots.txt. Author pages.
- webscraper.io e-commerce test shop: robots.txt blocks /test-sites/product/, /pagination/, /scroll/
  and /load-more/. The /test-sites/e-commerce/allinone/product/ pages used here are not blocked.
- en.wikipedia.org book articles: /wiki/ pages are allowed (/w/ and /api/ are not). CC BY-SA content,
  kept in the local cache only. 4 books show no OCLC number and 3 no page count, so some answers
  are "none" on purpose.

Requests say honestly who is asking (no browser disguise, no fake referer), one every 2-3 s.

A second, held-out set (--holdout) takes the next 10 pages of each site, never looked at while
writing fixes, so a fix is checked on pages it wasn't made from (bench/cache/holdout, bench/holdout_truth.json).

Run:  python -X utf8 bench/testset.py --fetch    (downloads, slowly)
      python -X utf8 bench/testset.py            (answers from the cache, plus 3 rows per site to check)
      python -X utf8 bench/testset.py --holdout --fetch
"""
import argparse, json, pathlib, random, re, sys, time
from scrapling.fetchers import Fetcher
from scrapling.parser import Selector

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fetch import challenged, text  # noqa: E402
from brains import truth as books_truth  # noqa: E402

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / 'cache' / 'testset'
TRUTH = ROOT / 'testset_truth.json'
HOLDOUT, HOLDOUT_TRUTH = ROOT / 'cache' / 'holdout', ROOT / 'holdout_truth.json'
PER_SITE = 10
HEADERS = {'User-Agent': 'ErrandTestSet/0.1 (personal non-commercial test set; 10 pages per site, '
                         'one request every 2-3 s; python scrapling)'}
WIKI_BOOKS = ['Pride_and_Prejudice', 'Nineteen_Eighty-Four', 'The_Hobbit', 'To_Kill_a_Mockingbird',
              'The_Great_Gatsby', 'Moby-Dick', 'Frankenstein', 'Dracula', 'The_Catcher_in_the_Rye',
              'Brave_New_World']
WIKI_HOLDOUT = ['Jane_Eyre', 'Wuthering_Heights', 'Great_Expectations', 'The_Picture_of_Dorian_Gray', 'Animal_Farm',
                'Lord_of_the_Flies', 'Of_Mice_and_Men', 'The_Grapes_of_Wrath', 'Fahrenheit_451', 'Little_Women']


def get(url):
    page = Fetcher.get(url, timeout=30, stealthy_headers=False, headers=HEADERS)
    html = text(page)
    if page.status != 200 or challenged(page.status, html):
        raise SystemExit(f'{url} -> HTTP {page.status}{" (bot challenge)" if challenged(page.status, html) else ""}: stopping')
    time.sleep(random.uniform(2, 3))
    return page, html


def discover(holdout=False):
    """The pages to fetch: 10 per site, found from each site's own listing pages. The held-out set
    takes the next 10 of each listing."""
    skip = PER_SITE if holdout else 0
    urls = {'books': None, 'wikipedia': [f'https://en.wikipedia.org/wiki/{t}' for t in (WIKI_HOLDOUT if holdout else WIKI_BOOKS)]}
    seen, n = [], 1
    while len(seen) < skip + PER_SITE:
        page, _ = get(f'https://quotes.toscrape.com/page/{n}/')
        for href in page.css('div.quote span a::attr(href)').getall():
            u = page.urljoin(href)
            if u not in seen:
                seen.append(u)
        n += 1
    urls['quotes'] = seen[skip:skip + PER_SITE]
    page, _ = get('https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops')
    links = [page.urljoin(h) for h in page.css('a.title::attr(href)').getall()]
    urls['webscraper'] = [u for u in dict.fromkeys(links) if '/test-sites/e-commerce/allinone/product/' in u][skip:skip + PER_SITE]
    return urls


def fetch(holdout=False):
    urls, cache = discover(holdout), HOLDOUT if holdout else CACHE
    for site, lst in urls.items():
        out = cache / site
        out.mkdir(parents=True, exist_ok=True)
        if site == 'books':  # already downloaded for the 105-page benchmark: take 10 spread-out pages
            src = sorted((ROOT / 'cache' / 'A').glob('*.html'))
            step = len(src) // PER_SITE
            picked = src[step // 2 if holdout else 0::step][:PER_SITE]
            for k, p in enumerate(picked):
                (out / f'{k:02d}.html').write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
            lst = [p.name for p in picked]
        else:
            assert len(lst) == PER_SITE, f'{site}: found {len(lst)} pages, want {PER_SITE}'
            if holdout:
                used = json.loads((CACHE / site / 'urls.json').read_text(encoding='utf-8'))
                assert not set(lst) & set(used), f'{site}: held-out pages overlap the test set'
            for k, u in enumerate(lst):
                _, html = get(u)
                (out / f'{k:02d}.html').write_text(html, encoding='utf-8')
                print(f'{site} {k:02d} {len(html):>7} chars  {u}')
        (out / 'urls.json').write_text(json.dumps(lst, indent=1), encoding='utf-8')


# ---- the hand-written answer recipes, one per site (None = the page truly has no such field) ----
MONTH = '(?:January|February|March|April|May|June|July|August|September|October|November|December)'
# real month names only ("Serialised 1860" is not a date), then ISO dates, then a bare year
DATE = re.compile(rf'\d{{1,2}} {MONTH} \d{{4}}|{MONTH} \d{{1,2}}, \d{{4}}|{MONTH} \d{{4}}|\d{{4}}-\d{{2}}-\d{{2}}|\d{{4}}')


def clean(t):
    """Drop Wikipedia footnote marks like [ 1 ] and hidden machine dates like ( 1949-06-08 )."""
    t = re.sub(r'\[\s*\w+\s*\]|\(\s*\d{4}-\d{2}-\d{2}\s*\)', '', t or '')
    return re.sub(r'\s+', ' ', t).replace(' ,', ',').strip() or None


def first_date(t):
    """The first date shown: Moby-Dick lists a UK and a US date; Frankenstein adds '; 208 years ago'."""
    m = DATE.search(t or '')
    return m.group() if m else t


def quotes(s):
    born = s.css('span.author-born-location::text').get() or ''
    return {'name': s.css('h3.author-title::text').get().strip(), 'born_date': s.css('span.author-born-date::text').get(),
            'born_location': re.sub(r'^in\s+', '', born.strip()) or None}


def webscraper(s):
    card = s.css('div.thumbnail')[0]
    return {'title': card.css('h4.title::text').get().strip(), 'price': card.css('span[itemprop=price]::text').get(),
            'description': card.css('p.description::text').get().strip(),
            'reviews': int(card.css('span[itemprop=reviewCount]::text').get()),
            'rating': len(card.css('div.ratings span.ws-icon-star'))}  # stars are only icons: no text, no label


def wikipedia(s):
    box = s.css('table.infobox')[0]
    rows = {}
    for r in box.css('tr'):
        th, td = r.css('th'), r.css('td')
        if th and td:
            rows.setdefault(th[0].get_all_text(separator=' ', strip=True), td[0].get_all_text(separator=' ', strip=True))
    pick = lambda *labels: next((clean(v) for k, v in rows.items() if k in labels), None)
    pages, published, publisher = pick('Pages'), pick('Publication date', 'Published'), pick('Publisher')
    if publisher is None and published:  # some boxes name it in "Published": "17 August 1945 ( Secker and Warburg , London, England)"
        rest = re.sub(r'[()]', ' ', DATE.sub('', published, count=1))
        publisher = clean(rest.split(',')[0])
    return {'title': clean(box.css('caption').first.get_all_text(strip=True) if box.css('caption') else
                           box.css('.infobox-title').first.get_all_text(strip=True)),
            'author': pick('Author'), 'publisher': publisher, 'published': first_date(published),
            'pages': int(re.search(r'\d[\d,]*', pages).group().replace(',', '')) if pages else None,
            'oclc': pick('OCLC')}  # none of these classics shows an ISBN; 6 of 10 show an OCLC number


RECIPES = {'books': lambda s: books_truth(str(s.html_content)), 'quotes': quotes, 'webscraper': webscraper,
           'wikipedia': wikipedia}


def build(holdout=False):
    out = {}
    for site, recipe in RECIPES.items():
        d = (HOLDOUT if holdout else CACHE) / site
        urls = json.loads((d / 'urls.json').read_text(encoding='utf-8'))
        rows = []
        for k in range(PER_SITE):
            s = Selector((d / f'{k:02d}.html').read_text(encoding='utf-8'))
            rows.append({'page': f'{site}/{k:02d}.html', 'url': urls[k], 'answers': recipe(s)})
        out[site] = rows
    # self-check: a recipe that silently returns None everywhere looks like a site with no data
    for site, rows in out.items():
        for f in rows[0]['answers']:
            vals = [r['answers'][f] for r in rows]
            assert any(v not in (None, '') for v in vals), f'{site}.{f} is empty on every page: recipe is broken'
    if holdout:
        used = json.loads((CACHE / 'books' / 'urls.json').read_text(encoding='utf-8'))
        assert not {r['url'] for r in out['books']} & set(used), 'books: held-out pages overlap the test set'
    (HOLDOUT_TRUTH if holdout else TRUTH).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--holdout', action='store_true')
    a = ap.parse_args()
    if a.fetch:
        fetch(a.holdout)
    out = build(a.holdout)
    for site, rows in out.items():
        empty = {f: sum(r['answers'][f] in (None, '') for r in rows) for f in rows[0]['answers']}
        print(f'\n== {site}: {len(rows)} pages · fields with "none" answers: {({f: n for f, n in empty.items() if n})}')
        for r in rows[:3]:  # 3 rows per site for you to check against the real page
            print(' ', r['url'])
            print('   ', json.dumps(r['answers'], ensure_ascii=False))
    print(f'\nanswers -> {HOLDOUT_TRUTH if a.holdout else TRUTH}')


if __name__ == '__main__':
    main()
