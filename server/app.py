import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Literal

import openai
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .character import load_character
from .config import ROOT, Settings, load_settings
from .memory import Memory
from .voice import Voice

log = logging.getLogger("ai-partner")

WEB_DIST = ROOT / "web" / "dist"
MAX_CHARS = 4000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CHARS)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)


def mock_reply(text: str) -> str:
    if "ただいま" in text:
        return "おかえりなさい。今日はどんな一日でしたか？"
    if "おやすみ" in text:
        return "おやすみなさい。あたたかくして寝てくださいね。"
    return f"（モック）「{text[:40]}」って送ってくれたんですね。よかったら、もう少し聞かせてもらえますか？"


def explain_error(e: Exception) -> str:
    if isinstance(e, openai.AuthenticationError):
        return "APIキーが受け付けられませんでした。.env の DASHSCOPE_API_KEY と、シンガポールのキーかどうかを確かめてください。"
    if isinstance(e, openai.NotFoundError):
        return "モデルか Base URL が見つかりませんでした。PARTNER_MODEL と DASHSCOPE_WORKSPACE_ID を確かめてください。"
    if isinstance(e, openai.RateLimitError):
        return "呼び出し回数か無料枠の上限に達したようです。少し待ってから試してください。"
    if isinstance(e, openai.APIConnectionError):
        return "Model Studio に接続できませんでした。ネットワークと Base URL を確かめてください。"
    if isinstance(e, openai.APIStatusError):
        return f"Model Studio がエラーを返しました（{e.status_code}）: {e.message}"
    return f"予期しないエラーが起きました: {e}"


def _line(event: dict) -> bytes:
    return (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")


def create_app(settings: Settings | None = None, llm: AsyncOpenAI | None = None) -> FastAPI:
    settings = settings or load_settings()
    character = load_character(settings.partner_dir, settings.partner_name)
    memory = Memory(settings.reme_url, settings.user_name, character.name)
    voice = Voice(
        settings.beijing_api_key,
        settings.beijing_workspace,
        settings.voice_model,
        settings.partner_dir,
        settings.voice_id,
    )
    if llm is None and settings.api_key:
        llm = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)

    app = FastAPI(title="ai-partner")
    background: set[asyncio.Task] = set()

    @app.get("/api/partner")
    def partner_info() -> dict:
        return {
            "name": character.name,
            "model": "mock" if settings.mock else settings.model,
            "ready": settings.chat_ready,
            "mock": settings.mock,
            "image": character.image is not None,
            "memory": memory.enabled,
            "voice": voice.enabled,
        }

    @app.get("/api/partner/image")
    def partner_image() -> FileResponse:
        if character.image is None:
            raise HTTPException(404, "立ち絵がありません")
        return FileResponse(character.image)

    async def stream_reply(messages: list[dict]) -> AsyncIterator[bytes]:
        if settings.mock:
            for ch in mock_reply(messages[-1]["content"]):
                yield _line({"type": "delta", "text": ch})
                await asyncio.sleep(0.02)
            yield _line({"type": "done"})
            return
        try:
            stream = await llm.chat.completions.create(model=settings.model, messages=messages, stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield _line({"type": "delta", "text": chunk.choices[0].delta.content})
            yield _line({"type": "done"})
        except Exception as e:  # report every upstream failure to the browser instead of cutting the stream
            log.exception("chat failed")
            yield _line({"type": "error", "message": explain_error(e)})

    @app.post("/api/chat")
    async def chat(req: ChatRequest) -> StreamingResponse:
        if not settings.chat_ready:
            raise HTTPException(503, "DASHSCOPE_API_KEY が設定されていません。.env に書いてから起動し直してください。")
        if req.messages[-1].role != "user":
            raise HTTPException(422, "最後のメッセージは user にしてください")
        history = [m.model_dump() for m in req.messages[-settings.history_turns * 2 :]]
        system = character.system
        recalled = await memory.recall(history[-1]["content"])
        if recalled:
            system += "\n\n# 覚えていること\n" + recalled
        messages = [{"role": "system", "content": system}, *history]
        return StreamingResponse(stream_reply(messages), media_type="application/x-ndjson")

    @app.post("/api/memory", status_code=202)
    async def remember(req: ChatRequest) -> dict:
        if not memory.enabled:
            raise HTTPException(404, "記憶（ReMe）は無効です。.env の REME_URL を設定してください。")
        task = asyncio.create_task(memory.remember([m.model_dump() for m in req.messages]))
        background.add(task)
        task.add_done_callback(background.discard)
        return {"accepted": True}

    @app.post("/api/speak")
    async def speak(req: SpeakRequest) -> Response:
        if not voice.enabled:
            raise HTTPException(404, "声は無効です。README の「声を付ける」を見てください。")
        try:
            audio = await run_in_threadpool(voice.speak, req.text)
        except Exception as e:  # SDK errors vary; surface them as a readable 502
            log.exception("speak failed")
            raise HTTPException(502, f"読み上げに失敗しました: {e}") from e
        return Response(audio, media_type="audio/wav")

    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    else:

        @app.get("/", response_class=HTMLResponse)
        def no_frontend() -> str:
            return "<p>画面がまだビルドされていません。<code>python start.py</code> で起動してください。</p>"

    return app


app = create_app()
