# Free ($0) integrations for Errand (personal, Windows laptop), as of October 2026

Research date: 2026-10-19. Pages fetched on 2026-10-19 unless marked "not fetched this session". If a page shows a "last updated" date, it is given.

## Q1. Google Sheets API + Drive API for a personal OAuth app: quotas, testing-mode OAuth, card

### Takeaway
Sheets and Drive APIs are free for normal use and have no daily request cap. The limits are per-minute (Sheets: 60 reads/min and 60 writes/min per user). A personal app can stay in OAuth "Testing" mode without Google verification (up to 100 test users), but its refresh tokens expire every 7 days, so you have to re-consent weekly. One new risk: Google says it plans to start billing for over-quota use "later in 2026".

### Cited Findings
- Sheets API: 300 read requests/min per project and 60/min per user per project. Writes are the same (300/min per project, 60/min per user). There is "no limit to the number of requests" per day as long as you stay within the per-minute quotas. Standard use is free. Google says exceeding quota "is planned to incur charges to your Google Cloud billing account later in 2026". Page last updated 2026-09-03. — [Google Sheets API usage limits](https://developers.google.com/workspace/sheets/api/limits)
- Drive API is now metered in "quota units": 1,000,000 units/min per project and 325,000 units/min per user per project. Method costs: `files.get` 5, `files.list` 100, `files.download` 200, `files.update` 50. Exceeding quota returns 403 "User rate limit exceeded" or 429, so retry with exponential backoff. — [Drive API usage limits](https://developers.google.com/workspace/drive/api/guides/limits) (last updated 2026-09-11)
- Drive also has a 750 GB/day upload+copy limit per user, a 5 TB max file size, 1 TB/day egress per project before charges, and a 400,000,000 quota-unit/day per-project "billing threshold" that cannot be raised. Standard use is free. Over-quota charges are "planned... later in 2026" with at least 90 days' notice. The limits changed on 2026-05-01: projects that used the API between Nov 2025 and Apr 2026 keep their old quotas, and projects created on or after 2026-05-01 get the new ones. — [Drive API usage limits](https://developers.google.com/workspace/drive/api/guides/limits)
- A Drive MCP server now exists, with its own quotas (325,000 / 1,000,000 query cost per min per project / per user). — [Drive API usage limits](https://developers.google.com/workspace/drive/api/guides/limits)
- Testing-mode OAuth: if the project uses the "External" user type with publishing status "Testing", Google issues "a refresh token expiring in 7 days". This does not apply if the app requests only `openid`/`email`/`profile`. — [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2) (last updated 2026-10-16)
- Installed/Desktop app client type: the client ID (and sometimes the secret) is embedded in the app, and Google says the secret is not treated as confidential in this case. That suits a local Windows app. — [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- Testing status allows up to 100 test users, listed on the consent screen. Test-user authorizations expire 7 days after consent. A published but unverified app that requests sensitive or restricted scopes shows an "unverified app" warning and has a hard cap of 100 users over the project's lifetime. Verification is required only for public apps with sensitive or restricted scopes. — [Manage App Audience (Google Cloud Help)](https://support.google.com/cloud/answer/15549945); [OAuth production readiness](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview) (both seen via search snippets only)

### Inferences
- For a single user (the owner), there are two $0 options:
  - (a) Stay in Testing mode and accept re-consent every 7 days. The app should detect `invalid_grant` and re-run the browser consent flow.
  - (b) Publish the app "In production" without verification. You click through the "unverified app" warning yourself, and the 100-user lifetime cap doesn't matter for one person. This likely avoids the 7-day expiry. It is inferred from the docs' wording that the 7-day rule is tied to "Testing" status, and was not tested.
- Scope choice matters (not re-verified this session): `drive.file` (only files the app created or opened) is generally classed as non-sensitive. `spreadsheets` is sensitive. If Errand creates its own spreadsheets, `drive.file` may be enough for both Drive uploads and writing to those sheets, which reduces warnings.
- No card should be needed. The Sheets and Drive pages say standard use is free, and no fetched page requires a billing account to enable these APIs. To keep $0 once over-quota billing starts, throttle to well under 60 writes/min (batch rows with `values.append`/`batchUpdate`) and don't link a billing account.

### Gaps
- Whether you need a Cloud billing account to enable the APIs. Not stated on the fetched pages; widely understood to be no.
- When over-quota billing will actually start, and what happens to projects with no billing account (rejected with 429 vs. charged). Google has only said "later in 2026" with 90 days' notice.
- Exact current sensitivity classes of `drive.file` and `spreadsheets`. The scopes page was not fetched.

## Q2. Slack: incoming webhooks / single-workspace app on the free plan; limits

### Takeaway
A Slack app with an incoming webhook, installed to your own workspace, costs $0 and takes about 4 clicks. Each webhook posts to one fixed channel at about 1 message/sec. For deleting messages, threading or picking the channel at runtime, use a bot token with `chat.postMessage` (also about 1 msg/sec per channel).

### Cited Findings
- Setup:
  1. Create an app at api.slack.com/apps for your workspace.
  2. Turn on "Activate Incoming Webhooks".
  3. Choose "Add New Webhook to Workspace", pick a channel, and authorize. The URL has the form `https://hooks.slack.com/services/...`.
  4. POST JSON such as `{"text": "..."}` to that URL.
  — [Sending messages using incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)
- Each webhook is tied to one channel ("specific to a single user and a single channel"). A request can't change the channel, username or icon. Webhooks can't delete messages and don't return the message `ts`. Treat the URL as a secret: Slack "actively searches out and revokes leaked secrets". — [Slack incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)
- Rate limits: incoming webhooks allow 1 per second with short bursts. `chat.postMessage` is generally 1 message/sec per channel plus a workspace-wide limit. Web API tiers are T1 1+/min, T2 20+/min, T3 50+/min, T4 100+/min. Since 2025-05-29, newly created commercially distributed apps not approved for the Marketplace get tighter `conversations.history`/`conversations.replies` limits. Internal (customer-built) apps "should not see changes". — [Slack rate limits](https://docs.slack.dev/apis/web-api/rate-limits)

### Inferences
- Errand would be an internal, single-workspace app, so the 2025 history-API limits shouldn't apply.
- Message history on Slack's free plan is limited, but that affects reading history, not posting.

### Gaps
- Whether the Slack free plan still caps the number of apps/integrations per workspace (historically 10). Not on the fetched pages; check Slack's plan or help page.
- The pages show no last-updated date.

## Q3. Notion API: free plan access, rate limits

### Takeaway
Notion's API is limited to 180 requests/min (about 3/s) per connection on non-Business plans, and payloads to 1,000 blocks / 500 KB. The fetched page doesn't say whether the Free plan has API access (widely understood: yes, through internal integrations), and a new Free-workspace block limit started on 2026-09-08.

### Cited Findings
- Per-connection rate limit: 600 requests/min (about 10/s) for Business and Enterprise workspaces, 180/min (about 3/s) for all other plans. There is also a per-workspace limit (no number given), and some endpoints have their own limits. — [Notion request limits](https://developers.notion.com/reference/request-limits)
- Errors: 429 `rate_limited` and 529 `service_overload`. Retry after `Retry-After`. — [Notion request limits](https://developers.notion.com/reference/request-limits)
- Size limits:
  - Rich text content and URLs: 2,000 characters each
  - Arrays of blocks or rich text: 100 elements
  - Whole payload: 1,000 blocks and 500 KB

  Violations return 400 `validation_error`. — [Notion request limits](https://developers.notion.com/reference/request-limits)
- A "Free workspace block limit" takes effect on 2026-09-08. It is separate from request limits. — [Notion request limits](https://developers.notion.com/reference/request-limits)

### Inferences
- Writing Errand results to a Notion database is feasible at $0: an internal integration token, results shared with the integration, under 3 req/s, and long text split into 2,000-character chunks.
- The 2026-09-08 Free-plan block limit could stop heavy logging into Notion once reached. Keep writes compact, e.g. one page per run rather than one block per row.

### Gaps
- Whether the Notion Free plan includes API/internal integrations. Not stated on the fetched page.
- The exact size of the 2026-09-08 Free workspace block limit. The page names the limit but gives no number.
- Notion's pages show no last-updated date.

## Q4. WhatsApp Business Platform (Cloud API) pricing in 2026, test number, card; Telegram alternative; unofficial libraries

### Takeaway
WhatsApp is no longer reliably $0 after 2026-10-01:
- Meta charges per delivered message. User-to-business messages are free.
- Service replies within the 24h window are free only for the first 1,000 per month per number.
- In-window utility messages are now charged.
- Meta tells businesses to add a payment method.

For a $0 personal assistant, the free test number (up to 5 verified recipients) works for experiments, but a Telegram bot is the clearly $0, terms-compliant channel. Unofficial WhatsApp Web automation is not terms-compliant.

### Cited Findings
- Since 2025-07-01, Meta charges per delivered message, replacing per-conversation pricing. Meta "does not charge for messages from users to businesses". Rates vary by category (marketing, utility, authentication = templates sendable any time; service = non-template replies in the 24h customer service window) and by recipient country. — [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- Service messages were free from 2024-11-01. From 2026-10-01 they are charged after a monthly free tier of 1,000 service messages per business phone number. The tier doesn't roll over and resets at midnight in the account's timezone. — [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- Utility messages inside the customer service window were free from 2025-07-01. They become charged on 2026-10-01, and the webhook pricing type changes from `free_customer_service` to `regular`. — [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- Free entry point window: when a user messages from a Click-to-WhatsApp ad, the window lasts up to 7 days and all categories are free during it. — [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- New "Meta Business Agent" category (2026-07-01): AI replies powered by Meta, billed at $2.00 per million tokens. — [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- Payment method: Solution Providers and directly integrated businesses with no payment method on file by 2026-09-30 stop getting service messages delivered once those become charged on 2026-10-01. The page also says that without a payment method, service messages stop after the free tier is used, and tells you to "ensure you have a payment method in Billing Hub". These two statements are somewhat inconsistent. — [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing) (no last-updated date shown; content references 2026-10-01 and 2026-10-12 changes)
- Test number: Meta's Get Started flow gives a test business number that can message up to 5 verified recipient numbers (each verified with a WhatsApp code), starting with the pre-approved `hello_world` template. Free-form text generally needs the recipient to message first (an open 24h window). — [WhatsApp Cloud API Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started/) (seen via search snippet; page not fetched in full)
- Telegram Bot API limits (official FAQ, seen via search snippet because core.telegram.org refused connections twice):
  - Avoid more than 1 msg/sec to a single chat.
  - At most 20 messages/min in a group.
  - About 30 messages/sec for bulk broadcasts. Paid broadcasts (Telegram Stars) raise this to 1,000/sec.
  - Exceeding limits gives HTTP 429.
  - Telegram does not document exact limits, and they can change.

  — [Telegram Bots FAQ](https://core.telegram.org/bots/faq); [python-telegram-bot wiki: Avoiding flood limits](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Avoiding-flood-limits); [grammY: Flood limits](https://grammy.dev/advanced/flood)

### Inferences
- For a personal "message Errand from my phone" flow: you send the task (inbound, free) and Errand replies within 24h (a service message). That fits inside 1,000 free service messages/month per number. Whether it is truly $0 without a card on file is unclear, because the pricing page contradicts itself (see above). Treat WhatsApp as "probably $0 at low volume but card-gated and changing quarterly".
- The test number limits you to 5 recipients and is intended for development, so it isn't a durable production channel.
- A Telegram bot (create one with @BotFather, then long-poll `getUpdates` from the laptop, no public URL needed) is the safest $0 choice. Personal use is far below the 1 msg/sec per chat limit. The Bot API being free and needing no card is well known, but the exact wording was not verified this session.
- Unofficial WhatsApp Web automation libraries (e.g. whatsapp-web.js, Baileys) drive a personal WhatsApp account through reverse-engineered web protocols. WhatsApp's Terms of Service forbid accessing the service through automated or unauthorized means, and accounts can be banned. They are not an official or terms-compliant route. (ToS page not fetched this session: [WhatsApp Terms of Service](https://www.whatsapp.com/legal/terms-of-service).)

### Gaps
- Whether a payment method is strictly required to send the first 1,000 free service messages after 2026-10-01. The pricing page is ambiguous.
- Whether the test number's messages count against the free tier, and whether the 5-recipient cap can be raised.
- Exact current Telegram Bot API file size limits (historically 50 MB upload / 20 MB download on the cloud Bot API). Not verified this session because core.telegram.org was unreachable.
- Exact WhatsApp ToS wording on automation. Not fetched.

## Q5. MCP: official SDKs, stdio vs streamable HTTP, connecting Claude Desktop / Claude Code

### Takeaway
Use the official Python SDK (`pip install "mcp[cli]"`, Python 3.11+, v2 uses `MCPServer`) and expose Errand as a stdio server. Claude Desktop and Claude Code both launch it as a local subprocess, with no ports and no auth. Streamable HTTP (`--transport streamable-http`, served at `http://localhost:8000/mcp`) is the option if several clients need to share one running Errand. SSE is deprecated.

### Cited Findings
- Official Python SDK: install with `uv add "mcp[cli]"` or `pip install "mcp[cli]"`. It requires Python 3.11+. The README has "What's new in v2" and migration-guide links. The current example uses `from mcp.server import MCPServer`, `mcp = MCPServer("Demo")` and `@mcp.tool()` decorators. It supports stdio, Streamable HTTP and SSE transports. Commands: `uv run mcp dev server.py` (Inspector) and `uv run mcp run server.py --transport streamable-http` (clients connect to e.g. `http://localhost:8000/mcp`). The `cli` extra provides `mcp install`. — [modelcontextprotocol/python-sdk README](https://github.com/modelcontextprotocol/python-sdk)
- Claude Code: `claude mcp add [options] <name> -- <command> [args...]` adds a stdio server. Everything after `--` goes to the server. `claude mcp add --transport http <name> <url>` adds an HTTP server, and `"type": "streamable-http"` is accepted as an alias for `"http"`. Scopes: `local` (default, `~/.claude.json`), `project` (`.mcp.json` in the repo; interactive sessions ask for approval) and `user`. SSE is "deprecated", and Claude Code falls back from HTTP to SSE automatically from v2.1.265. `claude mcp add-from-claude-desktop` imports Desktop servers (macOS and WSL only). — [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Desktop on Windows: config file at `%APPDATA%\Claude\claude_desktop_config.json` (Settings → Developer → Edit Config), shape `{"mcpServers": {"name": {"command": ..., "args": [...], "env": {...}}}}`. Fully quit and restart Desktop after editing. Logs are in `%APPDATA%\Claude\logs` (`mcp.log`, `mcp-server-NAME.log`). Use absolute paths. If a server fails with `${APPDATA}` in its logs, set `APPDATA` in `env`. — [Connect to local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
- The MCP docs site links to versioned paths such as `/docs/2026-07-28/...`. — [Connect to local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers)

### Inferences
- Minimal Errand wiring:
  - Claude Code: `claude mcp add --scope user errand -- python -m errand.mcp_server`
  - Claude Desktop: add `"errand": {"command": "C:\\path\\to\\python.exe", "args": ["-m", "errand.mcp_server"]}`

  A stdio server must never print to stdout, except protocol messages. Send logs to stderr.
- The `2026-07-28` docs path suggests a newer MCP spec revision dated 2026-07-28. Not confirmed.
- Using the SDK's `MCPServer` (v2) rather than the older `FastMCP` import is inferred from the current README. Code written for v1 may need the migration guide.
- TypeScript SDK: the package is `@modelcontextprotocol/sdk` (from prior knowledge, not fetched this session). It is only relevant if Errand's server isn't written in Python.

### Gaps
- Exact current Python SDK version number and supported spec revision. Not shown on the README.
- Claude Code's Windows-specific note (historically: wrap `npx` in `cmd /c` on native Windows). It was in the unread tail of the page. Not relevant if Errand runs `python` directly.
- Desktop Extensions (`.mcpb`) packaging for one-click install. Not covered on the fetched page.

## Q6. CLI: lightest standard approach

### Takeaway
Use Python's built-in `argparse` (zero dependencies) with subcommands such as `errand run "task"`, `errand export --to sheets` and `errand mcp`, and register it as a `[project.scripts]` entry point so `errand` is on PATH. Typer (built on Click) gives nicer help, but it is an extra dependency.

### Cited Findings
- `argparse` is in the standard library and supports subcommands through `add_subparsers()`. — [Python docs: argparse](https://docs.python.org/3/library/argparse.html) (not fetched this session; long-standing stdlib)
- Typer builds CLIs from type hints on top of Click. — [Typer docs](https://typer.tiangolo.com/) (not fetched this session)

### Inferences
- The MCP server and the CLI can share one entry point (`errand mcp` starts the stdio server), so there is a single install for Claude and for terminal use.

### Gaps
- None material.

## Q7. Summary: which integrations are truly $0 and terms-compliant (Oct 2026)

### Takeaway

| Integration | Status | Notes |
|---|---|---|
| Google Sheets / Drive | $0 | Watch per-minute quotas and the planned "later in 2026" over-quota billing. In Testing mode, re-consent every 7 days. |
| Slack (webhook or internal app) | $0 | About 1 msg/sec. |
| Notion internal integration | Likely $0 | About 3 req/s. New Free-plan block limit from 2026-09-08. |
| Telegram bot | $0 | — |
| MCP (stdio) and CLI | $0 | Local only. |
| WhatsApp Cloud API | Not reliably $0 | Charges began 2026-10-01 beyond 1,000 free service messages/month. Meta asks for a payment method. Test number allows 5 recipients. |
| Unofficial WhatsApp Web libraries | Not compliant | Excluded. |

### Cited Findings
- See Q1–Q6 for sources: [Sheets limits](https://developers.google.com/workspace/sheets/api/limits), [Drive limits](https://developers.google.com/workspace/drive/api/guides/limits), [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2), [Slack webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks), [Slack rate limits](https://docs.slack.dev/apis/web-api/rate-limits), [Notion limits](https://developers.notion.com/reference/request-limits), [WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing), [Telegram Bots FAQ](https://core.telegram.org/bots/faq), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Connect local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers)

### Inferences
- Recommended $0 default: Telegram as the chat channel, with WhatsApp as an optional adapter the user enables at their own risk and cost. Sheets and Drive should use `drive.file`-scoped OAuth with a desktop client, and Errand should handle 7-day re-consent if the app stays in Testing.

### Gaps
- Whether the Slack free plan caps apps; whether Notion's Free plan has API access and how big its block limit is; whether WhatsApp needs a card for the free tier; current Telegram file limits; how Google's planned over-quota billing will work. All explained above.
