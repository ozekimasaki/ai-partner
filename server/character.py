import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

PORTRAIT_EXTS = (".png", ".webp", ".jpg", ".jpeg", ".svg")


@dataclass(frozen=True)
class Character:
    name: str
    system: str
    partner_dir: Path

    def portrait(self) -> Path | None:
        return find_portrait(self.partner_dir)

    def set_portrait(self, source: Path, backup_dir: Path) -> Path:
        """Copy `source` to partner/partner.<ext>; an existing portrait is moved to `backup_dir`, not deleted."""
        current = self.portrait()
        if current is not None:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(current, backup_dir / f"portrait-{time.strftime('%Y%m%d-%H%M%S')}{current.suffix}")
        target = self.partner_dir / f"partner{source.suffix.lower()}"
        shutil.copyfile(source, target)
        return target


def find_portrait(partner_dir: Path) -> Path | None:
    return next((partner_dir / f"partner{ext}" for ext in PORTRAIT_EXTS if (partner_dir / f"partner{ext}").is_file()), None)


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
    return Character(name=name_override or guess_name(system), system=system, partner_dir=partner_dir)


def load_image_presets(partner_dir: Path) -> list[dict]:
    """partner_image.txt first, then each "## 見出し" section of image_presets.md."""
    presets = []
    base = partner_dir / "partner_image.txt"
    if base.is_file():
        presets.append({"label": "立ち絵（partner_image.txt）", "prompt": base.read_text(encoding="utf-8").strip()})
    extra = partner_dir / "image_presets.md"
    if extra.is_file():
        label, lines = None, []
        for line in [*extra.read_text(encoding="utf-8").splitlines(), "## "]:
            if line.startswith("## "):
                if label and "".join(lines).strip():
                    presets.append({"label": label, "prompt": "\n".join(lines).strip()})
                label, lines = line[3:].strip(), []
            elif label is not None:
                lines.append(line)
    return presets
