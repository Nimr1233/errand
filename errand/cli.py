"""Errand's command line: python -m errand start | mcp | setup | login | gemini | telegram | autostart | phone | inbox | exports | apply."""
import argparse
import asyncio
import pathlib
import sys

LOOK_ONLY = ('job_status', 'list_agents', 'agent_detail', 'get_updates', 'list_problems', 'problem_detail', 'past_jobs',
             'list_skills', 'list_schedules', 'for_you')


def start(demo=False, phone=False):
    """Run mission control (8765) and the terminal bridge (8766) together. demo: fake agents.
    phone: mission control also listens on this laptop's Tailscale address, behind the PIN; the
    terminal bridge never does."""
    import os
    import uvicorn
    if demo:
        os.environ['ERRAND_DEMO'] = '1'  # read when the server module loads, just below
    from . import server, term
    # warnings only: uvicorn's info lines print /ws?token=... and /term?token=..., token included
    places = [(server.app, '127.0.0.1', server.PORT), (term.app, '127.0.0.1', term.PORT)]
    if phone:
        from . import phone as ph
        ip = ph.tailscale_ip()
        if not ip:
            print("Tailscale isn't installed or connected, so the phone can't reach Errand yet. Install it free from "
                  'tailscale.com on this laptop and your phone, sign in on both, then run errand start --phone again.')
        else:
            if not ph.FILE.exists():
                print(f'Your phone PIN is {ph.set_pin()} (only a hash is kept; python -m errand phone makes a new one).')
            server.HOSTS.add(f'{ip}:{server.PORT}')
            server.PHONE_HOSTS.add(f'{ip}:{server.PORT}')
            places.append((server.app, ip, server.PORT))  # mission control only: never the terminal bridge
            print(f'On your phone (with Tailscale on), open http://{ip}:{server.PORT}/ and enter your PIN.')
    servers = [uvicorn.Server(uvicorn.Config(app, host=host, port=port, access_log=False, log_level='warning'))
               for app, host, port in places]
    print(f"Errand is running{' (demo agents)' if server.DEMO else ''}. Mission control: "
          f'http://127.0.0.1:{server.PORT}/   (Ctrl+C stops it)', flush=True)

    async def both():
        await asyncio.gather(*(s.serve() for s in servers))

    asyncio.run(both())


def setup():
    """Print the one-time command that gives Claude Code the Errand connector. Changes nothing itself."""
    from .term import find_claude
    claude = find_claude() or 'claude'
    project = pathlib.Path(__file__).resolve().parent.parent
    print('1. Run this once in PowerShell to give Claude Code the Errand connector:\n')
    print(f'   & "{claude}" mcp add -s user errand -e "PYTHONPATH={project}" -- "{sys.executable}" -m errand mcp\n')
    print(f'2. Optional: let Claude Code use the {len(LOOK_ONLY)} look-only tools without asking each time.')
    print('   Add these lines to "permissions" -> "allow" in your Claude Code settings (~/.claude/settings.json):\n')
    for name in LOOK_ONLY:
        print(f'   "mcp__errand__{name}",')
    print('\nThe tools that change things (start_job, answer_problem, stop_agent, pause_all, resume_all)'
          ' keep asking you every time.')


def login():
    """Run Claude Code in this terminal, the same way the room does, so you can finish its setup and
    log in where pasting the login code is easy. The room's Claude Code then uses the saved login."""
    import os
    import subprocess
    from .term import child_env, find_claude
    exe = find_claude()
    if not exe:
        print("Claude Code isn't installed: https://docs.claude.com/en/docs/claude-code/setup")
        return
    print('Log in with your Claude account (the subscription option). Type /exit when you are done.\n', flush=True)
    subprocess.run([exe], cwd=os.path.expanduser('~'), env=child_env(os.environ))


def main(argv=None):
    p = argparse.ArgumentParser(prog='errand', description='Errand: 53 free browser agents on this laptop.')
    p.add_argument('command', choices=['start', 'mcp', 'setup', 'login', 'gemini', 'telegram', 'autostart', 'phone', 'inbox', 'exports', 'apply'],
                   help='start: run mission control · mcp: the Claude Code connector · setup: how to connect it'
                        ' · login: log in to Claude Code here · gemini: check your Gemini key'
                        ' · telegram: pair your Telegram bot · autostart: how to start Errand with Windows'
                        ' · phone: make a new phone PIN · inbox: set up the webhook inbox'
                        ' · exports: send results to Slack or Notion'
                        ' · apply: fill your details into job pages (you do logins, CAPTCHAs and Submit)')
    p.add_argument('links', nargs='*', help='apply: the job page links to fill')
    p.add_argument('--demo', action='store_true', help='start: fake agents instead of the real engine')
    p.add_argument('--phone', action='store_true', help='start: also reachable from your phone over Tailscale, with a PIN')
    p.add_argument('--login', action='store_true', help='apply: open the saved browser so you can log in once, by hand')
    p.add_argument('--file', help='apply: a text file of job links, one a line')
    a = p.parse_args(argv)
    cmd = a.command
    if cmd == 'start':
        start(a.demo, a.phone)
    elif cmd == 'exports':
        from .exports import setup_text
        print(setup_text())
    elif cmd == 'inbox':
        from .inbox import setup_text
        print(setup_text())
    elif cmd == 'phone':
        from .phone import set_pin
        print(f'Your new phone PIN: {set_pin()}  (only a hash is kept; the old PIN stops working)')
    elif cmd == 'setup':
        setup()
    elif cmd == 'login':
        login()
    elif cmd == 'autostart':
        from .schedule import autostart_commands
        print(autostart_commands())
    elif cmd == 'telegram':
        from .telegram import pairing_code
        print(pairing_code())
    elif cmd == 'gemini':
        from .gemini import check
        print(check())
    elif cmd == 'apply':
        from .apply import run
        run(a.login, a.links, a.file)
    else:
        from .mcp_server import mcp
        mcp.run('stdio')
