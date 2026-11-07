# Errand

Errand is a free AI browser agent that runs on your own computer. You give it one prompt, and it sends a group of small AI agents to open web pages and pull out what you asked for. The AI models run on your machine through llama.cpp, so you don't need a cloud account, an API key or a paid plan.

It's an early project. So far it has been built and tested on one Windows 11 laptop with an RTX 3060 (6 GB of video memory) and 16 GB of RAM. On that laptop 53 agents run at the same time, and in one test they pulled the data out of 105 saved pages in 39 seconds. The measurements are in [bench/results.md](bench/results.md). Clicking through pages that take several steps is still being worked on, because small local models are weaker at it than big cloud models.

## What's included

- Mission control, a page at http://127.0.0.1:8765/ with a 3D room where you watch the agents work and answer the ones that get stuck
- A command line tool, `python -m errand <command>`
- An MCP server, so Claude Code or another MCP client can start jobs and check on them
- A Chrome extension that works in your current tab with your own logins (see [extension/README.md](extension/README.md))
- Optional extras: schedules, Telegram messages, phone access over Tailscale, a Cloudflare inbox, and Slack and Notion connections

Errand never types your passwords, creates accounts or solves CAPTCHAs. It leaves those to you.

## Setup

1. Install Python 3.11 or newer, then the packages and browsers:

   ```
   pip install -r requirements.txt
   playwright install chromium
   scrapling install
   ```

2. Download a CUDA build of llama.cpp from its [releases page](https://github.com/ggml-org/llama.cpp/releases) (tested with build b11718 and CUDA 12.4) and a GGUF file of [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) (tested with Unsloth's `Qwen3.5-2B-Q8_0.gguf`). Errand looks for them here:

   ```
   %USERPROFILE%\AppData\Local\Temp\errand\llama\llama-server.exe
   %USERPROFILE%\AppData\Local\Temp\errand\dl\Qwen3.5-2B-Q8_0.gguf
   ```

   To use files somewhere else, set the `ERRAND_LLAMA` and `ERRAND_MODEL` environment variables. An optional second model, a Qwen3.5-4B GGUF, helps with hard choices and runs on the CPU. Errand looks for it at `...\errand\dl\Qwen3.5-4B-Q4_K_M.gguf`, or wherever `ERRAND_SENIOR` points.

3. Start Errand, then open http://127.0.0.1:8765/:

   ```
   python -m errand start
   ```

   Errand starts llama-server by itself when a job needs it, which takes about 30 seconds. To look around without a GPU, run `python -m errand start --demo`, which uses fake agents.

4. Optional: connect Claude Code. Run `python -m errand setup` and paste the command it prints.

## Tests

```
python -m pytest
```

The extension has its own tests. See [extension/README.md](extension/README.md).

## License

MIT. See [LICENSE](LICENSE).
