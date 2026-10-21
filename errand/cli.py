"""Errand's command line: python -m errand start | mcp | setup | login | gemini."""
import argparse
import asyncio
import pathlib
import sys

LOOK_ONLY = ('job_status', 'list_agents', 'agent_detail', 'get_updates', 'list_problems', 'problem_detail', 'past_jobs')


def start(demo=False):
    """Run mission control (8765) and the terminal bridge (8766) together. demo: fake agents."""
    import os
    import uvicorn
    if demo:
        os.environ['ERRAND_DEMO'] = '1'  # read when the server module loads, just below
    from . import server, term
    # warnings only: uvicorn's info lines print /ws?token=... and /term?token=..., token included
    servers = [uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, access_log=False, log_level='warning'))
               for app, port in ((server.app, server.PORT), (term.app, term.PORT))]
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
    p.add_argument('command', choices=['start', 'mcp', 'setup', 'login', 'gemini'],
                   help='start: run mission control · mcp: the Claude Code connector · setup: how to connect it'
                        ' · login: log in to Claude Code here · gemini: check your Gemini key')
    p.add_argument('--demo', action='store_true', help='start: fake agents instead of the real engine')
    a = p.parse_args(argv)
    cmd = a.command
    if cmd == 'start':
        start(a.demo)
    elif cmd == 'setup':
        setup()
    elif cmd == 'login':
        login()
    elif cmd == 'gemini':
        from .gemini import check
        print(check())
    else:
        from .mcp_server import mcp
        mcp.run('stdio')
