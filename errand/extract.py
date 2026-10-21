"""Errand's page reader: how a small brain reads one kind of web page, and how code checks and
repeats its work. Each part won a measured test on 80 saved pages from 4 sites (bench/results.md
sections 4-7; the scoreboard is bench/score.py):
- the brain reads a numbered list of page pieces and writes values into a fixed form; code snaps
  each text value to the page piece holding it and copies that piece (section 4)
- a date field keeps one date; a number must be shown on the page, or it is none; style and
  script never reach the brain (section 6)
- a vote across pages: recipes learned from the brains' answers on a few sample pages, replayed by
  code on every page, so a brain is needed only for the fields no recipe covers (section 7)

fields = {name: (what it is, in words the brain reads, kind)}, kind 'text', 'number' or 'date'.
"""
import json, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from scrapling.parser import Selector

INLINE = {'a', 'abbr', 'b', 'bdi', 'br', 'cite', 'em', 'i', 'img', 'small', 'span', 'strong', 'sub', 'sup', 'time'}
KEEP = ('class', 'title', 'alt', 'itemprop', 'content', 'aria-label')  # labels that can hold an answer
SKIP = ('style', 'script', 'noscript')  # never page content: Wikipedia puts CSS inside its infobox
NUMBER_WORDS = {w: n for n, w in enumerate('One Two Three Four Five Six Seven Eight Nine Ten'.split(), 1)}
MONTH = '(?:January|February|March|April|May|June|July|August|September|October|November|December)'
# real month names, then ISO dates, then a bare year. bench/testset.py keeps its own copy for the
# answer key, so a bug here can't quietly change the key too.
DATE = re.compile(rf'\d{{1,2}} {MONTH} \d{{4}}|{MONTH} \d{{1,2}}, \d{{4}}|{MONTH} \d{{4}}|\d{{4}}-\d{{2}}-\d{{2}}|\d{{4}}')
VOTE_SHARE = 0.8  # a recipe must give back the brains' answer on 4 of 5 sample pages (8 of 10)
# ...and must read a real value right on at least 3 of them: a selector that finds nothing "agrees"
# with every page where the brain said none, so missing values are no evidence (bench/results.md section 8)
MIN_HITS = 3


def as_page(html):
    return html if isinstance(html, Selector) else Selector(html)


def own_text(el):
    return ' '.join(t.strip() for t in el.xpath('text()').getall() if t.strip())


def inline_only(el):
    """Insides are only inline bits that all hold text. An empty icon inside (star icons next to
    "14 reviews") carries meaning, so such a piece is not flattened and the icons keep their line."""
    kids = list(el.children)
    return bool(kids) and bool(el.get_all_text(strip=True)) and \
        all(c.tag in INLINE and (c.tag == 'br' or c.get_all_text(strip=True)) for c in kids)


def piece_text(el):
    """A piece's text: its own text, or all of it when its insides are only inline bits like links
    (Wikipedia's "<a>T. Egerton</a>, Whitehall" stays one piece)."""
    if inline_only(el):
        return re.sub(r'\s+', ' ', el.get_all_text(separator=' ', strip=True)).replace(' ,', ',')
    return own_text(el)


def clean_piece(el):
    return re.sub(r'\s*\[\s*\w+\s*\]', '', piece_text(el))  # footnote marks like [ 1 ] are never data


def numbered_view(html, focus=None, width=120, limit=9000, skip=SKIP):
    """One numbered line per page piece that holds text or a label, inside the page's main block
    (`focus`, a CSS selector; the page's body when None: the <head>'s "<title>Book | Shop</title>"
    would win the snap over the heading). Containers whose text lives in their children are skipped.
    A run of identical empty pieces, like star icons, becomes one line ending in ×N: code counts, not
    the brain. Returns (the text a brain reads, the elements in line order)."""
    s = as_page(html)
    block = s.css(focus or 'body')
    els, lines, last, inside = [], [], None, set()
    for el in (block[0] if block else s).css('*'):
        if id(el._root) in inside:  # part of an inline piece already shown whole
            continue
        if el.tag in skip:
            inside.update(id(d) for d in el._root.iterdescendants())
            continue
        own = piece_text(el)
        if inline_only(el):
            inside.update(id(d) for d in el._root.iterdescendants())
        labels = {k: re.sub(r'\s+', ' ', v).strip()[:80] for k, v in el.attrib.items()
                  if k in KEEP or k.startswith('data-')}
        if not own and (el.get_all_text(strip=True) or not labels):  # a container, or nothing to show
            continue
        tag = ' '.join([el.tag] + [f'{k}={v}' for k, v in labels.items()])
        if not own and not el.children and tag == last:  # same empty icon again
            count = int(lines[-1].rsplit('×', 1)[1]) + 1 if '×' in lines[-1] else 2
            lines[-1] = f"{lines[-1].rsplit(' ×', 1)[0]} ×{count}"
            continue
        last = tag if not own and not el.children else None
        els.append(el)
        lines.append(f'[{len(els)}] {tag}: {own[:width]}'.rstrip(': ') if not own else f'[{len(els)}] {tag}: {own[:width]}')
    text = '\n'.join(lines)
    return text[:limit], els  # shortcut: cut at `limit` chars, a page whose answers sit past it fails; prune smarter when that shows up


