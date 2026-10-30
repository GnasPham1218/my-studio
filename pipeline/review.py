"""Duyệt nội dung: báo cáo, fact-check, phê duyệt và cổng chặn trước TTS.

Luồng:

```
pipeline.script  ──► scripts/<fmt>.json
pipeline.review --factcheck  ──► review/factcheck-<fmt>.json (agent factchecker)
pipeline.review              ──► out/<id>/01-script/review-<fmt>.md (đọc để duyệt)
pipeline.review --approve    ──► project.json: review.<fmt> = approved + hash
pipeline.tts / build         ──► từ chối chạy nếu chưa duyệt hoặc script đã sửa
```

Phê duyệt gắn với hash nội dung script: sửa bất kỳ chữ nào sau khi duyệt thì
phải duyệt lại. Fact-check cũng gắn hash nên biết khi nào đã lỗi thời.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config, llm, paths, validate

ROOT = Path(__file__).resolve().parent.parent

VERDICTS = ("ok", "doubtful", "wrong", "unsupported")
VERDICT_ICON = {"ok": "✓", "doubtful": "?", "wrong": "✗", "unsupported": "∅"}

# Nhiều trang chặn user-agent mặc định của urllib, trả 403 dù link vẫn sống.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- gate


def approval(pid: str, fmt: str) -> dict[str, Any]:
    return (paths.read_project(pid).get("review") or {}).get(fmt) or {}


def approval_problem(pid: str, fmt: str) -> str | None:
    """Lý do script chưa được phép đi tiếp; None nếu đã duyệt đúng phiên bản."""
    record = approval(pid, fmt)
    status = record.get("status")
    if status == "rejected":
        note = record.get("note")
        return f"script {fmt} đã bị từ chối{f': {note}' if note else ''}"
    if status != "approved":
        return f"script {fmt} chưa được duyệt"
    if record.get("scriptHash") != paths.script_hash(pid, fmt):
        return f"script {fmt} đã bị sửa sau khi duyệt ({record.get('approvedAt')})"
    return None


def require_approved(pid: str, fmt: str, *, bypass: bool = False) -> None:
    """Cổng chặn: gọi ở đầu các bước tốn công (TTS) hoặc đọc nội dung (build)."""
    problem = approval_problem(pid, fmt)
    if problem is None:
        return
    if bypass:
        print(f"  ! bỏ qua cổng duyệt (--unapproved): {problem}", flush=True)
        return
    raise SystemExit(
        f"✗ {problem}.\n"
        f"  Xem & duyệt: python -m pipeline.review --project-id {pid} --format {fmt}\n"
        f"  Chạy nháp không cần duyệt: thêm --unapproved"
    )


# ---------------------------------------------------------------- links


BLOCKED_PREFIX = "bị chặn"


def check_url(url: str, timeout: float = 10.0) -> str:
    """'ok', 'bị chặn …' (server sống nhưng chặn bot) hoặc mô tả lỗi.

    Thử HEAD trước, trang nào không hỗ trợ thì GET.
    """
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url, method=method, headers={"User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout):
                return "ok"
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue
            # Vòng chuyển hướng (thường do cookie/consent): server vẫn trả lời.
            if 300 <= exc.code < 400:
                return "ok"
            if exc.code in (401, 403, 429):
                return f"{BLOCKED_PREFIX} (HTTP {exc.code}), mở bằng trình duyệt để kiểm"
            return f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            return f"lỗi mạng: {str(reason)[:80]}"
    return "không rõ"


def link_mark(status: str) -> str:
    if status == "ok":
        return "✓"
    return "?" if status.startswith(BLOCKED_PREFIX) else "!"


def check_sources(sources: list[dict[str, Any]]) -> list[tuple[int, str, str]]:
    """[(số thứ tự, url, trạng thái)] cho mọi nguồn có url."""
    targets = [
        (index, source["url"])
        for index, source in enumerate(sources, start=1)
        if source.get("url")
    ]
    if not targets:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda item: check_url(item[1]), targets))
    return [(index, url, status) for (index, url), status in zip(targets, statuses)]


# ---------------------------------------------------------------- factcheck


def load_factcheck(pid: str, fmt: str) -> dict[str, Any] | None:
    path = paths.factcheck_path(pid, fmt)
    return load_json(path) if path.exists() else None


def factcheck_errors(data: dict[str, Any]) -> list[str]:
    items = data.get("items")
    if not isinstance(items, list):
        return ["thiếu mảng 'items'"]
    errors: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] không phải object")
            continue
        for key in ("sceneId", "claim", "verdict"):
            if not item.get(key):
                errors.append(f"items[{index}] thiếu '{key}'")
        if item.get("verdict") and item["verdict"] not in VERDICTS:
            errors.append(f"items[{index}] verdict '{item['verdict']}' không hợp lệ")
    return errors


def run_factcheck(pid: str, fmt: str, *, model: str | None = None) -> dict[str, Any]:
    """Gọi agent factchecker, kiểm cấu trúc, đóng dấu hash script."""
    from .script import load_script

    script = paths.script_path(pid, fmt)
    if not script.exists():
        raise SystemExit(f"Không thấy {paths.rel(script)}")
    research = paths.research_path(pid)
    target = paths.factcheck_path(pid, fmt)
    target.parent.mkdir(parents=True, exist_ok=True)

    message = (
        f"projectId={pid} format={fmt} script={paths.rel(script)} "
        f"research={paths.rel(research) if research.exists() else 'none'} "
        f"out={paths.rel(target)}"
    )
    print(f"\n▶ Fact-check ({fmt}) bằng agent 'factchecker'", flush=True)
    before = target.stat().st_mtime_ns if target.exists() else None
    script_hash = paths.script_hash(pid, fmt)
    run = llm.run_agent("factchecker", message, cwd=ROOT, model=model, timeout=1200)
    print(f"  ✓ {run.duration_sec:.1f}s")

    data = load_script(
        target,
        run,
        before_mtime=before,
        attempt_file=paths.attempts_dir(pid) / f"factcheck-{fmt}.txt",
    )
    if data is None:
        raise SystemExit("Agent factchecker không ghi được JSON hợp lệ.")
    errors = factcheck_errors(data)
    if errors:
        raise SystemExit(
            "Kết quả fact-check sai cấu trúc:\n  - " + "\n  - ".join(errors)
        )

    # Hash do Python đóng dấu, không tin agent tự ghi.
    data["scriptHash"] = script_hash
    data["checkedAt"] = now()
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def verdict_counts(data: dict[str, Any] | None) -> dict[str, int]:
    counts = {verdict: 0 for verdict in VERDICTS}
    for item in (data or {}).get("items") or []:
        if item.get("verdict") in counts:
            counts[item["verdict"]] += 1
    return counts


# ---------------------------------------------------------------- report


def collect(pid: str, fmt: str, *, links: bool) -> dict[str, Any]:
    script = load_json(paths.script_path(pid, fmt))
    factcheck = load_factcheck(pid, fmt)
    current_hash = paths.script_hash(pid, fmt)
    return {
        "script": script,
        "hash": current_hash,
        "errors": validate.validate(script, fmt=fmt, project_id=pid),
        "claimIssues": validate.claim_issues(script),
        "links": check_sources(script.get("meta", {}).get("sources") or []) if links else None,
        "factcheck": factcheck,
        "factcheckStale": bool(factcheck) and factcheck.get("scriptHash") != current_hash,
        "approval": approval(pid, fmt),
        "approvalProblem": approval_problem(pid, fmt),
    }


def render_report(pid: str, fmt: str, state: dict[str, Any]) -> str:
    script = state["script"]
    meta = script.get("meta") or {}
    sources = meta.get("sources") or []
    factcheck = state["factcheck"]
    counts = verdict_counts(factcheck)
    by_scene: dict[str, list[dict[str, Any]]] = {}
    for item in (factcheck or {}).get("items") or []:
        by_scene.setdefault(item.get("sceneId", "?"), []).append(item)

    lines = [
        f"# Duyệt: {meta.get('title', pid)} · {fmt}",
        "",
        f"- Project: `{pid}` · script hash `{state['hash']}`",
        f"- Trạng thái: **{state['approvalProblem'] or 'đã duyệt đúng phiên bản này'}**",
    ]
    if factcheck:
        stale = " · **LỖI THỜI (script đã đổi)**" if state["factcheckStale"] else ""
        lines.append(
            f"- Fact-check {factcheck.get('checkedAt', '?')}{stale}: "
            + " · ".join(f"{VERDICT_ICON[v]} {v} {counts[v]}" for v in VERDICTS)
        )
        if factcheck.get("summary"):
            lines.append(f"- Tóm tắt: {factcheck['summary']}")
    else:
        lines.append("- Fact-check: **chưa chạy**")
    lines.append("")

    if state["errors"]:
        lines += ["## Lỗi validate (phải sửa)", ""]
        lines += [f"- {err}" for err in state["errors"]]
        lines.append("")
    if state["claimIssues"]:
        lines += ["## Cảnh báo: số liệu chưa gắn nguồn", ""]
        lines += [f"- {issue}" for issue in state["claimIssues"]]
        lines.append("")
    if state["links"] is not None:
        lines += ["## Nguồn", ""]
        status_of = {index: status for index, _, status in state["links"]}
        for index, source in enumerate(sources, start=1):
            status = status_of.get(index, "không có url")
            mark = link_mark(status)
            url = f" — {source['url']}" if source.get("url") else ""
            lines.append(f"{index}. {mark} {source.get('title', '?')}{url} ({status})")
        lines.append("")

    lines += ["## Từng scene", ""]
    for scene in script.get("scenes") or []:
        sid = scene.get("id", "?")
        seconds = validate._scene_seconds(scene)
        lines.append(f"### {sid} · {scene.get('type')} · ~{seconds:.1f}s")
        lines.append("")
        lines.append(f"> {validate._scene_text(scene)}")
        lines.append("")
        if scene.get("onScreenText"):
            lines.append(f"- Màn hình: {scene['onScreenText']}")
        for bullet in scene.get("bullets") or []:
            lines.append(f"- Bullet: {bullet}")
        if scene.get("stat"):
            stat = scene["stat"]
            lines.append(
                f"- Stat: {stat.get('value')} {stat.get('unit', '')} · {stat.get('label', '')}".rstrip(" ·")
            )
        for claim in scene.get("claims") or []:
            index = claim.get("source", 0)
            title = sources[index - 1].get("title", "?") if 0 < index <= len(sources) else "NGUỒN KHÔNG TỒN TẠI"
            lines.append(f"- Claim: {claim.get('text')} — [{index}] {title}")
        for item in by_scene.get(sid, []):
            verdict = item.get("verdict", "?")
            lines.append(
                f"- Fact-check {VERDICT_ICON.get(verdict, '?')} **{verdict}**: {item.get('claim')}"
            )
            if item.get("evidence"):
                lines.append(f"  - Bằng chứng: {item['evidence']}")
            if item.get("source"):
                lines.append(f"  - Nguồn: {item['source']}")
            if item.get("fix"):
                lines.append(f"  - Gợi ý sửa: {item['fix']}")
        lines.append("")
    return "\n".join(lines)


def print_summary(pid: str, fmt: str, state: dict[str, Any], report: Path) -> None:
    factcheck = state["factcheck"]
    counts = verdict_counts(factcheck)
    print(f"\n{'─' * 60}")
    print(f"  {state['script'].get('meta', {}).get('title', pid)} · {fmt}")
    print(f"  Trạng thái: {state['approvalProblem'] or 'đã duyệt'}")
    print(f"  Validate:   {len(state['errors'])} lỗi · {len(state['claimIssues'])} cảnh báo nguồn")
    if state["links"] is not None:
        dead = [item for item in state["links"] if item[2] != "ok"]
        print(f"  Link nguồn: {len(state['links']) - len(dead)}/{len(state['links'])} mở được")
        for index, url, status in dead:
            print(f"    {link_mark(status)} [{index}] {status} · {url}")
    if factcheck:
        stale = " (LỖI THỜI)" if state["factcheckStale"] else ""
        print(
            f"  Fact-check{stale}: "
            + " · ".join(f"{VERDICT_ICON[v]} {v} {counts[v]}" for v in VERDICTS)
        )
        for item in factcheck.get("items") or []:
            if item.get("verdict") in ("wrong", "doubtful"):
                print(f"    {VERDICT_ICON[item['verdict']]} {item.get('sceneId')}: {item.get('claim')}")
    else:
        print("  Fact-check: chưa chạy (--factcheck)")
    print(f"  Báo cáo:    {paths.rel(report)}")
    print("─" * 60)


def write_report(pid: str, fmt: str, *, links: bool) -> dict[str, Any]:
    state = collect(pid, fmt, links=links)
    report = paths.review_report_path(pid, fmt)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_report(pid, fmt, state), encoding="utf-8")
    print_summary(pid, fmt, state, report)
    return state


# ---------------------------------------------------------------- approve


def approve(
    pid: str,
    fmt: str,
    state: dict[str, Any],
    *,
    note: str,
    skip_factcheck: bool,
    force: bool,
) -> int:
    if state["errors"]:
        print("\n✗ Không duyệt được: script còn lỗi validate.", file=sys.stderr)
        return 1

    factcheck = state["factcheck"]
    if skip_factcheck:
        factcheck_status = "skipped"
    elif not factcheck or state["factcheckStale"]:
        print(
            "\n✗ Chưa có fact-check cho phiên bản script này.\n"
            f"  Chạy: python -m pipeline.review --project-id {pid} --format {fmt} --factcheck\n"
            "  Hoặc duyệt không fact-check (ghi lại trong project.json): --no-factcheck",
            file=sys.stderr,
        )
        return 1
    else:
        counts = verdict_counts(factcheck)
        if counts["wrong"] and not force:
            print(
                f"\n✗ Fact-check còn {counts['wrong']} khẳng định sai. Sửa script rồi "
                "fact-check lại, hoặc dùng --force nếu đã xác minh bằng tay.",
                file=sys.stderr,
            )
            return 1
        factcheck_status = "forced" if counts["wrong"] else "ok"
        unsure = counts["doubtful"] + counts["unsupported"]
        if unsure:
            print(f"  ! {unsure} khẳng định chưa chắc chắn (doubtful/unsupported) — duyệt với rủi ro.")

    paths.update_project(
        pid,
        review={
            fmt: {
                "status": "approved",
                "scriptHash": state["hash"],
                "approvedAt": now(),
                "rejectedAt": None,
                "factcheck": factcheck_status,
                "note": note,
            }
        },
    )
    print(f"\n✓ Đã duyệt script {fmt} (hash {state['hash']}, fact-check: {factcheck_status}).")
    print(f"  Tiếp: python -m pipeline.make --project-id {pid} --format {fmt}")
    return 0


def reject(pid: str, fmt: str, state: dict[str, Any], *, note: str) -> int:
    paths.update_project(
        pid,
        review={
            fmt: {
                "status": "rejected",
                "scriptHash": state["hash"],
                "approvedAt": None,
                "rejectedAt": now(),
                "note": note,
            }
        },
    )
    print(f"\n✓ Đã từ chối script {fmt}: {note}")
    return 0


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.review",
        description="Xem, fact-check và duyệt kịch bản trước khi sản xuất.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=config.format_ids())
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--factcheck", action="store_true", help="Chạy agent fact-check rồi báo cáo")
    action.add_argument("--approve", action="store_true", help="Duyệt phiên bản script hiện tại")
    action.add_argument("--reject", action="store_true", help="Từ chối (cần --note)")
    parser.add_argument("--note", default="", help="Ghi chú lưu cùng quyết định")
    parser.add_argument("--no-factcheck", action="store_true", help="[--approve] Duyệt khi chưa fact-check")
    parser.add_argument("--force", action="store_true", help="[--approve] Duyệt dù fact-check có verdict wrong")
    parser.add_argument("--no-links", action="store_true", help="Không kiểm tra link nguồn (offline)")
    parser.add_argument("--model", help="[--factcheck] provider/model cho OpenCode")
    args = parser.parse_args(argv)

    pid = args.project_id
    fmt = args.format or paths.detect_format(pid)
    if not fmt:
        parser.error("project có cả short và long (hoặc chưa có script): truyền --format")
    if not paths.script_path(pid, fmt).exists():
        raise SystemExit(f"Không thấy {paths.rel(paths.script_path(pid, fmt))}")
    if args.reject and not args.note:
        parser.error("--reject cần --note để ghi lý do")

    paths.snapshot(pid)
    if args.factcheck:
        try:
            run_factcheck(pid, fmt, model=args.model)
        except llm.AgentError as exc:
            raise SystemExit(f"✗ Fact-check thất bại: {exc}") from exc

    state = write_report(pid, fmt, links=not args.no_links)

    if args.approve:
        return approve(
            pid,
            fmt,
            state,
            note=args.note,
            skip_factcheck=args.no_factcheck,
            force=args.force,
        )
    if args.reject:
        return reject(pid, fmt, state, note=args.note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
