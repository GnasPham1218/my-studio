from __future__ import annotations

import argparse
import sys
import time

from . import align, build, capcut, config, paths, render, tts

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass

STAGES = ("TTS", "Align", "Build props", "Render")


def stage(name: str, index: int | None = None) -> float:
    counter = f"[{index}/{len(STAGES)}] " if index else ""
    print(f"\n{'=' * 62}\n▶ {counter}{name}\n{'=' * 62}", flush=True)
    return time.perf_counter()


def done(name: str, started: float) -> None:
    print(f"✓ {name} · {time.perf_counter() - started:.1f}s", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.make",
        description="Chạy toàn bộ pipeline cho một project đã có script: "
        "TTS → align → build → render.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=config.format_ids(), default="short")
    parser.add_argument(
        "--aspect",
        help="Khung hình, có thể nhiều giá trị cách nhau bằng dấu phẩy "
        f"({', '.join(config.aspect_ids())}). Audio và căn thời gian dùng chung.",
    )
    parser.add_argument("--provider", choices=["vieneu", "omnivoice"], help="Ghi đè engine TTS")
    parser.add_argument("--voice", help="[vieneu] Ghi đè giọng preset")
    parser.add_argument("--mode", choices=["auto", "design", "clone"], help="[omnivoice] Kiểu giọng")
    parser.add_argument("--ref-audio", help="[omnivoice] File mẫu để clone")
    parser.add_argument("--ref-text", help="[omnivoice] Lời thoại của file mẫu")
    parser.add_argument("--instruct", help="[omnivoice] Mô tả giọng cho mode design")
    parser.add_argument("--speed", type=float, help="[omnivoice] Hệ số tốc độ (>1 nhanh hơn)")
    parser.add_argument("--num-step", type=int, help="[omnivoice] Số bước giải mã")
    parser.add_argument("--force-tts", action="store_true")
    parser.add_argument("--force-align", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument(
        "--template",
        help="Ghi đè template của project (id trong config/templates)",
    )
    parser.add_argument(
        "--unapproved",
        action="store_true",
        help="Chạy nháp khi script chưa được duyệt (pipeline.review)",
    )
    parser.add_argument("--still", type=int, help="Render 1 frame PNG thay vì video")
    parser.add_argument("--preview", type=float, help="Chỉ render N giây đầu")
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument(
        "--capcut",
        action="store_true",
        help="Sau khi render, xuất thêm bộ file + draft CapCut (pipeline.capcut)",
    )
    args = parser.parse_args(argv)

    base: list[str] = ["--project-id", args.project_id, "--format", args.format]
    # align không đọc nội dung script để hiển thị nên không cần cổng duyệt.
    gate = ["--unapproved"] if args.unapproved else []
    template = ["--template", args.template] if args.template else []
    requested = [item.strip() for item in (args.aspect or "").split(",") if item.strip()]
    aspects = [
        paths.resolve_aspect(args.project_id, args.format, item)
        for item in requested or [None]
    ]

    overall = time.perf_counter()
    channel = paths.load_brand(args.project_id)["channel"]["name"]
    print(
        f"{channel} · project '{args.project_id}' · {args.format} · {', '.join(aspects)}",
        flush=True,
    )

    started = stage("TTS", 1)
    tts_args = list(base) + gate
    if args.provider:
        tts_args += ["--provider", args.provider]
    if args.voice:
        tts_args += ["--voice", args.voice]
    if args.mode:
        tts_args += ["--mode", args.mode]
    if args.ref_audio:
        tts_args += ["--ref-audio", args.ref_audio]
    if args.ref_text:
        tts_args += ["--ref-text", args.ref_text]
    if args.instruct:
        tts_args += ["--instruct", args.instruct]
    if args.speed:
        tts_args += ["--speed", str(args.speed)]
    if args.num_step:
        tts_args += ["--num-step", str(args.num_step)]
    if args.force_tts:
        tts_args += ["--force"]
    if tts.main(tts_args) != 0:
        return 1
    done("TTS", started)

    started = stage("Align", 2)
    align_args = list(base) + (["--force"] if args.force_align else [])
    if align.main(align_args) != 0:
        return 1
    done("Align", started)

    # Audio + căn thời gian dùng chung; chỉ build/render lặp lại theo từng khung hình.
    started = stage("Build props", 3)
    for aspect_id in aspects:
        if build.main(base + gate + template + ["--aspect", aspect_id]) != 0:
            return 1
    done("Build props", started)

    if args.skip_render:
        print("\n✓ Bỏ qua render theo yêu cầu.")
        return 0

    started = stage("Render", 4)
    for aspect_id in aspects:
        render_args: list[str] = [
            "--project-id",
            args.project_id,
            "--format",
            args.format,
            "--aspect",
            aspect_id,
        ]
        if args.still is not None:
            render_args += ["--still", str(args.still)]
        if args.preview is not None:
            render_args += ["--preview", str(args.preview)]
        if args.scale != 1.0:
            render_args += ["--scale", str(args.scale)]
        code = render.main(render_args)
        if code != 0:
            return code
        if args.capcut and args.still is None and args.preview is None:
            code = capcut.main(
                ["--project-id", args.project_id, "--format", args.format, "--aspect", aspect_id]
                + gate
            )
            if code != 0:
                return code
    done("Render", started)
    print(f"\n★ Hoàn tất toàn bộ sau {time.perf_counter() - overall:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
