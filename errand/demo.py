"""Demo engine (spec section 17 "demo mode"): fake agents that follow the real engine's rules,
so mission control and the Errand connector can be built and tested without the brains running.

Rules it follows:
- shared task queue: agents pull the next task, nobody owns a fixed page list (main spec section 13)
- the no-wait line (spec 2026-10-20-no-wait-line-design.md): agents never stand in line. A browser
  page that finds all 25 windows busy goes on the shelf and the agent takes the next task; an agent
  that finishes a browser page keeps its window for the next page on the shelf (a hand-off)
- an agent is "finished" when the queue has nothing left for it and its last task is done
- problems only you can solve (send, post, log in, CAPTCHA) wait for you until answered
- the huddle: problems agents can solve go on the problem board, one huddle at a time. Round 1
  has 3 agents, round 2 has 9, round 3 everyone; each suggests a fix, every fix is tried on 5 saved
  pages, the best wins (a vote breaks ties) and is used if it reads all 5. After round 3 the problem
  goes to you and that site's pages are set aside until you answer. Demo: fixes and scores are
  acted out with random numbers.
"""
import random
import re
from collections import deque

from .updates import UpdateLog

N = 53
WINDOWS = 25
STEP = 0.75  # seconds per tick
SITES = ['books.toscrape.com', 'quotes.toscrape.com', 'webscraper.io', 'scrapethissite.com']
REASONS = ['wants to submit a form', 'asks you to log in', 'wants to post a message',
           'page asks for a CAPTCHA']  # only you can solve these: never a huddle
HUDDLE_KINDS = ['recipe stopped working', 'checker disagrees with a price', 'page keeps failing to read',
                'stuck for 5 minutes']
HUDDLE_SIZES = (3, 9, None)  # None: everyone who isn't waiting on you or stopped
ROUND_TICKS = (3, 4, 5)  # demo: how long each round takes
FIX_CHANCE = (0.6, 0.6, 0.7)  # demo: chance a round finds a fix that reads all 5 test pages
TEST_PAGES = 5
HUDDLE_CHANCE = 0.0003  # per working-agent tick: about one huddle problem every 50 s
LOG = ['GET page 200', 'parse table ok', 'extract price ok', 'scroll +400', 'field upc ok',
       'recipe hit', 'fetch next page', 'validate row ok']
EXCERPTS = ['Title: A Light in the Attic · Price: £51.77 · In stock', 'Title: Tipping the Velvet · Price: £53.74',
            '"The world as we have created it is a process of our thinking." · Albert Einstein',
            'Country: Andorra · Capital: Andorra la Vella · Population: 84000']
PROBLEM_CHANCE = 0.0008  # per browser-agent tick: about one problem every 40 s with 25 windows busy
BLOCKED_CHANCE = 0.01
CHECK_CHANCE = 0.25


class Agent:
    def __init__(self, n, rng):
        self.n = n
        self.speed = 0.06 + rng.random() * 0.05  # task progress per tick: one task every 9-17 ticks
        self.reset()

    def reset(self):
        self.state = 'idle'  # idle | working | huddle | needs_you | finished | stopped
        self.task = None
        self.prog = 0.0
        self.pages = 0
        self.window = False
        self.used_window = False
        self.passes = 0  # pages it took from the shelf in a window it kept
        self.reason = ''
        self.steps = deque(maxlen=8)
        self.huddle = None  # the problem id it is huddling on
        self.fix_ok = self.fix_tried = 0  # its suggested fix: test pages read right / tried so far
        self.board_pid = None  # a huddle problem it waits on you for

    def view(self):
        t = self.task or {}
        return {'n': self.n, 'state': self.state, 'task': t.get('kind'), 'site': t.get('site'),
                'pages': self.pages, 'window': self.window, 'used_window': self.used_window,
                'passes': self.passes, 'reason': self.reason, 'prog': round(self.prog, 2),
                'log': self.steps[-1] if self.steps else '', 'huddle': self.huddle,
                'fix_ok': self.fix_ok, 'fix_tried': self.fix_tried}


