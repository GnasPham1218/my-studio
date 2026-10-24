"""Sửa lỗi fact-check: MobileBERT (2020) và DistilBERT (2019), không phải 2018."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "ai-nho-tren-may"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATCHES = {
    "short": {
        "s04": {
            "narration": "Năm 2019 và 2020, DistilBERT rồi MobileBERT đã chạy ngay trên điện thoại.",
            "onScreenText": "2019-2020: DistilBERT, MobileBERT",
            "emphasis": ["2019", "2020", "DistilBERT", "MobileBERT"],
        }
    },
    "long": {
        "s06": {
            "narration": (
                "Năm hai nghìn không trăm mười chín, DistilBERT và TinyBERT ra đời. "
                "Năm hai nghìn hai mươi, đến lượt MobileBERT. "
                "Mô hình nhỏ, chạy ngay trên điện thoại, làm tốt một việc cụ thể."
            ),
            "bullets": [
                "2019: DistilBERT, TinyBERT",
                "2020: MobileBERT",
                "Chạy ngay trên điện thoại",
            ],
            "emphasis": ["DistilBERT", "MobileBERT"],
        }
    },
}


def main() -> int:
    changed = 0
    for fmt, scenes in PATCHES.items():
        path = PROJECT / "scripts" / f"{fmt}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        by_id = {scene["id"]: scene for scene in data["scenes"]}
        for sid, fields in scenes.items():
            scene = by_id.get(sid)
            if scene is None:
                raise SystemExit(f"Không thấy {sid} trong {path.name}")
            before = dict(scene)
            scene.update(fields)
            if scene != before:
                changed += 1
                print(f"  ✓ {path.name} · {sid}")
                print(f"    cũ : {before.get('narration')}")
                print(f"    mới: {scene['narration']}")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"\n{changed} scene đã sửa")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
