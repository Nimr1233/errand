"""The scoreboard and guard (harness tuner). Runs the brains on the frozen 4-site test set
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

Phase 3, the fix loop: runs also ask the held-out pages (bench/holdout_truth.json, made by
testset.py --holdout), which were never looked at while writing fixes. A fix is kept only when, on
the held-out pages, it makes more items right than it makes wrong (majority over the runs).
  prompt and view fixes change what the brain reads, so they need a new brain run, and their held-out gain
               must beat the wobble between two runs of the same settings (p3-base vs p3-base2)
  post fixes   change what code does with the brain's written answer, so they are re-scored on the
               very same answers (--rescore): no brain noise at all
  vote (round 2) a post fix across pages: recipes are learned from the brains' majority answers on
               the test set pages only (never the answer key), then replayed on every page; on the
               held-out pages that is a recipe checked on pages it wasn't made from

Run:  python -X utf8 bench/score.py --variant base --runs 5
      python -X utf8 bench/score.py --compare base rea-off
      python -X utf8 bench/score.py --rescore p3-base p3-tail
      python -X utf8 bench/score.py --engine p3-engine-run  (errand.extract.read_pages on saved answers, 5 samples per set)
"""
import argparse, json, math, pathlib, random, re, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import brains as b  # noqa: E402  (also puts the repo on the path)
from errand import extract as x  # noqa: E402  the engine's page reader: what this scoreboard measures

ROOT = pathlib.Path(__file__).parent
SETS = {s: ROOT / 'cache' / s for s in ('testset', 'holdout', 'fresh')}  # fresh: only for checking the engine (section 8)
TRUTHS = {s: json.loads((ROOT / f'{s}_truth.json').read_text(encoding='utf-8')) for s in SETS
          if (ROOT / f'{s}_truth.json').exists()}
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
DATES = {'born_date', 'published'}
PROMPT_FIXES = {  # written from the testset failures only
    'once': 'A piece without ×N appears once.',  # webscraper/06: one star icon read as 5
    'heading': 'Take names and titles from headings and short labelled pieces, not from long description text.'}  # quotes/09
VIEW_FIXES = {'nostyle': x.SKIP}  # bug: Wikipedia's infobox CSS was shown to the brain
POST_FIXES = {'tail', 'ground', 'date', 'vote'}  # see finish() and vote()
OLD = [f for f in b.FLAGS if f not in ('-rea', 'off')] + ['--reasoning-budget', '0']  # before phase 1
VARIANTS = {  # name: (server flags, answer form on, fixes)
    'base': (OLD, True, ()),
    'rea-off': (b.FLAGS, True, ()),
    'ctxcp4': ([('4' if f == '2' and OLD[i - 1] == '-ctxcp' else f) for i, f in enumerate(OLD)], True, ()),
    'noschema': (OLD, False, ()),
    # phase 3: today's settings on both sets, a second run of the same to measure wobble, then one fix each
    'p3-base': (b.FLAGS, True, ()), 'p3-base2': (b.FLAGS, True, ()),
    **{f'p3-{f}': (b.FLAGS, True, (f,)) for f in [*PROMPT_FIXES, *VIEW_FIXES, *sorted(POST_FIXES)]},
    'p3-nostyle-date': (b.FLAGS, True, ('nostyle', 'date')),
    'p3-nostyle-date-ground': (b.FLAGS, True, ('nostyle', 'date', 'ground')),  # round 1's winner: start round 2 here
    'p3-r2-vote': (b.FLAGS, True, ('nostyle', 'date', 'ground', 'vote')),  # round 2's winner: start round 3 here
    # the same vote learned from a second brain run, to check the recipes are stable
    'p3-date-ground': (b.FLAGS, True, ('date', 'ground')), 'p3-date-ground-vote': (b.FLAGS, True, ('date', 'ground', 'vote')),
    # the engine (errand/extract.py) checked on all three sets, with fresh brain answers: see engine()
    'p3-engine-run': (b.FLAGS, True, ('nostyle', 'date', 'ground')),
    'p3-engine-run-vote': (b.FLAGS, True, ('nostyle', 'date', 'ground', 'vote'))}


def typed(site):
    """A site's FIELDS the way the engine takes them: each with its kind."""
    return {f: (d, 'number' if f in NUMBERS else 'date' if f in DATES else 'text') for f, d in FIELDS[site].items()}


def system_prompt(site, fixes=()):
    return x.system_prompt(typed(site), ' '.join(PROMPT_FIXES[f] for f in fixes if f in PROMPT_FIXES))


def schema(site):
    return x.schema(typed(site))


TAIL = re.compile(r'(?:,\s*[^,.;:()\[\]]+)+')  # ", South Gloucestershire, England" up to the piece's end


