"""The 4B senior, measured (bench/results.md section 16): how often are its hard calls wrong?
The senior has two jobs in the engine, and each is asked here the way the engine asks it:
- fix: a field most pages of a kind have (4 in 5) came back empty from the 2B. The senior re-reads the
  whole page (extract.read_page, no recipe) and only the empty fields are filled (engine._maybe_fix).
- click: "what do I click?" (clicks.llama_chooser). Each step is scored for the 2B alone, the 4B alone
  and the engine's rule on those same two picks (clicks.senior_chooser, section 17).
Both brains read the same 120 saved pages of bench/cache/{testset,holdout,fresh}, with answer keys.
Click steps are written here with their right answers; None means nothing on the page does it.

The 4B runs on the GPU here, so the run takes minutes, not hours. The engine runs it on the CPU, so a few
calls are repeated on the CPU to time them and to check that they give the same answers.
shortcut: what may be clicked is read from the saved HTML with the engine's CSS selector and safety rule,
not from a live window (no visibility check); use a browser if a site hides menus.

Run:  python -X utf8 bench/senior.py      (writes bench/score-senior.json)
      python -X utf8 bench/senior.py --rescore   (a changed click rule on the saved picks: no brain run)
"""
import json, pathlib, statistics, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import score as sc  # noqa: E402  (the scoreboard: pages, fields, answer keys, correct())
from errand import brains as eb, clicks, extract as x  # noqa: E402
from scrapling.parser import Selector  # noqa: E402

ROOT = pathlib.Path(__file__).parent
SEL = ('a[href], button, [role=button], [role=tab], [role=option], [role=radio], input[type=button], '
       'input[type=radio], input[type=checkbox], input[type=submit], summary')  # clicks.CANDIDATES_JS
BOOKS_URL = 'https://books.toscrape.com/catalogue/a-book_1/index.html'  # its saved links are relative
DEBATABLE = "open this book's category"  # both brains pick "Books" over "Poetry" (section 16)
OUT = ROOT / 'score-senior.json'


def offered(set_, site, k):
    """What the engine would offer to click on this saved page: the elements CANDIDATES_JS collects
    (first 400), then clicks.safe()."""
    url = sc.TRUTHS[set_][site][k]['url']
    url = url if url.startswith('http') else BOOKS_URL
    doc = Selector((sc.SETS[set_] / site / f'{k:02d}.html').read_text(encoding='utf-8'))
    out = []
    for e in list(doc.css(SEL))[:400]:
        a, tag, ups = e.attrib, e.tag, [e]
        while ups[-1].parent is not None:
            ups.append(ups[-1].parent)
        c = {'tag': tag, 'type': a.get('type', '').lower(), 'text': ' '.join(e.get_all_text().split())[:80],
             'title': a.get('title', ''), 'aria': a.get('aria-label', ''), 'value': a.get('value', ''),
             'href': urllib.parse.urljoin(url, a['href']) if tag == 'a' else '', 'role': a.get('role', ''),
             'disabled': 'disabled' in a or 'disabled' in a.get('class', '').split() or a.get('aria-disabled') == 'true',
             'form': any(p.tag == 'form' for p in ups[1:]), 'cls': ' '.join(a.get('class', '').split())[:60]}
        if clicks.safe(c, url)[0]:
            out.append(c)
    return out


def steps(set_, site, k, offer):
    """The click steps for one page, each with the names that are right (None: nothing fits)."""
    names = {x.core(clicks.name(c)) for c in offer}
    have = lambda *n: {m for m in n if x.core(m) in names}  # noqa: E731
    truth = sc.TRUTHS[set_][site][k]['answers']
    if site == 'books':
        cat = [clicks.name(c) for c in offer if '/category/books/' in c['href'] and clicks.name(c) != 'Books']
        s = [("open this book's category", set(cat[:1])), ('go back to the home page', have('Home', 'Books to Scrape'))]
    elif site == 'quotes':
        s = [('go back to the list of quotes', have('Quotes to Scrape'))]
    elif site == 'webscraper':  # a size the laptop can't have is a disabled button, so it isn't offered
        sizes = sorted(int(n) for n in names if n in ('128', '256', '512', '1024'))
        s = [('click the 256 option', have('256')), ('choose the 512 GB hard drive', have('512')),
             ('pick the largest storage size', {str(sizes[-1])}), ('pick the smallest storage size', {str(sizes[0])}),
             ('go to the phones section', have('Phones')), ('select 1 TB of storage', have('1024') or None)]
    else:
        s = [("open the Wikipedia article about the book's author", have(truth['author'])),
             ("go to Wikipedia's main page", have('Main page')), ('show me a random article', have('Random article')),
             ("open this article's talk page", have('Talk')), ("see this article's edit history", have('View history'))]
    s = [(step, ok) for step, ok in s if ok != set()]  # a right answer that isn't offered: drop the step
    return s + [('choose the 2 TB option', None), ("open the author's Goodreads page", None)]


