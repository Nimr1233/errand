"""Exports (errand/exports.py) with a stand-in for Slack and Notion: a summary always, rows only for
public jobs, at most 100 rows on Notion."""
import json

from errand import exports


def test_slack_and_notion(tmp_path):
    cfg = tmp_path / 'exports.json'
    cfg.write_text(json.dumps({'slack_webhook': 'https://hooks.slack.com/services/T/B/x', 'notion_token': 'secret_t',
                               'notion_page': 'page123'}))
    sent = []
    send = lambda url, body, headers=None: sent.append((url, body, headers)) or 200
    s = {'done': 150, 'blocked': 2, 'by_code': 140, 'results': 'jobs/shop.csv'}
    rows = {f'https://a.example/{k}': {'status': 'ok', 'price': f'£{k}'} for k in range(150)}
    assert exports.send_job('Shop', s, ['price'], rows, False, send, cfg) == [('slack', 200), ('notion', 200)]
    slack, notion = sent
    assert slack[1] == {'text': "Errand finished 'Shop': 150 pages, 2 blocked, 140 read by code. Results: jobs/shop.csv"}
    assert notion[0] == exports.NOTION and notion[2]['Authorization'] == 'Bearer secret_t'
    page = notion[1]
    assert page['parent'] == {'page_id': 'page123'} and page['properties']['title']['title'][0]['text']['content'] == 'Errand: Shop'
    table = page['children'][1]['table']
    assert table['table_width'] == 3 and len(table['children']) == 1 + exports.ROWS  # header + the first 100
    assert 'all 150 are in the CSV' in json.dumps(page['children'][2])


def test_a_private_job_sends_only_its_summary(tmp_path):
    cfg = tmp_path / 'exports.json'
    cfg.write_text(json.dumps({'notion_token': 't', 'notion_page': 'p'}))
    sent = []
    exports.send_job('Bank', {'done': 3, 'blocked': 0, 'by_code': 0, 'results': 'x.csv'}, ['balance'],
                     {'https://bank.example/1': {'status': 'ok', 'balance': '£9,000'}}, True,
                     lambda url, body, headers=None: sent.append(body) or 200, cfg)
    assert '9,000' not in json.dumps(sent) and len(sent[0]['children']) == 1


def test_nothing_set_up_sends_nothing(tmp_path):
    assert exports.send_job('x', {}, [], {}, False, lambda *a: 1 / 0, tmp_path / 'none.json') == []
