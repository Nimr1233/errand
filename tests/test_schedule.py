"""Schedules (errand/schedule.py) with a fake clock and a stand-in engine: due runs, missed runs that
collapse into one, and waiting while a job runs."""
import datetime as dt

import pytest

from errand import schedule
from errand.store import Store
from errand.updates import UpdateLog


class Engine:
    def __init__(self):
        self.job, self.done, self.runs, self.updates = None, True, [], UpdateLog()

    def complete(self):
        return self.done

    def run_skill(self, name, urls, values):
        self.runs.append((name, urls, values))


def test_how_often():
    t = dt.datetime(2026, 10, 21, 10, 30)
    assert schedule.parse('every 6 hours')(t) == dt.datetime(2026, 10, 21, 16, 30)
    assert schedule.parse('hourly')(t) == dt.datetime(2026, 10, 21, 11, 30)
    assert schedule.parse('daily 09:00')(t) == dt.datetime(2026, 10, 22, 9, 0)  # 09:00 today has passed
    assert schedule.parse('Daily at 23:15')(t) == dt.datetime(2026, 10, 21, 23, 15)
    for bad in ('every minute', 'daily 25:00', 'every 0 hours', ''):
        with pytest.raises(ValueError):
            schedule.parse(bad)


def test_due_runs_missed_runs_and_a_busy_engine(tmp_path):
    clock = [dt.datetime(2026, 10, 21, 8, 0)]
    store, eng = Store(tmp_path / 'e.db', tmp_path / 'c'), Engine()
    s = schedule.Scheduler(eng, store, now=lambda: clock[0])
    with pytest.raises(ValueError):
        s.add('no such skill', ['https://a.example/1'], 'hourly')
    store.save_skill('prices', '', {'price': 'the price'}, ['click the {size} option'])
    sid = s.add('prices', ['https://a.example/1'], 'every 6 hours', {'size': '256'})
    assert s.tick() is None and not eng.runs  # not due yet
    clock[0] += dt.timedelta(days=3)  # the laptop was off for 3 days: 12 runs missed
    eng.job, eng.done = 'another job', False
    assert s.tick() is None  # a job is running: the schedule waits
    eng.done = True
    assert s.tick() == sid and s.tick() is None  # one catch-up run, not twelve
    assert eng.runs == [('prices', ['https://a.example/1'], {'size': '256'})]
    nxt = store.schedules()[0]
    assert nxt['next_run'] == (clock[0] + dt.timedelta(hours=6)).isoformat(timespec='minutes') and nxt['last_run']
    assert store.remove_schedule(sid) and not store.schedules()