def score_click(offer, pick, ok):
    """'right', 'wrong click' (it would press something else), or 'no click' (the step fails safely)."""
    el = clicks.find(offer, pick)[0]
    if el is None:
        return 'right' if ok is None else 'no click'
    return 'right' if ok and x.core(clicks.name(el)) in {x.core(n) for n in ok} else 'wrong click'


def click_rows(jobs, picks2, picks4):
    """Each step scored for the 2B alone, the 4B alone and the engine's rule on the same two picks
    (the senior counted as ready)."""
    rows = []
    for j, p2, p4 in zip(jobs, picks2, picks4):
        final = clicks.senior_chooser(lambda s, o: p2, lambda s, o: p4)(j['step'], j['offer'])
        rows.append({'page': j['page'], 'step': j['step'], 'right': sorted(j['ok']) if j['ok'] else None,
                     'offered': len(j['offer']), '2b': p2, '4b': p4, 'final': final,
                     **{f'{b}_result': score_click(j['offer'], p, j['ok']) for b, p in (('2b', p2), ('4b', p4), ('final', final))}})
    return rows


def click_summary(rows):
    """Right answers and wrong clicks per kind of step, then per step."""
    kinds = {'real steps': lambda r: r['right'] and r['step'] != DEBATABLE, 'nothing fits': lambda r: not r['right'],
             'debatable': lambda r: r['step'] == DEBATABLE}
    kinds.update({step: lambda r, step=step: r['step'] == step for step in dict.fromkeys(r['step'] for r in rows)})
    out = {}
    for kind, want in kinds.items():
        rs = [r for r in rows if want(r)]
        out[kind] = {'n': len(rs), **{f'{b}_right': sum(r[f'{b}_result'] == 'right' for r in rs) for b in ('2b', '4b', 'final')},
                     **{f'{b}_wrong_clicks': sum(r[f'{b}_result'] == 'wrong click' for r in rs) for b in ('2b', '4b', 'final')}}
    return out


def rescore():
    """The click rule is code, so a new rule is scored on the saved picks: no brain run, no brain noise."""
    out = json.loads(OUT.read_text(encoding='utf-8'))
    saved = out['click_rows']
    jobs = [{'page': r['page'], 'step': r['step'], 'ok': set(r['right']) if r['right'] else None,
             'offer': offered(*r['page'].split('/')[:2], int(r['page'].split('/')[2]))} for r in saved]
    out['click_rows'] = click_rows(jobs, [r['2b'] for r in saved], [r['4b'] for r in saved])
    out['clicks'] = click_summary(out['click_rows'])
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=list), encoding='utf-8')
    print(json.dumps(out['clicks'], indent=1, ensure_ascii=False))


def check():  # the scoring rule on a made-up menu
    menu = [{'text': n, 'title': '', 'aria': '', 'value': '', 'href': ''} for n in ('128', '256')]
    assert score_click(menu, '256', {'256'}) == 'right' and score_click(menu, '128', {'256'}) == 'wrong click'
    assert score_click(menu, '2 TB', {'256'}) == 'no click'
    assert score_click(menu, None, None) == 'right' and score_click(menu, '2 TB', None) == 'right'
    assert score_click(menu, '128', None) == 'wrong click'


def ask_all(url, fields_jobs, click_jobs, workers):
    brain, choose = x.llama_brain(url), clicks.llama_chooser(url)

    def fix(j):
        s, site, k = j
        t = time.perf_counter()
        try:
            got = x.read_page(sc.page(s, site, k), sc.typed(site), brain, focus=sc.FOCUS[site])
        except Exception as e:  # one bad call is a wrong answer, not a stopped run
            got = {'error': f'{type(e).__name__}: {e}'[:200]}
        return got, round(time.perf_counter() - t, 2)

    def pick(j):
        t = time.perf_counter()
        try:
            name = choose(j['step'], j['offer'])
        except Exception as e:
            name = f'error: {type(e).__name__}'
        return name, round(time.perf_counter() - t, 2)
    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(fix, fields_jobs)), list(pool.map(pick, click_jobs))


def serve(model, url, slots, flags, log, fields_jobs, click_jobs):
    srv = eb.BrainServer(ROOT / log, model=model, url=url, slots=slots, ctx=4096, flags=flags)
    srv.start()
    try:
        return ask_all(url, fields_jobs, click_jobs, slots)
    finally:
        srv.stop()


