from types import SimpleNamespace

from server import voice as voice_module
from server.voice import Voice


class FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.designed = []
        self.spoken = []
        self.audio = SimpleNamespace(
            voice_design=SimpleNamespace(create=self._create),
            tts=SimpleNamespace(synthesize=self._synthesize),
        )

    def _create(self, **kwargs):
        self.designed.append(kwargs)
        return SimpleNamespace(voice_id="qwen-audio-vd-partner-1")

    def _synthesize(self, text, **kwargs):
        self.spoken.append((text, kwargs))
        return b"RIFF....WAVE"


def test_voice_is_designed_once_and_cached(tmp_path, monkeypatch):
    (tmp_path / "partner_voice.txt").write_text("A soft voice.", encoding="utf-8")
    clients = []
    monkeypatch.setattr(
        voice_module, "dashscope", SimpleNamespace(Client=lambda **kw: clients.append(FakeClient(**kw)) or clients[-1])
    )
    v = Voice("bj-key", "ws-bj", "qwen-audio-3.1-tts-flash", tmp_path)
    assert v.enabled
    assert v.speak("おかえりなさい") == b"RIFF....WAVE"
    assert v.speak("もう一回") == b"RIFF....WAVE"
    client = clients[0]
    assert client.kwargs == {"api_key": "bj-key", "workspace": "ws-bj", "region": "cn-beijing"}
    assert len(client.designed) == 1
    assert client.designed[0]["voice_prompt"] == "A soft voice."
    assert (tmp_path / ".voice_id").read_text(encoding="utf-8") == "qwen-audio-vd-partner-1"
    assert client.spoken[0][1]["voice"] == "qwen-audio-vd-partner-1"

    again = Voice("bj-key", "ws-bj", "qwen-audio-3.1-tts-flash", tmp_path)
    again.speak("三回目")
    assert len(clients[1].designed) == 0


def test_voice_disabled_without_keys(tmp_path):
    assert not Voice("", "w", "m", tmp_path).enabled
    assert not Voice("k", "", "m", tmp_path).enabled
