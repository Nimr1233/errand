"""The real engine (main spec sections 13-14). A job is a list of links and the fields to read from
each page. It reports to mission control the same way the demo engine does (errand/demo.py), so the
room and the Errand connector work with either.

53 agents share one task list and never wait in line: an agent takes the first task it can do now.
- fetch: one page, politely (errand/fetch.py). A page whose site is pausing waits; agents do other work.
- act: with clicking steps ("click the 256 GB option"), every page opens in a window, the steps are
  done safely (errand/clicks.py), and the page is read after them. A click that worked is replayed
  on later pages of that kind with no brain.
- render / stealth: a page the plain download couldn't read, in one of 25 shared browser windows
  (errand/browser.py). With every window busy the page waits on the shelf and the agent takes other
  work; an agent that finishes in a window hands it straight to the next page on the shelf.
- read: a brain reads one page (errand/extract.py). The first 10 pages of each kind of page (same
  site, same path depth) are samples.
- learn: the vote across pages learns a recipe from the samples' answers. Later pages of that kind
  are read by code, with a brain only for the fields no recipe covers (bench/results.md sections 7-8).
- reuse: a recipe saved by an earlier job for this kind of page (errand/store.py) is checked on 3
  pages instead of learned from 10; if the site changed and it no longer holds, it is learned afresh.
- fix: a page left without a field that most pages of its kind have (4 in 5 samples) is read again by
  a second brain: free Gemini (errand/gemini.py) for a public job within its daily budget, else the
  local 4B "senior" on the CPU (errand/brains.py) - for every private job, and public when Gemini is spent.
- huddle: when a recipe stops working (3 pages of its kind come back empty where the samples weren't),
  its new pages wait while agents gather: 3 re-read 3 pages with their brains and a new recipe is
  learned from them, then 9, then everyone. If no round fixes it, it goes to you: the brains read those
  fields page by page from then on (approve), or that kind's pages are skipped.
Results go to jobs/<job>.csv: one row per link, with its status ("ok", "blocked: bot check", ...).
A finished job leaves a short note in the chief's memory (errand/memory.py, gbrain) when gbrain is installed.
No checker brain: measured, it broke more answers than it fixed (bench/results.md section 11).
"""
import csv, pathlib, re, threading, time, urllib.parse
from collections import deque

from . import clicks, exports, extract as x, memory
from .gemini import Gemini
from .store import Store
from .brains import URL as BRAIN_URL, SENIOR, SENIOR_URL, SENIOR_SLOTS, SENIOR_CTX, SENIOR_FLAGS, BrainServer
from .demo import N, STEP, slug
from .browser import Pool
from .fetch import UA, Polite, challenged, login_wall, site
from .updates import UpdateLog

RESULTS = pathlib.Path(__file__).resolve().parent.parent / 'jobs'
SAMPLES = 10  # bench/results.md section 8: 5 samples broke fresh Wikipedia pages, 10 didn't
SAVE_EVERY = 20  # rows between rewrites of the results file
CHECK = 3  # pages a saved recipe is checked on before it is trusted again
WINDOW = ('render', 'stealth', 'act')  # tasks that need a browser window
HUDDLE_AT = 3  # broken pages of one kind before agents huddle on its recipe
HUDDLE_SIZES = (3, 9, None)  # pages re-read per round; None: every page of that kind at hand


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
        self.window = self.used_window = False
        self.passes = 0  # pages it took from the shelf in a window it kept
        self.shot, self.shot_n = None, 0  # its window's last picture, for the room
        self.huddle = self.board_pid = None  # the problem it huddles on / waits on you for
        self.reason = ''
        self.fix_ok = self.fix_tried = 0

    def view(self):
        kind, url = self.task or (None, '')
        return {'n': self.n, 'state': self.state, 'task': kind, 'site': site(url) if '://' in url else url,
                'pages': self.pages, 'window': self.window, 'used_window': self.used_window, 'passes': self.passes,
                'reason': self.reason, 'shot': self.shot_n,
                'prog': 0.5 if self.task else 0.0, 'log': self.steps[-1] if self.steps else '', 'huddle': self.huddle,
                'fix_ok': self.fix_ok, 'fix_tried': self.fix_tried}