def main():
    check()
    pages =[(s, site, k) for s, truth in sc.TRUTHS.items() for site in truth for k in range(len(truth[site]))]
    jobs = []
    for s, site, k in pages:
        if site in ('books', 'wikipedia') or k == 0:  # quotes and the shop show the same menu on every page
            offer = offered(s, site, k)
            jobs += [{'page': f'{s}/{site}/{k:02d}', 'step': st, 'ok': ok, 'offer': offer} for st, ok in steps(s, site, k, offer)]
    print(f'{len(pages)} pages to read, {len(jobs)} click steps')

    two, two_c = serve(eb.MODEL, eb.URL, eb.SLOTS, eb.FLAGS, 'server-senior-2b.log', pages, jobs)
    gpu = ['-ngl', '99'] + eb.SENIOR_FLAGS[2:]
    four, four_c = serve(eb.SENIOR, eb.SENIOR_URL, 4, gpu, 'server-senior-4b-gpu.log', pages, jobs)
    timed = [i for i, (s, site, k) in enumerate(pages) if s == 'testset' and k < 2]  # 8 pages, 2 per site
    timed_c = [i for i, j in enumerate(jobs) if j['page'].startswith('testset/')][::12][:8]
    cpu, cpu_c = serve(eb.SENIOR, eb.SENIOR_URL, eb.SENIOR_SLOTS, eb.SENIOR_FLAGS, 'server-senior-4b-cpu.log',
                       [pages[i] for i in timed], [jobs[i] for i in timed_c])

    # fix calls: per field, right for each brain, and the engine's trigger (empty from the 2B where the
    # 2B filled 4 in 5 of that set's pages of this site)
    items = []
    for (s, site, k), (a2, _), (a4, _) in zip(pages, two, four):
        for f, t in sc.TRUTHS[s][site][k]['answers'].items():
            share = statistics.mean(two[i][0].get(f) not in (None, '') for i, p in enumerate(pages) if p[:2] == (s, site))
            items.append({'item': f'{s}/{site}/{k:02d} {f}', 'truth': t, '2b': a2.get(f), '4b': a4.get(f),
                          '2b_right': sc.correct(f, a2.get(f), t), '4b_right': sc.correct(f, a4.get(f), t),
                          'fix_asked': a2.get(f) in (None, '') and share >= 0.8})
    hard = [i for i in items if i['fix_asked']]
    by_page = {}
    for i in items:
        by_page.setdefault(i['item'].rsplit(' ', 1)[0], []).append(i)

    def acc(key):
        p = [(sum(i[key] for i in v), len(v)) for v in by_page.values()]
        lo, hi = sc.bootstrap(p)
        return {'right': sum(c for c, _ in p), 'of': sum(n for _, n in p), 'ci95': [round(lo, 3), round(hi, 3)]}
    fixes = {'2b': acc('2b_right'), '4b': acc('4b_right'),
             '4b_fixed_2b_wrong': sum(i['4b_right'] and not i['2b_right'] for i in items),
             '4b_broke_2b_right': sum(i['2b_right'] and not i['4b_right'] for i in items),
             'senior_asked': len(hard),
             'senior_filled_right': sum(i['4b_right'] and i['truth'] is not None for i in hard),
             'senior_filled_wrong': sum(i['4b'] not in (None, '') and not i['4b_right'] for i in hard),
             'senior_left_empty': sum(i['4b'] in (None, '') and i['truth'] is not None for i in hard),
             'senior_right_none': sum(i['truth'] is None and i['4b_right'] for i in hard),
             '2b_wrong_value_never_asked': sum(i['2b'] not in (None, '') and not i['2b_right'] for i in items),
             'hard_items': hard}

    rows = click_rows(jobs, [p for p, _ in two_c], [p for p, _ in four_c])
    click = click_summary(rows)

    same = sum(c[0] == four[i][0] for c, i in zip(cpu, timed)) + sum(c[0] == four_c[i][0] for c, i in zip(cpu_c, timed_c))
    speed = {'2b_gpu_fix_s_median': statistics.median(s for _, s in two),
             '4b_gpu_fix_s_median': statistics.median(s for _, s in four),
             '4b_cpu_fix_s': [s for _, s in cpu], '4b_cpu_click_s': [s for _, s in cpu_c],
             'cpu_same_answers_as_gpu': f'{same} of {len(cpu) + len(cpu_c)}'}
    out = {'fixes': fixes, 'clicks': click, 'speed': speed, 'errors': sum('error' in a for a, _ in two + four),
           'click_rows': rows, 'items': items}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=list), encoding='utf-8')
    print(json.dumps({k: v for k, v in fixes.items() if k != 'hard_items'}, indent=1))
    print(json.dumps(click, indent=1, ensure_ascii=False))
    print(json.dumps(speed, indent=1))


if __name__ == '__main__':
    rescore() if '--rescore' in sys.argv else main()
