"""The chief's memory (errand/memory.py): a finished job leaves facts in gbrain. A stand-in gbrain
records what it is asked to remember; your real gbrain is never touched."""
import sys
import time

from errand import memory

FAKE = '''import json, sys
open(sys.argv[1], "a", encoding="utf-8").write(json.dumps(sys.argv[2:]) + "\\n")
'''


def stand_in(tmp_path, monkeypatch):
    script, log = tmp_path / 'gbrain.py', tmp_path / 'calls.txt'
    script.write_text(FAKE, encoding='utf-8')
    monkeypatch.setattr(memory, 'CMD', [sys.executable, str(script), str(log)])
    return log


def test_a_finished_job_leaves_its_facts(tmp_path, monkeypatch):
    log = stand_in(tmp_path, monkeypatch)
    rows = {'https://a.com/p/1': {'status': 'ok', 'title': 'Secret page text never stored'},
            'https://b.com/x': {'status': 'blocked: bot check'}, 'https://b.com/y': {'status': 'blocked: bot check'}}
    facts = memory.save_job('Shop', '2026-10-21 14:00', 3, ['title'], 0, 1, 'jobs/shop.csv', rows)
    assert facts[0] == ("Errand job 'Shop' finished 2026-10-21 14:00: 3 pages from a.com, b.com; fields title; "
                        '0 read by code, 1 brain calls; results in jobs/shop.csv', 'errand')
    assert facts[1] == ('b.com stopped Errand on 2026-10-21 14:00: 2 pages blocked: bot check', 'b.com')
    for _ in range(100):  # written in the background
        if log.exists() and len(log.read_text(encoding='utf-8').splitlines()) == 2:
            break
        time.sleep(0.1)
    calls = log.read_text(encoding='utf-8')
    assert calls.count('"remember"') == 2 and '"--entity", "b.com"' in calls and '"--provenance"' in calls
    assert 'Secret page text' not in calls  # facts about the job, never page text


def test_no_gbrain_means_no_memory_and_no_error(monkeypatch):
    monkeypatch.setattr(memory, 'CMD', [])
    assert memory.remember('anything') is False
    monkeypatch.setattr(memory, 'CMD', ['C:/no/such/gbrain.exe'])
    assert memory.remember('anything') is False  # a broken gbrain never breaks a job
