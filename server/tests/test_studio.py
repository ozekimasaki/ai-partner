"""Image and video generation against a fake dashscope SDK (no API key needed)."""

import shutil
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from server import images as images_module
from server import videos as videos_module
from server.app import create_app
from server.config import ROOT
from server.tests.test_app import settings


def response(status_code=200, code="", message="", output=None):
    return SimpleNamespace(status_code=status_code, code=code, message=message, output=output)


class Output(dict):
    """Mimics the SDK's DictMixin output: attribute access plus dict.get."""

    __getattr__ = dict.get


def image_output(url):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=[{"image": url}]))])


@pytest.fixture
def partner_dir(tmp_path):
    d = tmp_path / "partner"
    shutil.copytree(ROOT / "partner", d)
    return d


@pytest.fixture
def fake_download(monkeypatch):
    def download(url, target, default_ext):
        path = target.with_suffix(default_ext)
        path.write_bytes(f"downloaded:{url}".encode())
        return path

    monkeypatch.setattr(images_module, "download", download)
    monkeypatch.setattr(videos_module, "download", download)


def make_client(partner_dir, tmp_path, **overrides):
    s = replace(settings(), partner_dir=partner_dir, data_dir=tmp_path / "data", **overrides)
    return TestClient(create_app(s))


def test_image_options_include_partner_presets(partner_dir, tmp_path):
    options = make_client(partner_dir, tmp_path).get("/api/images/options").json()
    labels = [p["label"] for p in options["presets"]]
    assert labels[0] == "立ち絵（partner_image.txt）"
    assert "慌てた顔" in labels and "春の服" in labels
    assert options["presets"][0]["prompt"].startswith("アニメ調の全身イラスト。")
    assert options["model"] == "qwen-image-3.0-pro"
    assert {"id": "9:16", "label": "縦長 9:16", "size": "928*1664"} in options["ratios"]


def test_image_generation_and_set_as_portrait(partner_dir, tmp_path, monkeypatch, fake_download):
    calls = []

    def call(**kw):
        calls.append(kw)
        return response(output=image_output("https://example.com/a.png"))

    monkeypatch.setattr(images_module, "MultiModalConversation", SimpleNamespace(call=call))
    client = make_client(partner_dir, tmp_path)
    r = client.post("/api/images", json={"prompt": "温室のメイ", "negative_prompt": "文字", "ratio": "9:16"})
    assert r.status_code == 200, r.text
    item = r.json()
    assert item["model"] == "qwen-image-3.0-pro" and item["note"] == ""
    assert calls[0]["model"] == "qwen-image-3.0-pro"
    assert calls[0]["size"] == "928*1664"
    assert calls[0]["negative_prompt"] == "文字"
    assert calls[0]["prompt_extend"] is False
    assert client.get(f"/media/images/{item['file']}").content == b"downloaded:https://example.com/a.png"
    assert [i["id"] for i in client.get("/api/images").json()] == [item["id"]]

    info = client.post(f"/api/images/{item['id']}/portrait").json()
    assert info["image"] is True and info["image_version"] > 0
    assert (partner_dir / "partner.png").read_bytes() == b"downloaded:https://example.com/a.png"

    client.post(f"/api/images/{item['id']}/portrait")
    assert len(list((tmp_path / "data" / "portrait-backup").iterdir())) == 1

    assert client.delete(f"/api/images/{item['id']}").status_code == 200
    assert client.get("/api/images").json() == []


def test_image_falls_back_to_second_model(partner_dir, tmp_path, monkeypatch, fake_download):
    models = []

    def call(**kw):
        models.append(kw["model"])
        if kw["model"] == "qwen-image-3.0-pro":
            return response(500, code="InternalError", message="boom")
        return response(output=image_output("https://example.com/b.png"))

    monkeypatch.setattr(images_module, "MultiModalConversation", SimpleNamespace(call=call))
    item = make_client(partner_dir, tmp_path).post("/api/images", json={"prompt": "x"}).json()
    assert models == ["qwen-image-3.0-pro", "qwen-image-2.0-pro"]
    assert item["model"] == "qwen-image-2.0-pro"
    assert "qwen-image-2.0-pro で描きました" in item["note"]


def test_image_auth_error_does_not_fall_back(partner_dir, tmp_path, monkeypatch):
    models = []

    def call(**kw):
        models.append(kw["model"])
        return response(401, code="InvalidApiKey", message="Invalid API-key provided.")

    monkeypatch.setattr(images_module, "MultiModalConversation", SimpleNamespace(call=call))
    r = make_client(partner_dir, tmp_path).post("/api/images", json={"prompt": "x"})
    assert r.status_code == 401
    assert "APIキー" in r.json()["detail"]
    assert models == ["qwen-image-3.0-pro"]


