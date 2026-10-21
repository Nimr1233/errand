"""For You (reports/Full feature free Errand plan.md): suggestions made only from your own history on
this laptop: past jobs, skills and schedules. Plain rules rank them, so it costs nothing, explains
itself, and your history never leaves the laptop.
- a skill you ran by hand 3 times or more, with no schedule: schedule it
- a job you run again and again that hasn't run for a week: run it again
- a job you ran twice or more that isn't a skill yet: save it
- a job where many pages were blocked: Errand won't get past those checks, so cut those links
"""
import datetime as dt


def suggestions(store, now=None, limit=5):
    now = now or dt.datetime.now()
    jobs, skills = store.jobs(200), {k['name']: k for k in store.skills()}
    scheduled = {s['skill'] for s in store.schedules()}
    runs = {}
    for j in jobs:
        runs.setdefault(j['name'], []).append(j)
    out = []
    for name, js in runs.items():
        last = dt.datetime.fromisoformat(js[0]['started'])
        if name in skills and name not in scheduled and len(js) >= 3:
            out.append((3 + len(js), f"You ran '{name}' {len(js)} times by hand. Schedule it?",
                        {'tool': 'schedule_skill', 'skill': name}))
        if len(js) >= 2 and (now - last).days >= 7 and name not in scheduled:
            out.append((2 + len(js), f"'{name}' last ran {(now - last).days} days ago. Run it again?",
                        {'tool': 'run_skill' if name in skills else 'start_job', 'skill': name}))
        if name not in skills and len(js) >= 2:
            out.append((1 + len(js), f"You ran '{name}' {len(js)} times. Save it as a skill to rerun it in one step?",
                        {'tool': 'save_skill', 'job': name}))
        j = next((x for x in js if x['finished']), None)  # the newest run that got to the end
        if j and j['total'] and (j['blocked'] or 0) >= max(3, j['total'] // 5):
            out.append((2, f"{j['blocked']} of {j['total']} pages in '{name}' were blocked by the sites. Errand never gets past "
                           'those checks: leave those links out next time.', {'tool': 'past_jobs'}))
    return [{'text': t, 'action': a} for _, t, a in sorted(out, key=lambda o: -o[0])[:limit]]
