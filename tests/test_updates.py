from errand.updates import UpdateLog


def lines(path):
    return path.read_text(encoding='utf-8').splitlines()


def test_numbering_and_since(tmp_path):
    log = UpdateLog(tmp_path / 'job.log')
    for i in range(5):
        log.add('job', f'u{i}', agent=i)
    assert [u['n'] for u in log.since()] == [1, 2, 3, 4, 5]
    assert [u['text'] for u in log.since(3)] == ['u3', 'u4']
    assert log.since(5) == []
    assert len(lines(tmp_path / 'job.log')) == 5


def test_keeps_the_last_500_but_logs_every_one(tmp_path):
    log = UpdateLog(tmp_path / 'job.log')
    for i in range(600):
        log.add('job', str(i))
    assert len(log.since(0)) == 500 and log.since(0)[0]['n'] == 101
    newest = log.since()
    assert len(newest) == 50 and newest[-1]['n'] == 600
    assert len(lines(tmp_path / 'job.log')) == 600
