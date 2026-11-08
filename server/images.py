"""Image generation with Qwen-Image (STEP 4 of the chapter). Falls back to a second model when the first one fails."""

import html
import logging
import time
from pathlib import Path

from dashscope import MultiModalConversation

from .studio import JsonStore, StudioError, download, explain, new_id

log = logging.getLogger("ai-partner.images")

DEFAULT_NEGATIVE = "低解像度、低品質、崩れた手、余分な指、崩れた手足、ぼやけた顔、文字、透かし、余分な人物"

RATIOS = [
    {"id": "4:7", "label": "縦長 4:7（本の作例）", "size": "1536*2688"},
    {"id": "9:16", "label": "縦長 9:16", "size": "928*1664"},
    {"id": "3:4", "label": "縦 3:4", "size": "1140*1472"},
    {"id": "1:1", "label": "正方形 1:1", "size": "1328*1328"},
    {"id": "4:3", "label": "横 4:3", "size": "1472*1140"},
    {"id": "16:9", "label": "横長 16:9", "size": "1664*928"},
]
SIZES = {r["id"]: r["size"] for r in RATIOS}


class ImageStudio:
    def __init__(self, api_key: str, mock: bool, directory: Path, model: str, fallback_model: str):
        self.api_key = api_key
        self.mock = mock
        self.store = JsonStore(directory)
        self.model = model
        self.fallback_model = fallback_model

    @property
    def enabled(self) -> bool:
        return self.mock or bool(self.api_key)

    def path(self, item: dict) -> Path:
        return self.store.dir / item["file"]

    def generate(self, prompt: str, negative_prompt: str, ratio: str) -> dict:
        if ratio not in SIZES:
            raise StudioError(f"縦横比 {ratio} には対応していません", status=422)
        item_id = new_id("img")
        self.store.dir.mkdir(parents=True, exist_ok=True)
        target = self.store.dir / item_id
        note = ""
        if self.mock:
            time.sleep(1.2)
            path, model = self._mock(target, prompt, SIZES[ratio]), "mock"
        else:
            try:
                path, model = self._generate(self.model, target, prompt, negative_prompt, SIZES[ratio]), self.model
            except StudioError as e:
                if e.auth or e.status in {400, 422} or not self.fallback_model:
                    raise
                log.warning("%s failed (%s); falling back to %s", self.model, e.message, self.fallback_model)
                path = self._generate(self.fallback_model, target, prompt, negative_prompt, SIZES[ratio])
                model = self.fallback_model
                note = f"{self.model} が失敗したので {self.fallback_model} で描きました（{e.message}）"
        return self.store.save(
            {
                "id": item_id,
                "file": path.name,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "ratio": ratio,
                "model": model,
                "note": note,
                "created_at": time.time(),
            }
        )

    def _generate(self, model: str, target: Path, prompt: str, negative_prompt: str, size: str) -> Path:
        try:
            rsp = MultiModalConversation.call(
                api_key=self.api_key,
                model=model,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                result_format="message",
                stream=False,
                watermark=False,
                prompt_extend=False,
                negative_prompt=negative_prompt or None,
                size=size,
            )
        except Exception as e:  # network and SDK errors; the fallback model gets a chance
            raise StudioError(f"Model Studio に接続できませんでした: {e}") from e
        if rsp.status_code != 200:
            raise explain(rsp.code, rsp.message)
        try:
            url = rsp.output.choices[0].message.content[0]["image"]
        except (AttributeError, IndexError, KeyError, TypeError) as e:
            raise StudioError("画像のURLが返ってきませんでした") from e
        return download(url, target, ".png")

    @staticmethod
    def _mock(target: Path, prompt: str, size: str) -> Path:
        """A pastel placeholder figure; the prompt is kept only as the SVG title."""
        w, h = (int(n) for n in size.split("*"))
        hue = sum(prompt.encode("utf-8")) % 360
        s = min(w / 560, h / 1100)
        cx, top = w / 2, h * 0.5 - 475 * s
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<title>{html.escape(prompt[:200])}</title>
<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="hsl({hue} 45% 97%)"/><stop offset="1" stop-color="hsl({(hue + 40) % 360} 40% 88%)"/>
</linearGradient></defs>
<rect width="{w}" height="{h}" fill="url(#bg)"/>
<ellipse cx="{cx}" cy="{top + 860 * s}" rx="{260 * s}" ry="{34 * s}" fill="hsl({hue} 25% 70%)" opacity=".35"/>
<path d="M{cx - 210 * s} {top + 840 * s} L{cx - 120 * s} {top + 360 * s} Q{cx} {top + 320 * s} {cx + 120 * s} {top + 360 * s}
L{cx + 210 * s} {top + 840 * s} Z" fill="#3b3633"/>
<path d="M{cx - 120 * s} {top + 830 * s} L{cx - 80 * s} {top + 420 * s} L{cx + 80 * s} {top + 420 * s}
L{cx + 120 * s} {top + 830 * s} Z" fill="#fffdf8"/>
<circle cx="{cx}" cy="{top + 230 * s}" r="{120 * s}" fill="#f6e3d3"/>
<path d="M{cx - 135 * s} {top + 260 * s} Q{cx - 150 * s} {top + 80 * s} {cx} {top + 90 * s} Q{cx + 150 * s} {top + 80 * s}
{cx + 135 * s} {top + 260 * s} L{cx + 110 * s} {top + 200 * s} Q{cx} {top + 150 * s} {cx - 110 * s} {top + 200 * s} Z"
fill="#8a5a3c"/>
<path d="M{cx - 34 * s} {top + 360 * s} L{cx} {top + 390 * s} L{cx + 34 * s} {top + 360 * s}" stroke="#7aa7d8"
stroke-width="{16 * s}" fill="none" stroke-linecap="round"/>
<circle cx="{cx}" cy="{top + 400 * s}" r="{12 * s}" fill="#e2b93b"/>
<text x="{cx}" y="{h - 48 * s}" text-anchor="middle" font-family="sans-serif" font-size="{40 * s}"
fill="hsl({hue} 20% 45%)">mock</text>
</svg>"""
        path = target.with_suffix(".svg")
        path.write_text(svg, encoding="utf-8")
        return path
