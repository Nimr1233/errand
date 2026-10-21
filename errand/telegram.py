"""Telegram, free (WhatsApp replies cost money since October 2026): alerts on your phone and a small chat.
- Setup, once: make a bot with @BotFather in Telegram and paste its token into ~/.errand/telegram_token.
  Run `python -m errand telegram` for a pairing code and send it to your bot as "/pair 123456". Only
  that chat is ever answered or told anything.
- Alerts: an agent needs you, a job finished.
- Chat: /status, /problems, /approve N, /skip N, /pause, /resume.
- Only job status ever goes out, never text from a page.
- Telegram allows about one message a second per chat: messages wait their turn.
"""
import json, pathlib, random, threading, time, urllib.error, urllib.request

HOME = pathlib.Path.home() / '.errand'
TOKEN_FILE, CHAT_FILE, PAIR_FILE = HOME / 'telegram_token', HOME / 'telegram_chat', HOME / 'telegram_pair'
API = 'https://api.telegram.org/bot{token}/{method}'
ALERT = ('problem', 'job', 'huddle', 'cleared')  # update kinds worth a message
HELP = ('Errand here. /status · /problems · /approve N · /skip N · /pause · /resume')


def post(url, body, timeout=40):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'ok': False, 'error_code': e.code}
    except OSError:
        return {'ok': False}


def pairing_code():
    """`errand telegram`: a 6-digit code, good for 10 minutes."""
    code = f'{random.SystemRandom().randrange(10**6):06d}'
    HOME.mkdir(exist_ok=True)
    PAIR_FILE.write_text(json.dumps({'code': code, 'until': time.time() + 600}), encoding='utf-8')
    if not TOKEN_FILE.exists():
        return (f'No bot yet. In Telegram, message @BotFather, send /newbot, then paste the token it gives you into '
                f'{TOKEN_FILE}. Then run this again.')
    return f'Send this to your Errand bot in Telegram within 10 minutes:  /pair {code}'


class Telegram:
    def __init__(self, engine, token=None, send=post, chat_file=None, pair_file=None, gap=1.1):
        self.engine, self.send, self.gap = engine, send, gap
        self.token = token if token is not None else (TOKEN_FILE.read_text(encoding='utf-8').strip() if TOKEN_FILE.exists() else '')
        self.chat_file, self.pair_file = chat_file or CHAT_FILE, pair_file or PAIR_FILE
        self.chat = int(self.chat_file.read_text()) if self.chat_file.exists() else None
        self.offset, self.seen, self.last_send = 0, engine.updates.n, 0.0
        self.stop = threading.Event()

    def call(self, method, **body):
        return self.send(API.format(token=self.token, method=method), body)

    def say(self, text):
        if self.chat is None:
            return
        time.sleep(max(0.0, self.gap - (time.monotonic() - self.last_send)))  # about one message a second
        self.last_send = time.monotonic()
        self.call('sendMessage', chat_id=self.chat, text=text[:4000])

    def start(self):
        if self.token:
            threading.Thread(target=self.run, daemon=True, name='telegram').start()
        return self

    def run(self):
        while not self.stop.is_set():
            self.poll(timeout=25)
            self.alerts()

    def poll(self, timeout=0):
        r = self.call('getUpdates', offset=self.offset, timeout=timeout)
        for u in r.get('result', []) if r.get('ok') else []:
            self.offset = u['update_id'] + 1
            m = u.get('message') or {}
            if m.get('text'):
                self.handle(m['chat']['id'], m['text'].strip())
        if not r.get('ok'):
            self.stop.wait(5)  # Telegram unreachable: try again soon, never crash Errand

    def handle(self, chat, text):
        word, _, arg = text.partition(' ')
        if word == '/pair':
            return self.pair(chat, arg.strip())
        if chat != self.chat:
            return  # strangers get no answer at all
        e = self.engine
        if word == '/status':
            s = e.status()
            self.say(f"{s['job']}: {s['pages_done']}/{s['total']} pages · {s['problems']} waiting on you · "
                     f"{s['blocked']} blocked{' · paused' if s['paused'] else ''}{' · complete' if s['complete'] else ''}")
        elif word == '/problems':
            mine = [a for a in e.agents_view('needs_you')]
            self.say('\n'.join(f"#{a['n']}: {a['reason']}  (/approve {a['n']} or /skip {a['n']})" for a in mine)
                     or 'Nothing waits on you.')
        elif word in ('/approve', '/skip') and arg.strip().isdigit():
            r = e.answer_problem(int(arg), word == '/approve')
            self.say('Done.' if r.get('ok') else f"Couldn't: {r.get('error')}")
        elif word in ('/pause', '/resume'):
            (e.pause_all if word == '/pause' else e.resume_all)()
            self.say('All agents paused.' if word == '/pause' else 'All agents resumed.')
        else:
            self.say(HELP)

    def pair(self, chat, code):
        try:
            want = json.loads(self.pair_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        if code and code == want.get('code') and time.time() < want.get('until', 0):
            self.chat = chat
            self.chat_file.write_text(str(chat), encoding='utf-8')
            self.pair_file.unlink(missing_ok=True)  # one use
            self.say('Paired. You will hear from Errand here. ' + HELP)

    def alerts(self):
        for u in self.engine.updates.since(self.seen):
            self.seen = u['n']
            if u['kind'] in ALERT and (u['kind'] != 'job' or 'finished' in u['text']):
                self.say(u['text'])
