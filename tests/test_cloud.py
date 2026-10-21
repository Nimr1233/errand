"""The webhook inbox and website helper Workers (cloud/), run under Node with stand-ins for Cloudflare's
database and for Gemini; and Errand's side of the inbox (errand/inbox.py) with a stand-in inbox."""
import json
import pathlib
import shutil
import subprocess

import pytest

from errand import inbox
from errand.updates import UpdateLog

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not shutil.which('node'), reason='needs Node')
def test_the_workers():
    r = subprocess.run(['node', str(ROOT / 'tests' / 'cloud_test.mjs')], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert 'cloud workers ok' in r.stdout


class Engine:
    def __init__(self, busy=False):
        self.job, self.busy, self.runs, self.updates = ('x' if busy else None), busy, [], UpdateLog()

    def complete(self):
        return not self.busy

    def run_skill(self, name, urls, values):
        if name != 'laptop price':
            raise ValueError(f"there's no skill called '{name}'")
        self.runs.append((name, urls, values))


def make(tmp_path, eng, events):
    cfg = tmp_path / 'inbox.json'
    cfg.write_text(json.dumps({'url': 'https://inbox.example', 'secret': 's'}))
    acked = []

    def call(method, url, secret, body=None):
        assert secret == 's'
        if url.endswith('/events'):
            return [e for e in events if e['id'] not in acked]
        acked.extend(body['ids'])
        return {'ok': True}
    return inbox.Inbox(eng, cfg, call), acked


def test_a_request_runs_its_skill_and_is_acknowledged(tmp_path):
    eng = Engine()
    events = [{'id': 1, 'name': 'typo', 'body': json.dumps({'skill': 'no such'})},
              {'id': 2, 'name': 'price-check', 'body': json.dumps({'skill': 'laptop price', 'urls': ['https://a/1'], 'values': {'size': '256'}})}]
    box, acked = make(tmp_path, eng, events)
    assert box.tick() == 'laptop price'
    assert eng.runs == [('laptop price', ['https://a/1'], {'size': '256'})] and acked == [1, 2]
    assert any("dropped 'typo'" in u['text'] for u in eng.updates.since(None))  # a bad request is dropped, with a note


def test_requests_wait_while_a_job_runs(tmp_path):
    eng = Engine(busy=True)
    box, acked = make(tmp_path, eng, [{'id': 1, 'name': 'p', 'body': json.dumps({'skill': 'laptop price', 'urls': ['u']})}])
    assert box.tick() is None and not acked  # still in the inbox, not lost
    eng.busy = False
    assert box.tick() == 'laptop price' and acked == [1]


def test_setup_makes_a_secret_once(tmp_path):
    text = inbox.setup_text()
    secret = json.loads(inbox.CONFIG.read_text())['secret']
    assert secret in text and 'npx wrangler deploy' in text
    assert json.loads(inbox.CONFIG.read_text())['secret'] == secret and inbox.setup_text() == text
    assert inbox.Inbox(Engine(), tmp_path / 'missing.json').tick() is None  # not set up: nothing happens
