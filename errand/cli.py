"""Errand's command line: python -m errand start | mcp | setup."""
import argparse
import asyncio
import pathlib
import sys

LOOK_ONLY = ('job_status', 'list_agents', 'agent_detail', 'get_updates')


def start():
    """Run mission control (8765) and the terminal bridge (8766) together."""
    import uvicorn
    from . import server, term
    # warnings only: uvicorn's info lines print /ws?token=... and /term?token=..., token included
    servers = [uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, access_log=False, log_level='warning'))
               for app, port in ((server.app, server.PORT), (term.app, term.PORT))]
    print(f'Errand is running. Mission control: http://127.0.0.1:{server.PORT}/   (Ctrl+C stops it)', flush=True)

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
    print('2. Optional: let Claude Code use the four look-only tools without asking each time.')
    print('   Add these lines to "permissions" -> "allow" in your Claude Code settings (~/.claude/settings.json):\n')
    for name in LOOK_ONLY:
        print(f'   "mcp__errand__{name}",')
    print('\nThe tools that change things (start_job, answer_problem, stop_agent, pause_all, resume_all)'
          ' keep asking you every time.')


def main(argv=None):
    p = argparse.ArgumentParser(prog='errand', description='Errand: 53 free browser agents on this laptop.')
    p.add_argument('command', choices=['start', 'mcp', 'setup'],
                   help='start: run mission control · mcp: the Claude Code connector · setup: how to connect it')
    cmd = p.parse_args(argv).command
    if cmd == 'start':
        start()
    elif cmd == 'setup':
        setup()
    else:
        from .mcp_server import mcp
        mcp.run('stdio')
