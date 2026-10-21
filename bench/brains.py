"""Benchmark step 2 (spec section 15): N brains at once on the cached Set A pages.

Starts llama-server with N parallel slots (4,096 tokens each), sends all 105 extraction jobs
with N in flight, measures time, tokens and GPU memory, and scores answers against a
hand-written recipe (the ground truth). With --recipe it instead asks one brain to WRITE a
recipe (CSS selectors) from a sample page and replays it on all 105 pages with zero AI calls.

With --point ("point, don't write") brains read a numbered list of page pieces with their labels
kept and answer with line numbers; code copies the exact text. Code then turns the pointed pieces
on 5 sample pages into a recipe (the brain never writes CSS) and replays it on all pages.

Run:  python -X utf8 bench/brains.py --np 53
      python -X utf8 bench/brains.py --np 53 --point
      python -X utf8 bench/brains.py --np 1 --recipe
"""
import argparse, json, pathlib, re, statistics, subprocess, sys, threading, time, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from scrapling.parser import Selector

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))
from errand.extract import inline_only, last_json, numbered_view, own_text, piece_text  # noqa: E402,F401
from errand import extract  # noqa: E402
from errand.brains import FLAGS, LLAMA, MODEL, URL  # noqa: E402  the engine's measured settings
PAGES = sorted((ROOT / 'cache' / 'A').glob('*.html'))
FOCUS = 'article.product_page'
FIELDS = ['title', 'price', 'availability', 'upc', 'rating']
STARS = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
SYSTEM = ('You read one product page and fill in a form. Think in at most two short sentences, '
          'then output ONE JSON object with exactly these keys: "title" (the book title), '
          '"price" (as shown, with currency symbol), "availability" (integer number of copies in stock), '
          '"upc" (the UPC code), "rating" (integer number of stars, 1-5).')
# Measured on 35 pages: asking a 2B brain for line NUMBERS scored 39% (64% with null not allowed),
# writing the value and letting code snap it to the full line scored 96%. Small brains copy well
# and count badly.
POINT_SYSTEM = ('You read one product page, shown as numbered lines: [number] tag labels: text. Output ONE JSON object '
                'with exactly these keys: "title" (copy the book title exactly as written), "price" (with currency '
                'symbol), "availability" (integer copies in stock), "upc" (the UPC code), "rating" (integer 1-5 from '
                'the class that names the star count, e.g. star-rating Three = 3).')
POINT_SCHEMA = {'type': 'object', 'properties': {'title': {'type': 'string'}, 'price': {'type': 'string'},
                'availability': {'type': 'integer'}, 'upc': {'type': 'string'},
                'rating': {'type': 'integer', 'enum': [1, 2, 3, 4, 5]}},
                'required': FIELDS, 'additionalProperties': False}
WORDS = {v: k for k, v in STARS.items()}
RECIPE_SYSTEM = ('You write a scraping recipe. Given the HTML of one product page, output ONE JSON object '
                 'mapping each key to a CSS selector that selects the element holding that value on pages '
                 'with this layout. Keys: "title", "price", "availability", "upc", "rating". '
                 'For "rating" select the element whose class names the star count. Output only the JSON.')


def truth(html):
    """The hand-written recipe. Ground truth for scoring; spot-checked by eye on sample pages."""
    s = Selector(html)
    main = s.css('div.product_main')[0]
    avail = ' '.join(main.css('p.availability ::text').getall())
    return {'title': main.css('h1::text').get().strip(),
            'price': main.css('p.price_color::text').get().strip(),
            'availability': int(re.search(r'\d+', avail).group()),
            'upc': s.css('table.table-striped tr:first-child td::text').get().strip(),
            'rating': STARS[main.css('p.star-rating')[0].attrib['class'].split()[-1]]}


def norm(field, v):
    if v is None:
        return None
    if field in ('availability', 'rating'):
        m = re.search(r'\d+', str(v))
        return int(m.group()) if m else None
    if field == 'price':
        m = re.search(r'\d+(?:\.\d+)?', str(v))
        return float(m.group()) if m else None
    return str(v).strip().casefold()


def score(answer, gt):
    return {f: norm(f, answer.get(f)) == norm(f, gt[f]) for f in FIELDS}


def page_text(html, limit=6000):
    s = Selector(html)
    block = s.css('article.product_page')
    body = (block[0] if block else s).get_all_text(separator='\n', strip=True)
    return str(body)[:limit]


def snap(value, field, els):
    """Write, then snap: the line number (1-based) of the first page piece holding the brain's
    value, or None. Code then copies that whole piece, so a shortened title comes back in full."""
    if value is None or value == '':
        return None
    for n, el in enumerate(els, 1):
        if field == 'rating':
            if WORDS.get(value) in el.attrib.get('class', '').split():
                return n
        elif field == 'availability':  # a whole number, not the ".18" inside a price like £44.18
            if re.search(rf'(?<![\d.,]){value}(?!\d|[.,]\d)', piece_text(el)):
                return n
        elif str(value).strip().casefold() in piece_text(el).casefold():
            return n
    return None