def snap_text(value, els, fixes=()):
    """The engine's snap, plus the dropped 'tail' fix: an answer found inside a piece and followed only
    by a comma list to the piece's end ("Paris" in "Born: November 22, 1869 in Paris, France") came
    back with that list. It broke a held-out publisher, so it is not in the engine."""
    v = re.sub(r'\s+', ' ', str(value)).strip().casefold()
    pieces = [x.clean_piece(el) for el in els]
    if 'tail' in fixes and v and not any(t.casefold().startswith(v) for t in pieces):
        for t in pieces:
            for m in re.finditer(rf'(?<!\w){re.escape(v)}(?!\w)', t.casefold()):
                if TAIL.fullmatch(t[m.end():]):
                    return t[m.start():]
    return x.snap_text(value, els)


def finish(site, written, view, els, fixes=()):
    """Code's part after the brain writes. With round 1's winners (date, ground) this is the engine's
    finish(); other mixes, kept to reproduce earlier rounds, are put together from the engine's parts."""
    if {'date', 'ground'} <= set(fixes) and 'tail' not in fixes:
        return x.finish(typed(site), written, view, els)
    out = {}
    for f, v in (written or {}).items():
        if f not in FIELDS[site]:
            continue
        if f in NUMBERS:
            if 'ground' in fixes and v is not None and not (isinstance(v, int) and x.on_page(v, view)):
                v = None
        elif isinstance(v, str):
            v = snap_text(v, els, fixes)
            if 'date' in fixes and f in DATES:  # a date field holds one date: Moby-Dick lists the UK and US dates
                v = x.first_date(v)
        out[f] = v
    return out


def vote(rows, fixes):
    """'vote' fix: the engine's learn_recipe() on each site's 10 test set pages, fed the brains'
    majority answer per page over the runs (never the answer key). The recipe's value then replaces
    the brain's on every page of both sets."""
    skip = view_skip(fixes)
    recipes = {}
    for site in FIELDS:
        mine = [r for r in rows if r.get('set', 'testset') == 'testset' and r['site'] == site]
        samples = []
        for k in sorted({r['page'] for r in mine}):
            said = [r['answers'] for r in mine if r['page'] == k]
            samples.append((page('testset', site, k), {f: max(v := [a.get(f) for a in said], key=v.count)  # a tie goes to the first seen
                                                       for f in FIELDS[site]}))
        recipes[site] = x.learn_recipe(samples, typed(site), focus=FOCUS[site], skip=skip)
    out = [{**r, 'answers': {**r['answers'], **x.replay(page(r.get('set', 'testset'), r['site'], r['page']),
                                                        recipes[r['site']], typed(r['site']))}} for r in rows]
    return out, {f'{s}.{f}': list(key) for s, rec in recipes.items() for f, key in rec.items()}


def perfect_brain(fixes=()):
    """Feed the answer key in as if a brain wrote it: every item code's part spoils is a harness bug."""
    lost = []
    for s, truth in TRUTHS.items():
        for site, rows in truth.items():
            for k, r in enumerate(rows):
                got = finish(site, r['answers'], *page_view(s, site, k, fixes), fixes)
                lost += [f'{s} {site}/{k:02d} {f}' for f, t in r['answers'].items() if not correct(f, got[f], t)]
    return lost


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


PAGES = {}


def page(set_, site, k):
    if (set_, site, k) not in PAGES:
        PAGES[(set_, site, k)] = x.as_page((SETS[set_] / site / f'{k:02d}.html').read_text(encoding='utf-8'))
    return PAGES[(set_, site, k)]


def view_skip(fixes):
    return tuple(t for f in fixes for t in VIEW_FIXES.get(f, ()))


def page_view(set_, site, k, fixes=()):
    return x.numbered_view(page(set_, site, k), focus=FOCUS[site], skip=view_skip(fixes))


def ask(set_, site, k, use_schema, fixes=()):
    view, els = page_view(set_, site, k, fixes)
    extra = {'response_format': {'type': 'json_schema', 'json_schema': {'schema': schema(site)}}} if use_schema else {}
    data, secs = b.chat(system_prompt(site, fixes), view, max_tokens=300, **extra)
    content = data['choices'][0]['message'].get('content') or ''
    written = x.last_json(content)
    t = data.get('timings', {})
    return {'set': set_, 'site': site, 'page': k, 'seconds': round(secs, 2), 'valid_json': written is not None,
            'thinking_leak': '<think>' in content, 'written': written,
            'answers': finish(site, written, view, els, fixes), 'raw': content[:400],
            'prompt_tokens': t.get('prompt_n'), 'cached_tokens': t.get('cache_n'), 'gen_tokens': t.get('predicted_n')}


