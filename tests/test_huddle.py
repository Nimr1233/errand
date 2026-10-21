"""Real huddles (errand/engine.py): a site changes its layout halfway through a job, its recipe reads
nothing, and the agents gather to learn a new one, or hand it to you."""
import time

from errand import engine as real
from errand.fetch import Polite
from tests.test_engine import FIELD_WORDS, site, wait  # noqa: F401  (site is a fixture)
from tests.test_extract import fake_brain, product, truth

PAGES = 24


def page(k, redesign):
    """Pages 12 on wear the new layout: one more wrapper, so the old recipe's spots are empty."""
    html = product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1)
    depth = 0 if k < 12 else (1 if redesign == 'same' else k % 3 + 1)  # 'mixed': each page nests differently
    return html.replace('<div class="product">', '<div class="shell">' * depth + '<div class="product">')


def run(base, tmp_path, redesign):
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(PAGES)}
    eng = real.Engine(brain=fake_brain(said, []), results=tmp_path, remember=False, pool=None,
                      fetcher=Polite(delay=(0.02, 0.04), allow_local=True))
    pages = {f'/p/{k}.html': page(k, redesign) for k in range(PAGES)}
    eng.fetcher.get = lambda url: (200, pages[url.split(base)[1]]) if '/p/' in url else (404, '')
    eng.start_job('Redesign', [f'{base}/p/{k}.html' for k in range(PAGES)], FIELD_WORDS)
    return eng


def right(eng, base):
    return all(eng.rows[f'{base}/p/{k}.html'] == {'status': 'ok', **truth(f'Book {k}', k)} for k in range(PAGES))


def test_the_huddle_learns_a_new_recipe_when_a_site_changes(site, tmp_path):  # noqa: F811
    eng = run(site, tmp_path, 'same')
    s = wait(eng)
    eng.close()
    assert right(eng, site)  # the pages read wrongly before the huddle were read again
    p = eng.problem_detail('P-1')
    assert p['kind'] == 'recipe stopped working' and p['state'] == 'fixed' and len(p['rounds']) == 1
    assert p['rounds'][0]['winner'] and p['rounds'][0]['best'] == p['rounds'][0]['pages'] == 3
    assert s['fixed_by_huddles'] == 1 and s['raised'] == 1 and s['problems'] == 0
    assert any('fixed by the huddle in round 1' in u['text'] for u in eng.updates.since(None))
    assert eng.board_view()['recent'][0]['state'] == 'fixed'


def waits_on_you(eng, secs=60):
    t = time.monotonic()
    while not any(a.state == 'needs_you' for a in eng.agents):
        assert time.monotonic() - t < secs, eng.status()
        time.sleep(0.05)
    return next(a for a in eng.agents if a.state == 'needs_you')


def test_a_redesign_no_round_can_fix_goes_to_you(site, tmp_path):  # noqa: F811
    eng = run(site, tmp_path, 'mixed')
    a = waits_on_you(eng)
    p = eng.problem_detail(a.board_pid)
    assert p['state'] == 'yours' and len(p['rounds']) >= 2 and not any(r['winner'] for r in p['rounds'])
    assert eng.status()['problems'] == 1 and not eng.complete()  # its pages wait for your answer
    assert 'brains read' in a.reason
    assert eng.answer_problem(a.n, approve=True) == {'ok': True}
    wait(eng)
    eng.close()
    assert right(eng, site) and p['state'] == 'answered'  # the brains read the fields page by page


def test_skipping_that_site_ends_the_job(site, tmp_path):  # noqa: F811
    eng = run(site, tmp_path, 'mixed')
    a = waits_on_you(eng)
    assert eng.answer_problem(a.n, approve=False) == {'ok': True}
    s = wait(eng)
    eng.close()
    assert s['complete'] and any(r['status'] == 'skipped by you' for r in eng.rows.values())
    assert eng.answer_problem(a.n, approve=True)['ok'] is False  # nothing waits any more


def test_a_round_waiting_for_pages_still_ends_when_they_fail(site, tmp_path):  # noqa: F811
    """A round waits for more pages of its kind; if those all fail to download, it must not wait forever."""
    eng = run(site, tmp_path, 'mixed')
    good = eng.fetcher.get
    eng.fetcher.get = lambda url: (404, '') if '/p/' in url and int(url.split('/')[-1].split('.')[0]) >= 16 else good(url)
    a = waits_on_you(eng)  # rounds ran out of pages and handed it on instead of hanging
    eng.answer_problem(a.n, approve=True)
    s = wait(eng)
    eng.close()
    assert s['complete'] and sum(r['status'] == 'error: HTTP 404' for r in eng.rows.values()) == PAGES - 16
