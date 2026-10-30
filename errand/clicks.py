"""Safe clicking (the harness tuner's phase 2; council rule: clicks are navigation only). A job can
ask for steps before the fields are read, like "click the 256 GB option".
- Only safe things are ever offered: links within the same site, option and tab buttons, radios,
  checkboxes. Never buy, sign up, log in, send a form, leave the site, or anything disabled.
- The brain writes the name of the thing to click, and code finds the one element with that name
  ("point, don't write": a small brain copies well and counts badly).
- The bigger 4B "senior" (errand/brains.py, on the CPU) makes every brain choice it can; the 2B only when
  the senior can't run. Its answer stands, "nothing fits" included (bench/results.md sections 16-17).
- After a click something on the page must change (its text or address), or the step failed.
- A click that worked is recorded for that kind of page (errand/store.py) and replayed on later pages
  with no brain at all, by the same name; when that name isn't on a page, the brain is asked again
  (never "the same spot": that could press a different option and read the wrong price).
"""
import re

from . import extract as x
from .fetch import site

# shortcut: an English word list; pages in other languages only get their links and buttons offered
BLOCK = re.compile(r'\b(buy|add to (cart|basket|bag|wishlist)|cart|checkout|check out|purchase|order|pay|payment|'
                   r'subscribe|register|sign ?up|sign ?in|log ?in|log ?out|submit|send|post|delete|remove|donate|'
                   r'book now|reserve|apply|download|install|accept|agree|share|report)\b', re.I)

CANDIDATES_JS = r'''() => {
  const path = el => { const parts = [];
    while (el && el.nodeType === 1 && el !== document.body) { let i = 1, s = el;
      while ((s = s.previousElementSibling)) if (s.tagName === el.tagName) i++;
      parts.unshift(el.tagName.toLowerCase() + ':nth-of-type(' + i + ')'); el = el.parentElement; }
    return 'body > ' + parts.join(' > '); };
  const sel = 'a[href], button, [role=button], [role=tab], [role=option], [role=radio], input[type=button], ' +
              'input[type=radio], input[type=checkbox], input[type=submit], summary';
  return [...document.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
    .slice(0, 400).map(e => ({
      tag: e.tagName.toLowerCase(), type: (e.getAttribute('type') || '').toLowerCase(),
      text: (e.innerText || e.value || '').trim().replace(/\s+/g, ' ').slice(0, 80),
      title: e.getAttribute('title') || '', aria: e.getAttribute('aria-label') || '', value: e.getAttribute('value') || '',
      href: e.tagName === 'A' ? e.href : '', role: e.getAttribute('role') || '',
      disabled: !!e.disabled || /\bdisabled\b/.test(typeof e.className === 'string' ? e.className : '') ||
                e.getAttribute('aria-disabled') === 'true',
      form: !!e.closest('form'), cls: (typeof e.className === 'string' ? e.className : '').replace(/\s+/g, ' ').trim().slice(0, 60),
      css: path(e) }));
}'''


def name(c):
    return c['text'] or c['title'] or c['aria'] or c['value']


def safe(c, page_url):
    """(True, '') for a click Errand may make, else (False, why)."""
    if c['disabled']:
        return False, 'disabled'
    m = BLOCK.search(' '.join([c['text'], c['title'], c['aria'], c['value'], c['href'], c['cls']]))
    if m:
        return False, f'not allowed: "{m.group()}"'
    if c['type'] == 'submit' or (c['form'] and c['tag'] in ('button', 'input') and c['type'] not in ('button', 'radio', 'checkbox')):
        return False, 'sends a form'
    if c['tag'] == 'a':
        if not c['href'].startswith(('http://', 'https://')):
            return False, 'not a web link'
        if site(c['href']) != site(page_url):
            return False, 'leaves the site'
    return True, ''


def choose_prompt(step, offered):
    lines = '\n'.join(f'- {n}' for n in dict.fromkeys(name(c) for c in offered))  # names only: a 2B copies whole lines
    return (f'You choose what to click on a web page, to do this: {step}\nThe things you may click, one per line:\n{lines}\n'
            'Output ONE JSON object: {"click": the exact name of the one thing to click, or null if none of them does it}.')


