"""The real engine (main spec sections 13-14). A job is a list of links and the fields to read from
each page. It reports to mission control the same way the demo engine does (errand/demo.py), so the
room and the Errand connector work with either.

53 agents share one task list and never wait in line: an agent takes the first task it can do now.
- fetch: one page, politely (errand/fetch.py). A page whose site is pausing waits; agents do other work.
- read: a brain reads one page (errand/extract.py). The first 10 pages of each kind of page (same
  site, same path depth) are samples.
- learn: the vote across pages learns a recipe from the samples' answers. Later pages of that kind
  are read by code, with a brain only for the fields no recipe covers (bench/results.md sections 7-8).
Results go to jobs/<job>.csv: one row per link, with its status ("ok", "blocked: bot check", ...).
A finished job leaves a short note in the chief's memory (errand/memory.py, gbrain) when gbrain is installed.
Not built yet: browser windows (the stealth and JavaScript fetch steps), checker brains, huddles.
"""
import csv, pathlib, re, threading, time, urllib.parse
from collections import deque

from . import extract as x, memory
from .brains import URL as BRAIN_URL, BrainServer
from .demo import N, STEP, slug
from .fetch import Polite, site
from .updates import UpdateLog

RESULTS = pathlib.Path(__file__).resolve().parent.parent / 'jobs'
SAMPLES = 10  # bench/results.md section 8: 5 samples broke fresh Wikipedia pages, 10 didn't
SAVE_EVERY = 20  # rows between rewrites of the results file


def parse_fields(fields):
    """{name: what it is}. A description that starts with "number:" or "date:" sets the field's kind."""
    out = {}
    for name, what in (fields or {}).items():
        name = re.sub(r'\W+', '_', str(name)).strip('_')[:40]
        m = re.match(r'\s*(number|date|text)\s*:\s*(.*)', str(what or ''), re.I | re.S)
        kind, what = (m.group(1).lower(), m.group(2)) if m else ('text', str(what or ''))
        if name:
            out[name] = (what.strip()[:200] or name, kind)
    return out


def kind_of_page(url):
    """Pages of one kind share a site and a path depth; each kind learns its own recipe."""
    p = urllib.parse.urlsplit(url)
    return f"{site(url)}{'/*' * p.path.rstrip('/').count('/')}"


class Agent:
    def __init__(self, n):
        self.n = n
        self.reset()

    def reset(self):
        self.state = 'idle'  # idle | working | finished | stopped
        self.task = None
        self.pages = 0
        self.steps = deque(maxlen=8)
        self.excerpt = ''

    def view(self):
        kind, url = self.task or (None, '')
        return {'n': self.n, 'state': self.state, 'task': kind, 'site': site(url) if '://' in url else url,
                'pages': self.pages, 'window': False, 'used_window': False, 'passes': 0, 'reason': '',
                'prog': 0.5 if self.task else 0.0, 'log': self.steps[-1] if self.steps else '', 'huddle': None,
                'fix_ok': 0, 'fix_tried': 0}


