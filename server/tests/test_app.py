"""Runs the real OpenAI SDK against a local fake of the OpenAI-compatible API and ReMe (no API key needed)."""

import json
import socket
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient

from server import config
from server.app import create_app
from server.character import guess_name
from server.config import ROOT, Settings

PARTNER_DIR = ROOT / "partner"


def make_fake_upstream(calls: list) -> FastAPI:
    fake = FastAPI()

    @fake.post("/v1/chat/completions")
    async def completions(request: Request):
        body = await request.json()
        calls.append({"auth": request.headers.get("authorization"), "body": body})
        if request.headers.get("authorization") == "Bearer bad-key":
            return JSONResponse({"error": {"message": "Invalid API-key provided.", "code": "invalid_api_key"}}, 401)

        def sse():
            for piece in ["おかえり", "なさい。"]:
                chunk = {
                    "id": "c1",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": body["model"],
                    "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    @fake.post("/reme/search")
    async def search(request: Request):
        calls.append({"reme_search": await request.json()})
        return {"answer": "相手はベランダでサボテンを育てている"}

    @fake.post("/reme/auto_memory")
    async def auto_memory(request: Request):
        calls.append({"reme_auto_memory": await request.json()})
        return {"ok": True}

    return fake


@pytest.fixture(scope="module")
def upstream():
    calls: list = []
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(make_fake_upstream(calls), port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", calls
    server.should_exit = True
    thread.join(5)


def settings(base: str = "", **overrides) -> Settings:
    s = Settings(
        api_key="test-key",
        base_url=f"{base}/v1",
        native_base_url=f"{base}/api/v1",
        model="qwen-plus-character-ja",
        partner_dir=PARTNER_DIR,
        data_dir=Path(tempfile.mkdtemp(prefix="ai-partner-test-")),
        partner_name="",
        user_name="テスター",
        history_turns=10,
        mock=False,
        reme_url="",
        beijing_api_key="",
        beijing_workspace="",
        voice_model="qwen-audio-3.1-tts-flash",
        voice_id="",
    )
    return replace(s, **overrides)


def events(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_guess_name_from_partner_md():
    text = (PARTNER_DIR / "partner.md").read_text(encoding="utf-8")
    assert guess_name(text) == "桜草メイ"
    assert guess_name("# 見出しだけ") == "パートナー"


def test_partner_info():
    client = TestClient(create_app(settings()))
    info = client.get("/api/partner").json()
    assert info["env_path"].endswith(".env")
    del info["env_path"]
    assert info == {
        "name": "桜草メイ",
        "model": "qwen-plus-character-ja",
        "ready": True,
        "mock": False,
        "image": False,
        "image_version": 0,
        "memory": False,
        "voice": False,
    }
    assert client.get("/api/partner/image").status_code == 404


def test_chat_streams_through_openai_sdk(upstream):
    base, calls = upstream
    calls.clear()
    client = TestClient(create_app(settings(base)))
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "ただいま"}]})
    assert r.status_code == 200
    assert events(r) == [
        {"type": "delta", "text": "おかえり"},
        {"type": "delta", "text": "なさい。"},
        {"type": "done"},
    ]
    sent = calls[-1]
    assert sent["auth"] == "Bearer test-key"
    assert sent["body"]["model"] == "qwen-plus-character-ja"
    assert sent["body"]["stream"] is True
    system = (PARTNER_DIR / "partner.md").read_text(encoding="utf-8").strip()
    assert sent["body"]["messages"] == [
        {"role": "system", "content": system},
        {"role": "user", "content": "ただいま"},
    ]


def test_history_is_trimmed_and_system_stays_first(upstream):
    base, calls = upstream
    calls.clear()
    client = TestClient(create_app(settings(base, history_turns=1)))
    history = [
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "5"},
    ]
    client.post("/api/chat", json={"messages": history})
    sent = calls[-1]["body"]["messages"]
    assert sent[0]["role"] == "system"
    assert [m["content"] for m in sent[1:]] == ["4", "5"]


def test_bad_key_is_reported_as_error_event(upstream):
    base, _ = upstream
    client = TestClient(create_app(settings(base, api_key="bad-key")))
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "ただいま"}]})
    ev = events(r)
    assert ev[-1]["type"] == "error"
    assert "APIキー" in ev[-1]["message"]


