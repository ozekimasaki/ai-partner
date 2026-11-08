"""partner/partner_image.txt から立ち絵を描いて partner/partner.png に保存する（原稿 STEP 4 の draw.py）。

使い方: python scripts/draw.py
画面の「画像生成」タブでも同じことができます。
"""

import os
import sys
from pathlib import Path

import dashscope
import httpx
from dashscope import MultiModalConversation
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

workspace = os.getenv("DASHSCOPE_WORKSPACE_ID", "").strip()
host = f"https://{workspace}.ap-southeast-1.maas.aliyuncs.com" if workspace else "https://dashscope-intl.aliyuncs.com"
dashscope.base_http_api_url = host + "/api/v1"

partner_dir = ROOT / os.getenv("PARTNER_DIR", "partner")
prompt = (partner_dir / "partner_image.txt").read_text(encoding="utf-8")

response = MultiModalConversation.call(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model=os.getenv("PARTNER_IMAGE_MODEL", "qwen-image-3.0-pro"),
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    result_format="message",
    stream=False,
    watermark=False,
    prompt_extend=False,
    negative_prompt="低解像度、低品質、崩れた手、余分な指、崩れた手足、ぼやけた顔、文字、透かし、余分な人物",
    size="1536*2688",
)
if response.status_code != 200:
    sys.exit(f"描けませんでした: {response.code} {response.message}")
url = response.output.choices[0].message.content[0]["image"]
out = partner_dir / "partner.png"
out.write_bytes(httpx.get(url, timeout=60).content)
print(f"保存しました: {out}")
