import pytest

from errand import demo


def check(eng):
    """The no-wait line, checked after a step. A window may sit free while pages wait only after
    a stop (until an agent is free) or while a huddle holds agents."""
    in_use = sum(a.window for a in eng.agents)
    assert in_use <= demo.WINDOWS and in_use == demo.WINDOWS - eng.free
    assert eng.free == 0 or not eng.shelf or eng.huddle, 'a window sat free while pages waited'
    assert all(t['browser'] for t in eng.shelf)
    assert not any(t['site'] in eng.parked for t in [*eng.queue, *eng.shelf]), 'a set-aside site kept working'
    if eng.queue:  # momentum: every agent works, huddles, waits on you, or was stopped by you
        assert all(a.state in ('working', 'huddle', 'needs_you', 'stopped') for a in eng.agents), \
            [a.state for a in eng.agents]
    members = [a for a in eng.agents if a.state == 'huddle']
    assert len(members) == (len(eng.huddle['members']) if eng.huddle else 0)
    assert all(a.task is None and not a.window for a in members), 'a huddle member kept its work'


def run_job(eng, max_steps=20000):
    for _ in range(max_steps):
        if eng.complete():
            return
        for a in eng.agents:
            if a.state == 'needs_you':
                eng.answer_problem(a.n, approve=True)
        eng.step()
        check(eng)
    raise AssertionError('the job never completed')


def test_job_runs_to_complete():
    eng = demo.DemoEngine(seed=1, loop_jobs=False)
    run_job(eng)
    s = eng.status()
    assert s['pages_done'] == s['total'] == 1000
    assert s['finished'] == 53 and s['shelf'] == 0 and s['windows_in_use'] == 0 and s['set_aside'] == 0
    assert s['handoffs'] > 0  # the shelf was used: windows went straight to waiting pages
    assert s['handoffs'] == sum(u['kind'] == 'handoff' for u in eng.updates.since(0))
    assert s['handoffs'] == sum(a.passes for a in eng.agents)


def test_no_handoffs_when_no_page_waits():
    eng = demo.DemoEngine(seed=2, loop_jobs=False)
    eng.start_job('small', 20)  # fewer pages than windows: no page ever waits on the shelf
    run_job(eng)
    assert eng.status()['handoffs'] == 0


def test_fast_forward_opens_mid_job_with_problems():
    eng = demo.DemoEngine(seed=3, loop_jobs=False)
    eng.fast_forward(612, problems=2)
    s = eng.status()
    assert s['pages_done'] >= 612 and s['problems'] == 2 and s['raised'] == 2
    eng.fast_forward(612, problems=2)  # a second call changes nothing
    assert eng.status()['problems'] == 2


def test_answer_stop_pause():
    eng = demo.DemoEngine(seed=4, loop_jobs=False)
    eng.fast_forward(100, problems=1)
    n = next(a.n for a in eng.agents if a.state == 'needs_you')
    assert eng.answer_problem(n, approve=False) == {'ok': True}
    assert eng.answer_problem(n, approve=True)['ok'] is False
    w = next(a for a in eng.agents if a.state == 'working')
    queued = len(eng.queue)
    assert eng.stop_agent(w.n) == {'ok': True} and w.state == 'stopped'
    assert len(eng.queue) == queued + 1  # its task went back for another agent
    eng.pause_all()
    done = eng.pages_done
    eng.step()
    assert eng.pages_done == done
    eng.resume_all()
    eng.step()
    assert eng.pages_done >= done


@pytest.fixture
def quiet(monkeypatch):
    """No random problems: each huddle test raises its own."""
    monkeypatch.setattr(demo, 'PROBLEM_CHANCE', 0)
    monkeypatch.setattr(demo, 'HUDDLE_CHANCE', 0)
    eng = demo.DemoEngine(seed=6, loop_jobs=False)
    eng.fast_forward(200)
    return eng


