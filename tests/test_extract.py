"""The page reader (errand/extract.py): numbered view, snapping, the round 1 fixes and the vote
across pages, on small made-up pages, with a fake brain. No model, no network."""
import re

from errand import extract as x

WORD = {1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five'}
FIELDS = {'title': ('the product title', 'text'), 'price': ('the price', 'text'),
          'stock': ('integer copies in stock', 'number'), 'rating': ('integer stars', 'number'),
          'published': ('the first publication date', 'date')}


def product(title, price='£10.00', stock=7, stars=3, notes=0, date='October 18, 1851 (UK) November 14, 1851 (US)'):
    """A small shop page. `notes` paragraphs before the price move its spot on the page."""
    return f'''<html><head><style>.x{{padding:0}}</style><script>var n = 0;</script></head><body>
      <div class="product">
        <h1>{title}</h1>
        <p class="description">{title} is a lovely thing.</p>
        {'<p class="note">On sale</p>' * notes}
        <p class="price">{price}</p>
        <p class="stock">In stock ({stock} available)</p>
        <p class="star-rating {WORD[stars]}"></p>
        <div class="ratings"><p><span class="count">12</span> reviews {'<span class="star"></span>' * stars}</p></div>
        <table><tr><th>Published</th><td>{date} [ 1 ]</td></tr></table>
      </div></body></html>'''


def test_view_numbers_pieces_hides_style_and_counts_icons():
    view, els = x.numbered_view(product('Starving Hearts', stars=4), focus='div.product')
    lines = view.splitlines()
    assert lines[0] == '[1] h1: Starving Hearts' and len(lines) == len(els)
    assert '[2] p class=description: Starving Hearts is a lovely thing.' in lines
    assert any(line.endswith('span class=star ×4') for line in lines)  # code counts the icons, not the brain
    assert 'padding' not in view and 'var n' not in x.numbered_view(product('A'))[0]  # style and script never shown


def test_without_focus_the_view_is_the_body_so_the_tab_title_never_wins():
    """Found live on books.toscrape: "In Her Wake" snapped to <title>In Her Wake | Books to Scrape</title>."""
    page = '<html><head><title>In Her Wake | Books to Scrape</title></head><body><h1>In Her Wake</h1></body></html>'
    view, els = x.numbered_view(page)
    assert view == '[1] h1: In Her Wake' and x.snap_text('In Her Wake', els) == 'In Her Wake'


def test_view_keeps_a_linked_piece_whole():
    view, _ = x.numbered_view('<table><tr><td><a href="/e">T. Egerton</a>, Whitehall</td></tr></table>')
    assert view == '[1] td: T. Egerton, Whitehall'


def test_snap_copies_the_whole_piece_without_footnote_marks():
    _, els = x.numbered_view('<div><h1>Starving Hearts (Triangular Trade Trilogy, #1)</h1><td>February 1932 [ 1 ]</td>'
                             '<p>Born: November 22, 1869 in Paris, France</p></div>')
    assert x.snap_text('Starving Hearts', els) == 'Starving Hearts (Triangular Trade Trilogy, #1)'
    assert x.snap_text('February 1932', els) == 'February 1932'  # was "February 1932 [ 1 ]" before phase 1
    assert x.snap_text('Paris, France', els) == 'Paris, France'  # copying the "Born:" line would spoil it


def test_finish_keeps_one_date_and_numbers_shown_on_the_page():
    view, els = x.numbered_view(product('Moby-Dick', stock=7, stars=3), focus='div.product')
    got = x.finish({**FIELDS, 'reviews': ('reviews', 'number'), 'pages': ('page count', 'number')},
                   {'title': 'Moby', 'published': 'October 18, 1851 (UK) November 14, 1851 (US)', 'stock': 7,
                    'rating': 3, 'reviews': 12, 'pages': 0}, view, els)
    assert got['title'] == 'Moby-Dick'  # snapped to the heading
    assert got['published'] == 'October 18, 1851'  # a date field keeps one date
    assert (got['stock'], got['rating'], got['reviews']) == (7, 3, 12)  # digits, a class word ("Three")
    assert got['pages'] is None  # a 2B brain writes 0 for "no page count"; 0 isn't on the page
    assert got['price'] is None  # not written at all: none, not a crash
    lines = len(view.splitlines())
    assert x.finish({'n': ('a count', 'number')}, {'n': lines}, view, els)['n'] is None  # line numbers don't count
    assert x.finish({'n': ('a count', 'number')}, {'n': '7'}, view, els)['n'] is None  # the form asks for an integer


def test_answer_form_and_prompt():
    s = x.schema(FIELDS)
    assert s['required'] == list(FIELDS) and s['properties']['stock']['type'] == ['integer', 'null']
    assert s['properties']['published']['type'] == ['string', 'null']
    p = x.system_prompt(FIELDS, 'Extra rule.')
    assert '"title" (the product title)' in p and 'copies. Extra rule. Output ONE JSON' in p
    assert 'copies. Output ONE JSON' in x.system_prompt(FIELDS)
    assert x.last_json('think {"a": 1} then {"b": 2}') == {'b': 2} and x.last_json('no json') is None


def fake_brain(answers, calls):
    """Answers per page, found by the page's title in the view; counts its calls."""
    def brain(view, fields):
        calls.append(view)  # the whole title line: "Book 1" must not match "Book 12"
        return next(a for t, a in answers.items() if re.search(rf'^\[\d+\] h1: {re.escape(t)}$', view, re.M))
    return brain


def truth(title, k):
    return {'title': title, 'price': f'£1{k}.00', 'stock': k + 2, 'rating': k % 5 + 1, 'published': 'October 18, 1851'}


def test_the_vote_outvotes_one_brain_slip_and_reads_new_pages():
    titles = [f'Book {k}' for k in range(8)]
    pages = [product(t, f'£1{k}.00', k + 2, k % 5 + 1) for k, t in enumerate(titles)]
    said = {t: truth(t, k) for k, t in enumerate(titles)}
    said['Book 0'] = {**said['Book 0'], 'title': 'Book 0 is a lovely thing.', 'rating': 5}  # copied the description, misread stars
    samples = [(pages[k], x.finish(FIELDS, said[titles[k]], *x.numbered_view(pages[k], focus='div.product')))
               for k in range(5)]
    recipe = x.learn_recipe(samples, FIELDS, focus='div.product')
    assert set(recipe) == set(FIELDS) and recipe['title'][0] == 'text' and recipe['rating'][0] in ('word', 'count')
    for k in (0, 6, 7):  # the slipped sample page, and two pages the recipe wasn't made from
        assert x.replay(pages[k], recipe, FIELDS) == truth(titles[k], k)


def test_a_field_whose_spot_moves_gets_no_recipe():
    pages = [product(f'Book {k}', f'£1{k}.00', notes=k) for k in range(5)]  # the price moves down each page
    samples = [(p, {'title': f'Book {k}', 'price': f'£1{k}.00'}) for k, p in enumerate(pages)]
    recipe = x.learn_recipe(samples, {'title': FIELDS['title'], 'price': FIELDS['price']}, focus='div.product')
    assert 'title' in recipe and 'price' not in recipe


def test_agreeing_on_missing_values_is_no_evidence():
    """Wikipedia's bug: an id found on one page only, so the selector finds nothing on the others and
    "agrees" with every page where the brain said none. It was accepted on one real example."""
    pages = [f'<table><tr id="row{k}"><th>Pages</th><td>{n}</td></tr></table>' if n else '<table></table>'
             for k, n in enumerate([None, None, 544, None, 92])]
    field = {'pages': ('page count', 'number')}
    samples = [(p, {'pages': n}) for p, n in zip(pages, [None, None, 544, None, 92])]
    assert x.learn_recipe(samples, field) == {}  # right on 1 of the 2 pages that show a value
    # right on both pages that show one, and "agreeing" on 3 empty pages: still only 2 real values seen
    two = [(f'<table><tr><th>Pages</th><td>{n}</td></tr></table>' if n else '<p>no box</p>', {'pages': n})
           for n in [None, 300, None, 400, None]]
    assert x.learn_recipe(two, field) == {}
    same_row = [(f'<table><tr><th>Pages</th><td>{n}</td></tr></table>', {'pages': n}) for n in (100, 200, 300, 400, 500)]
    assert 'pages' in x.learn_recipe(same_row, field)


def test_read_pages_asks_brains_only_where_no_recipe_reads():
    titles = [f'Book {k}' for k in range(8)]
    said = {t: truth(t, k) for k, t in enumerate(titles)}
    pages = [product(t, f'£1{k}.00', k + 2, k % 5 + 1) for k, t in enumerate(titles)]
    calls = []
    got, recipe = x.read_pages(pages, FIELDS, fake_brain(said, calls), samples=5, focus='div.product')
    assert len(calls) == 5 and set(recipe) == set(FIELDS)  # 5 sample pages, then code reads every page
    assert got == [truth(t, k) for k, t in enumerate(titles)]

    calls.clear()  # a recipe kept from earlier pages of this kind: no samples, no brain at all
    more = [product(f'Book {k}', f'£1{k}.00', k + 2, k % 5 + 1) for k in range(8, 12)]
    got, _ = x.read_pages(more, FIELDS, fake_brain(said, calls), recipe=recipe, focus='div.product')
    assert calls == [] and [g['title'] for g in got] == [f'Book {k}' for k in range(8, 12)]

    moving = [product(t, f'£1{k}.00', k + 2, k % 5 + 1, notes=k) for k, t in enumerate(titles)]
    calls.clear()
    got, recipe = x.read_pages(moving, FIELDS, fake_brain(said, calls), samples=5, focus='div.product')
    assert 'price' not in recipe and len(calls) == 8  # the price has no recipe, so every page needs a brain
    assert [g['price'] for g in got] == [f'£1{k}.00' for k in range(8)]
    assert x.read_pages.__defaults__[0] == 10  # 5 samples broke fresh Wikipedia pages (bench/results.md section 8)
