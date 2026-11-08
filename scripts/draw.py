"""partner/partner_image.txt から立ち絵を描いて partner/partner.png に保存する（原稿 STEP 4 の draw.py）。

使い方: python scripts/draw.py
"""

import os
import sys
from pathlib import Path

import dashscope
import requests
from dashscope import MultiModalConversation
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

workspace = os.getenv("DASHSCOPE_WORKSPACE_ID", "").strip()
if workspace:
    dashscope.base_http_api_url = f"https://{workspace}.ap-southeast-1.maas.aliyuncs.com/api/v1"
else:
    dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"

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
    negative_prompt="low resolution, low quality, distorted hands, extra fingers, "
    "malformed limbs, blurry face, text, watermark, extra people",
    size="1536*2688",
)
if response.status_code != 200:
    sys.exit(f"描けませんでした: {response.code} {response.message}")
url = response.output.choices[0].message.content[0]["image"]
out = partner_dir / "partner.png"
out.write_bytes(requests.get(url, timeout=60).content)
print(f"保存しました: {out}")