def bootstrap(pages, draws=2000, seed=0):
    """95% interval for accuracy, resampling whole pages. pages: list of (correct, total)."""
    rng = random.Random(seed)
    accs = sorted(sum(c for c, _ in s) / sum(n for _, n in s) for s in
                  ([rng.choice(pages) for _ in pages] for _ in range(draws)))
    return accs[int(draws * 0.025)], accs[int(draws * 0.975)]


def summarize(rows, runs, TRUTH):
    """Per item: how often right over the runs. Per site: accuracy, page-bootstrap interval, wobble.
    `rows` and `TRUTH` belong to one set."""
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


def of_set(rows, s):
    return [r for r in rows if r.get('set', 'testset') == s]  # runs from before phase 3 hold the testset only


def report(rows, runs):
    out = {}
    for s, truth in TRUTHS.items():
        if of_set(rows, s):
            scores, wrong, _ = summarize(of_set(rows, s), runs, truth)
            out[s] = {'scores': scores, 'wrong_most_runs': wrong}
    return out


def run(variant, runs, np_=53):
    flags, use_schema, fixes = VARIANTS[variant]
    jobs = [(s, site, k) for _ in range(runs) for s, truth in TRUTHS.items() for site in truth for k in range(len(truth[site]))]
    with open(ROOT / f'server-score-{variant}.log', 'w') as log:
        proc, cmd = b.start_server(np_, 4096, log, flags)
        try:
            t = time.perf_counter()
            with ThreadPoolExecutor(np_) as pool:
                rows = list(pool.map(lambda j: ask(*j, use_schema, fixes), jobs))
            wall = time.perf_counter() - t
        finally:
            proc.terminate(); proc.wait(30)
    rows, recipes = vote(rows, fixes) if 'vote' in fixes else (rows, None)
    speed = {'pages_per_second': round(len(rows) / wall, 2), 'wall_seconds': round(wall, 1),
             'valid_json': sum(r['valid_json'] for r in rows) / len(rows),
             'thinking_leaks': sum(r['thinking_leak'] for r in rows),
             'mean_prompt_tokens': round(statistics.mean(r['prompt_tokens'] or 0 for r in rows)),
             'mean_cached_tokens': round(statistics.mean(r['cached_tokens'] or 0 for r in rows), 1),
             'latency_p50': sorted(r['seconds'] for r in rows)[len(rows) // 2]}
    out = {'variant': variant, 'runs': runs, 'server_cmd': ' '.join(cmd), 'fixes': list(fixes), 'recipes': recipes,
           'sets': report(rows, runs), 'speed': speed, 'rows': rows}
    (ROOT / f'score-{variant}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    return out


def rescore(src, dst):
    """A post fix, scored on the very same written answers as `src`: no new brain run, no brain noise."""
    (fa, sa, xa), (fb, sb, xb) = VARIANTS[src], VARIANTS[dst]
    assert (fa, sa) == (fb, sb) and set(xa) - POST_FIXES == set(xb) - POST_FIXES, 'only post fixes may differ'
    A = json.loads((ROOT / f'score-{src}.json').read_text(encoding='utf-8'))
    views, rows = {}, []
    for r in A['rows']:
        key = (r['set'], r['site'], r['page'])
        if key not in views:
            views[key] = page_view(*key, xb)
        rows.append({**r, 'answers': finish(r['site'], r['written'], *views[key], xb)})
    rows, recipes = vote(rows, xb) if 'vote' in xb else (rows, None)
    out = {**A, 'variant': dst, 'fixes': list(xb), 'rescored_from': src, 'recipes': recipes,
           'sets': report(rows, A['runs']), 'rows': rows}
    (ROOT / f'score-{dst}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    return out


def engine(src, out_name='engine', samples=5, learn_on=None):
    """The engine's own flow (errand.extract.read_pages) on saved brain answers. No new brain run:
    the "brain" hands back what the src run wrote for that page, one run at a time.
    learn_on=None: per set and site, brains read the first `samples` of its 10 pages, a recipe is
      learned from those answers alone, and code reads every page.
    learn_on='testset': the recipe is learned once from the 10 test set pages, then reused on every
      set, the way a recipe learned for a kind of page is kept for later pages of that kind.
    Fields with no recipe use the brain's answer."""
    A = json.loads((ROOT / f'score-{src}.json').read_text(encoding='utf-8'))
    fixes = VARIANTS[src][2]
    assert 'nostyle' in fixes, 'the engine hides style and script, so its views must match what the brain saw'
    rows, calls, recipes_seen = [], {}, {}
    for run in range(A['runs']):
        def read(s, site, n, recipe=None):
            ks = range(len(TRUTHS[s][site]))
            said = {page_view(s, site, k, fixes)[0]: [r for r in A['rows'] if r['set'] == s and r['site'] == site
                                                       and r['page'] == k][run]['written'] for k in ks}
            asked = []
            got, recipe = x.read_pages([page(s, site, k) for k in ks], typed(site),
                                       lambda view, fields: asked.append(view) or said[view],
                                       samples=n, recipe=recipe, focus=FOCUS[site], workers=1)
            calls[s] = calls.get(s, 0) + len(asked)
            return got, recipe
        learned = {site: read(learn_on, site, 10)[1] for site in FIELDS} if learn_on else {}
        for site, rec in learned.items():
            recipes_seen.setdefault(site, set()).add(tuple(sorted(rec)))
        for s, truth in TRUTHS.items():
            for site in truth:
                got, _ = read(s, site, samples, learned.get(site))
                rows += [{'set': s, 'site': site, 'page': k, 'answers': a} for k, a in enumerate(got)]
    out = {**A, 'variant': out_name, 'engine_from': src, 'min_hits': x.MIN_HITS, 'samples': samples, 'learn_on': learn_on,
           'fixes': ['engine'], 'recipes': {site: [list(r) for r in v] for site, v in recipes_seen.items()} or None,
           'brain_calls': {s: f'{n} of {sum(len(t) for t in TRUTHS[s].values()) * A["runs"]}' for s, n in calls.items()},
           'sets': report(rows, A['runs']), 'rows': rows}
    (ROOT / f'score-{out_name}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    return out


def compare(a, b_):
    """Per set, paired on the same items: majority-vote right/wrong per item, exact McNemar, page-bootstrap gap."""
    A, B = (json.loads((ROOT / f'score-{v}.json').read_text(encoding='utf-8')) for v in (a, b_))
    out = {s: compare_set(of_set(A['rows'], s), A['runs'], of_set(B['rows'], s), B['runs'], truth)
           for s, truth in TRUTHS.items() if of_set(A['rows'], s) and of_set(B['rows'], s)}
    return {'a': a, 'b': b_, **out, 'speed_a': A['speed']['pages_per_second'], 'speed_b': B['speed']['pages_per_second']}


def compare_set(rows_a, runs_a, rows_b, runs_b, truth):
    sa, _, ia = summarize(rows_a, runs_a, truth)
    sb, _, ib = summarize(rows_b, runs_b, truth)
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
    flips = lambda right_in_a: sorted(f'{s}/{pg:02d} {f}' for (s, pg, f), v in ia.items()
                                      if maj(v) == right_in_a and maj(ib[(s, pg, f)]) != right_in_a)
    return {'accuracy_a': sa['all']['accuracy'], 'accuracy_b': sb['all']['accuracy'],
            'gap_b_minus_a': round(sum(d for d, _ in diff) / sum(c for _, c in diff), 3),
            'gap_ci95': [round(draws[50], 3), round(draws[1949], 3)], 'right_only_in_a': only_a, 'right_only_in_b': only_b,
            'mcnemar_p': round(p, 4), 'fixed': flips(False), 'broken': flips(True)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', choices=list(VARIANTS))
    ap.add_argument('--runs', type=int, default=5)
    ap.add_argument('--compare', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--rescore', nargs=2, metavar=('FROM', 'TO'))
    ap.add_argument('--engine', metavar='FROM', help="the engine's read_pages() flow on a saved run's answers")
    ap.add_argument('--perfect-brain', action='store_true', help='how many right answers code spoils, per fix')
    a = ap.parse_args()
    if a.perfect_brain:
        for fixes in [(), *[(f,) for f in sorted(POST_FIXES - {'vote'})], tuple(sorted(POST_FIXES - {'vote'}))]:  # vote works across pages, not one page
            lost = perfect_brain(fixes)
            print(f"{'+'.join(fixes) or 'no fixes'}: a perfect brain loses {len(lost)}", lost)
        return
    if a.compare:
        print(json.dumps(compare(*a.compare), indent=1))
        return
    out = engine(a.engine) if a.engine else rescore(*a.rescore) if a.rescore else run(a.variant, a.runs)
    if a.engine:
        print('brain calls:', out['brain_calls'])
    print(json.dumps({'variant': out['variant'], 'speed': out['speed']}, ensure_ascii=False))
    for s, rep in out['sets'].items():
        print(f'== {s}:', json.dumps({k: v['accuracy'] for k, v in rep['scores'].items()}))
        print(f"   wrong in most runs: {len(rep['wrong_most_runs'])} items")
        for w in rep['wrong_most_runs']:
            print('  ', json.dumps(w, ensure_ascii=False)[:220])


if __name__ == '__main__':
    main()
