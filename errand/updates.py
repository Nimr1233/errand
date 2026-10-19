"""Agent updates (room spec section 5.3): numbered, readable lines for the updates column and
the get_updates tool. The last 500 stay in memory; every update is appended to the job log."""
import json
import time
from collections import deque

KEEP = 500


class UpdateLog:
    def __init__(self, path=None, keep=KEEP):
        self.items = deque(maxlen=keep)
        self.n = 0
        self.path = path

    def add(self, kind, text, agent=None):
        self.n += 1
        u = {'n': self.n, 'time': time.strftime('%H:%M:%S'), 'kind': kind, 'agent': agent, 'text': text}
        self.items.append(u)
        if self.path:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(u) + '\n')
        return u

    def since(self, n=None, limit=50):
        """Updates after number n, or the newest `limit` when n is None."""
        if n is None:
            return list(self.items)[-limit:]
        return [u for u in self.items if u['n'] > n]