class DemoEngine:
    def __init__(self, seed=None, log_path=None, loop_jobs=True):
        self.rng = random.Random(seed)
        self.agents = [Agent(i + 1, self.rng) for i in range(N)]
        self.updates = UpdateLog(log_path)
        self.problems = {}  # problem id -> its record, the newest 50
        self.pid = 0
        self.loop_jobs = loop_jobs
        self.start_job('Book prices', 1000)

    # ---- commands (the local API and the Errand connector call these) ----
    def start_job(self, prompt, count):
        self.job = prompt.strip()[:60] or 'Untitled job'
        self.total = max(1, int(count))
        self.queue = deque({'kind': 'extract', 'page': i, 'site': SITES[i % len(SITES)],
                            'browser': self.rng.random() < 0.45} for i in range(self.total))
        self.free = WINDOWS
        self.shelf = deque()  # browser pages waiting for a window
        self.board = deque()  # huddle problems waiting their turn
        self.huddle = None  # the running huddle
        self.parked = {}  # site -> its tasks, set aside while a problem on that site waits on you
        self.pages_done = self.handoffs = self.raised = self.blocked = self.fixed = 0
        self.last_hand = ''
        self.paused = False
        self.done_ticks = 0
        self.hist = [0]
        self.rate = 0.0
        for a in self.agents:
            a.reset()
        self.updates.add('job', f"Job '{self.job}' started · {self.total} pages")
        return {'job': self.job, 'pages': self.total}

    def answer_problem(self, n, approve):
        a = self._agent(n)
        if a is None or a.state != 'needs_you':
            return {'ok': False, 'error': f'agent #{n} has no problem waiting'}
        a.reason = ''
        if a.board_pid:  # a problem the huddle couldn't fix: its site's pages come back
            p = self.problems.get(a.board_pid)
            tasks = self.parked.pop(p['site'], []) if p else []
            if approve:
                self.queue.extendleft(reversed(tasks))
            else:
                self.pages_done += sum(t['kind'] == 'extract' for t in tasks)
            if p:
                p['state'] = 'answered'
            a.board_pid, a.state = None, 'idle'
            self.updates.add('cleared', f"#{n} {'approved: the site is back to work' if approve else 'skipped that site'}"
                             f" ({len(tasks)} pages)", n)
        elif approve:
            a.state = 'working'
            self.updates.add('cleared', f'#{n} approved, back to work', n)
        else:
            self._finish_task(a, skipped=True)
            self.updates.add('cleared', f'#{n} skipped that page', n)
        return {'ok': True}

    def stop_agent(self, n):
        a = self._agent(n)
        if a is None or a.state in ('finished', 'stopped'):
            return {'ok': False, 'error': f'agent #{n} is not running'}
        if a.task:
            self.queue.appendleft(a.task)  # its unfinished task goes back for another agent
            a.task = None
        if a.window:
            self._release(a)  # the next free agent takes it with a page from the shelf
        if a.state == 'huddle':
            self.huddle['members'].remove(a)
            a.huddle = None
        if a.board_pid:  # nobody will answer it now: its site's pages go back to work
            p = self.problems.get(a.board_pid)
            self.queue.extendleft(reversed(self.parked.pop(p['site'], []) if p else []))
            a.board_pid = None
        a.state = 'stopped'
        self.updates.add('stopped', f'#{n} stopped by you', n)
        return {'ok': True}

    def pause_all(self):
        self.paused = True
        self.updates.add('job', 'All agents paused')
        return {'ok': True}

    def resume_all(self):
        self.paused = False
        self.updates.add('job', 'All agents resumed')
        return {'ok': True}

    # ---- views ----
    def status(self):
        n_finished = sum(a.state == 'finished' for a in self.agents)
        left = self.total - self.pages_done
        return {'job': self.job, 'total': self.total, 'pages_done': self.pages_done, 'speed': round(self.rate, 1),
                'seconds_left': round(left / self.rate) if self.rate else None, 'agents': N,
                'finished': n_finished, 'handoffs': self.handoffs, 'shelf': len(self.shelf),
                'problems': sum(a.state == 'needs_you' for a in self.agents), 'raised': self.raised,
                'blocked': self.blocked, 'windows': WINDOWS, 'windows_in_use': WINDOWS - self.free,
                'next_on_shelf': [f"{t['site']}/page-{t['page']}" for t in list(self.shelf)[:3]],
                'last_handoff': self.last_hand,
                'brains': N, 'paused': self.paused, 'complete': self.complete(),
                'huddle': self._huddle_view(), 'board': len(self.board), 'fixed_by_huddles': self.fixed,
                'set_aside': sum(len(v) for v in self.parked.values()),
                'results': f'jobs/{slug(self.job)}.csv (demo: no file written)'}

    def agents_view(self, state=None):
        return [a.view() for a in self.agents if state is None or a.state == state]

    def board_view(self):
        """The problem board: the running huddle, problems waiting their turn, the newest 10 others."""
        short = lambda p: {k: p[k] for k in ('id', 'kind', 'site', 'by', 'state')} | {'rounds': len(p['rounds'])}
        return {'huddle': self._huddle_view(), 'waiting': [short(p) for p in self.board],
                'recent': [short(p) for p in reversed(self.problems.values())
                           if p['state'] not in ('huddle', 'waiting')][:10]}

    def problem_detail(self, pid):
        return self.problems.get(pid)

    def _huddle_view(self):
        h = self.huddle
        if not h:
            return None
        p = h['p']
        return {'id': p['id'], 'kind': p['kind'], 'site': p['site'], 'round': h['round'], 'size': len(h['members'])}

    def agent_detail(self, n):
        a = self._agent(n)
        if a is None:
            return None
        d = a.view()
        d['steps'] = list(a.steps)
        d['logged_in'] = False  # demo windows never log in
        d['page_excerpt'] = EXCERPTS[a.n % len(EXCERPTS)] if a.task else ''
        return d

    def complete(self):
        return not self.huddle and not self.board and all(a.state in ('finished', 'stopped') for a in self.agents)

    # ---- the clock ----
    def step(self):
        if self.paused:
            return
        if self.complete():
            self.done_ticks += 1
            if self.loop_jobs and self.done_ticks > 16:  # demo: hold "complete" ~12 s, then run again
                self.start_job(self.job, self.total)
            return
        self._huddle_step()
        for a in self.agents:
            if a.state == 'working':
                a.prog += a.speed
                if a.window and self.rng.random() < PROBLEM_CHANCE:
                    self._raise(a)
                elif a.prog >= 1:
                    self._finish_task(a)
                elif self.rng.random() < HUDDLE_CHANCE:
                    self._report(a, HUDDLE_KINDS[(a.n + self.pid) % len(HUDDLE_KINDS)])
            # a finished agent goes back to work if new tasks appear (a "check" added by a late
            # extract), or if a window frees up (after a stop) while pages wait on the shelf
            if a.state == 'idle' or (a.state == 'finished' and (self.queue or (self.shelf and self.free))):
                self._take_task(a)
        self.hist.append(self.pages_done)
        self.hist = self.hist[-9:]
        if len(self.hist) > 1:
            self.rate = (self.hist[-1] - self.hist[0]) / ((len(self.hist) - 1) * STEP)
        if self.complete():
            self.updates.add('job', f"Job '{self.job}' finished · {self.pages_done} pages · results: "
                                    f'jobs/{slug(self.job)}.csv (demo: no file written)')

    def fast_forward(self, pages, problems=0, huddles=0):
        """Run silently until `pages` are done, then raise `problems` for you and `huddles` for the
        agents (demo start-up, so the room opens mid-job with problems, like the approved mockup)."""
        global PROBLEM_CHANCE, HUDDLE_CHANCE
        if self.pages_done >= min(pages, self.total):
            return
        saved, PROBLEM_CHANCE, HUDDLE_CHANCE = (PROBLEM_CHANCE, HUDDLE_CHANCE), 0, 0
        try:
            while self.pages_done < min(pages, self.total) and not self.complete():
                self.step()
        finally:
            PROBLEM_CHANCE, HUDDLE_CHANCE = saved
        busy = [a for a in self.agents if a.state == 'working' and a.window]
        for a in busy[2::7][:problems]:
            self._raise(a)
        for a in [a for a in self.agents if a.state == 'working'][5:5 + huddles]:
            self._report(a, HUDDLE_KINDS[0])

    # ---- internals ----
    def _agent(self, n):
        return self.agents[n - 1] if 1 <= n <= N else None

    def _raise(self, a, reason=None):
        a.state = 'needs_you'
        a.reason = reason or REASONS[(a.n + self.raised) % len(REASONS)]
        self.raised += 1
        self.updates.add('problem', f'#{a.n} needs you: {a.reason}', a.n)

    # ---- the huddle ----
    def _report(self, a, kind):
        """A problem the agents can fix goes on the board; the agent who found it works on."""
        self.pid += 1
        p = {'id': f'P-{self.pid}', 'kind': kind, 'site': a.task['site'], 'by': a.n, 'state': 'waiting', 'rounds': []}
        self.problems[p['id']] = p
        done = [k for k, q in self.problems.items() if q['state'] in ('fixed', 'answered')]
        for k in done[:max(0, len(self.problems) - 50)]:
            del self.problems[k]
        self.board.append(p)
        self.updates.add('huddle', f"{p['id']} raised by #{a.n}: {kind} on {p['site']}", a.n)

    def _huddle_step(self):
        h = self.huddle
        if h is None:
            if self.board:
                p = self.board.popleft()
                p['state'] = 'huddle'
                self.huddle = {'p': p, 'round': 0, 'members': []}
                self._next_round()
            return
        h['ticks'] -= 1
        pages_a_tick = -(-TEST_PAGES // ROUND_TICKS[h['round'] - 1])
        for m in h['members']:  # each member tries its fix on the saved test pages
            m.fix_tried = min(TEST_PAGES, m.fix_tried + pages_a_tick)
            m.fix_ok = min(h['scores'].get(m.n, 0), m.fix_tried)
        if h['ticks'] <= 0:
            self._end_round()

    def _next_round(self):
        h = self.huddle
        h['round'] += 1
        r, size = h['round'], HUDDLE_SIZES[h['round'] - 1]
        # agents with nothing left to do join first, then agents without a window, so windows keep working
        joiners = [a for a in self.agents if a.state == 'finished'] + \
            sorted((a for a in self.agents if a.state == 'working'), key=lambda a: a.window)
        for a in joiners[:len(joiners) if size is None else max(0, size - len(h['members']))]:
            self._join(a)
        h['ticks'] = ROUND_TICKS[r - 1]
        h['scores'] = {m.n: self.rng.randint(0, TEST_PAGES - 1) for m in h['members']}
        if h['members'] and self.rng.random() < FIX_CHANCE[r - 1]:
            h['scores'][self.rng.choice(h['members']).n] = TEST_PAGES
        for m in h['members']:
            m.fix_ok = m.fix_tried = 0
        n = len(h['members'])
        self.updates.add('huddle', f"{h['p']['id']} round {r}: " +
                         (f'everyone huddles ({n} agents)' if size is None else f'{n} agents huddle'))

    def _join(self, a):
        if a.task:
            self.queue.appendleft(a.task)  # nothing lost: its task waits at the front of the queue
            a.task, a.prog = None, 0.0
        if a.window:
            self._release(a)
        a.state, a.huddle = 'huddle', self.huddle['p']['id']
        self.huddle['members'].append(a)

    def _end_round(self):
        h = self.huddle
        p, r, scores = h['p'], h['round'], h['scores']
        best = max(scores.values(), default=0)
        tied = [n for n, s in scores.items() if s == best]
        winner = self.rng.choice(tied) if tied else None  # a vote breaks a tie
        p['rounds'].append({'round': r, 'agents': len(h['members']), 'winner': winner, 'best': best,
                            'fixes': [{'agent': n, 'pages_ok': s} for n, s in scores.items()]})
        if best == TEST_PAGES:
            p['state'] = 'fixed'
            self.fixed += 1
            self.updates.add('huddle', f"{p['id']} fixed by the huddle in round {r}: #{winner}'s fix read "
                                       f'{best}/{TEST_PAGES} pages', winner)
            self._disband()
        elif r < len(HUDDLE_SIZES):
            self._next_round()
        else:
            self._disband()
            self._send_to_you(p)

    def _disband(self):
        for m in self.huddle['members']:
            m.state, m.huddle = 'idle', None  # back to work in this same step
        self.huddle = None

    def _send_to_you(self, p):
        """Round 3 didn't fix it: an agent waits for you, and that site's pages are set aside."""
        p['state'] = 'yours'
        site, kept = p['site'], self.parked.setdefault(p['site'], [])
        for line in (self.queue, self.shelf):
            kept += [t for t in line if t['site'] == site]
            rest = [t for t in line if t['site'] != site]
            line.clear()
            line.extend(rest)
        a = self._agent(p['by'])
        if a.state != 'idle':
            a = next((x for x in self.agents if x.state == 'idle'), None)
        if a is None:  # nobody free to wait for you: carry on with the site
            self.queue.extendleft(reversed(self.parked.pop(site)))
            return
        a.board_pid = p['id']
        self._raise(a, f"couldn't fix {p['id']} with the huddle: {p['kind']}")
        self.updates.add('huddle', f"{p['id']} sent to you: the huddle couldn't fix it · {len(kept)} pages on "
                                   f'{site} set aside', a.n)

    def _take_task(self, a):
        """The no-wait rule: a page from the shelf if a window is at hand, else the next queue task.
        A browser page that finds every window busy goes on the shelf and the agent takes the next."""
        if self.shelf and (a.window or self.free):
            t = self.shelf.popleft()
            if a.window:  # a hand-off: its window goes straight to the next page waiting
                self.handoffs += 1
                a.passes += 1
                self.last_hand = f"#{a.n} > page-{t['page']}"
                self.updates.add('handoff', f"#{a.n} kept its window for the next page: {t['site']}/page-{t['page']}", a.n)
            else:
                self._grab(a)
            return self._start(a, t)
        if a.window:
            self._release(a)  # no pages waiting: the window goes back to the pool
        while self.queue:
            t = self.queue.popleft()
            if t['site'] in self.parked:  # its site waits on you
                self.parked[t['site']].append(t)
                continue
            if not t['browser']:
                return self._start(a, t)
            if self.free:
                self._grab(a)
                return self._start(a, t)
            self.shelf.append(t)  # every window busy: the page waits, the agent doesn't
        if a.state != 'finished':
            a.state = 'finished'
            self.updates.add('finished', f'#{a.n} finished · no work left · {a.pages} pages done', a.n)

    def _start(self, a, t):
        a.task, a.prog, a.state = t, 0.0, 'working'

    def _grab(self, a):
        self.free -= 1
        a.window = a.used_window = True

    def _release(self, a):
        a.window = False
        self.free += 1

    def _finish_task(self, a, skipped=False):
        t = a.task
        if t['kind'] == 'extract':
            self.pages_done += 1
            if not skipped:
                a.pages += 1
            if self.rng.random() < BLOCKED_CHANCE:
                self.blocked += 1
                self.updates.add('blocked', f"#{a.n} blocked by a bot blocker: {t['site']}/page-{t['page']}", a.n)
            elif not skipped and self.rng.random() < CHECK_CHANCE:
                self.queue.append({'kind': 'check', 'page': t['page'], 'site': t['site'], 'browser': False})
        a.steps.append(f"{t['kind']} {t['site']}/page-{t['page']}: {LOG[(a.n + a.pages) % len(LOG)]}")
        a.task = None
        a.prog = 0.0
        a.state = 'idle'  # it keeps any window: _take_task passes it to a waiting page or returns it


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'job'
