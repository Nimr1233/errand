"""Phone access (main spec section 17; reports/Full feature free Errand plan.md: Tailscale, $0).
- The phone reaches only mission control (8765), over Tailscale: a private network between your own
  devices, so nothing is opened to the internet. The terminal bridge (8766, the room's Claude Code)
  never listens off this laptop.
- A second lock: a PIN (`python -m errand phone`), kept only as a salted hash. 5 wrong tries lock
  the PIN out for 10 minutes. A right one gives the phone a session cookie for 30 days.
- The phone gets the list view (/list): the job, what needs you, problems, updates. The 3D room
  stays on the laptop.
"""
import hashlib, hmac, json, pathlib, random, secrets, shutil, subprocess, threading, time

FILE = pathlib.Path.home() / '.errand' / 'phone.json'
TRIES, LOCK, DAYS = 5, 600, 30
COOKIE = 'errand_phone'


def set_pin(path=None):
    """`errand phone`: a new 6-digit PIN. Only its salted hash is kept."""
    pin = f'{random.SystemRandom().randrange(10**6):06d}'
    salt = secrets.token_hex(16)
    path = pathlib.Path(path or FILE)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'salt': salt, 'hash': _hash(pin, salt)}), encoding='utf-8')
    return pin


def _hash(pin, salt):
    return hashlib.pbkdf2_hmac('sha256', pin.encode(), salt.encode(), 200_000).hex()


def tailscale_ip():
    """This laptop's Tailscale address, or None when Tailscale isn't installed or isn't connected."""
    exe = shutil.which('tailscale') or r'C:\Program Files\Tailscale\tailscale.exe'
    try:
        out = subprocess.run([exe, 'ip', '-4'], capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out[0] if out and out[0].startswith('100.') else None


class Lock:
    """The PIN check and the phone sessions it hands out."""

    def __init__(self, path=None, clock=time.time):
        self.path, self.clock = pathlib.Path(path or FILE), clock
        self.lock = threading.Lock()
        self.fails, self.locked_until, self.sessions = 0, 0.0, {}

    def login(self, pin):
        """A session id for the right PIN; None for a wrong one; 'locked' after too many."""
        with self.lock:
            if self.clock() < self.locked_until:
                return 'locked'
            try:
                saved = json.loads(self.path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                return None  # no PIN set: nobody gets in
            if hmac.compare_digest(_hash(str(pin), saved['salt']), saved['hash']):
                self.fails = 0
                sid = secrets.token_urlsafe(32)
                self.sessions[sid] = self.clock() + DAYS * 86400
                return sid
            self.fails += 1
            if self.fails >= TRIES:
                self.fails, self.locked_until = 0, self.clock() + LOCK
            return None

    def ok(self, sid):
        with self.lock:
            return bool(sid) and self.sessions.get(sid, 0) > self.clock()
