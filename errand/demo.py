"""Demo engine (spec section 17 "demo mode"): fake agents that follow the real engine's rules,
so mission control and the Errand connector can be built and tested without the brains running.

Rules it follows:
- shared task queue: agents pull the next task, nobody owns a fixed page list (main spec section 13)
- 25-window pool: a browser task waits in line for a window; a returned window goes straight to
  the next agent in line (a hand-off, main spec section 16)
- an agent is "finished" when the queue has nothing left for it and its last task is done
- problems wait for you until answered
"""
import random
import re
from collections import deque

from .updates import UpdateLog

N = 53
WINDOWS = 25
STEP = 0.75  # seconds per tick
SITES = ['books.toscrape.com', 'quotes.toscrape.com', 'webscraper.io', 'scrapethissite.com']
REASONS = ['wants to submit a form', 'stuck for 5 minutes', 'asks you to log in',
           'wants to post a message', 'page asks for a CAPTCHA']
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
        self.state = 'idle'  # idle | working | waiting | needs_you | finished | stopped
        self.task = None
        self.prog = 0.0
        self.pages = 0
        self.window = False
        self.line = 0
        self.gave_to = 0
        self.used_window = False
        self.reason = ''
        self.steps = deque(maxlen=8)

    def view(self):
        t = self.task or {}
        return {'n': self.n, 'state': self.state, 'task': t.get('kind'), 'site': t.get('site'),
                'pages': self.pages, 'line': self.line, 'window': self.window, 'gave_to': self.gave_to,
                'used_window': self.used_window, 'reason': self.reason, 'prog': round(self.prog, 2),
                'log': self.steps[-1] if self.steps else ''}


class DemoEngine:
    def __init__(self, seed=None, log_path=None, loop_jobs=True):
        self.rng = random.Random(seed)
        self.agents = [Agent(i + 1, self.rng) for i in range(N)]
        self.updates = UpdateLog(log_path)
        self.loop_jobs = loop_jobs
        self.start_job('Book prices', 1000)

    # ---- commands (the local API and the Errand connector call these) ----
    def start_job(self, prompt, count):
        self.job = prompt.strip()[:60] or 'Untitled job'
        self.total = max(1, int(count))
        self.queue = deque({'kind': 'extract', 'page': i, 'site': SITES[i % len(SITES)],
                            'browser': self.rng.random() < 0.45} for i in range(self.total))
        self.free = WINDOWS
        self.line = deque()
        self.pages_done = self.handoffs = self.raised = self.blocked = 0
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
        if approve:
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
        if a in self.line:
            self.line.remove(a)
            self._reline()
        if a.task:
            self.queue.appendleft(a.task)  # its unfinished task goes back for another agent
            a.task = None
        if a.window:
            self._return_window(a)
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
                'finished': n_finished, 'handoffs': self.handoffs, 'waiting': len(self.line),
                'problems': sum(a.state == 'needs_you' for a in self.agents), 'raised': self.raised,
                'blocked': self.blocked, 'windows': WINDOWS, 'windows_in_use': WINDOWS - self.free,
                'next_in_line': [a.n for a in self.line][:3], 'last_handoff': self.last_hand,
                'brains': N, 'paused': self.paused, 'complete': self.complete(),
                'results': f'jobs/{slug(self.job)}.csv (demo: no file written)'}

    def agents_view(self, state=None):
        return [a.view() for a in self.agents if state is None or a.state == state]

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
        return all(a.state in ('finished', 'stopped') for a in self.agents)

    # ---- the clock ----
    def step(self):
        if self.paused:
            return
        if self.complete():
            self.done_ticks += 1
            if self.loop_jobs and self.done_ticks > 16:  # demo: hold "complete" ~12 s, then run again
                self.start_job(self.job, self.total)
            return
        for a in self.agents:
            if a.state == 'working':
                a.prog += a.speed
                if a.window and self.rng.random() < PROBLEM_CHANCE:
                    self._raise(a)
                elif a.prog >= 1:
                    self._finish_task(a)
            # a finished agent goes back to work if new tasks appear (a "check" added by a late extract)
            if a.state == 'idle' or (a.state == 'finished' and self.queue):
                self._take_task(a)
        self.hist.append(self.pages_done)
        self.hist = self.hist[-9:]
        if len(self.hist) > 1:
            self.rate = (self.hist[-1] - self.hist[0]) / ((len(self.hist) - 1) * STEP)
        if self.complete():
            self.updates.add('job', f"Job '{self.job}' finished · {self.pages_done} pages · results: "
                                    f'jobs/{slug(self.job)}.csv (demo: no file written)')

    def fast_forward(self, pages, problems=0):
        """Run silently until `pages` are done, then raise `problems` (demo start-up, so the room
        opens mid-job with problems waiting, like the approved mockup)."""
        global PROBLEM_CHANCE
        if self.pages_done >= min(pages, self.total):
            return
        saved, PROBLEM_CHANCE = PROBLEM_CHANCE, 0
        try:
            while self.pages_done < min(pages, self.total) and not self.complete():
                self.step()
        finally:
            PROBLEM_CHANCE = saved
        busy = [a for a in self.agents if a.state == 'working' and a.window]
        for a in busy[2::7][:problems]:
            self._raise(a)

    # ---- internals ----
    def _agent(self, n):
        return self.agents[n - 1] if 1 <= n <= N else None

    def _raise(self, a):
        a.state = 'needs_you'
        a.reason = REASONS[(a.n + self.raised) % len(REASONS)]
        self.raised += 1
        self.updates.add('problem', f'#{a.n} needs you: {a.reason}', a.n)

    def _take_task(self, a):
        if not self.queue:
            a.state = 'finished'
            self.updates.add('finished', f'#{a.n} finished · no work left · {a.pages} pages done', a.n)
            return
        a.task = self.queue.popleft()
        a.prog = 0.0
        if not a.task['browser']:
            a.state = 'working'
        elif self.free:
            self.free -= 1
            a.window = a.used_window = True
            a.state = 'working'
        else:
            a.state = 'waiting'
            self.line.append(a)
            a.line = len(self.line)

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
        if a.window:
            self._return_window(a)
        a.state = 'idle'

    def _return_window(self, a):
        a.window = False
        if self.line:
            w = self.line.popleft()
            w.window = w.used_window = True
            w.state = 'working'
            w.line = 0
            self._reline()
            self.handoffs += 1
            a.gave_to = w.n
            self.last_hand = f'#{a.n} > #{w.n}'
            self.updates.add('handoff', f'#{a.n} → #{w.n} window handed down', a.n)
        else:
            a.gave_to = 0  # its last window closed with no one waiting
            self.free += 1

    def _reline(self):
        for i, w in enumerate(self.line):
            w.line = i + 1


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'job'