def report(eng):
    a = next(a for a in eng.agents if a.state == 'working')
    eng._report(a, 'recipe stopped working')
    return eng.problems[f'P-{eng.pid}']


def run_until(eng, done, steps=60):
    for _ in range(steps):
        eng.step()
        check(eng)
        if done():
            return
    raise AssertionError('it never happened')


def test_the_huddle_grows_3_then_9_then_everyone_then_comes_to_you(quiet, monkeypatch):
    monkeypatch.setattr(demo, 'FIX_CHANCE', (0, 0, 0))  # no round finds a fix
    eng = quiet
    p = report(eng)
    sizes = {}

    def sent():
        if eng.huddle:
            sizes[eng.huddle['round']] = len(eng.huddle['members'])
        return p['state'] == 'yours'
    run_until(eng, sent)
    assert sizes == {1: 3, 2: 9, 3: 53}  # round 3: everyone (nobody was waiting on you)
    assert [r['agents'] for r in p['rounds']] == [3, 9, 53] and all(r['best'] < 5 for r in p['rounds'])
    waiter = next(a for a in eng.agents if a.state == 'needs_you')
    assert waiter.board_pid == p['id'] and p['id'] in waiter.reason
    kept = len(eng.parked[p['site']])
    assert kept > 0  # that site's pages are set aside, the rest carry on
    queued = len(eng.queue)
    assert eng.answer_problem(waiter.n, approve=True) == {'ok': True}
    assert p['site'] not in eng.parked and len(eng.queue) == queued + kept and p['state'] == 'answered'


def test_a_fix_in_round_1_sends_everyone_back_to_work(quiet, monkeypatch):
    monkeypatch.setattr(demo, 'FIX_CHANCE', (1, 1, 1))  # round 1 always finds a fix
    eng = quiet
    p = report(eng)
    run_until(eng, lambda: p['state'] == 'fixed')
    assert len(p['rounds']) == 1 and p['rounds'][0]['best'] == 5 and p['rounds'][0]['winner']
    assert eng.huddle is None and eng.fixed == 1
    assert not any(a.state == 'huddle' for a in eng.agents)


def test_one_huddle_at_a_time(quiet):
    eng = quiet
    first, second = report(eng), report(eng)
    eng.step()
    assert eng.huddle['p'] is first and second['state'] == 'waiting' and list(eng.board) == [second]
    run_until(eng, lambda: eng.huddle is not None and eng.huddle['p'] is second, steps=80)
    assert first['state'] in ('fixed', 'yours')


def test_your_kind_of_problem_never_starts_a_huddle(quiet):
    eng = quiet
    a = next(a for a in eng.agents if a.state == 'working' and a.window)
    eng._raise(a)
    eng.step()
    assert a.reason in demo.REASONS and eng.huddle is None and not eng.board


def test_no_pages_lost_when_every_huddle_fails(monkeypatch):
    monkeypatch.setattr(demo, 'FIX_CHANCE', (0, 0, 0))
    monkeypatch.setattr(demo, 'HUDDLE_CHANCE', 0.002)  # many problems, all sent to you and approved
    eng = demo.DemoEngine(seed=8, loop_jobs=False)
    run_job(eng)
    s = eng.status()
    assert s['pages_done'] == s['total'] and s['set_aside'] == 0
    assert sum(p['state'] == 'answered' for p in eng.problems.values()) > 0


def test_a_stopped_agents_window_goes_to_the_shelf():
    eng = demo.DemoEngine(seed=5, loop_jobs=False)
    eng.fast_forward(150)
    assert eng.shelf and eng.free == 0  # 53 agents, 25 windows: pages are waiting
    w = next(a for a in eng.agents if a.state == 'working' and a.window)
    eng.stop_agent(w.n)
    assert eng.free == 1 and not w.window
    for _ in range(30):  # as soon as an agent is free, it takes the window with a page from the shelf
        eng.step()
        if eng.free == 0:
            break
    assert eng.free == 0
    check(eng)