def test_image_rejects_unknown_ratio(partner_dir, tmp_path):
    r = make_client(partner_dir, tmp_path, mock=True).post("/api/images", json={"prompt": "x", "ratio": "2:1"})
    assert r.status_code == 422


def test_studio_needs_key(partner_dir, tmp_path):
    client = make_client(partner_dir, tmp_path, api_key="")
    assert client.post("/api/images", json={"prompt": "x"}).status_code == 503
    assert client.post("/api/videos", json={"prompt": "x"}).status_code == 503


def test_mock_image_is_svg(partner_dir, tmp_path):
    client = make_client(partner_dir, tmp_path, api_key="", mock=True)
    item = client.post("/api/images", json={"prompt": "<温室>", "ratio": "1:1"}).json()
    assert item["file"].endswith(".svg") and item["model"] == "mock"
    svg = client.get(f"/media/images/{item['file']}").text
    assert "&lt;温室&gt;" in svg


def test_video_task_is_polled_until_done(partner_dir, tmp_path, monkeypatch, fake_download):
    (partner_dir / "partner.png").write_bytes(b"png")
    created, statuses = [], ["PENDING", "RUNNING", "SUCCEEDED"]

    def async_call(**kw):
        created.append(kw)
        return response(output=SimpleNamespace(task_id="task-1", task_status="PENDING"))

    def fetch(task_id, api_key=None):
        assert task_id == "task-1" and api_key == "test-key"
        return response(output=Output(task_status=statuses.pop(0), video_url="https://example.com/v.mp4"))

    monkeypatch.setattr(videos_module, "VideoSynthesis", SimpleNamespace(async_call=async_call, fetch=fetch))
    client = make_client(partner_dir, tmp_path)
    item = client.post("/api/videos", json={"prompt": "振り返って鈴が鳴る", "duration": 5}).json()
    assert item["status"] == "pending"
    kw = created[0]
    assert kw["model"] == "wan3.0-video" and kw["duration"] == 5
    assert kw["media"][0]["type"] == "first_frame"
    assert kw["media"][0]["url"].startswith("file://") and kw["media"][0]["url"].endswith("partner.png")

    assert client.get(f"/api/videos/{item['id']}").json()["status"] == "pending"
    assert client.get(f"/api/videos/{item['id']}").json()["status"] == "running"
    done = client.get(f"/api/videos/{item['id']}").json()
    assert done["status"] == "succeeded" and done["file"].endswith(".mp4")
    assert client.get(f"/media/videos/{done['file']}").content == b"downloaded:https://example.com/v.mp4"
    assert client.get(f"/media/videos/{done['poster']}").content == b"png"
    assert client.get(f"/api/videos/{item['id']}").json()["status"] == "succeeded"


def test_video_failure_is_reported(partner_dir, tmp_path, monkeypatch):
    (partner_dir / "partner.png").write_bytes(b"png")
    monkeypatch.setattr(
        videos_module,
        "VideoSynthesis",
        SimpleNamespace(
            async_call=lambda **kw: response(output=SimpleNamespace(task_id="t", task_status="PENDING")),
            fetch=lambda task_id, api_key=None: response(
                output=Output(task_status="FAILED", message="内容審査で止められました")
            ),
        ),
    )
    client = make_client(partner_dir, tmp_path)
    item = client.post("/api/videos", json={"prompt": "x"}).json()
    failed = client.get(f"/api/videos/{item['id']}").json()
    assert failed["status"] == "failed" and failed["error"] == "内容審査で止められました"


def test_video_needs_portrait_and_valid_duration(partner_dir, tmp_path):
    client = make_client(partner_dir, tmp_path, mock=True)
    r = client.post("/api/videos", json={"prompt": "x"})
    assert r.status_code == 422 and "立ち絵" in r.json()["detail"]
    img = client.post("/api/images", json={"prompt": "x"}).json()
    assert client.post("/api/videos", json={"prompt": "x", "source": img["id"], "duration": 7}).status_code == 422


def test_mock_video_progresses(partner_dir, tmp_path, monkeypatch):
    client = make_client(partner_dir, tmp_path, api_key="", mock=True)
    img = client.post("/api/images", json={"prompt": "x"}).json()
    item = client.post("/api/videos", json={"prompt": "手を振る", "source": img["id"]}).json()
    assert item["model"] == "mock"
    real_time = time.time
    monkeypatch.setattr(videos_module.time, "time", lambda: real_time() + 4)
    assert client.get(f"/api/videos/{item['id']}").json()["status"] == "running"
    monkeypatch.setattr(videos_module.time, "time", lambda: real_time() + 20)
    assert client.get("/api/videos").json()[0]["status"] == "succeeded"
