"""Job requests from the Cloudflare inbox (cloud/inbox/worker.js), collected about once a minute while
Errand runs. A request names a saved skill and its links: {"skill": "...", "urls": [...], "values": {...}}.
It runs when no other job is running; until then it stays in the inbox, so nothing is lost while the
laptop is off or busy. Set up with `python -m errand inbox`."""
import json, pathlib, secrets, threading, urllib.error, urllib.request

CONFIG = pathlib.Path.home() / '.errand' / 'inbox.json'


def http(method, url, secret, body=None):
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={'Authorization': f'Bearer {secret}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def setup_text():
    """`errand inbox`: make the secret once, and say how to put the Worker online (your free account)."""
    cfg = json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}
    if not cfg.get('secret'):
        cfg = {'url': '', 'secret': secrets.token_urlsafe(32)}
        CONFIG.parent.mkdir(exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, indent=1), encoding='utf-8')
    folder = pathlib.Path(__file__).resolve().parent.parent / 'cloud' / 'inbox'
    return '\n'.join([
        'The webhook inbox runs on your own free Cloudflare account. In PowerShell, in this folder:', f'   cd "{folder}"',
        '   npx wrangler login', '   npx wrangler d1 create errand-inbox      (paste its id into wrangler.toml)',
        '   npx wrangler d1 execute errand-inbox --remote --file schema.sql',
        '   npx wrangler secret put SECRET           (paste the secret below)', '   npx wrangler deploy',
        f'Your secret (keep it private; it is also in {CONFIG}):', f'   {cfg["secret"]}',
        f'Then put the address wrangler prints into "url" in {CONFIG} and restart Errand.',
        'Services post to <address>/hook/<any-name> with the header X-Errand-Secret and a body like',
        '   {"skill": "laptop price", "urls": ["https://..."], "values": {"size": "256"}}'])


class Inbox:
    def __init__(self, engine, config=None, call=http):
        self.engine, self.call = engine, call
        path = pathlib.Path(config or CONFIG)
        cfg = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        self.url, self.secret = cfg.get('url', '').rstrip('/'), cfg.get('secret', '')
        self.stop = threading.Event()

    def tick(self):
        """Run at most one waiting request. Returns the name of the skill started, or None."""
        if not (self.url and self.secret) or self.engine.job and not self.engine.complete():
            return None
        for ev in self.call('GET', f'{self.url}/events', self.secret) or []:
            try:
                body = json.loads(ev['body'])
                self.engine.run_skill(str(body.get('skill') or ''), body.get('urls') or [], body.get('values') or {})
                started = body['skill']
                self.engine.updates.add('job', f"Inbox: '{ev['name']}' started the skill '{started}'")
            except (ValueError, KeyError, TypeError) as e:  # a bad request is dropped, with a note, never retried forever
                started = None
                self.engine.updates.add('problem', f"Inbox: dropped '{ev.get('name')}': {e}")
            self.call('POST', f'{self.url}/events/ack', self.secret, {'ids': [ev['id']]})
            if started:
                return started
        return None

    def start(self):
        if self.url and self.secret:
            def loop():
                while not self.stop.wait(60):
                    try:
                        self.tick()
                    except Exception as e:  # the inbox never stops Errand
                        self.engine.updates.add('problem', f'Inbox error: {type(e).__name__}')
            threading.Thread(target=loop, daemon=True, name='inbox').start()
        return self
