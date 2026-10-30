"""Quy ước đường dẫn duy nhất cho source và output.

Repo tách rõ hai loại dữ liệu:

```
projects/<projectId>/              # SOURCE — giữ lâu dài, có thể backup
  project.json                     # style, format mặc định, metadata
  research.md
  scripts/short.json  long.json
  review/factcheck-short.json      # kết quả agent fact-check (theo hash script)

out/<projectId>/                   # OUTPUT — xoá/render lại được bất cứ lúc nào
  status.json                      # tiến độ, thống kê của lần chạy gần nhất
  01-script/                       # bản snapshot để đọc output (không sửa)
    review-short.md                # báo cáo duyệt do pipeline.review sinh
  02-audio/short/  manifest.json  s01.wav …
  03-captions/short/  words.json          # không phụ thuộc khung hình
  03-captions/short/vertical/  captions.srt  captions.ass
  04-props/short/vertical/  props.json
  05-video/  short-vertical.mp4             # <format>-<aspect>.mp4
  06-capcut/short-vertical/  scenes/ audio/ captions.srt draft/   # pipeline.capcut
  99-logs/  brief.txt  repair.txt  stills/
```

``format`` (short|long) là độ dài/luật nội dung; ``aspect`` (vertical|horizontal|
square) là khung hình. Audio và word timing dùng chung cho mọi aspect.

Muốn sửa nội dung thì sửa trong ``projects/``. ``out/01-script`` chỉ là bản
copy do pipeline tạo ra. Mọi module phải lấy đường dẫn qua file này.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
OUT = ROOT / "out"

FORMATS = config.format_ids()

SCRIPT_DIR = "01-script"
AUDIO_DIR = "02-audio"
CAPTIONS_DIR = "03-captions"
PROPS_DIR = "04-props"
VIDEO_DIR = "05-video"
CAPCUT_DIR = "06-capcut"
LOGS_DIR = "99-logs"

PROJECT_CONFIG = "project.json"
STATUS_NAME = "status.json"

# Mặc định dùng config/brand.json (kênh hiện tại). Kênh khác dùng
# config/brands/<brand>.json và khai báo "brand" trong project.json.
DEFAULT_BRAND = "default"
BRANDS_DIR = ROOT / "config" / "brands"


# ---------------------------------------------------------------- project


def source_dir(project_id: str) -> Path:
    return PROJECTS / project_id


def out_dir(project_id: str) -> Path:
    return OUT / project_id


def rel(path: Path) -> str:
    """Đường dẫn tương đối từ gốc repo, dạng dùng trong log và agent."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def project_config_path(project_id: str) -> Path:
    return source_dir(project_id) / PROJECT_CONFIG