def system_prompt(fields, extra=''):
    """`extra`: more rule sentences, for the tuner to try (bench/score.py PROMPT_FIXES)."""
    keys = ', '.join(f'"{k}" ({d})' for k, (d, _) in fields.items())
    return ('You read one web page, shown as numbered lines: [number] tag labels: text. A repeated empty piece '
            f'ends in ×N, the number of copies.{" " + extra if extra else ""} Output ONE JSON object with exactly '
            f'these keys: {keys}. Copy text exactly as written on the page. Use null only when the page truly does not show it.')


def schema(fields):
    """The fixed answer form llama.cpp holds the brain to."""
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields),
            'properties': {k: {'type': ['integer' if kind == 'number' else 'string', 'null']} for k, (_, kind) in fields.items()}}


def last_json(text):
    for m in reversed(list(re.finditer(r'\{[^{}]*\}', text or '', re.S))):
        try:
            return json.loads(m.group())
        except ValueError:
            continue
    return None


def chat(url, system, user, max_tokens=300, **extra):
    body = json.dumps({'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                       'max_tokens': max_tokens, 'temperature': 0, **extra}).encode()
    req = urllib.request.Request(url + '/v1/chat/completions', body, {'Content-Type': 'application/json'})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.loads(r.read())
    return data, time.perf_counter() - t


def llama_brain(url='http://127.0.0.1:8080', max_tokens=300):
    """A brain for read_pages: one llama-server call per page, held to the answer form."""
    def brain(view, fields):
        data, _ = chat(url, system_prompt(fields), view, max_tokens,
                       response_format={'type': 'json_schema', 'json_schema': {'schema': schema(fields)}})
        return last_json(data['choices'][0]['message'].get('content'))
    return brain


def snap_text(value, els):
    """Copy a whole page piece only when the brain's answer is how that piece starts (a cut-short
    title comes back whole). Otherwise keep the brain's words: on a "Born: <date> in <place>" line,
    copying the line would spoil both answers."""
    v = re.sub(r'\s+', ' ', str(value)).strip().casefold()
    for el in els:
        t = clean_piece(el)
        if v and t.casefold().startswith(v):
            return t
    return value


def on_page(n, view):
    """A number answer must be shown on the page, as digits, a ×N count or a number word in a label.
    Line numbers don't count."""
    if n == 1:  # shortcut: a lone icon means 1 but shows no number, so 1 always passes; a made-up 1 slips through
        return True
    text = re.sub(r'^\[\d+\] ', '', view, flags=re.M)
    words = [w for w, v in NUMBER_WORDS.items() if v == n]
    return bool(re.search(rf'(?<![\d.,]){n}(?!\d|[.,]\d)', text) or any(re.search(rf'\b{w}\b', text) for w in words))


def first_date(text):
    """The first date shown: Moby-Dick lists a UK and a US date; Frankenstein adds '; 208 years ago'."""
    m = DATE.search(text or '')
    return m.group() if m else text


def finish(fields, written, view, els):
    """Code's part after the brain writes: snap text to its piece, one date per date field, and a
    number not shown on the page becomes none (a 2B brain writes 0 for "no page count")."""
    out = {}
    for f, (_, kind) in fields.items():
        v = (written or {}).get(f)
        if kind == 'number':
            if v is not None and not (isinstance(v, int) and on_page(v, view)):
                v = None
        elif isinstance(v, str):
            v = snap_text(v, els)
            if kind == 'date':
                v = first_date(v)
        out[f] = v
    return out


READERS = {  # how code reads a value out of one page piece, so a recipe can replay it on any page
    'text': lambda el: clean_piece(el) or None,
    'number': lambda el: (int(m.group().replace(',', '')) if
                          (m := re.search(r'(?<![\d.,])\d+(?:,\d{3})*(?!\d|[.,]\d)', piece_text(el))) else None),
    'word': lambda el: next((NUMBER_WORDS[w] for w in el.attrib.get('class', '').split() if w in NUMBER_WORDS), None),
    # a run of identical empty icons, like stars: how many share this one's tag and class under its parent
    'count': lambda el: None if piece_text(el) or el.parent is None else
             sum(c.tag == el.tag and c.attrib.get('class') == el.attrib.get('class') for c in el.parent.children)}


def read(el, reader, kind):
    v = READERS[reader](el)
    return first_date(v) if kind == 'date' and v else v


def same(kind, a, b):
    """Do a recipe's value and a brain's answer agree? Both none counts as agreeing."""
    if a in (None, '') or b in (None, ''):
        return a in (None, '') and b in (None, '')
    if kind == 'number':
        return str(a).strip() == str(b).strip()
    return re.sub(r'\s+', ' ', str(a)).strip().casefold() == re.sub(r'\s+', ' ', str(b)).strip().casefold()


def replay(page, recipe, fields):
    """Read every field a recipe covers off one page, with no brain."""
    page, out = as_page(page), {}
    for f, (reader, selector) in recipe.items():
        el = page.css(selector)
        out[f] = read(el[0], reader, fields[f][1]) if el else None
    return out


def learn_recipe(pages, fields, share=VOTE_SHARE, **view):
    """The vote across pages. pages: [(html, answers)] for sample pages of one kind, with the answers
    the brains gave (never an answer key). Every page piece that holds a brain's answer suggests a
    (reader, CSS selector); per field, the one that gives back the brains' answers on the most
    sample pages wins, if that is at least `share` of them and it reads a real value right on at
    least MIN_HITS of them, and on `share` of the pages where the brains saw one. A field no recipe
    can read (its spot moves from page to page) gets none and stays with the brain.
    `view`: numbered_view options."""
    parsed = [(as_page(h), a) for h, a in pages]
    pieces = [numbered_view(p, **view)[1] for p, _ in parsed]
    recipe = {}
    for f, (_, kind) in fields.items():
        readers = ('number', 'word', 'count') if kind == 'number' else ('text',)
        votes = {}
        for (_, answers), els in zip(parsed, pieces):
            want = answers.get(f)
            if want in (None, ''):
                continue
            for el in els:
                for name in readers:
                    got = read(el, name, kind)
                    if got not in (None, '') and same(kind, got, want):
                        key = (name, el.generate_css_selector)
                        votes[key] = votes.get(key, 0) + 1
        shown = sum(a.get(f) not in (None, '') for _, a in parsed)
        for key in sorted(votes, key=votes.get, reverse=True)[:10]:
            got = [(replay(p, {f: key}, fields)[f], a.get(f)) for p, a in parsed]
            agree = sum(same(kind, g, w) for g, w in got)
            hits = sum(w not in (None, '') and same(kind, g, w) for g, w in got)
            if agree >= share * len(parsed) and hits >= max(MIN_HITS, share * shown):
                recipe[f] = key
                break
    return recipe


def read_pages(htmls, fields, brain, samples=10, recipe=None, workers=53, **view):
    """Read many pages of one kind. Brains read `samples` pages, a recipe is learned from their
    answers, and code replays it on every page. Pass back a `recipe` learned earlier for this kind
    of page to skip the samples. A field with no recipe is read by a brain on every page.
    brain(view_text, fields) returns the answers it wrote (llama_brain() makes one).
    Returns (answers per page, the recipe).
    samples: 10, not 5. On fresh Wikipedia pages, 5 boxes happened to share one row order, the
    recipe trusted it and broke the next pages; 10 pages show the order moving (results.md section 8)."""
    pages = [as_page(h) for h in htmls]
    with ThreadPoolExecutor(workers) as pool:
        n = 0 if recipe is not None else min(samples, len(pages))
        first = dict(zip(range(n), pool.map(lambda i: read_page(pages[i], fields, brain, **view), range(n))))
        recipe = recipe if recipe is not None else learn_recipe([(pages[i], a) for i, a in first.items()], fields, **view)
        rest = [i for i in range(len(pages)) if i not in first]
        later = dict(zip(rest, pool.map(lambda i: read_page(pages[i], fields, brain, recipe, **view), rest)))
    return [{**first[i], **replay(p, recipe, fields)} if i in first else later[i] for i, p in enumerate(pages)], recipe


def read_page(html, fields, brain, recipe=None, **view):
    """One page: code reads the fields the recipe covers, and a brain reads the page only if any
    field is left. `brain` may be None when the recipe covers every field."""
    page, recipe = as_page(html), recipe or {}
    got = {}
    if set(fields) - set(recipe):
        text, els = numbered_view(page, **view)
        got = finish(fields, brain(text, fields), text, els)
    return {**{f: got.get(f) for f in fields}, **replay(page, recipe, fields)}
