import re
from dataclasses import dataclass
from pathlib import Path

IMAGE_NAMES = ("partner.png", "partner.webp", "partner.jpg", "partner.jpeg")


@dataclass(frozen=True)
class Character:
    name: str
    system: str
    image: Path | None


def guess_name(system: str) -> str:
    """Take the first sentence of the first non-heading line, e.g. "桜草メイ。北海道出身" -> "桜草メイ"."""
    for line in system.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[。、,，.\s（(]", line, maxsplit=1)[0]
        if 0 < len(name) <= 20:
            return name
        break
    return "パートナー"


def load_character(partner_dir: Path, name_override: str = "") -> Character:
    system = (partner_dir / "partner.md").read_text(encoding="utf-8").strip()
    image = next((partner_dir / n for n in IMAGE_NAMES if (partner_dir / n).is_file()), None)
    return Character(name=name_override or guess_name(system), system=system, image=image)