def pointed_value(el, field):
    """Code, not the brain, reads the value out of the piece the brain pointed at."""
    if field == 'rating':
        words = el.attrib.get('class', '').split()
        return STARS.get(words[-1]) if words else None
    return piece_text(el) or str(el.get_all_text(separator=' ', strip=True))


def chat(system, user, max_tokens=300, **extra):
    return extract.chat(URL, system, user, max_tokens, **extra)


class GpuSampler(threading.Thread):
    """Max dedicated VRAM (nvidia-smi) and max Windows shared GPU memory, sampled while running."""
    def __init__(self):
        super().__init__(daemon=True)
        self.stop, self.vram, self.shared = threading.Event(), 0, 0

    @staticmethod
    def shared_mib():
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              "(Get-Counter '\\GPU Adapter Memory(*)\\Shared Usage').CounterSamples | "
                              "Measure-Object CookedValue -Sum | ForEach-Object Sum"],
                             capture_output=True, text=True).stdout.strip()
        return float(out or 0) / 2**20

    def run(self):
        while not self.stop.is_set():
            v = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                               capture_output=True, text=True).stdout.strip()
            self.vram = max(self.vram, int(v or 0))
            self.shared = max(self.shared, self.shared_mib())
            self.stop.wait(1)


def start_server(np_, ctx, log, flags=FLAGS):
    cmd = [str(LLAMA), '-m', str(MODEL), '-np', str(np_), '-c', str(np_ * ctx), *flags,
           '--host', '127.0.0.1', '--port', '8080']
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(360):  # up to 3 minutes to load
        try:
            with urllib.request.urlopen(URL + '/health', timeout=2) as r:
                if r.status == 200:
                    return proc, cmd
        except OSError:
            pass
        if proc.poll() is not None:
            raise SystemExit(f'llama-server exited with code {proc.returncode}; see {log.name}')
        time.sleep(0.5)
    proc.kill()
    raise SystemExit('llama-server did not become healthy in 3 minutes')


