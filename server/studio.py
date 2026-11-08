"""Shared pieces for image and video generation: errors, ids, and the JSON-per-item store under data/."""

import json
import secrets
import time
from pathlib import Path

import httpx


class StudioError(Exception):
    def __init__(self, message: str, *, status: int = 502, auth: bool = False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.auth = auth


def explain(code: str | None, message: str | None) -> StudioError:
    code = code or ""
    if code in {"InvalidApiKey", "Unauthorized"} or "api key" in (message or "").lower():
        return StudioError(
            "APIキーが受け付けられませんでした。.env の DASHSCOPE_API_KEY がシンガポールのキーか確かめてください。",
            status=401,
            auth=True,
        )
    if code == "Arrearage":
        return StudioError("アカウントの残高か無料枠が足りないようです。Model Studio の利用状況を確かめてください。")
    if code == "DataInspectionFailed":
        return StudioError("プロンプトか画像が内容審査で止められました。表現を変えて試してください。", status=400)
    if code.startswith("Throttling"):
        return StudioError("混み合っているか、呼び出し回数の上限です。少し待ってから試してください。", status=429)
    if code in {"ModelNotFound", "Model.AccessDenied"}:
        return StudioError(f"モデルが使えませんでした（{code}）。リージョンとモデルIDを確かめてください。")
    return StudioError(f"Model Studio がエラーを返しました（{code or '不明'}）: {message or '詳細なし'}")


def new_id(prefix: str) -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"


def download(url: str, target_without_ext: Path, default_ext: str) -> Path:
    try:
        r = httpx.get(url, timeout=120, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise StudioError(f"できたファイルを取りにいけませんでした: {e}") from e
    ctype = r.headers.get("content-type", "")
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "video/mp4": ".mp4"}.get(
        ctype.split(";")[0].strip(), default_ext
    )
    path = target_without_ext.with_suffix(ext)
    path.write_bytes(r.content)
    return path


class JsonStore:
    def __init__(self, directory: Path):
        self.dir = directory

    def save(self, item: dict) -> dict:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        return item

    def get(self, item_id: str) -> dict | None:
        if not item_id.replace("-", "").isalnum():
            return None
        path = self.dir / f"{item_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def list(self) -> list[dict]:
        if not self.dir.is_dir():
            return []
        items = [json.loads(p.read_text(encoding="utf-8")) for p in self.dir.glob("*.json")]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)

    def delete(self, item_id: str) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        for name in (item.get("file"), item.get("poster")):
            if name:
                (self.dir / name).unlink(missing_ok=True)
        (self.dir / f"{item_id}.json").unlink(missing_ok=True)
        return True
