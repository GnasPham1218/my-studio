"""Dòng lệnh: python -m pipeline.analyze <run|infer|compare|show|fonts>."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from .. import config
from ..progress import Progress
from . import compare, infer, measure, store, text

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass


def write_template(template_id: str, template: dict[str, Any], *, force: bool) -> Path:
    """Ghi config/templates/<id>.json; không ghi đè bản đã sửa tay nếu thiếu --force."""
    target = config.template_path(template_id)
    if target.exists() and not force:
        target = store.reference_dir(template_id) / "template.generated.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def print_summary(analysis: dict[str, Any]) -> None:
    video = analysis["video"]
    print(
        f"\n  Video: {video['width']}x{video['height']} @ {video['fps']}fps · "
        f"{video['durationSec']}s · khung hình gần nhất: {video['aspect']}"
    )
    pacing = analysis.get("pacing") or {}
    if pacing:
        print(
            f"  Nhịp: {len(analysis['cuts'])} cảnh · trung bình {pacing['avgSceneSec']}s/cảnh · "
            f"{pacing['cutsPerMinute']} cắt/phút"
        )
    background = analysis["background"]
    print(f"  Nền: {background['kind']} {background['color']} (độ lệch {background['spread']})")
    print("  Màu: " + "  ".join(f"{role} {value}" for role, value in analysis["palette"].items()))
    cap = analysis.get("caption")
    if cap:
        print(
            f"  Phụ đề: đáy {cap['bottomRel']:.3f}H · cỡ {cap['fontSizeRel']:.4f} cạnh ngắn · "
            f"rộng {cap['maxWidthRel']:.2f}W · {cap['linesPerCard']:.1f} dòng/card · "
            f"tin cậy {cap['confidence']}"
        )
        print(
            f"    chữ {cap['textColor']} · nhấn {cap['highlightColor']} ({cap['highlightShare']:.0%}) · "
            f"viền {cap['outlineColor']} ({cap['outlineShare']:.0%}) · "
            f"thẻ {cap['cardColor']} ({cap['cardShare']:.0%})"
        )
    else:
        print("  Phụ đề: không tìm thấy")
    chrome = analysis["chrome"]
    print(f"  Chrome: số scene {'có' if chrome['sceneIndex'] else 'không'} · "
          f"watermark {'có' if chrome['watermark'] else 'không'}")
    audio = analysis["audio"]
    print(f"  Âm thanh: {audio['loudnessDbfs']} dBFS · nhạc nền {audio['hasMusicBed']} · nhịp {audio['tempoBpm']}")


def cmd_run(args: argparse.Namespace) -> int:
    video = Path(args.video)
    if not video.exists():
        raise SystemExit(f"Không thấy video: {video}")
    use_ocr = not args.no_ocr
    if use_ocr and not text.ocr_available():
        print(
            "  ! Chưa cài OCR nên không đo được phụ đề/watermark/màu chữ.\n"
            "    Cài: uv pip install --python .venv\\Scripts\\python.exe -r requirements-analyze.txt\n"
            "    Hoặc chạy tiếp với --no-ocr để chỉ đo nền, màu, nhịp.",
            flush=True,
        )

    bar: Progress | None = None

    def on_progress(done: int, total: int) -> None:
        nonlocal bar
        if bar is None:
            bar = Progress(total, "OCR", unit="frame")
        bar.set(done, detail="", total=total)

    print(f"Phân tích {video.name} …", flush=True)
    analysis, samples = measure.measure_video(
        video,
        sample_every=args.sample_every,
        max_ocr=args.ocr_frames,
        max_seconds=args.max_seconds,
        use_ocr=use_ocr,
        progress=on_progress,
    )
    if bar:
        bar.close()

    picks = measure.keyframes(samples, analysis["cuts"], limit=12)
    frames_dir = store.reference_dir(args.id) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("kf-*.png"):
        old.unlink()
    for index, (_, image) in enumerate(picks):
        Image.fromarray(image).save(frames_dir / f"kf-{index:02d}.png")
    store.contact_sheet(
        [image for _, image in picks],
        store.contact_sheet_path(args.id),
        labels=[f"{t:.1f}s" for t, _ in picks],
    )
    path = store.save_analysis(args.id, analysis)
    print_summary(analysis)
    print(f"\n  Số đo:        {path.relative_to(config.ROOT).as_posix()}")
    print(f"  Contact sheet: {store.contact_sheet_path(args.id).relative_to(config.ROOT).as_posix()}")
    return emit_template(args.id, analysis, video.name, force=args.force)


def emit_template(template_id: str, analysis: dict[str, Any], source: str, *, force: bool) -> int:
    template, notes = infer.infer_template(analysis, template_id, source_name=source)
    target = write_template(template_id, template, force=force)
    rel = target.relative_to(config.ROOT).as_posix()
    if target == config.template_path(template_id):
        print(f"\n✓ Template: {rel}")
    else:
        print(
            f"\n✓ Template '{template_id}' đã tồn tại và không bị ghi đè. Bản mới: {rel}\n"
            "  (dùng --force để thay thế bản đang dùng)"
        )
    if notes:
        print("\nCần xem lại bằng tay:")
        for note in notes:
            print(f"  - {note}")
    print(
        f"\nÁp dụng lên project có sẵn: python -m pipeline.make --project-id <id> --template {template_id}"
        f"\nKiểm tra độ giống:           python -m pipeline.analyze compare --id {template_id} --project-id <id>"
    )
    return 0


def cmd_infer(args: argparse.Namespace) -> int:
    analysis = store.load_analysis(args.id)
    return emit_template(args.id, analysis, analysis["video"]["file"], force=args.force)


def cmd_show(args: argparse.Namespace) -> int:
    print_summary(store.load_analysis(args.id))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    report = compare.run_compare(
        args.id,
        args.project_id,
        fmt=args.format,
        aspect=args.aspect,
        max_frames=args.frames,
        use_ocr=not args.no_ocr,
    )
    print(f"\nĐộ giống template '{args.id}' với video mẫu: {report['score']}/100 "
          f"(project {report['project']}, khung {report['aspect']})\n")
    for metric in report["metrics"]:
        mark = "✓" if metric["ok"] else "✗"
        note = f"  [{metric['note']}]" if metric["note"] else ""
        print(f"  {mark} {metric['name']}: mẫu={metric['reference']} · template={metric['ours']}{note}")
    sheet = store.reference_dir(args.id) / "compare" / "compare_sheet.png"
    if sheet.exists():
        print(f"\n  Ảnh đối chiếu: {sheet.relative_to(config.ROOT).as_posix()}")
    return 0


def cmd_fonts(_: argparse.Namespace) -> int:
    package = json.loads((config.ROOT / "video" / "package.json").read_text(encoding="utf-8"))
    names = sorted(
        name.split("/", 1)[1] for name in package.get("dependencies", {}) if name.startswith("@fontsource/")
    )
    print("Font đã cài (có thể điền vào template.fonts, đúng tên hiển thị của font):")
    for name in names:
        print(f"  - {name.replace('-', ' ').title()}   (@fontsource/{name})")
    print("\nThêm font: cd video && npm i @fontsource/<tên>, rồi import css trong video/src/index.ts.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.analyze",
        description="Phân tích video mẫu để tạo template giao diện (config/templates).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Phân tích video, ghi số đo và template")
    run.add_argument("video", help="Đường dẫn video mẫu (mp4/mov/webm...)")
    run.add_argument("--id", required=True, help="Id template (chữ thường, số, dấu gạch ngang)")
    run.add_argument("--sample-every", type=float, default=0.5, help="Giây giữa hai frame mẫu")
    run.add_argument("--ocr-frames", type=int, default=80, help="Số frame tối đa đưa vào OCR")
    run.add_argument("--max-seconds", type=float, help="Chỉ phân tích N giây đầu")
    run.add_argument("--no-ocr", action="store_true", help="Bỏ OCR (chỉ đo nền, màu, nhịp)")
    run.add_argument("--force", action="store_true", help="Ghi đè template đã có")
    run.set_defaults(func=cmd_run)

    redo = sub.add_parser("infer", help="Suy lại template từ số đo đã lưu (không đọc lại video)")
    redo.add_argument("--id", required=True)
    redo.add_argument("--force", action="store_true")
    redo.set_defaults(func=cmd_infer)

    show = sub.add_parser("show", help="In số đo đã lưu")
    show.add_argument("--id", required=True)
    show.set_defaults(func=cmd_show)

    cmp = sub.add_parser("compare", help="Render project mẫu bằng template rồi so với video mẫu")
    cmp.add_argument("--id", required=True)
    cmp.add_argument("--project-id", required=True)
    cmp.add_argument("--format", choices=config.format_ids())
    cmp.add_argument("--aspect", choices=config.aspect_ids())
    cmp.add_argument("--frames", type=int, default=8)
    cmp.add_argument("--no-ocr", action="store_true")
    cmp.set_defaults(func=cmd_compare)

    fonts = sub.add_parser("fonts", help="Liệt kê font đã cài")
    fonts.set_defaults(func=cmd_fonts)

    args = parser.parse_args(argv)
    pattern = config.template_schema()["properties"]["id"]["pattern"]
    if getattr(args, "id", None) and not re.fullmatch(pattern, args.id):
        parser.error(f"--id phải khớp {pattern} (chữ thường, số, dấu gạch ngang)")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
