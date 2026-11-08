import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

SINGAPORE_HOST = "https://{workspace}.ap-southeast-1.maas.aliyuncs.com"
SINGAPORE_DEFAULT_HOST = "https://dashscope-intl.aliyuncs.com"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _flag(name: str) -> bool:
    return _env(name).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    native_base_url: str
    model: str
    partner_dir: Path
    data_dir: Path
    partner_name: str
    user_name: str
    history_turns: int
    mock: bool
    reme_url: str
    beijing_api_key: str
    beijing_workspace: str
    voice_model: str
    voice_id: str
    image_model: str = "qwen-image-3.0-pro"
    image_fallback_model: str = "qwen-image-2.0-pro"
    video_model: str = "wan3.0-video"

    @property
    def chat_ready(self) -> bool:
        return self.mock or bool(self.api_key)

    @property
    def memory_enabled(self) -> bool:
        return bool(self.reme_url)

    @property
    def voice_configured(self) -> bool:
        return bool(self.beijing_api_key and self.beijing_workspace)


def _host() -> str:
    workspace = _env("DASHSCOPE_WORKSPACE_ID")
    return SINGAPORE_HOST.format(workspace=workspace) if workspace else SINGAPORE_DEFAULT_HOST


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    host = _host()
    return Settings(
        api_key=_env("DASHSCOPE_API_KEY"),
        base_url=_env("DASHSCOPE_BASE_URL") or f"{host}/compatible-mode/v1",
        native_base_url=f"{host}/api/v1",
        model=_env("PARTNER_MODEL", "qwen-plus-character-ja"),
        partner_dir=_resolve(_env("PARTNER_DIR", "partner")),
        data_dir=_resolve(_env("DATA_DIR", "data")),
        partner_name=_env("PARTNER_NAME"),
        user_name=_env("USER_NAME", "あなた"),
        history_turns=int(_env("HISTORY_TURNS", "10") or 10),
        mock=_flag("PARTNER_MOCK"),
        reme_url=_env("REME_URL").rstrip("/"),
        beijing_api_key=_env("DASHSCOPE_API_KEY_BEIJING"),
        beijing_workspace=_env("DASHSCOPE_WORKSPACE_ID_BEIJING"),
        voice_model=_env("PARTNER_VOICE_MODEL", "qwen-audio-3.1-tts-flash"),
        voice_id=_env("PARTNER_VOICE_ID"),
        image_model=_env("PARTNER_IMAGE_MODEL", "qwen-image-3.0-pro"),
        image_fallback_model=_env("PARTNER_IMAGE_FALLBACK_MODEL", "qwen-image-2.0-pro"),
        video_model=_env("PARTNER_VIDEO_MODEL", "wan3.0-video"),
    )
