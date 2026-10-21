"""Telegram (errand/telegram.py) against a stand-in for Telegram's Bot API: pairing, commands, alerts,
and silence towards anyone who isn't paired."""
import json
import time

from errand import demo, telegram as tg


class FakeTelegram:
    def __init__(self):
        self.inbox, self.sent = [], []

    def __call__(self, url, body):
        method = url.rsplit('/', 1)[1]
        assert url.startswith('https://api.telegram.org/bottest-token/')
        if method == 'getUpdates':
            return {'ok': True, 'result': [u for u in self.inbox if u['update_id'] >= body['offset']]}
        self.sent.append((body['chat_id'], body['text']))
        return {'ok': True}

    def message(self, chat, text):
        self.inbox.append({'update_id': len(self.inbox) + 1, 'message': {'chat': {'id': chat}, 'text': text}})


def bot(tmp_path):
    eng = demo.DemoEngine(seed=7, loop_jobs=False)
    eng.fast_forward(300, problems=2)
    fake = FakeTelegram()
    return eng, fake, tg.Telegram(eng, token='test-token', send=fake, gap=0)


def test_pairing_and_strangers(tmp_path):
    eng, fake, b = bot(tmp_path)
    assert 'No bot yet' in tg.pairing_code()  # no token file: it says how to make a bot
    tg.TOKEN_FILE.write_text('test-token')
    code = tg.pairing_code().split('/pair ')[1]
    fake.message(999, '/status')
    fake.message(999, '/pair 000000' if code != '000000' else '/pair 111111')
    b.poll()
    assert fake.sent == [] and b.chat is None  # a stranger and a wrong code get nothing
    fake.message(42, f'/pair {code}')
    fake.message(999, f'/pair {code}')  # the code works once
    b.poll()
    assert b.chat == 42 and fake.sent[0][0] == 42 and fake.sent[0][1].startswith('Paired.')
    assert len(fake.sent) == 1 and not tg.PAIR_FILE.exists()
    assert tg.Telegram(eng, token='test-token', send=fake).chat == 42  # remembered after a restart


def test_commands_and_alerts(tmp_path):
    eng, fake, b = bot(tmp_path)
    b.chat = 42
    n = next(a.n for a in eng.agents if a.state == 'needs_you')
    for text in ('/status', '/problems', f'/approve {n}', '/pause', '/nonsense'):
        fake.message(42, text)
    b.poll()
    said = [t for _, t in fake.sent]
    assert said[0].startswith('Book prices: 3') and 'waiting on you' in said[0]
    assert f'#{n}:' in said[1] and f'/approve {n}' in said[1]
    assert said[2] == 'Done.' and eng.agents[n - 1].state == 'working'
    assert said[3] == 'All agents paused.' and eng.paused
    assert said[4].startswith('Errand here.')
    fake.sent.clear()
    b.seen = eng.updates.n
    eng.updates.add('problem', '#7 needs you: page asks for a CAPTCHA', 7)
    eng.updates.add('handoff', '#3 kept its window')  # not worth a message
    eng.updates.add('job', "Job 'x' finished · 10 pages")
    b.alerts()
    assert [t for _, t in fake.sent] == ['#7 needs you: page asks for a CAPTCHA', "Job 'x' finished · 10 pages"]


def test_no_token_means_no_bot(tmp_path):
    eng = demo.DemoEngine(seed=1, loop_jobs=False)
    b = tg.Telegram(eng, send=lambda *a: (_ for _ in ()).throw(AssertionError('no call without a token')))
    assert b.start() is b and not b.token
