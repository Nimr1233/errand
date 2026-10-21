"""Exports (reports/Full feature free Errand plan.md: your own free apps, no middleman). When a job
finishes, Errand can post a summary to Slack and put the results table on a Notion page.
- Settings live in ~/.errand/exports.json (`python -m errand exports` says how to get them):
  {"slack_webhook": "https://hooks.slack.com/services/...", "notion_token": "...", "notion_page": "<page id>"}
- A private job sends only its summary, never its rows.
- Notion gets at most 100 rows (one request); the CSV always has everything.
- Not built: Google Sheets. It needs your own Google sign-in client; the CSV opens in Sheets as it is.
"""
import json, pathlib, threading, urllib.error, urllib.request

CONFIG = pathlib.Path.home() / '.errand' / 'exports.json'
NOTION = 'https://api.notion.com/v1/pages'
ROWS = 100


def post(url, body, headers=None):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError:
        return None


def summary(job, s):
    return (f"Errand finished '{job}': {s['done']} pages, {s['blocked']} blocked, {s['by_code']} read by code. "
            f"Results: {s['results']}")


def text(v):
    return {'type': 'text', 'text': {'content': '' if v is None else str(v)[:2000]}}


def notion_page(parent, job, s, fields, rows, private):
    children = [{'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': [text(summary(job, s))]}}]
    if not private and rows:
        cols = ['url', 'status', *fields]
        table = [[u, r['status'], *(r.get(f) for f in fields)] for u, r in list(rows.items())[:ROWS] if r]
        children.append({'object': 'block', 'type': 'table', 'table': {
            'table_width': len(cols), 'has_column_header': True,
            'children': [{'type': 'table_row', 'table_row': {'cells': [[text(c)] for c in row]}} for row in [cols, *table]]}})
        if len(rows) > ROWS:
            children.append({'object': 'block', 'type': 'paragraph',
                             'paragraph': {'rich_text': [text(f'The first {ROWS} rows; all {len(rows)} are in the CSV.')]}})
    return {'parent': {'page_id': parent}, 'properties': {'title': {'title': [text(f'Errand: {job}')]}}, 'children': children}


def send_job(job, s, fields, rows, private, send=post, config=None):
    """Post a finished job wherever exports are set up. Returns what was sent, for the log."""
    path = pathlib.Path(config or CONFIG)
    cfg = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    sent = []
    if cfg.get('slack_webhook'):
        sent.append(('slack', send(cfg['slack_webhook'], {'text': summary(job, s)})))
    if cfg.get('notion_token') and cfg.get('notion_page'):
        sent.append(('notion', send(NOTION, notion_page(cfg['notion_page'], job, s, fields, rows, private),
                                   {'Authorization': f"Bearer {cfg['notion_token']}", 'Notion-Version': '2022-06-28'})))
    return sent


def send_later(engine, *args):
    """In the background, so no agent waits; the outcome goes to the updates."""
    def run():
        for where, status in send_job(*args):
            engine.updates.add('job' if status == 200 else 'problem',
                               f'Results sent to {where}' if status == 200 else f"Couldn't send results to {where} (HTTP {status})")
    threading.Thread(target=run, daemon=True, name='exports').start()


def setup_text():
    return '\n'.join([f'Exports are set in {CONFIG}, a small JSON file you make. Any of:',
                      '  "slack_webhook": in Slack, create an app for your workspace, turn on Incoming Webhooks, add one '
                      'to a channel, copy its URL.',
                      '  "notion_token" and "notion_page": at notion.so/my-integrations make an internal integration, copy '
                      'its secret; open the page results should go under, Share it with the integration, copy the page id '
                      'from its link.',
                      'Example: {"slack_webhook": "https://hooks.slack.com/services/...", "notion_token": "secret_...", '
                      '"notion_page": "0123abcd..."}'])
