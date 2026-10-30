from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from . import config, llm, paths, validate

ROOT = Path(__file__).resolve().parent.parent

# Console Windows mặc định có thể là cp1252 → vỡ tiếng Việt khi in.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


# ---------------------------------------------------------------- helpers


def slugify(text: str, max_len: int = 40) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text or "video")[:max_len].strip("-")


def parse_json_text(raw: str) -> dict[str, Any]:
    """Bóc JSON khỏi text có thể còn code fence / lời dẫn / dấu phẩy thừa."""
    text = raw.strip().lstrip("\ufeff")
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text).strip()

    start = text.find("{")
    if start < 0:
        raise ValueError(f"Không tìm thấy JSON trong output:\n{text[:400]}")

    candidate = text[start:]
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        # Thử sửa lỗi phổ biến: dấu phẩy trước } hoặc ].
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            obj, _ = json.JSONDecoder().raw_decode(candidate)

    if not isinstance(obj, dict):
        raise ValueError("JSON gốc phải là một object")
    return obj


def rel(path: Path) -> str:
    return paths.rel(path)


def step(title: str) -> float:
    print(f"\n▶ {title}")
    return time.perf_counter()


def done(started: float) -> None:
    print(f"  ✓ {time.perf_counter() - started:.1f}s")


def load_script(
    target: Path,
    run: llm.AgentRun,
    *,
    before_mtime: int | None,
    attempt_file: Path,
) -> dict[str, Any] | None:
    """Ưu tiên file agent tự ghi; fallback sang parse stdout."""
    attempt_file.parent.mkdir(parents=True, exist_ok=True)
    attempt_file.write_text(run.text, encoding="utf-8")

    changed = target.exists() and (
        before_mtime is None or target.stat().st_mtime_ns != before_mtime
    )
    if changed:
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            try:
                return parse_json_text(target.read_text(encoding="utf-8"))
            except ValueError:
                pass

    try:
        data = parse_json_text(run.text)
    except ValueError:
        return None

    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


# ---------------------------------------------------------------- pipeline


def ensure_research(
    pid: str,
    brief: dict[str, str],
    *,
    model: str | None,
    skip: bool,
) -> Path:
    research = paths.research_path(pid)
    if skip:
        if not research.exists():
            raise SystemExit(
                f"--skip-research nhưng không thấy {rel(research)}. Chạy lại không skip."
            )
        print(f"  · dùng lại {rel(research)}")
        return research

    brief_path = paths.logs_dir(pid) / "brief.txt"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(
        "\n".join(f"{k}: {v}" for k, v in brief.items()), encoding="utf-8"
    )

    started = step("Research")
    run = llm.run_agent(
        "researcher",
        f"projectId={pid} brief={rel(brief_path)}",
        cwd=ROOT,
        model=model,
        timeout=900,
    )
    done(started)
    attempts = paths.attempts_dir(pid)
    attempts.mkdir(parents=True, exist_ok=True)
    (attempts / "research-chat.txt").write_text(run.text, encoding="utf-8")

    if not research.exists() or research.stat().st_size < 200:
        raise SystemExit(
            "Agent không ghi research.md (hoặc file quá ngắn). "
            f"Output cuối:\n{run.text[:800]}"
        )
    paths.snapshot(pid)
    return research


