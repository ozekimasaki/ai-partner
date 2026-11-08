"""Text-to-speech with a voice designed in the Beijing region. Enabled only when the Beijing key and workspace are set."""

import logging
import threading
from pathlib import Path

import dashscope

log = logging.getLogger("ai-partner.voice")

VOICE_ID_FILE = ".voice_id"
PREVIEW_TEXT = "Welcome home. How was your day today?"
SAMPLE_RATE = 24000


class Voice:
    def __init__(self, api_key: str, workspace: str, model: str, partner_dir: Path, voice_id: str = ""):
        self.api_key = api_key
        self.workspace = workspace
        self.model = model
        self.partner_dir = partner_dir
        self._voice_id = voice_id
        self._lock = threading.Lock()
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.workspace)

    def _get_client(self):
        if self._client is None:
            self._client = dashscope.Client(api_key=self.api_key, workspace=self.workspace, region="cn-beijing")
        return self._client

    def _voice(self) -> str:
        with self._lock:
            if self._voice_id:
                return self._voice_id
            cache = self.partner_dir / VOICE_ID_FILE
            if cache.is_file() and cache.read_text(encoding="utf-8").strip():
                self._voice_id = cache.read_text(encoding="utf-8").strip()
                return self._voice_id
            prompt = (self.partner_dir / "partner_voice.txt").read_text(encoding="utf-8")
            designed = self._get_client().audio.voice_design.create(
                target_model=self.model,
                prefix="partner",
                voice_prompt=prompt,
                preview_text=PREVIEW_TEXT,
                language_hints=["en"],
                parameters={"sample_rate": SAMPLE_RATE, "response_format": "wav"},
            )
            self._voice_id = designed.voice_id
            cache.write_text(self._voice_id, encoding="utf-8")
            log.info("designed a new voice: %s (saved to %s)", self._voice_id, cache)
            return self._voice_id

    def speak(self, text: str) -> bytes:
        return self._get_client().audio.tts.synthesize(
            text, model=self.model, voice=self._voice(), format="wav", sample_rate=SAMPLE_RATE
        )
