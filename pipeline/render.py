from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import paths
from .progress import Progress

ROOT = Path(__file__).resolve().parent.parent

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass


def total_frames(props_file: Path) -> tuple[int, int]:
    """Trả về (số frame, fps) theo props.json."""
    props = json.loads(props_file.read_text(encoding="utf-8"))
    fps = int(props["fps"])
    return int(round(float(props["totalSec"]) * fps)), fps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.render",
        description="Render video bằng Remotion (Node chỉ là worker).",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=["short", "long"])
    parser.add_argument("--build", action="store_true", help="Chạy pipeline.build trước")
    parser.add_argument("--still", type=int, help="Chỉ render 1 frame ra PNG")
    parser.add_argument("--preview", type=float, help="Chỉ render N giây đầu")
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--unapproved",
        action="store_true",
        help="Chạy nháp khi script chưa được duyệt (pipeline.review)",
    )
    args = parser.parse_args(argv)

    pid = args.project_id
    project_dir = paths.out_dir(pid)
    if not project_dir.exists():
        raise SystemExit(
            f"Không thấy output: {paths.rel(project_dir)}. "
            "Chạy pipeline.tts/align/build trước."
        )

    fmt = args.format or paths.detect_format(pid)
    if not fmt:
        raise SystemExit("Không xác định được format: truyền --format short|long")

    props_file = paths.props_path(pid, fmt)
    if args.build or not props_file.exists():
        from . import build

        code = build.main(
            ["--project-id", args.project_id, "--format", fmt]
            + (["--unapproved"] if args.unapproved else [])
        )
        if code != 0:
            return code

    node = shutil.which("node")
    if not node:
        raise SystemExit("Không tìm thấy node trong PATH.")

    # Đích của lần render này: PNG cho --still, MP4 cho video/preview.
    if args.still is not None:
        output = paths.stills_dir(pid) / f"{fmt}-{args.still}.png"
    elif args.preview is not None:
        output = paths.preview_path(pid, fmt, args.preview)
    else:
        output = paths.video_path(pid, fmt)
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        node,
        str(ROOT / "video" / "render.mjs"),
        str(project_dir),
        "--props",
        str(props_file),
        "--out",
        str(output),
    ]
    if args.still is not None:
        command += ["--still", str(args.still)]
    if args.preview is not None:
        command += ["--preview", str(args.preview)]
    if args.scale != 1.0:
        command += ["--scale", str(args.scale)]
    if args.concurrency:
        command += ["--concurrency", str(args.concurrency)]
    if args.verbose:
        command += ["--verbose"]

    print("$ " + " ".join(command))

    # Ảnh tĩnh: không có tiến trình để theo dõi.
    if args.still is not None:
        return subprocess.run(command, cwd=ROOT).returncode

    frames, fps = total_frames(props_file)
    if args.preview is not None:
        frames = min(frames, max(1, int(round(args.preview * fps))))
    bar = Progress(frames, "Render", unit="frame")

    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None

    started_detail = "chuẩn bị (bundle + trình duyệt)"
    bar.set(0, detail=started_detail)
    rendered = 0

    for raw in proc.stdout:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("PROGRESS "):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    rendered = int(parts[1])
                    total = int(parts[2])
                except ValueError:
                    continue
                if not rendered:
                    continue
                bar.set(rendered, detail="", total=max(total, rendered))
            continue
        # Dòng log khác của Remotion: in ra để còn debug khi cần.
        print(f"  {line}")

    code = proc.wait()
    if code == 0:
        bar.close("✓ xong")
        if args.preview is None:
            paths.update_status(
                pid,
                video={fmt: {"file": paths.rel(output), "bytes": output.stat().st_size}},
            )
    else:
        bar.close(f"✗ Remotion thoát với mã {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
