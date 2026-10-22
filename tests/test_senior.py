"""The 4B 'senior' brain (errand/brains.py SENIOR_*, the engine's fix step): a bigger local brain on the
CPU that answers the hard calls the 53 can't settle. It is the second opinion for every private job
(which never reaches Gemini) and the fallback for a public job whose free Gemini is spent. Public jobs
with a working Gemini still use Gemini. A fake senior brain stands in: no download, no CPU server."""
from errand import engine as real, gemini as gm
from errand.fetch import Polite
from tests.test_engine import FIELD_WORDS, site, wait  # noqa: F401  (site is a fixture)
from tests.test_extract import fake_brain, product, truth
from tests.test_gemini import Google


def run_senior(site, tmp_path, private, gemini=None):  # noqa: F811
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(14)}
    said['Book 12'] = {**said['Book 12'], 'price': None}  # the 2B missed the price on one page
    senior_said = {f'Book {k}': truth(f'Book {k}', k) for k in range(14)}  # the 4B senior reads it right
    scalls = []
    eng = real.Engine(brain=fake_brain(said, []), results=tmp_path, remember=False, pool=None,
                      fetcher=Polite(delay=(0.05, 0.08), allow_local=True),
                      senior=fake_brain(senior_said, scalls), gemini=gemini)
    # prices move down the page (notes=k), so no recipe can read them: the brains read every price
    pages = {f'/p/{k}.html': product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1, notes=k) for k in range(14)}
    eng.fetcher.get = lambda url: (200, pages[url.split(site)[1]]) if '/p/' in url else (404, '')
    eng.start_job('Shop', [f'{site}/p/{k}.html' for k in range(14)], FIELD_WORDS, private=private)
    s = wait(eng)
    eng.close()
    return eng, s, scalls


def test_a_private_job_now_gets_the_senior(site, tmp_path):  # noqa: F811
    """The win: a private page the 2B read short now gets a strong second opinion, all on the laptop."""
    eng, s, scalls = run_senior(site, tmp_path, private=True)
    assert eng.rows[f'{site}/p/12.html']['price'] == '£112.00'  # the senior filled what the 2B missed
    assert s['senior_fixed'] == 1 and s['senior_calls'] == 1 and len(scalls) == 1
    assert s['gemini_calls'] == 0 and s['gemini'] == 'off: private job'  # a private job never reaches Gemini
    assert any('the 4B senior filled price' in u['text'] for u in eng.updates.since(None))


def test_public_falls_back_to_the_senior_when_gemini_is_off(site, tmp_path):  # noqa: F811
    eng, s, scalls = run_senior(site, tmp_path, private=False)  # no Gemini key: the senior fills in
    assert eng.rows[f'{site}/p/12.html']['price'] == '£112.00'
    assert s['senior_fixed'] == 1 and s['gemini_calls'] == 0 and len(scalls) == 1


def test_public_prefers_gemini_over_the_senior(site, tmp_path):  # noqa: F811
    g = gm.Gemini(key='test-key', send=Google(), usage_file=tmp_path / 'u.json')
    eng, s, scalls = run_senior(site, tmp_path, private=False, gemini=g)
    assert eng.rows[f'{site}/p/12.html']['price'] == '£112.00'
    assert s['gemini_fixed'] == 1 and s['senior_fixed'] == 0 and s['senior_calls'] == 0 and not scalls
