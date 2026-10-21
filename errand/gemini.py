"""The Gemini helper (reports/Full feature free Errand plan.md: Gemini helps, the 2B does the bulk,
code checks both). Free tier, one key, never swapped for another.
- Public pages only. A job marked private never goes to Gemini: free-tier prompts can be read by
  Google's reviewers.
- Your key: paste it into ~/.errand/gemini_key (or set GEMINI_API_KEY). It is sent only to Google and
  never written to logs, updates or results.
- A daily budget (ERRAND_GEMINI_DAILY, default 200 calls). When a model's free allowance runs out
  (HTTP 429), the next model is used: gemini-3.8-flash, then gemini-3.5-flash-lite, then none (the 2B
  alone) until midnight Pacific, when Google resets the count.
Model names checked on ai.google.dev/gemini-api/docs/models (updated 2026-10-19): both stable.
"""
import datetime, json, os, pathlib, threading, urllib.error, urllib.request
from zoneinfo import ZoneInfo

from . import extract as x

URL = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
MODELS = ('gemini-3.8-flash', 'gemini-3.5-flash-lite')
KEY_FILE = pathlib.Path.home() / '.errand' / 'gemini_key'
USAGE_FILE = pathlib.Path.home() / '.errand' / 'gemini_usage.json'
DAILY = int(os.environ.get('ERRAND_GEMINI_DAILY', 200))


def load_key():
    k = os.environ.get('GEMINI_API_KEY')
    if not k and KEY_FILE.exists():
        k = KEY_FILE.read_text(encoding='utf-8').strip()
    return k or None


def pacific_day():
    return datetime.datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()


def post(url, body, headers, timeout=60):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


class Gemini:
    def __init__(self, key=..., send=post, daily=DAILY, usage_file=None):
        self.key = load_key() if key is ... else key
        self.send, self.daily, self.usage_file = send, daily, usage_file or USAGE_FILE
        self.lock = threading.Lock()
        self.usage = self._load()

    def _load(self):
        try:
            u = json.loads(self.usage_file.read_text(encoding='utf-8'))
        except Exception:
            u = {}
        return u if u.get('day') == pacific_day() else {'day': pacific_day(), 'calls': 0, 'out': []}

    def _save(self):
        try:
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text(json.dumps(self.usage), encoding='utf-8')
        except OSError:
            pass

    def state(self):
        with self.lock:
            if self.usage['day'] != pacific_day():  # a new day: Google's count reset at midnight Pacific
                self.usage = {'day': pacific_day(), 'calls': 0, 'out': []}
            if not self.key:
                return 'no key'
            if self.usage['calls'] >= self.daily:
                return f'daily budget used ({self.daily} calls)'
            if all(m in self.usage['out'] for m in MODELS):
                return 'free allowance used until midnight Pacific'
            return 'ready'

    def brain(self, view, fields):
        """Read one page's numbered view, the same way a local brain does. Returns the answers or None."""
        if self.state() != 'ready':
            return None
        for model in MODELS:
            with self.lock:
                if model in self.usage['out'] or self.usage['calls'] >= self.daily:
                    continue
                self.usage['calls'] += 1
                self._save()
            status, data = self.send(URL, {'model': model, 'reasoning_effort': 'low', 'messages': [
                {'role': 'system', 'content': x.system_prompt(fields)}, {'role': 'user', 'content': view}]},
                {'Authorization': f'Bearer {self.key}'})
            if status == 429:  # this model's free allowance is used up for today
                with self.lock:
                    self.usage['out'].append(model)
                    self._save()
                continue
            if status != 200 or not data:
                return None
            return x.last_json((data.get('choices') or [{}])[0].get('message', {}).get('content'))
        return None

    def calls_today(self):
        return self.usage['calls']


def check():
    """`errand gemini`: is the key there, and which of Errand's models can it use? Listing models
    spends none of the free allowance. The key itself is never printed."""
    key = load_key()
    if not key:
        return f'No Gemini key yet. Make the file {KEY_FILE}, paste your key from aistudio.google.com/apikey into it, save.'
    req = urllib.request.Request(URL.replace('chat/completions', 'models'), headers={'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            have = {m['id'].split('/')[-1] for m in json.loads(r.read()).get('data', [])}
    except urllib.error.HTTPError as e:
        return f'Google refused the key (HTTP {e.code}). Check it was copied whole from aistudio.google.com/apikey.'
    except OSError as e:
        return f"Couldn't reach Google: {e}"
    g = Gemini(key=key)
    lines = [f"{m}: {'available' if m in have else 'NOT available to this key'}" for m in MODELS]
    return '\n'.join(['Gemini key works.', *lines, f"Today: {g.calls_today()} of {g.daily} calls used · {g.state()}"])

