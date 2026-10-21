"""The scoreboard and guard (harness tuner, phase 1). Runs the brains on the frozen 4-site test set
(bench/testset_truth.json, pages saved in bench/cache/testset) several times in one mixed batch and
scores every site with honest error bars.

Scoring rules:
- a wrong "none" on a real answer and a made-up value on a "none" item are both errors
- error bars resample whole pages (2,000 bootstrap draws), because one page's answers stand or fall
  together; 190 answers can only show differences of about 5 points
- --runs 5 asks every page 5 times, mixed in one batch, so run-to-run wobble is measured

Variants (A/B tests of server and answer settings) write bench/score-<variant>.json:
  base     the starting settings: --reasoning-budget 0, -ctxcp 2, JSON-schema answer form
  rea-off  -rea off instead of --reasoning-budget 0 (which turns GPU sampling off). Won on speed
           at equal accuracy, so it is now brains.FLAGS
  ctxcp4   -ctxcp 4, so the shared start of the prompt can stay cached
  noschema plain JSON answers parsed by code, no grammar (the grammar halves decode speed)

Run:  python -X utf8 bench/score.py --variant base --runs 5
      python -X utf8 bench/score.py --compare base rea-off
"""
import argparse, json, math, pathlib, random, re, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import brains as b  # noqa: E402

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / 'cache' / 'testset'
TRUTH = json.loads((ROOT / 'testset_truth.json').read_text(encoding='utf-8'))
FOCUS = {'books': 'article.product_page', 'quotes': 'div.author-details', 'webscraper': 'div.thumbnail',
         'wikipedia': 'table.infobox'}  # each site's main block; a real engine finds this itself
FIELDS = {  # what each field is, in the words the brain reads
    'books': {'title': 'the book title', 'price': 'the price with currency symbol',
              'availability': 'integer copies in stock', 'upc': 'the UPC code',
              'rating': 'integer 1-5 from the class that names the star count, e.g. star-rating Three = 3'},
    'quotes': {'name': "the author's name", 'born_date': 'the birth date as written',
               'born_location': "the birth place as written, without the word 'in'"},
    'webscraper': {'title': 'the product title', 'price': 'the price with currency symbol',
                   'description': 'the product description', 'reviews': 'integer number of reviews',
                   'rating': 'integer number of stars (the ×N after the star icon)'},
    'wikipedia': {'title': "the book's title from the infobox heading", 'author': 'the author',
                  'publisher': 'the publisher as written', 'published': 'the first publication date as written',
                  'pages': 'integer page count', 'oclc': 'the OCLC number'}}
NUMBERS = {'availability', 'rating', 'reviews', 'pages'}
OLD = [f for f in b.FLAGS if f not in ('-rea', 'off')] + ['--reasoning-budget', '0']  # before phase 1
VARIANTS = {
    'base': (OLD, True),
    'rea-off': (b.FLAGS, True),
    'ctxcp4': ([('4' if f == '2' and OLD[i - 1] == '-ctxcp' else f) for i, f in enumerate(OLD)], True),
    'noschema': (OLD, False)}


def system_prompt(site):
    keys = ', '.join(f'"{k}" ({v})' for k, v in FIELDS[site].items())
    return ('You read one web page, shown as numbered lines: [number] tag labels: text. A repeated empty piece '
            f'ends in ×N, the number of copies. Output ONE JSON object with exactly these keys: {keys}. '
            'Copy text exactly as written on the page. Use null only when the page truly does not show it.')


def schema(site):
    return {'type': 'object', 'additionalProperties': False, 'required': list(FIELDS[site]),
            'properties': {k: {'type': ['integer' if k in NUMBERS else 'string', 'null']} for k in FIELDS[site]}}


def snap_text(value, els):
    """Copy a whole page piece only when the brain's answer is how that piece starts (a cut-short
    title comes back whole). Otherwise keep the brain's words: on quotes one line holds both the
    birth date and the place, and copying the line would spoil both."""
    v = re.sub(r'\s+', ' ', str(value)).strip().casefold()
    for el in els:
        t = re.sub(r'\s*\[\s*\w+\s*\]', '', b.piece_text(el))  # footnote marks like [ 1 ] are never data
        if v and t.casefold().startswith(v):
            return t
    return value


