"""Image-to-video with Wan (STEP 4 of the chapter). Generation is an async task: create, then poll until it finishes."""

import logging
import shutil
import time
from pathlib import Path

from dashscope import VideoSynthesis

from .studio import JsonStore, StudioError, download, explain, new_id

log = logging.getLogger("ai-partner.videos")

ACTIVE = {"pending", "running"}
STATUS = {
    "PENDING": "pending",
    "RUNNING": "running",
    "SUCCEEDED": "succeeded",
    "FAILED": "failed",
    "CANCELED": "failed",
    "UNKNOWN": "failed",
}
DURATIONS = [5, 10, 15]
MOCK_PENDING_SECONDS = 2.5
MOCK_TOTAL_SECONDS = 8.0


class VideoStudio:
    def __init__(self, api_key: str, mock: bool, directory: Path, model: str):
        self.api_key = api_key
        self.mock = mock
        self.store = JsonStore(directory)
        self.model = model

    @property
    def enabled(self) -> bool:
        return self.mock or bool(self.api_key)

    def create(self, prompt: str, first_frame: Path, duration: int) -> dict:
        if duration not in DURATIONS:
            raise StudioError(f"長さは {DURATIONS} 秒から選んでください", status=422)
        item_id = new_id("vid")
        self.store.dir.mkdir(parents=True, exist_ok=True)
        poster = self.store.dir / f"{item_id}-poster{first_frame.suffix}"
        shutil.copyfile(first_frame, poster)
        task_id = ""
        if not self.mock:
            try:
                rsp = VideoSynthesis.async_call(
                    api_key=self.api_key,
                    model=self.model,
                    prompt=prompt,
                    media=[{"type": "first_frame", "url": first_frame.resolve().as_uri()}],
                    duration=duration,
                    watermark=False,
                )
            except Exception as e:  # upload of the first frame and the HTTP call can both fail here
                poster.unlink(missing_ok=True)
                raise StudioError(f"動画のタスクを作れませんでした: {e}") from e
            if rsp.status_code != 200:
                poster.unlink(missing_ok=True)
                raise explain(rsp.code, rsp.message)
            task_id = rsp.output.task_id
        return self.store.save(
            {
                "id": item_id,
                "task_id": task_id,
                "prompt": prompt,
                "duration": duration,
                "model": "mock" if self.mock else self.model,
                "status": "pending",
                "error": "",
                "file": "",
                "poster": poster.name,
                "created_at": time.time(),
                "finished_at": None,
            }
        )

    def refresh(self, item_id: str) -> dict | None:
        item = self.store.get(item_id)
        if item is None or item["status"] not in ACTIVE:
            return item
        if item["model"] == "mock":
            elapsed = time.time() - item["created_at"]
            if elapsed >= MOCK_TOTAL_SECONDS:
                item.update(status="succeeded", finished_at=time.time())
            else:
                item["status"] = "pending" if elapsed < MOCK_PENDING_SECONDS else "running"
            return self.store.save(item)
        try:
            rsp = VideoSynthesis.fetch(item["task_id"], api_key=self.api_key)
        except Exception as e:  # transient network errors: keep the task and try again on the next poll
            log.warning("fetch %s failed: %s", item["task_id"], e)
            return item
        if rsp.status_code != 200:
            err = explain(rsp.code, rsp.message)
            item.update(status="failed", error=err.message, finished_at=time.time())
            return self.store.save(item)
        status = STATUS.get(rsp.output.task_status, "running")
        if status == "succeeded":
            try:
                path = download(rsp.output.video_url, self.store.dir / item_id, ".mp4")
                item.update(file=path.name)
            except StudioError as e:
                status = "failed"
                item["error"] = e.message
        elif status == "failed":
            item["error"] = rsp.output.get("message") or rsp.message or "動画を作れませんでした"
        item["status"] = status
        if status not in ACTIVE:
            item["finished_at"] = time.time()
        return self.store.save(item)

    def list(self) -> list[dict]:
        return [self.refresh(i["id"]) if i["status"] in ACTIVE else i for i in self.store.list()]
