"""Schedules (reports/Full feature free Errand plan.md: schedules run on the laptop, $0): a saved skill
runs on its links every N hours, or daily at a set time, while Errand is running.
- A run missed while the laptop was off happens once when Errand starts again, not once per miss.
- A schedule that comes due while another job runs waits until that job is done.
- Starting Errand with Windows is a Windows setting: `python -m errand autostart` prints the one
  command for you to run (and the one that undoes it). Errand changes no Windows setting itself.
"""
import datetime as dt, re, sys, threading

EVERY = re.compile(r'^\s*(?:every\s+(\d+)\s+hours?|hourly|daily(?:\s+at)?\s+(\d{1,2}):(\d{2}))\s*$', re.I)


def parse(every):
    """'every 6 hours' / 'hourly' / 'daily 09:00' -> a function: last run time -> next run time."""
    m = EVERY.match(every or '')
    if not m:
        raise ValueError('say "every 6 hours", "hourly" or "daily 09:00"')
    if m.group(2):
        h, mi = int(m.group(2)), int(m.group(3))
        if h > 23 or mi > 59:
            raise ValueError('a daily time looks like 09:00')

        def daily(t):
            n = t.replace(hour=h, minute=mi, second=0, microsecond=0)
            return n if n > t else n + dt.timedelta(days=1)
        return daily
    hours = int(m.group(1) or 1)
    if not 1 <= hours <= 24 * 7:
        raise ValueError('every 1 to 168 hours')
    return lambda t: t + dt.timedelta(hours=hours)


class Scheduler:
    """Checks every 30 s; runs what is due through engine.run_skill when no job is running."""

    def __init__(self, engine, store, now=dt.datetime.now):
        self.engine, self.store, self.now = engine, store, now
        self.stop = threading.Event()

    def add(self, skill, urls, every, values=None):
        if self.store.skill(skill) is None:
            raise ValueError(f"there's no skill called '{skill}'")
        urls = [u for u in urls or [] if isinstance(u, str) and u.strip()]
        if not urls:
            raise ValueError('give the links the skill runs on')
        nxt = parse(every)(self.now())
        return self.store.add_schedule(skill, urls, every, values or {}, nxt.isoformat(timespec='minutes'))

    def tick(self):
        """Run at most one due schedule. Missed runs collapse into one: the next time counts from now."""
        if self.engine.job and not self.engine.complete():
            return None  # a job is running: due schedules wait for it
        t = self.now()
        for s in self.store.schedules():
            if dt.datetime.fromisoformat(s['next_run']) <= t:
                self.store.mark_run(s['id'], t.isoformat(timespec='minutes'), parse(s['every'])(t).isoformat(timespec='minutes'))
                try:
                    self.engine.run_skill(s['skill'], s['urls'], s['values'])
                    self.engine.updates.add('job', f"Schedule #{s['id']} ran '{s['skill']}' ({s['every']})")
                except ValueError as e:
                    self.engine.updates.add('problem', f"Schedule #{s['id']} couldn't run '{s['skill']}': {e}")
                return s['id']
        return None

    def start(self):
        def loop():
            while not self.stop.wait(30):
                try:
                    self.tick()
                except Exception as e:  # a bad schedule never stops Errand
                    self.engine.updates.add('problem', f'The scheduler hit an error: {type(e).__name__}')
        threading.Thread(target=loop, daemon=True, name='scheduler').start()
        return self


def autostart_commands():
    """The Windows commands that start Errand when you log on, and stop doing so. You run them yourself."""
    py = sys.executable
    return ('To start Errand whenever you log on to Windows, run this once in PowerShell:\n\n'
            f'   schtasks /Create /SC ONLOGON /TN Errand /RL LIMITED /TR \'"{py}" -m errand start\'\n\n'
            'To undo it:\n\n   schtasks /Delete /TN Errand /F\n\n'
            'Schedules run only while Errand is running and the laptop is awake; a run missed while it was off '
            'happens once when Errand starts again.')

