import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

SINGAPORE_BASE_URL = "https://{workspace}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
SINGAPORE_DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _flag(name: str) -> bool:
    return _env(name).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    partner_dir: Path
    partner_name: str
    user_name: str
    history_turns: int
    mock: bool
    reme_url: str
    beijing_api_key: str
    beijing_workspace: str
    voice_model: str
    voice_id: str

    @property
    def chat_ready(self) -> bool:
        return self.mock or bool(self.api_key)

    @property
    def memory_enabled(self) -> bool:
        return bool(self.reme_url)

    @property
    def voice_configured(self) -> bool:
        return bool(self.beijing_api_key and self.beijing_workspace)


def _base_url() -> str:
    explicit = _env("DASHSCOPE_BASE_URL")
    if explicit:
        return explicit
    workspace = _env("DASHSCOPE_WORKSPACE_ID")
    if workspace:
        return SINGAPORE_BASE_URL.format(workspace=workspace)
    return SINGAPORE_DEFAULT_BASE_URL


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    partner_dir = Path(_env("PARTNER_DIR", "partner"))
    if not partner_dir.is_absolute():
        partner_dir = ROOT / partner_dir
    return Settings(
        api_key=_env("DASHSCOPE_API_KEY"),
        base_url=_base_url(),
        model=_env("PARTNER_MODEL", "qwen-plus-character-ja"),
        partner_dir=partner_dir,
        partner_name=_env("PARTNER_NAME"),
        user_name=_env("USER_NAME", "あなた"),
        history_turns=int(_env("HISTORY_TURNS", "10") or 10),
        mock=_flag("PARTNER_MOCK"),
        reme_url=_env("REME_URL").rstrip("/"),
        beijing_api_key=_env("DASHSCOPE_API_KEY_BEIJING"),
        beijing_workspace=_env("DASHSCOPE_WORKSPACE_ID_BEIJING"),
        voice_model=_env("PARTNER_VOICE_MODEL", "qwen-audio-3.1-tts-flash"),
        voice_id=_env("PARTNER_VOICE_ID"),
    )