class Engine:
    def __init__(self, brain=None, fetcher=None, results=RESULTS, samples=SAMPLES, log_path=None, server_log=None,
                 remember=True):
        self.lock = threading.Condition()
        self.agents = [Agent(i + 1) for i in range(N)]
        self.updates = UpdateLog(log_path)
        self.fetcher = fetcher or Polite()
        self.brain = brain  # brain(view_text, fields) -> answers; None: start llama-server on the first job
        self.server = None if brain else BrainServer(server_log)
        self.brains = 'ready' if brain else 'off'  # off | starting | ready | failed: why
        self.results, self.samples, self.remember = results, samples, remember
        self.threads, self.closed, self.paused = [], False, False
        self.job, self.total, self.done, self.inflight, self.blocked, self.brain_calls, self.by_code = None, 0, 0, 0, 0, 0, 0
        self.tasks, self.rows, self.html, self.groups = deque(), {}, {}, {}
        self.hist, self.rate = [0], 0.0
        self.out = None

    # ---- commands (the local API and the Errand connector call these) ----
    def start_job(self, prompt, urls, fields, focus=None):
        fields = parse_fields(fields)
        if not fields:
            raise ValueError('say which fields to read, like {"price": "the price", "stock": "number: copies in stock"}')
        urls = list(dict.fromkeys(u.strip() for u in urls or [] if u and u.strip()))
        if not urls:
            raise ValueError('give urls or a file with one link per line')
        with self.lock:
            if self.job and not self.complete():
                raise ValueError(f"job '{self.job}' is still running")
            self.job, self.fields, self.focus = prompt.strip()[:60] or 'Untitled job', fields, focus or None
            self.total, self.done, self.inflight, self.blocked, self.brain_calls, self.by_code = len(urls), 0, 0, 0, 0, 0
            self.tasks = deque(('fetch', u) for u in urls)
            self.rows, self.html, self.groups = {u: None for u in urls}, {}, {}
            for u in urls:
                g = self.groups.setdefault(kind_of_page(u), {'recipe': None, 'samples': {}, 'sampling': set(),
                                                            'waiting': [], 'unfetched': 0, 'learning': False})
                g['unfetched'] += 1
            self.out, self.announced, self.saved_at = self._free_name(slug(self.job)), False, 0
            self.hist, self.rate = [0], 0.0
            for a in self.agents:
                a.reset()
            self.updates.add('job', f"Job '{self.job}' started · {self.total} pages · reading "
                                    + ', '.join(f'{k} ({kind})' if kind != 'text' else k for k, (_, kind) in fields.items()))
            self._start_brains()
            self._start_agents()
            self.lock.notify_all()
        return {'job': self.job, 'pages': self.total}

    def answer_problem(self, n, approve):
        return {'ok': False, 'error': f'agent #{n} has no problem waiting'}  # read-only jobs never ask you

    def stop_agent(self, n):
        a = self._agent(n)
        if a is None or a.state in ('finished', 'stopped'):
            return {'ok': False, 'error': f'agent #{n} is not running'}
        with self.lock:
            a.state = 'stopped'  # a page it is fetching or reading now is finished first
        self.updates.add('stopped', f'#{n} stopped by you', n)
        return {'ok': True}

    def pause_all(self):
        self.paused = True
        self.updates.add('job', 'All agents paused (pages being read now are finished first)')
        return {'ok': True}

    def resume_all(self):
        with self.lock:
            self.paused = False
            self.lock.notify_all()
        self.updates.add('job', 'All agents resumed')
        return {'ok': True}

    def close(self):
        with self.lock:
            self.closed = True
            self.lock.notify_all()
        if self.server:
            self.server.stop()

    # ---- views ----
    def status(self):
        with self.lock:
            fetched = self.total - sum(g['unfetched'] for g in self.groups.values())
            recipes = [k for k, g in self.groups.items() if g['recipe']]
            calls, by_code = self.brain_calls, self.by_code
            left = self.total - self.done
            return {
                'job': self.job or 'No job yet', 'total': self.total, 'pages_done': self.done,
                'speed': round(self.rate, 1), 'seconds_left': round(left / self.rate) if self.rate else None,
                'agents': N, 'finished': sum(a.state == 'finished' for a in self.agents), 'handoffs': 0, 'shelf': 0,
                'problems': 0, 'raised': 0, 'blocked': self.blocked, 'windows': 0, 'windows_in_use': 0,
                'next_on_shelf': [], 'last_handoff': '', 'brains': N, 'paused': self.paused, 'complete': self.complete(),
                'huddle': None, 'board': 0, 'fixed_by_huddles': 0, 'set_aside': 0,
                'results': str(self.out) if self.out else 'no job yet',
                'mode': 'real', 'brains_state': self.brains, 'fetched': fetched, 'recipes': len(recipes),
                'brain_calls': calls, 'by_code': by_code,
                # the room's middle TV and desk monitors (no browser windows yet, so no hand-offs to show)
                'tv_hand': {'label': '// PAGES READ BY CODE', 'val': by_code, 'of': f'/{self.done}',
                            'sub': f'{len(recipes)} recipe{"s" * (len(recipes) != 1)} learned from the brains'},
                'desks': [['PAGES FETCHED', f'{fetched}/{self.total}', 'one request per site every 2-3 s'],
                          ['BRAINS', self.brains.split(':')[0].upper(), self.brains if ':' in self.brains else
                           f'{N} slots on the GPU'],
                          ['RECIPES LEARNED', str(len(recipes)), ', '.join(recipes)[:40] or 'from 10 sample pages each'],
                          ['BRAIN CALLS', str(calls), f'{by_code} pages needed none'],
                          ['SPEED', f'{self.rate:.1f} p/s' if self.rate else '...', 'pages per second']]}

    def agents_view(self, state=None):
        with self.lock:
            return [a.view() for a in self.agents if state is None or a.state == state]

    def agent_detail(self, n):
        a = self._agent(n)
        if a is None:
            return None
        with self.lock:
            return {**a.view(), 'steps': list(a.steps), 'logged_in': False, 'page_excerpt': a.excerpt[:600]}

    def board_view(self):
        return {'huddle': None, 'waiting': [], 'recent': []}

    def problem_detail(self, pid):
        return None

    def complete(self):
        return bool(self.job) and self.done >= self.total and not self.tasks and not self.inflight

    def step(self):
        """The server's clock: keeps the speed reading. The work itself runs in the agents' threads."""
        with self.lock:
            self.hist = (self.hist + [self.done])[-9:]
            self.rate = (self.hist[-1] - self.hist[0]) / ((len(self.hist) - 1) * STEP) if len(self.hist) > 1 else 0.0

    # ---- the agents ----
    def _agent(self, n):
        return self.agents[n - 1] if 1 <= n <= N else None

    def _start_agents(self):
        if not self.threads:
            self.threads = [threading.Thread(target=self._work, args=(a,), daemon=True, name=f'agent-{a.n}')
                            for a in self.agents]
            for t in self.threads:
                t.start()

    def _start_brains(self):
        if self.brains in ('ready', 'starting'):
            return
        self.brains = 'starting'
        self.updates.add('job', 'Starting the brains (llama-server, about 30 s)')

        def run():
            try:
                self.server.start()
                self.brain, state = x.llama_brain(BRAIN_URL), 'ready'
                self.updates.add('job', f'Brains ready · {N} slots')
            except Exception as e:
                state = f'failed: {e}'
                self.updates.add('problem', f'The brains could not start: {e}')
            with self.lock:
                self.brains = state
                if state != 'ready':  # nothing can be read: every page left ends with this status
                    for g in self.groups.values():
                        g['unfetched'], g['sampling'], g['waiting'] = 0, set(), []
                    for u, row in self.rows.items():
                        if row is None:
                            self._row(u, {'status': 'error: no brains'}, by_brain=False)
                    self.tasks.clear()
                    self._finish_check()
                self.lock.notify_all()
        threading.Thread(target=run, daemon=True, name='brains').start()

    def _needs_brain(self, url):
        g = self.groups[kind_of_page(url)]
        return g['recipe'] is None or bool(set(self.fields) - set(g['recipe']))

    def _work(self, a):
        while True:
            with self.lock:
                while not self.closed and (t := self._take(a)) is None:
                    if a.state != 'stopped':
                        a.state = 'finished' if self.job and not self.tasks and self._all_assigned() else 'idle'
                    self.lock.wait(0.5)
                if self.closed:
                    return
                a.task, a.state = t, 'working'
                self.inflight += 1
            try:
                result = self._do(a, t)
            except Exception as e:  # one bad page never stops an agent
                result = {'status': f'error: {type(e).__name__}'}
            with self.lock:
                self.inflight -= 1
                self._record(a, t, result)
                a.task = None
                if a.state == 'working':
                    a.state = 'idle'
                self.lock.notify_all()

    def _all_assigned(self):
        return all(not g['waiting'] and not g['sampling'] and not g['learning'] for g in self.groups.values())

    def _take(self, a):
        if self.paused or a.state == 'stopped' or not self.job:
            return None
        busy = set()
        for i, t in enumerate(self.tasks):
            if t[0] == 'read' and self.brains != 'ready' and self._needs_brain(t[1]):
                continue
            if t[0] == 'fetch':
                s = site(t[1])
                if s in busy or not self.fetcher.take(t[1]):
                    busy.add(s)
                    continue
            del self.tasks[i]
            return t
        return None

    def _do(self, a, t):
        kind, key = t
        if kind == 'fetch':
            return self.fetcher.fetch(key)
        if kind == 'learn':
            g = self.groups[key]
            return {'recipe': x.learn_recipe([(self.html[u], ans) for u, ans in g['samples'].items()],
                                             self.fields, focus=self.focus)}
        g, used = self.groups[kind_of_page(key)], []

        def brain(view, fields):  # counts brain calls and keeps what the agent is reading, for the room
            a.excerpt = view
            used.append(1)
            return self.brain(view, fields)
        return {'answers': x.read_page(self.html[key], self.fields, brain, g['recipe'], focus=self.focus),
                'brain': bool(used)}

    def _record(self, a, t, r):
        kind, key = t
        if kind == 'fetch':
            g = self.groups[kind_of_page(key)]
            if r['status'] in ('retry', 'again'):  # the page goes back in line while its site pauses
                self.tasks.appendleft(t) if r['status'] == 'again' else self.tasks.append(t)
                if r['status'] == 'retry':  # the site asked to slow down
                    self.updates.add('blocked', f"{site(key)} asked us to slow down: pausing it {r['pause']} s", a.n)
                return
            g['unfetched'] -= 1
            a.steps.append(f"fetch {key[-60:]}: {r['status']}")
            if r['status'] != 'ok':
                self._row(key, {'status': r['status']}, by_brain=False)
                if r['status'].startswith(('blocked', 'disallowed', 'refused')):
                    self.blocked += 1
                    self.updates.add('blocked', f'#{a.n} {r["status"]}: {key[-80:]}', a.n)
            else:
                self.html[key] = r['html']
                if g['recipe'] is not None:
                    self.tasks.appendleft(('read', key))  # reads go first: brains work while sites pause
                elif len(g['samples']) + len(g['sampling']) < self.samples:
                    g['sampling'].add(key)
                    self.tasks.appendleft(('read', key))
                else:
                    g['waiting'].append(key)  # waits for its kind's recipe
            self._maybe_learn(g, kind_of_page(key))
        elif kind == 'learn':
            g = self.groups[key]
            g['recipe'], g['learning'] = r.get('recipe', {}), False
            for u, ans in g['samples'].items():  # the vote also corrects the samples' slips
                self.rows[u] = {'status': 'ok', **ans, **x.replay(self.html[u], g['recipe'], self.fields)}
                self.html.pop(u, None)
            self.tasks.extendleft(('read', u) for u in reversed(g['waiting']))
            g['waiting'] = []
            covered = len(g['recipe'])
            a.steps.append(f'learn {key}: {covered}/{len(self.fields)} fields by code')
            self.updates.add('recipe', f"#{a.n} learned a recipe for {key} from {len(g['samples'])} pages: "
                                       f'{covered} of {len(self.fields)} fields now read by code', a.n)
            self._save()
        else:
            g = self.groups[kind_of_page(key)]
            if 'answers' not in r:
                self._row(key, {'status': r['status']}, by_brain=False)
                g['sampling'].discard(key)
            elif key in g['sampling']:
                g['sampling'].discard(key)
                g['samples'][key] = r['answers']
                self._row(key, {'status': 'ok', **r['answers']}, by_brain=True)  # html kept for the vote
            else:
                self._row(key, {'status': 'ok', **r['answers']}, by_brain=r['brain'])
                self.html.pop(key, None)
            a.pages += 1
            a.steps.append(f"read {key[-60:]}: {'brain' if r.get('brain') else 'code'}")
            self._maybe_learn(g, kind_of_page(key))
        self._finish_check()

    def _finish_check(self):
        if self.complete() and not self.announced:
            self.announced = True
            self._save()
            self.updates.add('job', f"Job '{self.job}' finished · {self.done} pages · {self.blocked} blocked · "
                                    f'{self.by_code} read by code · results: {self.out}')
            if self.remember:  # the chief's memory (gbrain): what ran, which sites blocked, where results are
                memory.save_job(self.job, time.strftime('%Y-%m-%d %H:%M'), self.done, list(self.fields),
                                self.by_code, self.brain_calls, self.out, dict(self.rows))

    def _maybe_learn(self, g, key):
        if g['recipe'] is None and not g['learning'] and not g['sampling'] and g['samples'] and \
                (len(g['samples']) >= self.samples or g['unfetched'] == 0):
            g['learning'] = True
            self.tasks.appendleft(('learn', key))

    def _row(self, url, row, by_brain):
        if self.rows.get(url) is None:  # a page counts once
            self.done += 1
        self.rows[url] = row
        self.brain_calls += by_brain
        self.by_code += row['status'] == 'ok' and not by_brain
        if self.done - self.saved_at >= SAVE_EVERY:
            self._save()

    def _free_name(self, name):
        """jobs/<name>.csv, or <name>-2.csv and so on: an earlier job's results are never overwritten."""
        out, k = self.results / f'{name}.csv', 1
        while out.exists():
            k += 1
            out = self.results / f'{name}-{k}.csv'
        return out

    def _save(self):
        self.saved_at = self.done
        self.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.out.with_suffix('.tmp')
        with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig: Excel shows £ and é right
            w = csv.writer(f)
            w.writerow(['url', 'status', *self.fields])
            for u, row in self.rows.items():
                if row:
                    w.writerow([u, row['status'], *(row.get(k, '') if row.get(k) is not None else '' for k in self.fields)])
        tmp.replace(self.out)