class Engine:
    def __init__(self, brain=None, fetcher=None, results=RESULTS, samples=SAMPLES, log_path=None, server_log=None,
                 remember=True, gemini=None, store=None, pool=..., chooser=None, senior=None, senior_log=None):
        self.lock = threading.Condition()
        self.agents = [Agent(i + 1) for i in range(N)]
        self.updates = UpdateLog(log_path)
        self.fetcher = fetcher or Polite()
        self.brain = brain  # brain(view_text, fields) -> answers; None: start llama-server on the first job
        self.chooser = chooser  # chooser(step, offered) -> name to click; made with the brains when None
        self.server = None if brain else BrainServer(server_log)
        self.brains = 'ready' if brain else 'off'  # off | starting | ready | failed: why
        self.senior = senior  # the 4B senior brain; None: start its own CPU llama-server when a hard call needs it
        self.senior_server = None if senior else BrainServer(senior_log, model=SENIOR, url=SENIOR_URL,
                                                             slots=SENIOR_SLOTS, ctx=SENIOR_CTX, flags=SENIOR_FLAGS)
        self.senior_state = 'ready' if senior else 'off'  # off | absent | starting | ready | failed: why
        self.results, self.samples, self.remember = results, samples, remember
        self.gemini = gemini or Gemini()
        self.store = store or Store()
        self.pool = Pool() if pool is ... else pool  # None: no browser steps (plain downloads only)
        self.handoffs, self.last_hand, self.why = 0, '', {}
        self.job_id, self.reused = None, 0
        self.board, self.huddle, self.problems, self.pid, self.raised, self.fixed = deque(), None, {}, 0, 0, 0
        self.private, self.gemini_calls, self.gemini_fixed = False, 0, 0
        self.senior_calls, self.senior_fixed, self.senior_clicks = 0, 0, 0
        self.steps, self.spec, self.clicks_by_brain, self.clicks_replayed = [], {}, 0, 0
        self.threads, self.closed, self.paused = [], False, False
        self.job, self.total, self.done, self.inflight, self.blocked, self.brain_calls, self.by_code = None, 0, 0, 0, 0, 0, 0
        self.tasks, self.rows, self.html, self.groups = deque(), {}, {}, {}
        self.hist, self.rate = [0], 0.0
        self.out = None

    # ---- commands (the local API and the Errand connector call these) ----
    def start_job(self, prompt, urls, fields, focus=None, private=False, steps=None):
        spec = {'fields': dict(fields or {}), 'steps': [str(s).strip() for s in steps or [] if str(s).strip()][:10]}
        fields = parse_fields(fields)
        if spec['steps'] and not self.pool:
            raise ValueError('clicking steps need browser windows, and this Errand runs without them')
        if not fields:
            raise ValueError('say which fields to read, like {"price": "the price", "stock": "number: copies in stock"}')
        urls = list(dict.fromkeys(u.strip() for u in urls or [] if u and u.strip()))
        if not urls:
            raise ValueError('give urls or a file with one link per line')
        with self.lock:
            if self.job and not self.complete():
                raise ValueError(f"job '{self.job}' is still running")
            self.job, self.fields, self.focus = prompt.strip()[:60] or 'Untitled job', fields, focus or None
            self.private, self.gemini_calls, self.gemini_fixed = bool(private), 0, 0  # private: Gemini never sees it
            self.senior_calls, self.senior_fixed, self.senior_clicks = 0, 0, 0
            self.spec, self.steps, self.clicks_by_brain, self.clicks_replayed = spec, spec['steps'], 0, 0
            self.total, self.done, self.inflight, self.blocked, self.brain_calls, self.by_code = len(urls), 0, 0, 0, 0, 0
            self.tasks = deque(('fetch', u) for u in urls)
            self.rows, self.html, self.groups = {u: None for u in urls}, {}, {}
            for u in urls:
                g = self.groups.setdefault(kind_of_page(u), {'recipe': None, 'samples': {}, 'sampling': set(),
                                                            'waiting': [], 'unfetched': 0, 'learning': False,
                                                            'broken': [], 'hold': False})
                g['unfetched'] += 1
            for kind, g in self.groups.items():  # a saved recipe for every field: check it on 3 pages, not 10
                g['clicks'] = {s: n for s, n in self.store.clicks(kind).items() if s in self.steps}
                saved = self.store.recipes(kind, fields)
                g['saved'] = saved if set(saved) == set(fields) else None
                g['target'] = CHECK if g['saved'] else self.samples
            self.job_id, self.reused = self.store.start_job(self.job, self.total, fields, self.private), 0
            self.handoffs, self.last_hand, self.why = 0, '', {}
            self.board, self.huddle, self.problems, self.raised, self.fixed = deque(), None, {}, 0, 0
            self.out, self.announced, self.saved_at = self._free_name(slug(self.job)), False, 0
            self.hist, self.rate = [0], 0.0
            for a in self.agents:
                a.reset()
            self.updates.add('job', f"Job '{self.job}' started · {self.total} pages · reading "
                                    + ', '.join(f'{k} ({kind})' if kind != 'text' else k for k, (_, kind) in fields.items())
                                    + (f" · after: {'; '.join(self.steps)}" if self.steps else ''))
            self._start_brains()
            self._start_agents()
            self.lock.notify_all()
        return {'job': self.job, 'pages': self.total}

    def answer_problem(self, n, approve):
        """A huddle couldn't fix a recipe: approve lets the brains read those fields page by page; no skips
        that kind's pages."""
        with self.lock:
            a = self._agent(n)
            if a is None or a.state != 'needs_you' or not a.board_pid:
                return {'ok': False, 'error': f'agent #{n} has no problem waiting'}
            p = self.problems[a.board_pid]
            g = self.groups[p['site']]
            pages = list(dict.fromkeys(g['broken'] + g['waiting']))
            if approve:
                self.tasks.extendleft(('read', u) for u in reversed(pages))  # brains read what the recipe can't
            else:  # pages the broken recipe already read are unreliable too
                for u in pages:
                    self._row(u, {'status': 'skipped by you'}, by_brain=False)
                    self.html.pop(u, None)
            g['broken'], g['waiting'], g['hold'] = [], [], False
            p['state'], a.state, a.board_pid, a.reason = 'answered', 'idle', None, ''
            self.updates.add('cleared', f"#{n} {'approved: brains read ' + ', '.join(p['fields']) + ' on ' + p['site'] if approve else 'skipped ' + p['site']}"
                                        f' ({len(pages)} pages)', n)
            self._finish_check()
            self.lock.notify_all()
        return {'ok': True}

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
        if self.pool:
            self.pool.close()

    # ---- views ----
    def status(self):
        with self.lock:
            fetched = self.total - sum(g['unfetched'] for g in self.groups.values())
            recipes = [k for k, g in self.groups.items() if g['recipe']]
            calls, by_code = self.brain_calls, self.by_code
            left = self.total - self.done
            shelf = [t[1] for t in self.tasks if t[0] in WINDOW]
            size, in_use = (self.pool.size, self.pool.in_use) if self.pool else (0, 0)
            return {
                'job': self.job or 'No job yet', 'total': self.total, 'pages_done': self.done,
                'speed': round(self.rate, 1), 'seconds_left': round(left / self.rate) if self.rate else None,
                'agents': N, 'finished': sum(a.state == 'finished' for a in self.agents), 'handoffs': self.handoffs,
                'shelf': len(shelf), 'problems': sum(a.state == 'needs_you' for a in self.agents), 'raised': self.raised,
                'blocked': self.blocked, 'windows': size,
                'windows_in_use': in_use, 'next_on_shelf': [u.rstrip('/').rsplit('/', 1)[-1][:30] for u in shelf[:3]],
                'last_handoff': self.last_hand, 'brains': N, 'paused': self.paused, 'complete': self.complete(),
                'huddle': self._huddle_view(), 'board': len(self.board), 'fixed_by_huddles': self.fixed,
                'set_aside': sum(len(g['waiting']) for g in self.groups.values() if g['hold']),
                'results': str(self.out) if self.out else 'no job yet',
                'mode': 'real', 'brains_state': self.brains, 'fetched': fetched, 'recipes': len(recipes),
                'brain_calls': calls, 'by_code': by_code, 'private': self.private, 'recipes_reused': self.reused,
                'gemini': 'off: private job' if self.private else self.gemini.state(),
                'gemini_calls': self.gemini_calls, 'gemini_fixed': self.gemini_fixed, 'steps': self.steps,
                'senior': self.senior_state, 'senior_calls': self.senior_calls, 'senior_fixed': self.senior_fixed,
                'senior_clicks': self.senior_clicks,
                'clicks_by_brain': self.clicks_by_brain, 'clicks_replayed': self.clicks_replayed,
                # the room's middle TV and desk monitors
                'tv_hand': {'label': '// PAGES READ BY CODE', 'val': by_code, 'of': f'/{self.done}',
                            'sub': f'{len(recipes)} recipe{"s" * (len(recipes) != 1)} learned from the brains'},
                'desks': [['WINDOWS IN USE', f'{in_use}/{size}', 'private, wiped after every page'],
                          ['BRAINS', self.brains.split(':')[0].upper(), self.brains if ':' in self.brains else
                           f'{fetched}/{self.total} pages fetched'],
                          ['PAGES WAITING FOR A WINDOW', str(len(shelf)), 'none waiting' if not shelf else
                           'next: ' + ' '.join(u.rstrip('/').rsplit('/', 1)[-1][:12] for u in shelf[:3])],
                          ['BRAIN CALLS', str(calls), f'{by_code} by code · {len(recipes)} recipes · '
                           f'Gemini {self.gemini_calls} · senior {self.senior_calls}'],
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
        """The problem board: the running huddle, problems waiting their turn, the newest 10 others."""
        short = lambda p: {k: p[k] for k in ('id', 'kind', 'site', 'by', 'state')} | {'rounds': len(p['rounds'])}
        with self.lock:
            return {'huddle': self._huddle_view(), 'waiting': [short(p) for p in self.board],
                    'recent': [short(p) for p in reversed(self.problems.values()) if p['state'] not in ('huddle', 'waiting')][:10]}

    def _huddle_view(self):
        h = self.huddle
        if not h:
            return None
        p = h['p']
        return {'id': p['id'], 'kind': p['kind'], 'site': p['site'], 'round': h['round'], 'size': len(h['pages'])}

    def history(self, limit=20):
        return self.store.jobs(limit)

    def save_skill(self, name, description):
        """Keep the current job's fields and steps under a name; {blanks} in them are filled when it runs."""
        if not self.spec:
            raise ValueError('run a job first: a skill is saved from the current job')
        self.store.save_skill(name.strip()[:60], description.strip()[:300], self.spec['fields'], self.spec['steps'])
        return {'ok': True, 'skill': name.strip()[:60]}

    def run_skill(self, name, urls, values=None):
        k = self.store.skill(name)
        if k is None:
            raise ValueError(f"there's no skill called '{name}'")
        v = values or {}
        return self.start_job(clicks.fill(k['name'], v), urls, {f: clicks.fill(d, v) for f, d in k['fields'].items()},
                              steps=[clicks.fill(s, v) for s in k['steps']])

    def problem_detail(self, pid):
        return self.problems.get(pid)

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
                senior_pick = self._count_senior_clicks(clicks.llama_chooser(SENIOR_URL))
                self.chooser = self.chooser or clicks.senior_chooser(
                    clicks.llama_chooser(BRAIN_URL), senior_pick, ready=self._ensure_senior_for_click)
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

    def _start_senior(self):
        """Wake the 4B senior on its own CPU llama-server. Non-blocking, like the brains; idempotent."""
        if self.senior_state in ('ready', 'starting'):
            return
        if not SENIOR.exists():
            self.senior_state = 'absent'
            return
        self.senior_state = 'starting'
        self.updates.add('job', 'Waking the 4B senior brain (CPU, about 30 s) for the hard calls')

        def run():
            try:
                self.senior_server.start()
                self.senior, state = x.llama_brain(SENIOR_URL), 'ready'
                self.updates.add('job', 'The 4B senior is ready')
            except Exception as e:
                state = f'failed: {e}'
                self.updates.add('problem', f'The 4B senior could not start: {e}')
            with self.lock:
                self.senior_state = state
                self.lock.notify_all()
        threading.Thread(target=run, daemon=True, name='senior').start()

    def _senior_possible(self):
        return self.senior_state in ('ready', 'starting') or (self.senior_state == 'off' and SENIOR.exists())

    def _fix_wants_senior(self):
        """The local senior answers a fix whenever Gemini can't: every private job, and any public job
        whose free Gemini has no key or is out of its daily budget."""
        return self.private or self.gemini.state() != 'ready'

    def _fix_available(self):
        """Is any second-opinion brain available for a fix right now (or startable)?"""
        return (not self.private and self.gemini.state() == 'ready') or self._senior_possible()

    def _fix_brain(self):
        """The brain and label for a 'fix' call, or (None, None) if none is available."""
        if not self.private and self.gemini.state() == 'ready':
            return self.gemini.brain, 'gemini'
        return (self.senior, 'senior') if self.senior_state == 'ready' else (None, None)

    def _ensure_senior_for_click(self):
        """Make the 4B senior ready for a click choice: start it and wait once for it to load.
        True if it can answer. Runs off the engine lock, so it may block just this one agent briefly."""
        with self.lock:
            if self.senior_state != 'ready':
                if not self._senior_possible():
                    return False
                self._start_senior()
                self.lock.wait_for(lambda: self.senior_state in ('ready', 'failed', 'absent'), timeout=120)
            return self.senior_state == 'ready'

    def _count_senior_clicks(self, pick):
        """Wrap the senior's click chooser so the room can see how often the big brain chose a click."""
        def choose(step, offered):
            with self.lock:
                self.senior_clicks += 1
            return pick(step, offered)
        return choose

    def _needs_brain(self, url):
        g = self.groups[kind_of_page(url)]
        return g['recipe'] is None or bool(set(self.fields) - set(g['recipe']))

    def _work(self, a):
        t = None
        while True:
            with self.lock:
                while t is None and not self.closed and (t := self._take(a)) is None:
                    if a.state not in ('stopped', 'needs_you'):
                        a.state = 'finished' if self.job and not self.tasks and self._all_assigned() else 'idle'
                    self.lock.wait(0.5)
                if self.closed:
                    return
                a.task, a.state = t, 'huddle' if t[0] in ('hread', 'hlearn') else 'working'
                a.huddle = self.huddle['p']['id'] if a.state == 'huddle' and self.huddle else None
                self.inflight += 1
            try:
                result = self._do(a, t)
            except Exception as e:  # one bad page never stops an agent
                result = {'status': f'error: {type(e).__name__}'}
            with self.lock:
                self.inflight -= 1
                self._record(a, t, result)
                a.task, a.huddle = None, None
                if a.state in ('working', 'huddle'):
                    a.state = 'idle'
                t = self._hand_off(a) if a.window else None
                self.lock.notify_all()

    def _hand_off(self, a):
        """An agent done with its window gives it straight to the next page on the shelf (whose site
        is free), or returns it to the pool."""
        if not self.paused and a.state != 'stopped':
            for i, t in enumerate(self.tasks):
                if t[0] in WINDOW and self.fetcher.take(t[1]):
                    del self.tasks[i]
                    a.passes += 1
                    self.handoffs += 1
                    self.last_hand = f"#{a.n} > {t[1].rstrip('/').rsplit('/', 1)[-1][:20]}"
                    self.updates.add('handoff', f'#{a.n} kept its window for the next page: {t[1][-60:]}', a.n)
                    return t
        self.pool.give_back()
        a.window = False
        return None

    def _all_assigned(self):
        return not self.huddle and not self.board and \
            all(not g['waiting'] and not g['sampling'] and not g['learning'] for g in self.groups.values())

    def _take(self, a):
        if self.paused or a.state in ('stopped', 'needs_you') or not self.job:
            return None
        busy, no_window = set(), False
        for i, t in enumerate(self.tasks):
            if (t[0] == 'read' and self._needs_brain(t[1]) or t[0] == 'hread' or
                    t[0] == 'act' and set(self.steps) - set(self.groups[kind_of_page(t[1])]['clicks'])) and self.brains != 'ready':
                continue
            if t[0] == 'fix' and self._fix_wants_senior() and self.senior_state != 'ready':
                if self.senior_state in ('failed', 'absent'):
                    del self.tasks[i]  # the senior can't answer: leave the field as the 2B read it
                    return self._take(a)
                self._start_senior()
                continue  # wait until the senior has loaded
            if t[0] == 'render' and t[1] in self.html and self._data_only(kind_of_page(t[1])):
                del self.tasks[i]  # queued for a window before the recipe existed; its hidden data is enough now
                self._page(a, t[1], self.html[t[1]], 'ok')
                return self._take(a)
            if t[0] in WINDOW and no_window:
                continue  # every window is busy: browser pages wait on the shelf, the agent takes other work
            if t[0] == 'fetch' or t[0] in WINDOW:
                s = site(t[1])
                if s in busy or not self.fetcher.take(t[1]):
                    busy.add(s)
                    continue
                if t[0] in WINDOW:
                    if not self.pool.take():
                        self.fetcher.release(t[1], pause=0)
                        no_window = True
                        continue
                    a.window = a.used_window = True
            del self.tasks[i]
            return t
        return None

    def _do(self, a, t):
        kind, key = t
        if kind == 'fetch':
            return self.fetcher.fetch(key)
        if kind == 'render' and key in self.html and self._data_only(kind_of_page(key)):
            self.fetcher.release(key)  # handed a window before the recipe existed: the hidden data is enough
            return {'status': 'ok', 'code': 200, 'html': self.html[key]}
        if kind in WINDOW:
            try:
                r = self.pool.render(key, UA) if kind == 'render' else self.pool.stealth(key) if kind == 'stealth' else \
                    self.pool.act(key, UA, self.steps, dict(self.groups[kind_of_page(key)]['clicks']), self.chooser)
            finally:
                self.fetcher.release(key)
            if r.get('shot'):
                a.shot, a.shot_n = r['shot'], a.shot_n + 1
            return r
        if kind == 'hlearn':  # the huddle's fix: a new recipe from the pages its members just re-read
            h = self.huddle
            pages = [(self.html[u], ans) for u, ans in h['answers'].items()]
            recipe = x.learn_recipe(pages, self.fields, focus=self.focus)
            ok = sum(all(x.same(self.fields[f][1], x.replay(p, {f: recipe[f]}, self.fields)[f], ans.get(f))
                         for f in h['p']['fields'] if f in recipe) for p, ans in pages)
            return {'recipe': recipe, 'pages_ok': ok if all(f in recipe for f in h['p']['fields']) else 0}
        if kind == 'learn':
            g = self.groups[key]
            pages = [(self.html[u], ans) for u, ans in g['samples'].items()]
            if g['saved']:  # a recipe from an earlier job: does it still read this site right?
                ok = all(x.holds(pages, self.fields, f, k) for f, k in g['saved'].items())
                return {'recipe': g['saved'], 'reused': True} if ok else {'changed': True}
            return {'recipe': x.learn_recipe(pages, self.fields, focus=self.focus)}
        g, used, who = self.groups[kind_of_page(key)], [], None
        if kind == 'fix':
            helper, who = self._fix_brain()
            if helper is None:  # no second-opinion brain available: leave the row as it was
                return {'answers': {}, 'brain': False, 'by': None}
        else:
            helper = self.brain

        def brain(view, fields):  # counts brain calls and keeps what the agent is reading, for the room
            a.excerpt = view
            used.append(1)
            return helper(view, fields)
        recipe = None if kind in ('fix', 'hread') else g['recipe']  # a fix and huddles read the whole page afresh
        return {'answers': x.read_page(self.html[key], self.fields, brain, recipe, focus=self.focus),
                'brain': bool(used), 'by': who}

    def _record(self, a, t, r):
        kind, key = t
        if kind == 'fetch':
            g = self.groups[kind_of_page(key)]
            if r['status'] in ('retry', 'again'):  # the page goes back in line while its site pauses
                self.tasks.appendleft(t) if r['status'] == 'again' else self.tasks.append(t)
                if r['status'] == 'retry':  # the site asked to slow down
                    self.updates.add('blocked', f"{site(key)} asked us to slow down: pausing it {r['pause']} s", a.n)
                return
            a.steps.append(f"fetch {key[-60:]}: {r['status']}")
            if self.steps and r['status'] in ('ok', 'needs browser'):  # clicking needs the page in a window
                self.tasks.append(('act', key))
                return
            if r['status'] == 'needs browser' and self._data_only(kind_of_page(key)):
                r = {'status': 'ok', 'html': r['html']}  # its hidden data holds every field: no window needed
            if r['status'] == 'needs browser' and self.pool:  # a JavaScript page: up the ladder to a window
                self.html[key] = r['html']  # the plain page, in case the window can't load it
                self.tasks.append(('render', key))
                return
            if r['status'] == 'needs stealth' and self.pool:
                self.why[key] = r['why']
                self.tasks.append(('stealth', key))
                return
            if r['status'] == 'needs browser':
                r = {'status': 'ok', 'html': r['html']}
            elif r['status'] == 'needs stealth':
                r = {'status': r['why']}
            self._page(a, key, r.get('html'), r['status'])
        elif kind == 'act':
            g, done = self.groups[kind_of_page(key)], r.get('done', [])
            for d in done:
                if d['ok'] and d['how'] == 'brain':
                    g['clicks'][d['step']] = d['name']  # replayed on this kind's next pages with no brain
                    if not self.private:
                        self.store.save_click(kind_of_page(key), d['step'], d['name'])
            self.clicks_by_brain += sum(d['ok'] and d['how'] == 'brain' for d in done)
            self.clicks_replayed += sum(d['ok'] and d['how'] == 'replay' for d in done)
            failed = next((d for d in done if not d['ok']), None)
            status = r['status'] if r['status'] != 'ok' else f"click failed: {failed['why']}" if failed else 'ok'
            if status == 'ok' and (challenged(r.get('code') or 200, r['html']) or login_wall(r['html'])):
                status = 'blocked: bot check' if challenged(r.get('code') or 200, r['html']) else 'blocked: login page'
            a.steps.append(f'act {key[-50:]}: {clicks.describe(done) or status}')
            self._page(a, key, r.get('html') if status == 'ok' else None, status)
        elif kind in WINDOW:
            html, status = (r.get('html'), 'ok') if r['status'] == 'ok' else (None, r['status'])
            if html and challenged(r.get('code') or 200, html):  # still a bot check: never solved
                html, status = None, self.why.pop(key, 'blocked: bot check')
            elif html and login_wall(html):
                html, status = None, 'blocked: login page'
            if html is None and kind == 'render' and key in self.html:  # read the plain page after all
                html, status = self.html[key], 'ok'
            a.steps.append(f'{kind} {key[-60:]}: {status}')
            self._page(a, key, html, status)
        elif kind == 'hread':
            h = self.huddle
            h['answers'][key] = r.get('answers', {})
            h['members'].add(a.n)
            self.brain_calls += r.get('brain', False)
            a.fix_tried, a.fix_ok = 1, int(bool(r.get('answers')))
            if len(h['answers']) == len(h['pages']):
                self.tasks.appendleft(('hlearn', h['p']['site']))
        elif kind == 'hlearn':
            self._end_round(a, r)
        elif kind == 'learn' and r.get('changed'):  # the saved recipe no longer holds: learn from 10 pages
            g = self.groups[key]
            g['saved'], g['target'], g['learning'] = None, self.samples, False
            self.store.forget_recipe(key, self.fields)
            while g['waiting'] and len(g['samples']) + len(g['sampling']) < g['target']:
                u = g['waiting'].pop(0)
                g['sampling'].add(u)
                self.tasks.appendleft(('read', u))
            self.updates.add('recipe', f'#{a.n} the saved recipe for {key} no longer reads it right '
                                       f'(the site changed?): learning a new one from {self.samples} pages', a.n)
            self._maybe_learn(g, key)
        elif kind == 'learn':
            g = self.groups[key]
            g['recipe'], g['learning'] = r.get('recipe', {}), False
            if r.get('reused'):
                self.reused += 1
            elif g['recipe'] and not self.private:
                self.store.save_recipe(key, g['recipe'], self.fields, self.job_id)
            g['filled'] = {f: sum(ans.get(f) not in (None, '') for ans in g['samples'].values()) / len(g['samples'])
                           for f in self.fields}
            for u, ans in g['samples'].items():  # the vote also corrects the samples' slips
                self.rows[u] = {'status': 'ok', **ans, **x.replay(self.html[u], g['recipe'], self.fields)}
                if not self._maybe_fix(g, u):
                    self.html.pop(u, None)
            self.tasks.extendleft(('read', u) for u in reversed(g['waiting']))
            g['waiting'] = []
            covered = len(g['recipe'])
            a.steps.append(f'learn {key}: {covered}/{len(self.fields)} fields by code')
            self.updates.add('recipe', f"#{a.n} {'reused the saved recipe' if r.get('reused') else 'learned a recipe'} "
                                       f"for {key}, checked on {len(g['samples'])} pages: "
                                       f'{covered} of {len(self.fields)} fields now read by code', a.n)
            self._save()
        else:
            g = self.groups[kind_of_page(key)]
            if kind == 'fix':  # a fix only fills what was missing; a failed fix changes nothing
                filled = {f: v for f, v in r.get('answers', {}).items()
                          if v not in (None, '') and self.rows[key].get(f) in (None, '')}
                self.rows[key].update(filled)
                if r.get('by') == 'senior':
                    self.senior_calls += r.get('brain', False)
                    self.senior_fixed += len(filled)
                    label = 'the 4B senior'
                else:
                    self.gemini_calls += r.get('brain', False)
                    self.gemini_fixed += len(filled)
                    label = 'Gemini'
                self.html.pop(key, None)
                if filled:
                    self.updates.add('fixed', f"#{a.n} {label} filled {', '.join(filled)} on {key[-70:]}", a.n)
            elif 'answers' not in r:
                self._row(key, {'status': r['status']}, by_brain=False)
                g['sampling'].discard(key)
            elif key in g['sampling']:
                g['sampling'].discard(key)
                g['samples'][key] = r['answers']
                self._row(key, {'status': 'ok', **r['answers']}, by_brain=True)  # html kept for the vote
            else:
                self._row(key, {'status': 'ok', **r['answers']}, by_brain=r['brain'])
                bad = self._broken(g, key)
                if bad and not g['hold']:  # the recipe read nothing where the samples had something
                    g['broken'].append(key)  # html kept: a huddle may re-read it
                    if len(g['broken']) >= HUDDLE_AT:
                        self._raise(a, kind_of_page(key), g, bad)
                    else:
                        self._maybe_fix(g, key)
                elif not self._maybe_fix(g, key):
                    self.html.pop(key, None)
            a.pages += kind != 'fix'
            a.steps.append(f"read {key[-60:]}: {'brain' if r.get('brain') else 'code'}")
            self._maybe_learn(g, kind_of_page(key))
        self._finish_check()

    def _finish_check(self):
        if self.complete() and not self.announced:
            self.announced = True
            self._save()
            self.updates.add('job', f"Job '{self.job}' finished · {self.done} pages · {self.blocked} blocked · "
                                    f'{self.by_code} read by code · results: {self.out}')
            self.store.finish_job(self.job_id, self.rows, done=self.done, blocked=self.blocked, by_code=self.by_code,
                                  brain_calls=self.brain_calls, gemini_calls=self.gemini_calls, results=self.out)
            exports.send_later(self, self.job, {'done': self.done, 'blocked': self.blocked, 'by_code': self.by_code,
                                                'results': self.out}, list(self.fields), dict(self.rows), self.private)
            if self.remember:  # the chief's memory (gbrain): what ran, which sites blocked, where results are
                memory.save_job(self.job, time.strftime('%Y-%m-%d %H:%M'), self.done, list(self.fields),
                                self.by_code, self.brain_calls, self.out, dict(self.rows))

    def _page(self, a, key, html, status):
        """A link's fetching is over: read the page it gave, or record why there is none."""
        g = self.groups[kind_of_page(key)]
        g['unfetched'] -= 1
        if html is None:
            self.html.pop(key, None)
            self._row(key, {'status': status}, by_brain=False)
            if status.startswith(('blocked', 'disallowed', 'refused')):
                self.blocked += 1
                self.updates.add('blocked', f'#{a.n} {status}: {key[-80:]}', a.n)
        else:
            self.html[key] = html
            if not self.private:
                self.store.cache_page(key, html)
            if g['hold']:
                g['waiting'].append(key)  # its recipe is being fixed by a huddle, or waits on you
            elif g['recipe'] is not None:
                self.tasks.appendleft(('read', key))  # reads go first: brains work while sites pause
            elif len(g['samples']) + len(g['sampling']) < g['target']:
                g['sampling'].add(key)
                self.tasks.appendleft(('read', key))
            else:
                g['waiting'].append(key)  # waits for its kind's recipe
        if self.huddle and self.huddle['wanting'] and self.huddle['p']['site'] == kind_of_page(key):
            self._round()  # a waiting round starts once the pages it needs arrived, or no more can come
        self._maybe_learn(g, kind_of_page(key))

    def _data_only(self, kind):
        """This kind's recipe reads every field from the page's hidden data (JSON-LD and the like)."""
        rec = self.groups[kind]['recipe'] or {}
        return set(rec) == set(self.fields) and all(reader == 'data' for reader, _ in rec.values())

    def _broken(self, g, url):
        """Fields the recipe should read but gave nothing for, where 4 in 5 samples had a value."""
        row = self.rows[url]
        return [f for f in (g['recipe'] or {}) if row.get(f) in (None, '') and g.get('filled', {}).get(f, 0) >= 0.8]

    def _raise(self, a, kind, g, fields):
        """A recipe stopped working: a problem on the board, and that kind's new pages wait."""
        self.pid += 1
        self.raised += 1
        p = {'id': f'P-{self.pid}', 'kind': 'recipe stopped working', 'site': kind, 'by': a.n, 'state': 'waiting',
             'rounds': [], 'fields': fields}
        self.problems[p['id']] = p
        self.board.append(p)
        g['hold'] = True
        self.updates.add('huddle', f"{p['id']} raised by #{a.n}: the recipe for {kind} stopped reading {', '.join(fields)}", a.n)
        self._next_huddle()

    def _next_huddle(self):
        if self.huddle is None and self.board:
            p = self.board.popleft()
            p['state'] = 'huddle'
            self.huddle = {'p': p, 'round': 0, 'pages': [], 'answers': {}, 'members': set(), 'wanting': False}
            self._round()

    def _round(self):
        """The next round: more agents re-read more pages of the broken kind with their brains."""
        h = self.huddle
        g = self.groups[h['p']['site']]
        size = HUDDLE_SIZES[h['round']]
        at_hand = [u for u in dict.fromkeys(g['broken'] + g['waiting']) if u in self.html]
        h['wanting'] = len(at_hand) < (size or len(at_hand) + 1) and g['unfetched'] > 0
        if h['wanting']:
            return  # more pages of this kind are still being fetched: the round starts when they arrive
        pages = at_hand if size is None else at_hand[:size]
        if len(pages) < x.MIN_HITS or len(pages) <= len(h['pages']):  # no more pages to learn from
            return self._to_you()
        h['round'] += 1
        h['pages'], h['answers'], h['members'] = pages, {}, set()
        self.tasks.extendleft(('hread', u) for u in reversed(pages))
        self.updates.add('huddle', f"{h['p']['id']} round {h['round']}: {len(pages)} agents re-read {len(pages)} pages of "
                                   f"{h['p']['site']}")

    def _end_round(self, a, r):
        h = self.huddle
        p, g = h['p'], self.groups[h['p']['site']]
        ok, recipe = r.get('pages_ok', 0), r.get('recipe', {})
        p['rounds'].append({'round': h['round'], 'agents': len(h['members']), 'pages': len(h['pages']),
                            'winner': a.n if ok else None, 'best': ok, 'fixes': [{'agent': a.n, 'pages_ok': ok}]})
        if not ok:
            return self._round() if h['round'] < len(HUDDLE_SIZES) else self._to_you()
        g['recipe'], g['hold'] = recipe, False  # the site changed: the new recipe replaces the old one
        self.store.forget_recipe(p['site'], self.fields)
        if not self.private:
            self.store.save_recipe(p['site'], recipe, self.fields, self.job_id)
        self.tasks.extendleft(('read', u) for u in reversed(list(dict.fromkeys(g['broken'] + g['waiting']))))
        g['broken'], g['waiting'] = [], []
        p['state'] = 'fixed'
        self.fixed += 1
        self.updates.add('huddle', f"{p['id']} fixed by the huddle in round {h['round']}: a new recipe for {p['site']} "
                                   f"reads {ok}/{len(h['pages'])} pages right", a.n)
        self.huddle = None
        self._next_huddle()

    def _to_you(self):
        """No round fixed it: one agent waits on you, and that kind's pages wait with it."""
        p = self.huddle['p']
        g = self.groups[p['site']]
        g['recipe'] = {f: k for f, k in (g['recipe'] or {}).items() if f not in p['fields']}  # brains read those now
        a = next((a for a in self.agents if a.state in ('idle', 'finished')), self._agent(p['by']))
        a.state, a.board_pid = 'needs_you', p['id']
        a.reason = f"couldn't fix the recipe for {p['site']}: brains read {', '.join(p['fields'])} page by page if you approve"
        p['state'] = 'yours'
        self.updates.add('problem', f"#{a.n} needs you: {a.reason}", a.n)
        self.huddle = None
        self._next_huddle()

    def _maybe_fix(self, g, url):
        """Queue a second opinion when a field most pages of this kind have came back empty here: free
        Gemini for a public job, else the local 4B senior (every private job, and public when Gemini is spent)."""
        if 'filled' not in g or not self._fix_available():
            return False
        if any(self.rows[url].get(f) in (None, '') and share >= 0.8 for f, share in g['filled'].items()):
            if self._fix_wants_senior():
                self._start_senior()
            self.tasks.appendleft(('fix', url))
            return True
        return False

    def _maybe_learn(self, g, key):
        if g['recipe'] is None and not g['learning'] and not g['sampling'] and g['samples'] and \
                (len(g['samples']) >= g['target'] or g['unfetched'] == 0):
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
