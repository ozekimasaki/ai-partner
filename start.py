"""ai-partner をワンコマンドで起動する（Mac / Windows / Linux 共通）。

    Mac:     python3 start.py
    Windows: py start.py

初回は .venv の作成、Python と Node の依存の導入、画面のビルドまで自動で行います。

オプション:
    --mock        APIキーなしで、決まった返事を返すモックで起動する
    --dev         画面の開発モード（Vite+ の dev サーバーとサーバーの自動リロード）
    --port 8000   サーバーのポート
    --no-browser  ブラウザを自動で開かない
"""

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WEB = ROOT / "web"
SERVER = ROOT / "server"
IS_WINDOWS = os.name == "nt"


def say(msg: str) -> None:
    print(f"[ai-partner] {msg}", flush=True)


def fail(msg: str) -> None:
    say(msg)
    sys.exit(1)


def run(cmd: list, **kwargs) -> None:
    result = subprocess.run([str(c) for c in cmd], **kwargs)
    if result.returncode != 0:
        fail(f"コマンドが失敗しました: {' '.join(str(c) for c in cmd)}")


def digest(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in paths:
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def read_env() -> dict:
    env = {}
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def ensure_env_file() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        shutil.copy(ROOT / ".env.example", env_file)
        say(".env を作りました。DASHSCOPE_API_KEY を書き込んでから、もう一度起動してください。")
        say("（キーなしで画面だけ見たいときは --mock を付けて起動できます）")


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def ensure_python_deps(with_extra: bool) -> Path:
    if not venv_python().exists():
        say("Python の仮想環境 .venv を作っています…")
        run([sys.executable, "-m", "venv", VENV])
    py = venv_python()
    reqs = [SERVER / "requirements.txt"]
    if with_extra:
        reqs.append(SERVER / "requirements-extra.txt")
    stamp = VENV / ".ai-partner-requirements"
    want = digest(*reqs)
    if not stamp.exists() or stamp.read_text() != want:
        say("Python のライブラリを入れています…")
        run([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", "pip"])
        cmd = [py, "-m", "pip", "install", "--disable-pip-version-check", "-q"]
        for r in reqs:
            cmd += ["-r", r]
        run(cmd)
        stamp.write_text(want)
    return py


def ensure_web(build: bool) -> None:
    npm = shutil.which("npm")
    if npm is None:
        if (WEB / "dist").is_dir():
            say("npm が見つからないので、ビルド済みの画面をそのまま使います。")
            return
        fail("Node.js（npm）が見つかりません。https://nodejs.org/ から LTS 版を入れてください。")
    stamp = WEB / "node_modules" / ".ai-partner-lock"
    want = digest(WEB / "package.json", WEB / "package-lock.json")
    if not stamp.exists() or stamp.read_text() != want:
        say("画面のライブラリを入れています（npm install）…")
        run([npm, "install", "--no-audit", "--no-fund"], cwd=WEB)
        stamp.write_text(want)
    if build:
        say("画面をビルドしています（Vite+）…")
        run([npm, "run", "build"], cwd=WEB, stdout=subprocess.DEVNULL)


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def open_when_ready(url: str, port: int) -> None:
    def wait_and_open():
        for _ in range(150):
            if port_in_use(port):
                webbrowser.open(url)
                return
            time.sleep(0.2)

    threading.Thread(target=wait_and_open, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="ai-partner を起動する")
    parser.add_argument("--mock", action="store_true", help="APIキーなしのモックで起動する")
    parser.add_argument("--dev", action="store_true", help="画面の開発モード")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        fail(f"Python 3.10 以上が必要です（いまは {sys.version.split()[0]}）。")

    ensure_env_file()
    env_values = read_env()
    with_extra = bool(env_values.get("DASHSCOPE_API_KEY_BEIJING"))
    py = ensure_python_deps(with_extra)
    ensure_web(build=not args.dev)

    if port_in_use(args.port):
        fail(f"ポート {args.port} はほかのアプリが使っています。--port 8001 のように変えて起動してください。")

    env = dict(os.environ, PYTHONUTF8="1", AI_PARTNER_PORT=str(args.port))
    if args.mock:
        env["PARTNER_MOCK"] = "1"
    elif not env_values.get("DASHSCOPE_API_KEY") and not os.getenv("DASHSCOPE_API_KEY"):
        say("DASHSCOPE_API_KEY が空です。画面は開きますが、返事はできません（.env を確認してください）。")

    server_cmd = [str(py), "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", str(args.port)]
    procs = []
    if args.dev:
        server_cmd += ["--reload", "--reload-dir", str(SERVER), "--reload-dir", str(ROOT / "partner")]
        procs.append(subprocess.Popen(server_cmd, cwd=ROOT, env=env))
        procs.append(subprocess.Popen([shutil.which("npm"), "run", "dev"], cwd=WEB, env=env))
        url, wait_port = "http://localhost:5173", 5173
    else:
        procs.append(subprocess.Popen(server_cmd, cwd=ROOT, env=env))
        url, wait_port = f"http://127.0.0.1:{args.port}", args.port

    say(f"起動しました: {url} （止めるときは Ctrl+C）")
    if not args.no_browser:
        open_when_ready(url, wait_port)
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()
    say("終了しました。")


if __name__ == "__main__":
    main()
