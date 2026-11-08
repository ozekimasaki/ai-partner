import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Literal

import dashscope
import openai
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .character import load_character, load_image_presets
from .config import ROOT, Settings, load_settings
from .images import DEFAULT_NEGATIVE, RATIOS, ImageStudio
from .memory import Memory
from .studio import StudioError
from .videos import DURATIONS, VideoStudio
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


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=MAX_CHARS)
    negative_prompt: str = Field(default="", max_length=MAX_CHARS)
    ratio: str = "4:7"


class VideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=MAX_CHARS)
    source: str = "portrait"
    duration: int = 5


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
    dashscope.base_http_api_url = settings.native_base_url
    images = ImageStudio(
        settings.api_key,
        settings.mock,
        settings.data_dir / "images",
        settings.image_model,
        settings.image_fallback_model,
    )
    videos = VideoStudio(settings.api_key, settings.mock, settings.data_dir / "videos", settings.video_model)

    app = FastAPI(title="ai-partner")
    background: set[asyncio.Task] = set()

    @app.exception_handler(StudioError)
    async def studio_error(_, e: StudioError) -> JSONResponse:
        return JSONResponse({"detail": e.message}, status_code=e.status)

    @app.get("/api/partner")
    def partner_info() -> dict:
        portrait = character.portrait()
        return {
            "name": character.name,
            "model": "mock" if settings.mock else settings.model,
            "ready": settings.chat_ready,
            "mock": settings.mock,
            "image": portrait is not None,
            "image_version": int(portrait.stat().st_mtime) if portrait else 0,
            "memory": memory.enabled,
            "voice": voice.enabled,
            "env_path": str(ROOT / ".env"),
        }

    @app.get("/api/partner/image")
    def partner_image() -> FileResponse:
        portrait = character.portrait()
        if portrait is None:
            raise HTTPException(404, "立ち絵がありません")
        return FileResponse(portrait, headers={"Cache-Control": "no-cache"})

    def require_studio(enabled: bool) -> None:
        if not enabled:
            raise HTTPException(503, "DASHSCOPE_API_KEY が設定されていません。.env に書いてから起動し直してください。")

    @app.get("/api/images/options")
    def image_options() -> dict:
        return {
            "presets": load_image_presets(settings.partner_dir),
            "negative_prompt": DEFAULT_NEGATIVE,
            "ratios": RATIOS,
            "model": settings.image_model,
            "fallback_model": settings.image_fallback_model,
        }

    @app.get("/api/images")
    def list_images() -> list[dict]:
        return images.store.list()

    @app.post("/api/images")
    async def create_image(req: ImageRequest) -> dict:
        require_studio(images.enabled)
        return await run_in_threadpool(images.generate, req.prompt, req.negative_prompt, req.ratio)

    @app.delete("/api/images/{item_id}")
    def delete_image(item_id: str) -> dict:
        if not images.store.delete(item_id):
            raise HTTPException(404, "画像が見つかりません")
        return {"deleted": item_id}

    @app.post("/api/images/{item_id}/portrait")
    def set_portrait(item_id: str) -> dict:
        item = images.store.get(item_id)
        if item is None:
            raise HTTPException(404, "画像が見つかりません")
        character.set_portrait(images.path(item), settings.data_dir / "portrait-backup")
        return partner_info()

    @app.get("/api/videos/options")
    def video_options() -> dict:
        return {"durations": DURATIONS, "model": settings.video_model}

    @app.get("/api/videos")
    async def list_videos() -> list[dict]:
        return await run_in_threadpool(videos.list)

    @app.post("/api/videos")
    async def create_video(req: VideoRequest) -> dict:
        require_studio(videos.enabled)
        if req.source == "portrait":
            first_frame = character.portrait()
            if first_frame is None:
                raise HTTPException(422, "立ち絵がまだありません。画像生成タブで描いて「立ち絵に設定」してください。")
        else:
            item = images.store.get(req.source)
            if item is None:
                raise HTTPException(404, "元の画像が見つかりません")
            first_frame = images.path(item)
        if first_frame.suffix == ".svg" and not settings.mock:
            raise HTTPException(422, "モックで作った画像（SVG）は動画にできません。実際に描いた画像を選んでください。")
        return await run_in_threadpool(videos.create, req.prompt, first_frame, req.duration)

    @app.get("/api/videos/{item_id}")
    async def get_video(item_id: str) -> dict:
        item = await run_in_threadpool(videos.refresh, item_id)
        if item is None:
            raise HTTPException(404, "動画が見つかりません")
        return item

    @app.delete("/api/videos/{item_id}")
    def delete_video(item_id: str) -> dict:
        if not videos.store.delete(item_id):
            raise HTTPException(404, "動画が見つかりません")
        return {"deleted": item_id}

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

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.data_dir), name="media")
    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    else:

        @app.get("/", response_class=HTMLResponse)
        def no_frontend() -> str:
            return "<p>画面がまだビルドされていません。<code>python start.py</code> で起動してください。</p>"

    return app


app = create_app()
