"""Polite fetching (main spec section 14, the plain-download step). The rules:
- only http/https links, never this laptop or a private network address
- robots.txt is read once per site (kept 24 h) and obeyed, including its Crawl-delay
- one request per site at a time, then a 2-3 s pause; requests say honestly who is asking
- a site that answers 429 or 503 is left alone for 60 s, then 120 s, then 240 s, then given up
- a bot check, CAPTCHA or login page stops that page: Errand never solves or logs in. Its status
  says why, in the results.
The stealth-browser and JavaScript-browser steps are not built yet; such pages end as blocked.
"""
import ipaddress, random, socket, threading, time, urllib.parse, urllib.robotparser

UA = 'Errand/0.1 (personal, non-commercial; one request per site every 2-3 s; python scrapling)'
UA_TOKEN = 'Errand'  # the name robots.txt rules are matched against
CHALLENGE_MARKERS = ('just a moment', 'challenge-platform', 'verify you are human',
                     'enable javascript and cookies', 'checking your browser')
DELAY = (2.0, 3.0)
BACKOFF = (60, 120, 240)
ROBOTS_TTL = 24 * 3600


def text(r):
    b = r.body
    return b.decode('utf-8', 'replace') if isinstance(b, (bytes, bytearray)) else b


def challenged(status, html):
    return status in (403, 429, 503) or any(m in html.lower() for m in CHALLENGE_MARKERS)


def login_wall(html):
    return 'type="password"' in html.lower() or "type='password'" in html.lower()


def site(url):
    return urllib.parse.urlsplit(url).netloc.lower()


def refused(url, allow_local=False):
    """Why a link may not be fetched, or None. allow_local is for tests only."""
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname:
        return 'refused: only http and https links'
    if allow_local:
        return None
    host = p.hostname.lower()
    if host == 'localhost' or host.endswith('.localhost'):
        return 'refused: this laptop'
    try:
        addrs = {a[4][0] for a in socket.getaddrinfo(host, p.port or (443 if p.scheme == 'https' else 80))}
    except socket.gaierror:
        return 'error: unknown site'
    for a in addrs:
        ip = ipaddress.ip_address(a.split('%')[0])
        if not ip.is_global:
            return 'refused: a private network address'
    return None


def scrapling_get(url):
    from scrapling.fetchers import Fetcher
    page = Fetcher.get(url, timeout=30, stealthy_headers=False, headers={'User-Agent': UA})
    return page.status, text(page)


class Polite:
    """Fetches pages, one per site at a time. Agents never wait for a site: take(url) says whether
    the site is free right now; if not, the agent does other work and the page waits."""

    def __init__(self, get=scrapling_get, delay=DELAY, backoff=BACKOFF, allow_local=False):
        self.get, self.delay, self.backoff, self.allow_local = get, delay, backoff, allow_local
        self.lock = threading.Lock()
        self.busy = set()  # sites with a request in flight
        self.next_ok = {}  # site -> when its next request may start (time.monotonic)
        self.robots = {}  # site -> (parser, when read)
        self.strikes = {}  # site -> back-offs so far
        self.gone = set()  # sites given up on

    def take(self, url):
        s = site(url)
        with self.lock:
            if s in self.busy or (s not in self.gone and time.monotonic() < self.next_ok.get(s, 0)):
                return False
            self.busy.add(s)
            return True

    def fetch(self, url):
        """Call only after take(url) said yes. Returns {'status': 'ok', 'html': ...}; 'again' when this
        request went to the site's robots.txt (fetch the page later); 'retry' when the site asked to
        slow down; or {'status': <why not>}."""
        s, pause = site(url), random.uniform(*self.delay)
        try:
            if s in self.gone:
                return {'status': 'blocked: the site kept refusing'}
            why = refused(url, self.allow_local)
            if why:
                return {'status': why}
            if not self._robots_known(url):  # reading robots.txt is this site's request: the page comes after the pause
                rules = self._robots(url)
                if rules is None:
                    return {'status': 'error: could not read robots.txt'}
                return {'status': 'again'} if rules.can_fetch(UA_TOKEN, url) else {'status': 'disallowed by robots.txt'}
            rules = self._robots(url)
            pause = max(pause, rules.crawl_delay(UA_TOKEN) or 0)
            if not rules.can_fetch(UA_TOKEN, url):
                return {'status': 'disallowed by robots.txt'}
            code, html = self.get(url)
            if code in (429, 503):
                n = self.strikes[s] = self.strikes.get(s, 0) + 1
                if n > len(self.backoff):
                    self.gone.add(s)
                    return {'status': 'blocked: the site kept refusing'}
                pause = max(pause, self.backoff[n - 1])
                return {'status': 'retry', 'pause': self.backoff[n - 1]}
            if challenged(code, html):
                return {'status': 'blocked: bot check' if code == 200 or any(m in html.lower() for m in CHALLENGE_MARKERS)
                        else f'blocked: HTTP {code}'}
            if code != 200:
                return {'status': f'error: HTTP {code}'}
            if login_wall(html):
                return {'status': 'blocked: login page'}
            return {'status': 'ok', 'html': html}
        except Exception as e:  # a network error ends this page, not the job
            return {'status': f'error: {type(e).__name__}'}
        finally:
            with self.lock:
                self.busy.discard(s)
                self.next_ok[s] = max(self.next_ok.get(s, 0), time.monotonic() + pause)

    def _robots_known(self, url):
        hit = self.robots.get(site(url))
        return bool(hit) and time.time() - hit[1] < ROBOTS_TTL

    def _robots(self, url):
        s = site(url)
        hit = self.robots.get(s)
        if hit and time.time() - hit[1] < ROBOTS_TTL:
            return hit[0]
        p = urllib.parse.urlsplit(url)
        rules = urllib.robotparser.RobotFileParser()
        try:
            code, body = self.get(f'{p.scheme}://{p.netloc}/robots.txt')
        except Exception:  # can't read the rules: this page isn't fetched, the next page tries again
            return None
        if code == 200:
            rules.parse(body.splitlines())
        elif code in (401, 403) or code >= 500:  # rules unreadable: assume everything is off limits
            rules.disallow_all = True
        else:  # no robots.txt: everything allowed
            rules.allow_all = True
        self.robots[s] = (rules, time.time())
        return rules