def norm(v):  # case, spacing and a leading "in " don't count
    return re.sub(r'^in ', '', re.sub(r'\s+', ' ', str(v)).strip().casefold())


def correct(field, answer, truth):
    """Wrong "none" and made-up values on "none" items are both errors."""
    if truth is None or answer in (None, ''):
        return truth is None and answer in (None, '')
    if isinstance(truth, int):
        m = re.search(r'\d[\d,]*', str(answer))
        return bool(m) and int(m.group().replace(',', '')) == truth
    if field == 'price':
        a, t = (re.search(r'\d+(?:\.\d+)?', str(x).replace(',', '')) for x in (answer, truth))
        return bool(a and t) and float(a.group()) == float(t.group())
    return norm(answer) == norm(truth)


def ask(site, k, use_schema):
    html = (CACHE / site / f'{k:02d}.html').read_text(encoding='utf-8')
    view, els = b.numbered_view(html, focus=FOCUS[site])
    extra = {'response_format': {'type': 'json_schema', 'json_schema': {'schema': schema(site)}}} if use_schema else {}
    data, secs = b.chat(system_prompt(site), view, max_tokens=300, **extra)
    content = data['choices'][0]['message'].get('content') or ''
    written = b.last_json(content)
    answers = {f: (snap_text(v, els) if f not in NUMBERS and isinstance(v, str) else v)
               for f, v in (written or {}).items() if f in FIELDS[site]}
    t = data.get('timings', {})
    return {'site': site, 'page': k, 'seconds': round(secs, 2), 'valid_json': written is not None,
            'thinking_leak': '<think>' in content, 'answers': answers, 'raw': content[:400],
            'prompt_tokens': t.get('prompt_n'), 'cached_tokens': t.get('cache_n'), 'gen_tokens': t.get('predicted_n')}


def bootstrap(pages, draws=2000, seed=0):
    """95% interval for accuracy, resampling whole pages. pages: list of (correct, total)."""
    rng = random.Random(seed)
    accs = sorted(sum(c for c, _ in s) / sum(n for _, n in s) for s in
                  ([rng.choice(pages) for _ in pages] for _ in range(draws)))
    return accs[int(draws * 0.025)], accs[int(draws * 0.975)]


def summarize(rows, runs):
    """Per item: how often right over the runs. Per site: accuracy, page-bootstrap interval, wobble."""
    items = {}
    for r in rows:
        truth = TRUTH[r['site']][r['page']]['answers']
        for f, t in truth.items():
            items.setdefault((r['site'], r['page'], f), []).append(correct(f, r['answers'].get(f), t))
    out = {}
    for site in TRUTH:
        pages = []
        for k in range(len(TRUTH[site])):
            hits = [sum(v) / len(v) for (s, p, f), v in items.items() if s == site and p == k]
            pages.append((sum(hits), len(hits)))
        lo, hi = bootstrap(pages)
        per_run = []
        for run in range(runs):  # the run-th answer of every item
            cells = [v[run] for (s, _, _), v in items.items() if s == site and len(v) > run]
            per_run.append(sum(cells) / len(cells))
        out[site] = {'accuracy': round(sum(c for c, _ in pages) / sum(n for _, n in pages), 3),
                     'ci95': [round(lo, 3), round(hi, 3)], 'runs_min_max': [round(min(per_run), 3), round(max(per_run), 3)]}
    allp = [(sum(sum(v) / len(v) for (s, p, f), v in items.items() if s == site and p == k),
             sum(1 for (s, p, f) in items if s == site and p == k)) for site in TRUTH for k in range(len(TRUTH[site]))]
    lo, hi = bootstrap(allp)
    out['all'] = {'accuracy': round(sum(c for c, _ in allp) / sum(n for _, n in allp), 3), 'ci95': [round(lo, 3), round(hi, 3)],
                  'unstable_items': sum(0 < sum(v) < len(v) for v in items.values()),
                  'none_items_wrong': sum(1 for (s, p, f), v in items.items()
                                          if TRUTH[s][p]['answers'][f] is None and sum(v) < len(v)),
                  'false_none': sum(1 for r in rows for f, t in TRUTH[r['site']][r['page']]['answers'].items()
                                    if t is not None and r['answers'].get(f) in (None, ''))}
    wrong = [{'item': f'{s}/{p:02d} {f}', 'truth': TRUTH[s][p]['answers'][f], 'right_runs': f'{sum(v)}/{len(v)}',
              'brain': [r['answers'].get(f) for r in rows if r['site'] == s and r['page'] == p][:runs]}
             for (s, p, f), v in sorted(items.items()) if sum(v) * 2 < len(v)]  # wrong in most runs
    return out, wrong, items


