"""Saved data (errand/store.py): past jobs, results, and recipes reused by later jobs after a check on
3 pages. Uses a database in a temporary folder (tests/conftest.py), never your real one."""
from errand import engine as real, store as st
from errand.fetch import Polite
from tests.test_engine import FIELD_WORDS, site, wait  # noqa: F401  (site is a fixture)
from tests.test_extract import fake_brain, product, truth


def shop(eng, base, notes=0, private=False, name='Shop'):
    """Serve 14 product pages; `notes` lines before the price change the page layout."""
    pages = {f'/p/{k}.html': product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1, notes=notes) for k in range(14)}
    eng.fetcher.get = lambda url: (200, pages[url.split(base)[1]]) if '/p/' in url else (404, '')
    eng.start_job(name, [f'{base}/p/{k}.html' for k in range(14)], FIELD_WORDS, private=private)
    return wait(eng)


def engine(tmp_path, calls):
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(14)}
    return real.Engine(brain=fake_brain(said, calls), results=tmp_path, remember=False, pool=None,
                       fetcher=Polite(delay=(0.02, 0.04), allow_local=True))


def test_a_second_job_reuses_the_recipe_after_checking_3_pages(site, tmp_path):  # noqa: F811
    calls = []
    eng = engine(tmp_path, calls)
    first = shop(eng, site)
    assert len(calls) == real.SAMPLES and first['recipes_reused'] == 0
    calls.clear()
    second = shop(eng, site, name='Shop again')
    assert len(calls) == real.CHECK and second['recipes_reused'] == 1  # 3 brain calls instead of 10
    assert all(eng.rows[f'{site}/p/{k}.html'] == {'status': 'ok', **truth(f'Book {k}', k)} for k in range(14))
    assert any('reused the saved recipe' in u['text'] for u in eng.updates.since(None))
    jobs = eng.history()
    assert [j['name'] for j in jobs] == ['Shop again', 'Shop'] and jobs[0]['done'] == 14 and jobs[0]['brain_calls'] == 3
    eng.close()


def test_a_site_that_changed_gets_a_new_recipe(site, tmp_path):  # noqa: F811
    calls = []
    eng = engine(tmp_path, calls)
    shop(eng, site)
    calls.clear()
    s = shop(eng, site, notes=1, name='After a redesign')  # a note now sits where the price was
    assert s['recipes_reused'] == 0 and len(calls) == real.SAMPLES  # the check failed: learned from 10 again
    assert all(eng.rows[f'{site}/p/{k}.html']['price'] == f'£1{k}.00' for k in range(14))
    assert any('no longer reads it right' in u['text'] for u in eng.updates.since(None))
    eng.close()


def test_results_are_saved_and_private_pages_are_not_cached(site, tmp_path):  # noqa: F811
    eng = engine(tmp_path, [])
    shop(eng, site, name='Public')
    assert eng.store.cached(f'{site}/p/3.html') and 'Book 3' in eng.store.cached(f'{site}/p/3.html')
    rows = eng.store.db.execute('select url, status, data from results where job=?', (eng.job_id,)).fetchall()
    assert len(rows) == 14 and all(r[1] == 'ok' for r in rows)
    eng.store.cache.joinpath('x').mkdir(parents=True, exist_ok=True)
    for f in eng.store.cache.glob('*.html'):
        f.unlink()
    shop(eng, site, private=True, name='Private')
    assert not list(eng.store.cache.glob('*.html'))  # private pages never stay on disk
    assert eng.store.path == st.DB and str(tmp_path) in str(st.DB)  # the test database, not yours
    eng.close()
