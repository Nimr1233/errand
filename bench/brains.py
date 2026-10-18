"""Benchmark step 2 (spec section 15): N brains at once on the cached Set A pages.

Starts llama-server with N parallel slots (4,096 tokens each), sends all 105 extraction jobs
with N in flight, measures time, tokens and GPU memory, and scores answers against a
hand-written recipe (the ground truth). With --recipe it instead asks one brain to WRITE a
recipe (CSS selectors) from a sample page and replays it on all 105 pages with zero AI calls.

Run:  python -X utf8 bench/brains.py --np 53
      python -X utf8 bench/brains.py --np 1 --recipe
"""
import argparse, json, pathlib, re, statistics, subprocess, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from scrapling.parser import Selector

ROOT = pathlib.Path(__file__).parent
PAGES = sorted((ROOT / 'cache' / 'A').glob('*.html'))
LLAMA = pathlib.Path.home() / 'AppData/Local/Temp/errand/llama/llama-server.exe'
MODEL = pathlib.Path.home() / 'AppData/Local/Temp/errand/dl/Qwen3.5-2B-Q4_K_M.gguf'
URL = 'http://127.0.0.1:8080'
FIELDS = ['title', 'price', 'availability', 'upc', 'rating']
STARS = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
SYSTEM = ('You read one product page and fill in a form. Think in at most two short sentences, '
          'then output ONE JSON object with exactly these keys: "title" (the book title), '
          '"price" (as shown, with currency symbol), "availability" (integer number of copies in stock), '
          '"upc" (the UPC code), "rating" (integer number of stars, 1-5).')
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


def last_json(text):
    for m in reversed(list(re.finditer(r'\{[^{}]*\}', text or '', re.S))):
        try:
            return json.loads(m.group())
        except ValueError:
            continue
    return None


def chat(system, user, max_tokens=300):
    body = json.dumps({'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                       'max_tokens': max_tokens, 'temperature': 0}).encode()
    req = urllib.request.Request(URL + '/v1/chat/completions', body, {'Content-Type': 'application/json'})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.loads(r.read())
    return data, time.perf_counter() - t


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


def start_server(np_, log):
    cmd = [str(LLAMA), '-m', str(MODEL), '-np', str(np_), '-c', str(np_ * 4096), '-ngl', '99',
           '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0', '-ctxcp', '2', '-cram', '2048',
           '--reasoning-budget', '0', '--host', '127.0.0.1', '--port', '8080']
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


def run_extract(np_):
    htmls = [p.read_text(encoding='utf-8') for p in PAGES]
    gts = [truth(h) for h in htmls]

    def job(i):
        data, secs = chat(SYSTEM, page_text(htmls[i]))
        msg = data['choices'][0]['message']
        answer = last_json(msg.get('content')) or {}
        t = data.get('timings', {})
        return {'i': i, 'seconds': round(secs, 2), 'parsed': bool(answer), 'score': score(answer, gts[i]),
                'prompt_tokens': t.get('prompt_n'), 'gen_tokens': t.get('predicted_n'),
                'gen_tok_s': t.get('predicted_per_second'), 'answer': answer}

    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=np_) as pool:  # exactly np_ requests in flight
        rows = list(pool.map(job, range(len(htmls))))
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
    a = ap.parse_args()
    assert len(PAGES) == 105, f'run bench/fetch.py first: found {len(PAGES)} cached pages'
    for h in (PAGES[0], PAGES[50], PAGES[104]):  # self-check: ground truth parses on every layout sample
        print('truth sample:', truth(h.read_text(encoding='utf-8')))

    name = f"recipe" if a.recipe else f"np{a.np}"
    with open(ROOT / f'server-{name}.log', 'w') as log:
        baseline_shared = GpuSampler.shared_mib()
        proc, cmd = start_server(a.np, log)
        gpu = GpuSampler(); gpu.start()
        try:
            if a.recipe:
                summary, rows = run_recipe(), []
            else:
                rows, summary = run_extract(a.np)
        finally:
            gpu.stop.set(); gpu.join(); proc.terminate(); proc.wait(30)
    summary.update({'np': a.np, 'server_cmd': ' '.join(cmd), 'max_vram_mib': gpu.vram,
                    'shared_gpu_mib_delta': round(gpu.shared - baseline_shared)})
    (ROOT / f'brains-{name}.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=2),
                                              encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