def llama_chooser(url='http://127.0.0.1:8080'):
    """The 2B picks by writing a name. Returns the name it wrote, or None."""
    form = {'type': 'object', 'required': ['click'], 'properties': {'click': {'type': ['string', 'null']}}}

    def choose(step, offered):
        data, _ = x.chat(url, 'You pick one thing to click. Answer with JSON only.', choose_prompt(step, offered), 60,
                         response_format={'type': 'json_schema', 'json_schema': {'schema': form}})
        return (x.last_json(data['choices'][0]['message'].get('content')) or {}).get('click')
    return choose


def senior_chooser(base, senior, ready=None):
    """Pick what to click with the 4B senior whenever it can answer, else the 2B (base). Measured: the 4B
    picks right on 89% of real steps to the 2B's 76%. Asking it only when the 2B's pick matched nothing
    missed the 2B's wrong-but-real picks, and turned the 2B's right "nothing fits" into a click. So no
    answer is handed on: a null or a name that isn't on the page fails the step safely in do_steps.
    A choice is made once per kind of page and then replayed, so the slower CPU brain costs little.
    base and senior are choosers (step, offered) -> name. ready() says whether the senior can answer now
    (e.g. it has finished loading on the CPU); without it the senior is always used."""
    def choose(step, offered):
        use = senior if senior is not None and (ready is None or ready()) else base
        return use(step, offered)
    return choose


def find(offered, wanted):
    """The one offered element with this name. Several with the same name are fine only if they go to the
    same place (a product's picture and title link); otherwise the step is ambiguous."""
    same = [c for c in offered if x.core(name(c)) == x.core(wanted or '')]
    if not same and wanted:  # the brain copied a label too, like "256 (button)"
        bare = re.sub(r'\s*\([^()]*\)\s*$', '', wanted)
        same = [c for c in offered if x.core(name(c)) == x.core(bare)]
    if not same:
        return None, f'nothing called "{wanted}"' if wanted else 'nothing fits'
    hrefs = {c['href'] for c in same}
    if len(same) > 1 and (len(hrefs) > 1 or '' in hrefs):
        return None, f'more than one thing is called "{wanted}"'
    return same[0], ''


async def do_steps(page, url, steps, recorded, choose, run_blocking):
    """Run each step on an open page. recorded: {step: name clicked on earlier pages of this kind}.
    choose(step, offered) -> name is the brain; run_blocking runs it off the browser's thread.
    Returns [{'step', 'name', 'how': 'replay' | 'brain', 'ok', 'why'}]."""
    done = []
    for step in steps:
        offered = [c for c in await page.evaluate(CANDIDATES_JS) if safe(c, page.url)[0]]
        target, how, why = None, 'replay', ''
        if step in recorded:  # last time on this kind of page: the same name, with no brain
            target = find(offered, recorded[step])[0]
        if target is None:
            how = 'brain'
            target, why = find(offered, await run_blocking(choose, step, offered))
        if target is None:
            done.append({'step': step, 'ok': False, 'how': how, 'why': why})
            return done
        before, address = await page.evaluate('document.body.innerText'), page.url
        try:
            await page.locator(target['css']).first.click(timeout=5000)
            try:
                await page.wait_for_load_state('networkidle', timeout=3000)
            except Exception:
                pass
        except Exception as e:
            done.append({'step': step, 'ok': False, 'how': how, 'why': f'the click failed: {type(e).__name__}'})
            return done
        if site(page.url) != site(url):
            done.append({'step': step, 'ok': False, 'how': how, 'why': 'the click left the site'})
            return done
        if page.url == address and await page.evaluate('document.body.innerText') == before:
            done.append({'step': step, 'ok': False, 'how': how, 'why': f'clicking "{name(target)}" changed nothing'})
            return done
        done.append({'step': step, 'ok': True, 'how': how, 'name': name(target), 'why': ''})
    return done


def fill(text, values):
    """A skill's blanks: "click the {size} option" with {"size": "256"}."""
    return re.sub(r'\{(\w+)\}', lambda m: str(values.get(m.group(1), m.group())), text)


def describe(done):
    return '; '.join(f"{d['step']}: {d.get('name') or d['why']} ({d['how']})" for d in done)
