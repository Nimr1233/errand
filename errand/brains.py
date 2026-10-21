"""The brain server: llama.cpp's llama-server running Qwen3.5-2B in 53 slots on the laptop GPU, with
the settings measured in bench/results.md (sections 2 and 5). Only listens on 127.0.0.1.
Set ERRAND_LLAMA and ERRAND_MODEL to use other files."""
import os, pathlib, subprocess, time, urllib.request

TMP = pathlib.Path.home() / 'AppData/Local/Temp/errand'  # where the benchmark put the downloads
LLAMA = pathlib.Path(os.environ.get('ERRAND_LLAMA', TMP / 'llama/llama-server.exe'))
MODEL = pathlib.Path(os.environ.get('ERRAND_MODEL', TMP / 'dl/Qwen3.5-2B-Q4_K_M.gguf'))
URL = 'http://127.0.0.1:8080'
SLOTS, CTX = 53, 4096  # 53 x 4k tokens fit in 4.4 of the 6 GB VRAM
# -rea off, not --reasoning-budget 0: same accuracy, about 13% faster (bench/results.md section 5)
FLAGS = ['-ngl', '99', '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0', '-ctxcp', '2', '-cram', '2048',
         '-rea', 'off']


def healthy(url=URL):
    try:
        with urllib.request.urlopen(url + '/health', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


class BrainServer:
    def __init__(self, log_path=None):
        self.log_path, self.proc = log_path, None

    def start(self, wait=180):
        """Start llama-server and wait until it answers. One that is already running is used as is."""
        if healthy():
            return
        missing = next((p for p in (LLAMA, MODEL) if not p.exists()), None)
        if missing:
            raise RuntimeError(f'brains not installed: {missing} is missing')
        log = open(self.log_path, 'w') if self.log_path else subprocess.DEVNULL
        self.proc = subprocess.Popen(
            [str(LLAMA), '-m', str(MODEL), '-np', str(SLOTS), '-c', str(SLOTS * CTX), *FLAGS,
             '--host', '127.0.0.1', '--port', URL.rsplit(':', 1)[1]],
            stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(wait * 2):
            if healthy():
                return
            if self.proc.poll() is not None:
                raise RuntimeError(f'llama-server stopped with code {self.proc.returncode}')
            time.sleep(0.5)
        self.stop()
        raise RuntimeError(f'llama-server did not answer within {wait} s')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
