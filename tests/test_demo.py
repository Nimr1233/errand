from errand import demo


def check(eng):
    in_use = sum(a.window for a in eng.agents)
    assert in_use <= demo.WINDOWS and in_use == demo.WINDOWS - eng.free
    assert eng.free == 0 or not eng.line, 'a window sat free while an agent waited'
    assert all(a.state == 'waiting' for a in eng.line)
    if eng.queue:
        assert not any(a.state == 'finished' for a in eng.agents), 'finished while work was left'


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
    assert s['finished'] == 53 and s['waiting'] == 0 and s['windows_in_use'] == 0
    assert s['handoffs'] > 0
    assert s['handoffs'] == sum(u['kind'] == 'handoff' for u in eng.updates.since(0))


def test_no_handoffs_when_nobody_waits():
    eng = demo.DemoEngine(seed=2, loop_jobs=False)
    eng.start_job('small', 20)  # fewer pages than windows: nobody ever waits in line
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
    check(eng)
