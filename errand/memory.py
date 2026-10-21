"""Errand's notes in gbrain (github.com/garrytan/gbrain, installed with Bun, keyless). After each job
Errand saves one short fact about it, plus one per site that blocked it, so the chief (Claude in the
room, which has gbrain's memory tools) remembers past jobs, which sites block, and where the results
are. Only facts about the job: never text from a page. Nothing happens when gbrain isn't installed."""
import os, pathlib, shutil, subprocess, threading

EXE = os.environ.get('ERRAND_GBRAIN') or shutil.which('gbrain') or str(pathlib.Path.home() / '.bun/bin/gbrain.exe')
CMD = [EXE] if pathlib.Path(EXE).exists() else []  # a list, so tests can put a stand-in here
PROVENANCE = 'Errand job loop (errand/engine.py), written when a job finished'


def remember(fact, entity='errand'):
    """Save one fact; True if gbrain took it. Never raises: memory must not break a job."""
    if not CMD:
        return False
    try:
        r = subprocess.run([*CMD, 'remember', fact[:1000], '--entity', entity, '--provenance', PROVENANCE],
                           cwd=pathlib.Path.home(), capture_output=True, timeout=120,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return r.returncode == 0
    except Exception:
        return False


def job_facts(job, when, done, fields, by_code, brain_calls, out, rows):
    """The facts one finished job leaves behind: what was read and where, and which sites blocked."""
    from .fetch import site
    sites = sorted({site(u) for u in rows})
    facts = [(f"Errand job '{job}' finished {when}: {done} pages from {', '.join(sites[:5])}"
              f"{' and more' if len(sites) > 5 else ''}; fields {', '.join(fields)}; {by_code} read by code, "
              f'{brain_calls} brain calls; results in {out}', 'errand')]
    blocked = {}
    for u, row in rows.items():
        if row and row['status'] != 'ok':
            blocked.setdefault(site(u), {}).setdefault(row['status'], 0)
            blocked[site(u)][row['status']] += 1
    for s, why in sorted(blocked.items()):
        facts.append((f'{s} stopped Errand on {when}: ' + ', '.join(f'{n} pages {w}' for w, n in why.items()), s))
    return facts


def save_job(*args):
    """Write a finished job's facts in the background, so no agent waits on gbrain."""
    facts = job_facts(*args)
    threading.Thread(target=lambda: [remember(f, e) for f, e in facts], daemon=True, name='gbrain').start()
    return facts
