"""Assisted apply: fill your own details into job application pages, in a visible browser that remembers
your logins. You log in or sign up once, by hand (python -m errand apply --login); the saved profile
keeps you signed in after that.
Errand never types a password, never makes an account, never solves a CAPTCHA and never clicks Submit:
it fills the fields it recognises, then hands the page to you.
"""
import json
import os
import pathlib

from .store import HOME

PROFILE = HOME / 'apply_profile'  # the browser's saved logins and cookies
DATA = HOME / 'apply.json'        # your details

TEMPLATE = {
    'first_name': '', 'last_name': '', 'full_name': '',
    'email': '', 'phone': '',
    'address': '', 'city': '', 'state': '', 'zip': '', 'country': '',
    'linkedin': '', 'github': '', 'website': '',
    'current_company': '', 'current_title': '', 'years_experience': '',
    'cover_letter': '',
    'resume': '',
}

# (detail, words that mark the field, words that rule it out). First match wins, so the specific ones come first.
FIELDS = [
    ('email', ['email', 'e-mail'], []),
    ('phone', ['phone', 'mobile', 'telephone', 'tel'], []),
    ('first_name', ['first name', 'firstname', 'first_name', 'given name', 'forename', 'fname'], []),
    ('last_name', ['last name', 'lastname', 'last_name', 'surname', 'family name', 'lname'], []),
    ('full_name', ['full name', 'your name', 'legal name', 'name'],
     ['first', 'last', 'middle', 'user', 'company', 'file', 'nick', 'screen', 'maiden', 'business']),
    ('linkedin', ['linkedin'], []),
    ('github', ['github'], []),
    ('website', ['portfolio', 'website', 'web site', 'personal site', 'url'], ['linkedin', 'github']),
    ('current_company', ['current company', 'current employer', 'employer', 'company', 'organisation', 'organization'], []),
    ('current_title', ['current title', 'job title', 'current role', 'title', 'position', 'role'], ['salutation', 'prefix']),
    ('years_experience', ['years of experience', 'years experience', 'total experience', 'experience (years)'], []),
    ('city', ['city', 'town'], []),
    ('state', ['state', 'province', 'region', 'county'], []),
    ('zip', ['zip', 'postal', 'postcode', 'post code'], []),
    ('country', ['country'], []),
    ('address', ['address', 'street'], []),
    ('cover_letter', ['cover letter', 'coverletter'], []),
]

SKIP_TYPES = {'password', 'hidden', 'submit', 'button', 'checkbox', 'radio', 'file', 'reset', 'image'}

# A field's label, name, id, placeholder and aria-label, joined: what classify() reads.
HINTS_JS = """el => {
  let label = '';
  if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) label = l.innerText; }
  if (!label) { const p = el.closest('label'); if (p) label = p.innerText; }
  const parts = [label, el.name, el.id, el.placeholder, el.getAttribute('aria-label')];
  return {type: (el.getAttribute('type') || el.tagName).toLowerCase(), hints: parts.filter(Boolean).join(' ')};
}"""

BANNER_JS = """text => {
  const d = document.createElement('div');
  d.textContent = text;
  d.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#0b3d3f;color:#8ff7fb;'
    + 'font:15px/1.4 system-ui,sans-serif;padding:10px 14px;box-shadow:0 2px 8px #0008';
  d.onclick = () => d.remove();
  document.body.appendChild(d);
}"""


def classify(hints):
    """Which of your details a field asks for, from its label text, or None."""
    low = hints.lower()
    for key, marks, nots in FIELDS:
        if any(m in low for m in marks) and not any(n in low for n in nots):
            return key
    return None


def load_details():
    """Your details, or None after writing an empty form for you to fill in."""
    HOME.mkdir(parents=True, exist_ok=True)
    if not DATA.exists():
        DATA.write_text(json.dumps(TEMPLATE, indent=2), encoding='utf-8')
        return None
    d = json.loads(DATA.read_text(encoding='utf-8'))
    if not d.get('full_name'):
        d['full_name'] = f"{d.get('first_name', '')} {d.get('last_name', '')}".strip()
    return d


def fill_page(page, details):
    """Fill every empty field on the page that matches one of your details. Returns what was filled."""
    filled = []
    for h in page.locator('input, textarea').element_handles():
        try:
            f = h.evaluate(HINTS_JS)
            if f['type'] in SKIP_TYPES or not h.is_visible() or not h.is_editable():
                continue
            key = classify(f['hints'])
            if key and details.get(key) and not h.input_value():  # never overwrite what's already there
                h.fill(details[key])
                filled.append(key)
        except Exception:
            continue  # one odd field shouldn't stop the rest
    resume = details.get('resume')
    if resume and os.path.isfile(resume):
        boxes = page.locator('input[type=file]').element_handles()
        for h in boxes:
            try:
                hints = h.evaluate(HINTS_JS)['hints'].lower()
                # a single upload box is the resume; with several, only one labelled for it (not a photo box)
                if len(boxes) == 1 or any(w in hints for w in ('resume', 'cv', 'curriculum')):
                    h.set_input_files(resume)
                    filled.append('resume')
                    break
            except Exception:
                continue
    return filled


def apply_one(ctx, url, details):
    page = ctx.new_page()
    try:
        page.goto(url, wait_until='load', timeout=30000)
        try:
            page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            pass  # a page that keeps talking is filled as it is now
        while True:
            filled = fill_page(page, details)
            print(f"  Filled {len(filled)}: {', '.join(filled) or 'nothing I recognised'}")
            try:
                page.evaluate(BANNER_JS, 'Errand filled what it could. Check it, answer the other questions, '
                                         'solve any CAPTCHA, then click the site\'s Submit yourself. (Click to hide.)')
            except Exception:
                pass
            ans = input('  Enter = next job   r = fill again (the form changed)   s = skip: ').strip().lower()
            if ans != 'r':
                break
    except Exception as e:
        print(f'  Could not open it: {type(e).__name__}. Skipping.')
    finally:
        page.close()


def run(login=False, urls=(), url_file=None):
    from playwright.sync_api import sync_playwright
    if login:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(str(PROFILE), headless=False, no_viewport=True)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto('https://accounts.google.com/')
            print('Log in (or sign up) to Google and your job sites in that window, by hand. Open new tabs as you need.\n'
                  'Errand types nothing there. When you are done, come back here and press Enter.')
            input()
            ctx.close()
        print(f'Saved. You stay logged in for every "errand apply" from now on (profile: {PROFILE}).')
        return
    details = load_details()
    if details is None:
        print(f'I made a form for your details:\n  {DATA}\nOpen it in Notepad, fill in what you want (resume: the full '
              'path to your CV file, with / or \\\\ between folders), save it, then run this again.')
        return
    todo = list(urls)
    if url_file:
        todo += [l.strip() for l in pathlib.Path(url_file).read_text(encoding='utf-8').splitlines()
                 if l.strip() and not l.strip().startswith('#')]
    if not todo:
        print('Give me job links: python -m errand apply <link> <link> ...  or  --file jobs.txt (one link a line).\n'
              'First time? python -m errand apply --login')
        return
    if details.get('resume') and not os.path.isfile(details['resume']):
        print(f"  Heads up: no file at resume path {details['resume']}, so I won't upload it.")
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE), headless=False, no_viewport=True)
        try:
            for i, url in enumerate(todo, 1):
                print(f'\n[{i}/{len(todo)}] {url}')
                apply_one(ctx, url, details)
        finally:
            ctx.close()
    print('\nAll done. Logins, CAPTCHAs and Submit stayed yours.')
