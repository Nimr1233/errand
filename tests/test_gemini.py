"""The Gemini helper (errand/gemini.py) and the engine's fix step, with a stand-in for Google's API:
no key, no network, no allowance spent."""
import json
import re

from errand import engine as real, gemini as gm
from errand.fetch import Polite
from tests.test_engine import FIELD_WORDS, site, wait  # noqa: F401  (site is a fixture)
from tests.test_extract import FIELDS, fake_brain, product, truth


class Google:
    """Answers like Gemini's OpenAI-style endpoint; can run out of free allowance per model."""
    def __init__(self, out=()):
        self.calls, self.out = [], set(out)

    def __call__(self, url, body, headers):
        self.calls.append((url, body['model'], headers))
        if body['model'] in self.out:
            return 429, None
        title = re.search(r'h1: (Book \d+)', body['messages'][1]['content']).group(1)
        answer = truth(title, int(title.split()[1]))
        return 200, {'choices': [{'message': {'content': json.dumps(answer)}}]}


def view(k):
    return f'[1] h1: Book {k}\n[2] p class=price: £1{k}.00'


def test_the_model_ladder_and_the_daily_budget(tmp_path):
    g = gm.Gemini(key='test-key', send=Google(out={'gemini-3.8-flash'}), daily=3, usage_file=tmp_path / 'u.json')
    assert g.state() == 'ready'
    assert g.brain(view(4), FIELDS)['price'] == '£14.00'  # 3.8 Flash was out: 3.5 Flash-Lite answered
    assert [m for _, m, _ in g.send.calls] == ['gemini-3.8-flash', 'gemini-3.5-flash-lite']
    url, _, headers = g.send.calls[0]
    assert url == gm.URL and headers == {'Authorization': 'Bearer test-key'}  # the key goes to Google only
    assert g.brain(view(5), FIELDS) is not None and g.state() == 'daily budget used (3 calls)'
    assert g.brain(view(6), FIELDS) is None and len(g.send.calls) == 3  # no call past the budget
    assert json.loads((tmp_path / 'u.json').read_text())['calls'] == 3  # kept across restarts today
    assert 'test-key' not in (tmp_path / 'u.json').read_text()


def test_out_of_allowance_and_no_key():
    both = gm.Gemini(key='k', send=Google(out=set(gm.MODELS)), usage_file=None)
    assert both.brain(view(1), FIELDS) is None and both.state() == 'free allowance used until midnight Pacific'
    none = gm.Gemini(key=None, send=Google())
    assert none.state() == 'no key' and none.brain(view(1), FIELDS) is None and not none.send.calls


def run(site, tmp_path, private):  # noqa: F811
    said = {f'Book {k}': truth(f'Book {k}', k) for k in range(14)}
    said['Book 12'] = {**said['Book 12'], 'price': None}  # the 2B missed the price on one page
    google = Google()
    eng = real.Engine(brain=fake_brain(said, []), results=tmp_path, remember=False, pool=None,
                      fetcher=Polite(delay=(0.05, 0.08), allow_local=True),
                      gemini=gm.Gemini(key='test-key', send=google, usage_file=tmp_path / 'u.json'))
    # prices move down the page (notes=k), so no recipe can read them: the brains read every price
    pages = {f'/p/{k}.html': product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1, notes=k) for k in range(14)}
    eng.fetcher.get = lambda url: (200, pages[url.split(site)[1]]) if '/p/' in url else (404, '')
    eng.start_job('Shop', [f'{site}/p/{k}.html' for k in range(14)], FIELD_WORDS, private=private)
    s = wait(eng)
    eng.close()
    return eng, s, google


def test_gemini_fills_a_field_the_brains_missed(site, tmp_path):  # noqa: F811
    eng, s, google = run(site, tmp_path, private=False)
    assert eng.rows[f'{site}/p/12.html']['price'] == '£112.00'
    assert s['gemini_calls'] == 1 and s['gemini_fixed'] == 1 and len(google.calls) == 1
    assert any('Gemini filled price' in u['text'] for u in eng.updates.since(None))
    assert 'test-key' not in json.dumps(s) + json.dumps(eng.updates.since(None))


def test_a_private_job_never_reaches_gemini(site, tmp_path):  # noqa: F811
    eng, s, google = run(site, tmp_path, private=True)
    assert eng.rows[f'{site}/p/12.html']['price'] is None and not google.calls
    assert s['gemini'] == 'off: private job' and s['gemini_calls'] == 0
