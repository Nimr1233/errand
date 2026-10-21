"""For You (errand/foryou.py): suggestions from a made-up history in a temporary database."""
import datetime as dt

from errand import foryou
from errand.store import Store


def test_suggestions_come_from_your_own_history(tmp_path):
    st = Store(tmp_path / 'e.db', tmp_path / 'c')
    now = dt.datetime(2026, 10, 21, 12, 0)
    for _ in range(3):
        st.start_job('laptop price', 10, {}, False)
    st.save_skill('laptop price', '', {'price': 'the price'}, [])
    j = st.start_job('Book prices', 20, {}, False)
    st.finish_job(j, {}, done=20, blocked=8, by_code=10, brain_calls=10, gemini_calls=0, results='x.csv')
    st.start_job('Book prices', 20, {}, False)
    old = (now - dt.timedelta(days=9)).strftime('%Y-%m-%d %H:%M:%S')
    st.db.execute("update jobs set started=? where name='Book prices'", (old,))
    st.db.commit()
    tips = foryou.suggestions(st, now)
    texts = ' | '.join(t['text'] for t in tips)
    assert "You ran 'laptop price' 3 times by hand. Schedule it?" in texts
    assert "'Book prices' last ran 9 days ago" in texts
    assert "Save it as a skill" in texts and 'were blocked' in texts
    assert tips[0]['action'] == {'tool': 'schedule_skill', 'skill': 'laptop price'}  # the strongest first
    st.add_schedule('laptop price', ['u'], 'daily 09:00', {}, '2026-10-22T09:00')
    assert not any('Schedule it' in t['text'] for t in foryou.suggestions(st, now))  # done already: not suggested


def test_no_history_no_suggestions(tmp_path):
    assert foryou.suggestions(Store(tmp_path / 'e.db', tmp_path / 'c')) == []
