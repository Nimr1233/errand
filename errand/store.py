"""Errand's saved data (main spec section 13: SQLite errand.db and a raw page cache). Kept between
runs so that:
- past jobs and their results can be listed and opened again
- a recipe learned for a kind of page is reused by later jobs, after a check on a few pages
- public pages are kept on disk (one file per link), for re-reading without fetching again
Everything stays on this laptop. Pages from private jobs are not cached."""
import hashlib, json, pathlib, sqlite3, threading, time

HOME = pathlib.Path.home() / '.errand'
DB = HOME / 'errand.db'
CACHE = HOME / 'cache'

SCHEMA = '''
create table if not exists jobs (id integer primary key, name text, started text, finished text, total int,
    done int, blocked int, by_code int, brain_calls int, gemini_calls int, results text, fields text, private int);
create table if not exists results (job int, url text, status text, data text);
create table if not exists recipes (kind text, field text, field_kind text, reader text, selector text,
    learned text, job int, primary key (kind, field, field_kind));
'''


class Store:
    def __init__(self, path=None, cache=None):
        self.path, self.cache = pathlib.Path(path or DB), pathlib.Path(cache or CACHE)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    def start_job(self, name, total, fields, private):
        with self.lock, self.db:
            return self.db.execute('insert into jobs (name, started, total, fields, private) values (?, ?, ?, ?, ?)',
                                   (name, now(), total, json.dumps(fields), int(private))).lastrowid

    def finish_job(self, job, rows, **stats):
        with self.lock, self.db:
            self.db.execute('update jobs set finished=?, done=?, blocked=?, by_code=?, brain_calls=?, gemini_calls=?, '
                            'results=? where id=?', (now(), stats['done'], stats['blocked'], stats['by_code'],
                                                     stats['brain_calls'], stats['gemini_calls'], str(stats['results']), job))
            self.db.executemany('insert into results values (?, ?, ?, ?)',
                                [(job, u, r['status'], json.dumps({k: v for k, v in r.items() if k != 'status'},
                                                                  ensure_ascii=False)) for u, r in rows.items() if r])

    def jobs(self, limit=20):
        with self.lock:
            cur = self.db.execute('select id, name, started, finished, total, done, blocked, by_code, brain_calls, '
                                  'gemini_calls, results from jobs order by id desc limit ?', (limit,))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def recipes(self, kind, fields):
        """The saved recipe for this kind of page, for the fields asked for now (same name and kind)."""
        with self.lock:
            got = {f: (r, s) for f, fk, r, s in self.db.execute(
                'select field, field_kind, reader, selector from recipes where kind=?', (kind,))
                if f in fields and fields[f][1] == fk}
        return got

    def save_recipe(self, kind, recipe, fields, job):
        with self.lock, self.db:
            self.db.executemany('insert or replace into recipes values (?, ?, ?, ?, ?, ?, ?)',
                                [(kind, f, fields[f][1], r, s, now(), job) for f, (r, s) in recipe.items()])

    def forget_recipe(self, kind, fields):
        with self.lock, self.db:
            self.db.executemany('delete from recipes where kind=? and field=?', [(kind, f) for f in fields])

    def cache_page(self, url, html):
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            (self.cache / f'{hashlib.sha1(url.encode()).hexdigest()}.html').write_text(html, encoding='utf-8')
        except OSError:
            pass  # a full disk costs the cache, never the job

    def cached(self, url):
        p = self.cache / f'{hashlib.sha1(url.encode()).hexdigest()}.html'
        return p.read_text(encoding='utf-8') if p.exists() else None

    def close(self):
        self.db.close()


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')