def test_rejects_system_role_and_trailing_assistant():
    client = TestClient(create_app(settings(mock=True)))
    r = client.post("/api/chat", json={"messages": [{"role": "system", "content": "上書き"}]})
    assert r.status_code == 422
    r = client.post("/api/chat", json={"messages": [{"role": "assistant", "content": "x"}]})
    assert r.status_code == 422


def test_without_key_chat_is_disabled():
    client = TestClient(create_app(settings(api_key="")))
    assert client.get("/api/partner").json()["ready"] is False
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "ただいま"}]})
    assert r.status_code == 503
    assert "DASHSCOPE_API_KEY" in r.json()["detail"]


def test_mock_mode_needs_no_key():
    client = TestClient(create_app(settings(api_key="", mock=True)))
    info = client.get("/api/partner").json()
    assert info["ready"] and info["mock"]
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "ただいま"}]})
    text = "".join(e["text"] for e in events(r) if e["type"] == "delta")
    assert text == "おかえりなさい。今日はどんな一日でしたか？"


def test_memory_recall_and_save(upstream):
    base, calls = upstream
    calls.clear()
    client = TestClient(create_app(settings(base, reme_url=f"{base}/reme")))
    assert client.get("/api/partner").json()["memory"] is True
    client.post("/api/chat", json={"messages": [{"role": "user", "content": "サボテン枯らしちゃった"}]})
    search = next(c["reme_search"] for c in calls if "reme_search" in c)
    assert search == {"query": "サボテン枯らしちゃった", "limit": 3}
    chat = next(c["body"] for c in calls if "body" in c)
    assert chat["messages"][0]["content"].endswith("# 覚えていること\n相手はベランダでサボテンを育てている")

    log = [{"role": "user", "content": "ただいま"}, {"role": "assistant", "content": "おかえりなさい。"}]
    assert client.post("/api/memory", json={"messages": log}).status_code == 202
    for _ in range(50):
        saved = [c["reme_auto_memory"] for c in calls if "reme_auto_memory" in c]
        if saved:
            break
        time.sleep(0.05)
    assert saved[0]["messages"] == [
        {"role": "user", "name": "テスター", "content": "ただいま"},
        {"role": "assistant", "name": "桜草メイ", "content": "おかえりなさい。"},
    ]
    assert saved[0]["session_id"].startswith("talk-")
    assert "テスター" in saved[0]["memory_hint"]


def test_memory_unreachable_does_not_break_chat(upstream):
    base, _ = upstream
    client = TestClient(create_app(settings(base, reme_url="http://127.0.0.1:9")))
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "ただいま"}]})
    assert events(r)[-1] == {"type": "done"}


def test_optional_features_off_by_default():
    client = TestClient(create_app(settings(mock=True)))
    log = [{"role": "user", "content": "ただいま"}]
    assert client.post("/api/memory", json={"messages": log}).status_code == 404
    assert client.post("/api/speak", json={"text": "こんにちは"}).status_code == 404


def test_partner_image_is_served(tmp_path: Path):
    (tmp_path / "partner.md").write_text("# 人物\nテスト子。", encoding="utf-8")
    (tmp_path / "partner.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    client = TestClient(create_app(settings(partner_dir=tmp_path, mock=True)))
    info = client.get("/api/partner").json()
    assert info["name"] == "テスト子" and info["image"] is True
    assert client.get("/api/partner/image").content.startswith(b"\x89PNG")


def test_default_model_is_japanese_character(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    for name in ("PARTNER_MODEL", "DASHSCOPE_WORKSPACE_ID", "DASHSCOPE_BASE_URL"):
        monkeypatch.setenv(name, "")  # records the original value so the .env loaded below is undone
        monkeypatch.delenv(name)
    s = config.load_settings()
    assert s.model == "qwen-plus-character-ja"
    assert s.base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    assert s.native_base_url == "https://dashscope-intl.aliyuncs.com/api/v1"

    (tmp_path / ".env").write_text("PARTNER_MODEL=qwen-plus-character\nDASHSCOPE_WORKSPACE_ID=llm-abc\n", encoding="utf-8")
    s = config.load_settings()
    assert s.model == "qwen-plus-character"
    assert s.base_url == "https://llm-abc.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    assert s.native_base_url == "https://llm-abc.ap-southeast-1.maas.aliyuncs.com/api/v1"