def run_extract(np_, point=False):
    htmls = [p.read_text(encoding='utf-8') for p in PAGES]
    gts = [truth(h) for h in htmls]

    def job(k):
        i = k % len(htmls)  # with more slots than pages, pages repeat so every slot is busy at once
        points = None
        if point:  # the brain writes values in a fixed form; code snaps each to its page piece and copies it
            view, els = numbered_view(htmls[i], focus=FOCUS)
            data, secs = chat(POINT_SYSTEM, view, max_tokens=200,
                              response_format={'type': 'json_schema', 'json_schema': {'schema': POINT_SCHEMA}})
            written = last_json(data['choices'][0]['message'].get('content')) or {}
            points = {f: snap(written.get(f), f, els) for f in FIELDS} if written else {}
            answer = {f: pointed_value(els[n - 1], f) if n else written.get(f) for f, n in points.items()}
        else:
            data, secs = chat(SYSTEM, page_text(htmls[i]))
            answer = last_json(data['choices'][0]['message'].get('content')) or {}
        t = data.get('timings', {})
        return {'i': i, 'seconds': round(secs, 2), 'parsed': bool(points if point else answer),
                'score': score(answer, gts[i]), 'prompt_tokens': t.get('prompt_n'), 'gen_tokens': t.get('predicted_n'),
                'gen_tok_s': t.get('predicted_per_second'), 'answer': answer, 'points': points,
                'written': written if point else None}

    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=np_) as pool:  # exactly np_ requests in flight
        rows = list(pool.map(job, range(max(len(htmls), np_))))
    wall = time.perf_counter() - t
    lat = sorted(r['seconds'] for r in rows)
    cells = [ok for r in rows for ok in r['score'].values()]
    return rows, {
        'pages': len(rows), 'wall_seconds': round(wall, 1), 'pages_per_second': round(len(rows) / wall, 3),
        'latency_p50': lat[len(lat) // 2], 'latency_p90': lat[int(len(lat) * 0.9)],
        'mean_prompt_tokens': round(statistics.mean(r['prompt_tokens'] or 0 for r in rows)),
        'mean_gen_tok_s_per_slot': round(statistics.mean(r['gen_tok_s'] or 0 for r in rows), 1),
        'json_parse_failures': sum(not r['parsed'] for r in rows),
        'field_accuracy': round(sum(cells) / len(cells), 3),
        # rating is only in a CSS class, never in the page text the brains read
        'field_accuracy_excl_rating': round(statistics.mean(
            ok for r in rows for f, ok in r['score'].items() if f != 'rating'), 3),
        'per_field': {f: round(sum(r['score'][f] for r in rows) / len(rows), 3) for f in FIELDS}}


def replay(html, selector, field):
    el = Selector(html).css(selector)
    return pointed_value(el[0], field) if el else None


def recipe_from_points(rows, samples=5):
    """The brain never writes CSS: code turns the pieces it pointed at on 5 sample pages into
    selectors. A field gets a recipe if its selector gives back the brain's value on all samples
    but one: a vote where the page test decides, so one brain slip (say, reading another book's
    stars further down the page) can't block it. Consistent is not the same as correct, so Errand
    will also ask you to OK 3 rows per new kind of page."""
    htmls = [p.read_text(encoding='utf-8') for p in PAGES]
    first = {}
    for r in rows:
        first.setdefault(r['i'], r)
    ids = sorted(first)[:samples]
    recipe = {}
    for f in FIELDS:
        votes = Counter()
        for i in ids:
            n, els = first[i]['points'].get(f), numbered_view(htmls[i], focus=FOCUS)[1]
            if isinstance(n, int) and 1 <= n <= len(els):
                votes[els[n - 1].generate_css_selector] += 1
        for sel, _ in votes.most_common():
            if sum(replay(htmls[i], sel, f) == first[i]['answer'].get(f) for i in ids) >= max(3, len(ids) - 1):
                recipe[f] = sel
                break
    t = time.perf_counter()
    scored = [score({f: replay(h, s, f) for f, s in recipe.items()}, truth(h)) for h in htmls]
    return {'recipe': recipe, 'fields_with_recipe': len(recipe), 'brain_calls': len(ids),
            'replay_seconds_105_pages': round(time.perf_counter() - t, 3),
            'per_field': {f: round(sum(r[f] for r in scored) / len(scored), 3) for f in FIELDS}}


def run_recipe():
    htmls = [p.read_text(encoding='utf-8') for p in PAGES]
    sample = Selector(htmls[0]).css('article.product_page')[0]
    html = re.sub(r'\s+', ' ', str(sample.html_content))[:8000]
    data, write_secs = chat(RECIPE_SYSTEM, html, max_tokens=400)
    recipe = last_json(data['choices'][0]['message'].get('content')) or {}
    t = time.perf_counter()
    rows = []
    for h in htmls:
        s, got = Selector(h), {}
        for f in FIELDS:
            try:
                el = s.css(recipe.get(f, ''))
                el = el[0] if el else None
                got[f] = None if el is None else (
                    el.attrib.get('class', '') if f == 'rating' else str(el.get_all_text(separator=' ', strip=True)))
            except Exception:  # an invalid selector from the model counts as a miss, not a crash
                got[f] = None
        if got.get('rating'):
            got['rating'] = STARS.get(got['rating'].split()[-1])
        rows.append(score(got, truth(h)))
    replay = time.perf_counter() - t
    cells = [ok for r in rows for ok in r.values()]
    return {'recipe': recipe, 'write_seconds': round(write_secs, 2), 'replay_seconds_105_pages': round(replay, 3),
            'ai_calls': 1, 'field_accuracy': round(sum(cells) / len(cells), 3),
            'per_field': {f: round(sum(r[f] for r in rows) / len(rows), 3) for f in FIELDS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--np', type=int, required=True)
    ap.add_argument('--recipe', action='store_true')
    ap.add_argument('--point', action='store_true', help="point, don't write")
    ap.add_argument('--ctx', type=int, default=4096, help='tokens of memory per slot')
    a = ap.parse_args()
    assert len(PAGES) == 105, f'run bench/fetch.py first: found {len(PAGES)} cached pages'
    for h in (PAGES[0], PAGES[50], PAGES[104]):  # self-check: ground truth parses on every layout sample
        print('truth sample:', truth(h.read_text(encoding='utf-8')))

    name = 'recipe' if a.recipe else f"np{a.np}" + ('' if a.ctx == 4096 else f'-c{a.ctx}') + ('-point' if a.point else '')
    with open(ROOT / f'server-{name}.log', 'w') as log:
        baseline_shared = GpuSampler.shared_mib()
        proc, cmd = start_server(a.np, a.ctx, log)
        gpu = GpuSampler(); gpu.start()
        try:
            if a.recipe:
                summary, rows = run_recipe(), []
            else:
                rows, summary = run_extract(a.np, a.point)
                if a.point:
                    summary['recipe_from_points'] = recipe_from_points(rows)
        finally:
            gpu.stop.set(); gpu.join(); proc.terminate(); proc.wait(30)
    summary.update({'np': a.np, 'ctx_per_slot': a.ctx, 'server_cmd': ' '.join(cmd), 'max_vram_mib': gpu.vram,
                    'shared_gpu_mib_delta': round(gpu.shared - baseline_shared)})
    (ROOT / f'brains-{name}.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=2),
                                              encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