def run(variant, runs, np_=53):
    flags, use_schema = VARIANTS[variant]
    jobs = [(site, k) for _ in range(runs) for site in TRUTH for k in range(len(TRUTH[site]))]
    with open(ROOT / f'server-score-{variant}.log', 'w') as log:
        proc, cmd = b.start_server(np_, 4096, log, flags)
        try:
            t = time.perf_counter()
            with ThreadPoolExecutor(np_) as pool:
                rows = list(pool.map(lambda j: ask(j[0], j[1], use_schema), jobs))
            wall = time.perf_counter() - t
        finally:
            proc.terminate(); proc.wait(30)
    scores, wrong, _ = summarize(rows, runs)
    speed = {'pages_per_second': round(len(rows) / wall, 2), 'wall_seconds': round(wall, 1),
             'valid_json': sum(r['valid_json'] for r in rows) / len(rows),
             'thinking_leaks': sum(r['thinking_leak'] for r in rows),
             'mean_prompt_tokens': round(statistics.mean(r['prompt_tokens'] or 0 for r in rows)),
             'mean_cached_tokens': round(statistics.mean(r['cached_tokens'] or 0 for r in rows), 1),
             'latency_p50': sorted(r['seconds'] for r in rows)[len(rows) // 2]}
    out = {'variant': variant, 'runs': runs, 'server_cmd': ' '.join(cmd), 'scores': scores, 'speed': speed,
           'wrong_most_runs': wrong, 'rows': rows}
    (ROOT / f'score-{variant}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    return out


def compare(a, b_):
    """Paired on the same items: majority-vote right/wrong per item, exact McNemar, page-bootstrap gap."""
    A, B = (json.loads((ROOT / f'score-{v}.json').read_text(encoding='utf-8')) for v in (a, b_))
    _, _, ia = summarize(A['rows'], A['runs'])
    _, _, ib = summarize(B['rows'], B['runs'])
    maj = lambda v: sum(v) * 2 > len(v)
    only_a = sum(maj(ia[k]) and not maj(ib[k]) for k in ia)
    only_b = sum(maj(ib[k]) and not maj(ia[k]) for k in ia)
    n, k = only_a + only_b, min(only_a, only_b)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    pages = sorted({(s, pg) for s, pg, _ in ia})
    diff = [(sum(sum(ib[x]) / len(ib[x]) - sum(ia[x]) / len(ia[x]) for x in ia if x[:2] == pg),
             sum(1 for x in ia if x[:2] == pg)) for pg in pages]
    rng = random.Random(1)
    draws = sorted(sum(d for d, _ in s) / sum(c for _, c in s) for s in ([rng.choice(diff) for _ in diff] for _ in range(2000)))
    return {'a': a, 'b': b_, 'accuracy_a': A['scores']['all']['accuracy'], 'accuracy_b': B['scores']['all']['accuracy'],
            'gap_b_minus_a': round(sum(d for d, _ in diff) / sum(c for _, c in diff), 3),
            'gap_ci95': [round(draws[50], 3), round(draws[1949], 3)], 'right_only_in_a': only_a, 'right_only_in_b': only_b,
            'mcnemar_p': round(p, 4), 'speed_a': A['speed']['pages_per_second'], 'speed_b': B['speed']['pages_per_second']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', choices=list(VARIANTS))
    ap.add_argument('--runs', type=int, default=5)
    ap.add_argument('--compare', nargs=2, metavar=('A', 'B'))
    a = ap.parse_args()
    if a.compare:
        print(json.dumps(compare(*a.compare), indent=1))
        return
    out = run(a.variant, a.runs)
    print(json.dumps({k: out[k] for k in ('variant', 'scores', 'speed')}, indent=1, ensure_ascii=False))
    print(f"wrong in most runs: {len(out['wrong_most_runs'])} items")
    for w in out['wrong_most_runs']:
        print(' ', json.dumps(w, ensure_ascii=False)[:220])


if __name__ == '__main__':
    main()