def generate_script(
    pid: str,
    fmt: str,
    *,
    research: Path | None,
    source: Path | None,
    agent: str,
    model: str | None,
    max_repairs: int,
) -> dict[str, Any]:
    target = paths.script_path(pid, fmt)
    target.parent.mkdir(parents=True, exist_ok=True)
    attempts = paths.attempts_dir(pid)

    if source is not None:
        base = f"projectId={pid} format={fmt} source={rel(source)} out={rel(target)}"
    else:
        assert research is not None
        base = f"projectId={pid} format={fmt} research={rel(research)} out={rel(target)}"

    script: dict[str, Any] | None = None
    errors: list[str] = []

    for attempt in range(max_repairs + 1):
        if attempt == 0:
            message = base
            started = step(f"Viết kịch bản ({fmt}) bằng agent '{agent}'")
        else:
            invalid = paths.logs_dir(pid) / "invalid.json"
            invalid.write_text(
                json.dumps(script, ensure_ascii=False, indent=2) if script else "{}",
                encoding="utf-8",
            )
            repair = paths.logs_dir(pid) / "repair.txt"
            repair.write_text(
                validate.as_repair_prompt(errors)
                if errors
                else "Output trước không phải JSON hợp lệ. Trả lại toàn bộ object JSON.",
                encoding="utf-8",
            )
            message = (
                f"projectId={pid} format={fmt} fix={rel(repair)} out={rel(target)}"
            )
            started = step(f"Repair lần {attempt}/{max_repairs} ({len(errors)} lỗi)")

        before = target.stat().st_mtime_ns if target.exists() else None
        run = llm.run_agent(agent, message, cwd=ROOT, model=model, timeout=900)
        done(started)

        script = load_script(
            target,
            run,
            before_mtime=before,
            attempt_file=attempts / f"script-{fmt}-{attempt + 1}.txt",
        )

        if script is None:
            errors = [
                "[json] Agent không ghi file JSON hợp lệ và output chat cũng không parse được"
            ]
            print("  ✗ không đọc được JSON")
            continue

        errors = validate.validate(script, fmt=fmt, project_id=pid)
        if not errors:
            print(f"  ✓ hợp lệ · {len(script.get('scenes', []))} scene")
            # Chỉ cảnh báo, không đưa vào repair: heuristic chữ số bắt nhầm
            # ("3 mẹo"), ép agent sẽ khiến nó bịa claim cho có.
            for issue in validate.claim_issues(script):
                print(f"    ! {issue}")
            break

        print(f"  ✗ {len(errors)} lỗi:")
        for err in errors[:10]:
            print(f"    - {err}")
        if len(errors) > 10:
            print(f"    … và {len(errors) - 10} lỗi khác")

    if errors:
        repair = paths.logs_dir(pid) / "repair.txt"
        repair.write_text(validate.as_repair_prompt(errors), encoding="utf-8")
        print("\n✗ Kịch bản vẫn không hợp lệ:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(f"\nXem {rel(repair)} để biết chi tiết.", file=sys.stderr)
        raise SystemExit(1)

    assert script is not None
    # voice/music là cấu hình runtime (brand config), không phải nội dung.
    script.pop("voice", None)
    script.pop("music", None)
    target.write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths.snapshot(pid)
    return script


def factcheck_and_report(pid: str, fmt: str, *, model: str | None, skip: bool) -> None:
    """Fact-check ngay sau khi viết, rồi in báo cáo để người duyệt đọc."""
    from . import review

    if not skip:
        try:
            review.run_factcheck(pid, fmt, model=model)
        except llm.AgentError as exc:
            print(f"\n! Fact-check thất bại: {exc}", file=sys.stderr)
            print(
                f"  Chạy lại: python -m pipeline.review --project-id {pid} "
                f"--format {fmt} --factcheck",
                file=sys.stderr,
            )
    review.write_report(pid, fmt, links=True)
    print(
        "\nĐọc báo cáo, sửa script nếu cần, rồi duyệt:\n"
        f"  python -m pipeline.review --project-id {pid} --format {fmt} --approve"
    )


def summarize(script: dict[str, Any]) -> None:
    scenes = script.get("scenes", [])
    total = sum(validate._scene_seconds(s) for s in scenes)
    counts: dict[str, int] = {}
    for scene in scenes:
        counts[scene["type"]] = counts.get(scene["type"], 0) + 1

    print("\n" + "─" * 60)
    print(f"  {script['meta']['title']}")
    print(f"  format: {script['format']}  ·  {len(scenes)} scene  ·  ~{total:.0f}s")
    print("  " + ", ".join(f"{k}×{v}" for k, v in sorted(counts.items())))
    print("─" * 60)


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.script",
        description="Research + viết kịch bản video bằng OpenCode agent.",
    )
    parser.add_argument("--topic", help="Chủ đề video (bắt buộc nếu tạo mới)")
    parser.add_argument("--format", choices=config.format_ids(), default="long")
    parser.add_argument("--project-id", help="Slug dự án; mặc định sinh từ chủ đề")
    parser.add_argument("--audience", default="người quan tâm AI và công nghệ")
    parser.add_argument("--angle", default="")
    parser.add_argument("--language", default="vi")
    parser.add_argument(
        "--style",
        default="tech-explainer",
        help="Style trình bày trong video/src/styles (mặc định tech-explainer)",
    )
    parser.add_argument(
        "--brand",
        help="Brand profile trong config/brands (mặc định config/brand.json)",
    )
    parser.add_argument("--skip-research", action="store_true")
    parser.add_argument("--research-only", action="store_true")
    parser.add_argument(
        "--from-long",
        action="store_true",
        help="Tạo short từ script.long.json đã có (không research lại)",
    )
    parser.add_argument("--model", help="provider/model, mặc định theo OpenCode")
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument(
        "--skip-factcheck",
        action="store_true",
        help="Không chạy agent factchecker sau khi viết script",
    )
    args = parser.parse_args(argv)

    if args.from_long:
        if not args.project_id:
            parser.error("--from-long cần --project-id")
        pid = args.project_id
        source = paths.script_path(pid, "long")
        if not source.exists():
            parser.error(f"Không thấy {rel(source)}")
        paths.update_project(pid, formats=["long", "short"])
        script = generate_script(
            pid,
            "short",
            research=None,
            source=source,
            agent="shortener",
            model=args.model,
            max_repairs=args.max_repairs,
        )
        print(f"\n✓ Đã ghi {rel(paths.script_path(pid, 'short'))}")
        summarize(script)
        factcheck_and_report(pid, "short", model=args.model, skip=args.skip_factcheck)
        return 0

    if not args.topic:
        parser.error("thiếu --topic (hoặc dùng --from-long)")

    pid = args.project_id or f"{slugify(args.topic)}-{date.today().isoformat()}"
    paths.skeleton(pid)
    paths.update_project(
        pid,
        topic=args.topic,
        language=args.language,
        formats=[args.format],
        defaultFormat=args.format,
        style=args.style,
        **({"brand": args.brand} if args.brand else {}),
    )

    print(
        f"Project: {pid}\n"
        f"Nguồn:  {rel(paths.source_dir(pid))}\n"
        f"Output: {rel(paths.out_dir(pid))}"
    )

    brief = {
        "topic": args.topic,
        "format": args.format,
        "language": args.language,
        "audience": args.audience,
        "angle": args.angle or "(tự chọn góc tốt nhất)",
        "channel": "AI và công nghệ",
    }

    research = ensure_research(
        pid,
        brief,
        model=args.model,
        skip=args.skip_research,
    )
    print(f"  · research: {rel(research)} ({research.stat().st_size:,} bytes)")

    if args.research_only:
        print("\n✓ Chỉ research theo yêu cầu.")
        return 0

    script = generate_script(
        pid,
        args.format,
        research=research,
        source=None,
        agent="scriptwriter",
        model=args.model,
        max_repairs=args.max_repairs,
    )

    print(f"\n✓ Đã ghi {rel(paths.script_path(pid, args.format))}")
    summarize(script)
    factcheck_and_report(pid, args.format, model=args.model, skip=args.skip_factcheck)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