def read_project(project_id: str) -> dict[str, Any]:
    path = project_config_path(project_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _merge(old: Any, new: Any) -> Any:
    """Gộp dict lồng nhau, các kiểu khác thì lấy giá trị mới."""
    if isinstance(old, dict) and isinstance(new, dict):
        merged = dict(old)
        for key, value in new.items():
            merged[key] = _merge(old.get(key), value)
        return merged
    return new


def _update_json(path: Path, **fields: Any) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = _merge(data, fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


def update_project(project_id: str, **fields: Any) -> dict[str, Any]:
    """Gộp metadata vào projects/<id>/project.json."""
    path = project_config_path(project_id)
    data = _update_json(path, **fields)
    data.setdefault("projectId", project_id)
    data.setdefault("style", config.DEFAULT_TEMPLATE)
    data.setdefault("createdAt", datetime.now().isoformat(timespec="seconds"))
    data["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


def style_id(project_id: str) -> str:
    """Id template trong config/templates (khoá ``style`` của project.json)."""
    return str(read_project(project_id).get("style") or config.DEFAULT_TEMPLATE)


def resolve_aspect(project_id: str, fmt: str, requested: str | None = None) -> str:
    """Khung hình: tham số CLI > ``aspect`` trong project.json > mặc định của format."""
    chosen = requested or read_project(project_id).get("aspect") or config.default_aspect(fmt)
    config.aspect(chosen)  # báo lỗi rõ nếu id không tồn tại
    return str(chosen)


def brand_id(project_id: str) -> str:
    """Brand profile của project; rỗng = kênh mặc định."""
    return str(read_project(project_id).get("brand") or DEFAULT_BRAND)


def brand_path(project_id: str) -> Path:
    """Trả về file brand của project, kiểm tra tồn tại."""
    bid = brand_id(project_id)
    if bid == DEFAULT_BRAND:
        return ROOT / "config" / "brand.json"
    path = BRANDS_DIR / f"{bid}.json"
    if not path.exists():
        raise SystemExit(
            f"Không thấy brand '{bid}' tại {rel(path)}. "
            f"Tạo file hoặc bỏ 'brand' trong project.json."
        )
    return path


def load_brand(project_id: str) -> dict[str, Any]:
    return json.loads(brand_path(project_id).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- source


def research_path(project_id: str) -> Path:
    return source_dir(project_id) / "research.md"


def script_dir(project_id: str) -> Path:
    return source_dir(project_id) / "scripts"


def script_path(project_id: str, fmt: str) -> Path:
    return script_dir(project_id) / f"{fmt}.json"


def script_hash(project_id: str, fmt: str) -> str:
    """Hash nội dung script, bỏ qua khác biệt khoảng trắng/thứ tự key.

    Dùng để gắn phê duyệt và fact-check với đúng một phiên bản kịch bản.
    """
    data = json.loads(script_path(project_id, fmt).read_text(encoding="utf-8"))
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def review_dir(project_id: str) -> Path:
    return source_dir(project_id) / "review"


def factcheck_path(project_id: str, fmt: str) -> Path:
    return review_dir(project_id) / f"factcheck-{fmt}.json"


def detect_format(project_id: str) -> str | None:
    """Format duy nhất đang có script; None nếu chưa có hoặc có cả hai."""
    found = [fmt for fmt in FORMATS if script_path(project_id, fmt).exists()]
    return found[0] if len(found) == 1 else None


def snapshot(project_id: str) -> None:
    """Copy source research/scripts sang out/<id>/01-script để dễ đọc output.

    Không bao giờ đọc ngược từ snapshot. Đây chỉ là bản mirror một chiều.
    """
    target = out_dir(project_id) / SCRIPT_DIR
    target.mkdir(parents=True, exist_ok=True)
    research = research_path(project_id)
    if research.exists():
        shutil.copy2(research, target / research.name)
    for fmt in FORMATS:
        script = script_path(project_id, fmt)
        if script.exists():
            shutil.copy2(script, target / script.name)


# ---------------------------------------------------------------- output


def review_report_path(project_id: str, fmt: str) -> Path:
    return out_dir(project_id) / SCRIPT_DIR / f"review-{fmt}.md"


def audio_dir(project_id: str, fmt: str) -> Path:
    return out_dir(project_id) / AUDIO_DIR / fmt


def manifest_path(project_id: str, fmt: str) -> Path:
    return audio_dir(project_id, fmt) / "manifest.json"


def audio_path(project_id: str, fmt: str, scene_id: str) -> Path:
    return audio_dir(project_id, fmt) / f"{scene_id}.wav"


def captions_dir(project_id: str, fmt: str) -> Path:
    return out_dir(project_id) / CAPTIONS_DIR / fmt


def words_path(project_id: str, fmt: str) -> Path:
    return captions_dir(project_id, fmt) / "words.json"


def cards_dir(project_id: str, fmt: str, aspect: str) -> Path:
    """SRT/ASS: cách chia card phụ thuộc khung hình nên nằm riêng theo aspect."""
    return captions_dir(project_id, fmt) / aspect


def props_path(project_id: str, fmt: str, aspect: str) -> Path:
    return out_dir(project_id) / PROPS_DIR / fmt / aspect / "props.json"


def video_dir(project_id: str) -> Path:
    return out_dir(project_id) / VIDEO_DIR


def video_path(project_id: str, fmt: str, aspect: str) -> Path:
    return video_dir(project_id) / f"{fmt}-{aspect}.mp4"


def preview_path(project_id: str, fmt: str, aspect: str, seconds: float) -> Path:
    return video_dir(project_id) / f"{fmt}-{aspect}.preview-{seconds:g}s.mp4"


def capcut_dir(project_id: str, fmt: str, aspect: str) -> Path:
    """Bộ file mở bằng CapCut: clip từng cảnh, audio, phụ đề, draft."""
    return out_dir(project_id) / CAPCUT_DIR / f"{fmt}-{aspect}"


def logs_dir(project_id: str) -> Path:
    return out_dir(project_id) / LOGS_DIR


def attempts_dir(project_id: str) -> Path:
    return logs_dir(project_id) / "attempts"


def stills_dir(project_id: str) -> Path:
    return logs_dir(project_id) / "stills"


def still_path(project_id: str, fmt: str, aspect: str, frame: int) -> Path:
    return stills_dir(project_id) / f"{fmt}-{aspect}-{frame}.png"


# ---------------------------------------------------------------- status


def status_path(project_id: str) -> Path:
    return out_dir(project_id) / STATUS_NAME


def read_status(project_id: str) -> dict[str, Any]:
    path = status_path(project_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update_status(project_id: str, **fields: Any) -> dict[str, Any]:
    """Gộp thống kê lần chạy vào out/<id>/status.json."""
    path = status_path(project_id)
    data = _update_json(path, **fields)
    data.setdefault("projectId", project_id)
    data.setdefault("createdAt", datetime.now().isoformat(timespec="seconds"))
    data["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


# ---------------------------------------------------------------- skeleton


def skeleton(project_id: str) -> None:
    """Tạo sẵn thư mục source + output cho một project mới."""
    for directory in (
        script_dir(project_id),
        logs_dir(project_id),
        attempts_dir(project_id),
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if not project_config_path(project_id).exists():
        update_project(project_id)
