"""Assisted apply: which detail each job-form field gets, and a real fill on a local page (no website)."""
import pytest

from errand.apply import classify, fill_page

CASES = {
    'Email': 'email', 'E-mail address': 'email', 'Phone number': 'phone', 'Mobile': 'phone',
    'First Name': 'first_name', 'Given name': 'first_name', 'Last name': 'last_name', 'Surname': 'last_name',
    'Full name': 'full_name', 'Your Name': 'full_name', 'Name': 'full_name',
    'Company name': 'current_company', 'Current employer': 'current_company', 'Job title': 'current_title',
    'LinkedIn URL': 'linkedin', 'GitHub profile': 'github', 'Portfolio website': 'website',
    'Street address': 'address', 'City': 'city', 'State / Province': 'state', 'Postal code': 'zip',
    'Zip': 'zip', 'Country': 'country', 'Years of experience': 'years_experience', 'Cover letter': 'cover_letter',
}


@pytest.mark.parametrize('hints,key', CASES.items())
def test_classify(hints, key):
    assert classify(hints) == key


@pytest.mark.parametrize('hints', ['Describe your experience with Python', 'Password', 'How did you hear about us?'])
def test_unknown_fields_left_for_you(hints):
    assert classify(hints) is None


FORM = """<form>
<label for=f>First name</label><input id=f>
<label>Email address <input type=email name=em></label>
<input name=company_name placeholder="Company name">
<input name=nick placeholder="Name" value="already typed">
<label for=pw>Password</label><input id=pw type=password>
<textarea aria-label="Why do you want this job?"></textarea>
<label for=cv>Resume/CV</label><input id=cv type=file>
<label for=ph>Profile photo</label><input id=ph type=file>
</form>"""


def test_fill_page(tmp_path):
    from playwright.sync_api import sync_playwright
    cv = tmp_path / 'cv.pdf'
    cv.write_bytes(b'%PDF-1.4')
    details = {'first_name': 'Sam', 'email': 'sam@example.com', 'current_company': 'Acme',
               'full_name': 'Sam Lee', 'resume': str(cv)}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page()
        page.set_content(FORM)
        filled = fill_page(page, details)
        assert sorted(filled) == ['current_company', 'email', 'first_name', 'resume']
        assert page.input_value('#f') == 'Sam'
        assert page.input_value('[name=em]') == 'sam@example.com'
        assert page.input_value('[name=nick]') == 'already typed'  # never overwritten
        assert page.input_value('#pw') == ''                       # passwords are never touched
        assert page.input_value('textarea') == ''                  # open questions stay yours
        assert page.eval_on_selector('#cv', 'e => e.files.length') == 1
        assert page.eval_on_selector('#ph', 'e => e.files.length') == 0  # the photo box is left alone
        b.close()
