"""Giao diện duyệt: đọc kịch bản + nguồn → duyệt → xem animation → tạo video.

Animation chỉ dựng cho kịch bản đã duyệt (server chặn, không chỉ ẩn nút).

    python -m pipeline.ui            # mở http://127.0.0.1:8765

Server chỉ nghe trên máy (127.0.0.1), dùng thư viện chuẩn. Frontend React ở
``video/ui/`` (dùng chung composition Remotion của video), được build bằng
esbuild mỗi lần khởi động. API:

    GET  /api/projects                       danh sách dự án + trạng thái duyệt
    GET  /api/review?project=&format=        kịch bản, nguồn, lỗi, fact-check, duyệt
    GET  /api/research?project=&format=      nội dung research.md
    POST /api/links     {project, format}                     kiểm tra link nguồn
    POST /api/check     {project, format, script}             lỗi của bản đang sửa
    POST /api/notes     {project, format, notes}              ghi chú animation theo cảnh
    POST /api/preview   {project, format, aspect?}            animation (chỉ khi đã duyệt)
    POST /api/script    {project, format, script}             lưu kịch bản
    POST /api/approve   {project, format, note, skipFactcheck, force}
    POST /api/reject    {project, format, note}
    POST /api/jobs      {kind: make|factcheck, project, format, ...}
    GET  /api/jobs/<id>                      trạng thái + log
"""

from __future__ import annotations

import argparse
import contextlib
import io
import itertools
import json
import mimetypes
import shutil
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import config, llm, motion, paths, preview, review, validate

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

UI_DIR = paths.ROOT / "video" / "ui"
DIST_DIR = UI_DIR / "dist"
JOB_LOG_LINES = 400


class ApiError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- dữ liệu


def project_ids() -> list[str]:
    if not paths.PROJECTS.exists():
        return []
    return sorted(
        item.name
        for item in paths.PROJECTS.iterdir()
        if item.is_dir() and not item.name.startswith(("_", ".")) and (item / "scripts").is_dir()
    )


def checked(pid: Any, fmt: Any) -> tuple[str, str]:
    """Chỉ nhận id dự án có thật và format hợp lệ (chặn đường dẫn lạ)."""
    if pid not in project_ids():
        raise ApiError(f"Không có dự án '{pid}'", HTTPStatus.NOT_FOUND)
    if fmt not in paths.FORMATS:
        raise ApiError(f"Format không hợp lệ: {fmt!r}")
    if not paths.script_path(pid, fmt).exists():
        raise ApiError(f"Dự án '{pid}' chưa có kịch bản {fmt}", HTTPStatus.NOT_FOUND)
    return pid, fmt


def list_projects() -> list[dict[str, Any]]:
    result = []
    for pid in project_ids():
        project = paths.read_project(pid)
        formats = []
        for fmt in paths.FORMATS:
            if not paths.script_path(pid, fmt).exists():
                continue
            problem = review.approval_problem(pid, fmt)
            formats.append(
                {
                    "format": fmt,
                    "approved": problem is None,
                    "problem": problem,
                    "video": [
                        aspect
                        for aspect in config.aspect_ids()
                        if paths.video_path(pid, fmt, aspect).exists()
                    ],
                }
            )
        result.append({"id": pid, "title": project.get("title") or pid, "formats": formats})
    return result


def review_state(pid: str, fmt: str) -> dict[str, Any]:
    state = review.collect(pid, fmt, links=False)
    meta = state["script"].get("meta") or {}
    return {
        "project": pid,
        "format": fmt,
        "title": paths.read_project(pid).get("title") or pid,
        "script": state["script"],
        "sources": [
            {"index": index, **source}
            for index, source in enumerate(meta.get("sources") or [], start=1)
        ],
        "assumptions": meta.get("assumptions") or [],
        "hasResearch": paths.research_path(pid).exists(),
        "motion": motion.describe(pid, fmt, state["script"]),
        "notes": motion.load_notes(pid, fmt),
        "errors": state["errors"],
        "claimIssues": state["claimIssues"],
        "factcheck": state["factcheck"],
        "factcheckStale": state["factcheckStale"],
        "approval": state["approval"],
        "approvalProblem": state["approvalProblem"],
        "aspects": config.aspect_ids(),
        "aspect": paths.resolve_aspect(pid, fmt),
        "llm": llm.backend(),
    }


def save_script(pid: str, fmt: str, script: Any) -> dict[str, Any]:
    if not isinstance(script, dict) or not isinstance(script.get("scenes"), list):
        raise ApiError("Kịch bản không hợp lệ (thiếu scenes)")
    path = paths.script_path(pid, fmt)
    path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths.snapshot(pid)
    return review_state(pid, fmt)


def draft(pid: str, fmt: str, aspect: Any) -> dict[str, Any]:
    """Animation xem trước của kịch bản ĐÃ DUYỆT (bản đã lưu), không nhận bản sửa dở."""
    if aspect is not None and aspect not in config.aspect_ids():
        raise ApiError(f"Khung hình không hợp lệ: {aspect!r}")
    problem = review.approval_problem(pid, fmt)
    if problem:
        raise ApiError(
            f"Duyệt kịch bản trước khi xem animation ({problem})", HTTPStatus.FORBIDDEN
        )
    errors: list[str] = []
    try:
        props = preview.draft_props(pid, fmt, aspect)
    except SystemExit as exc:  # build_scenes báo lỗi nội dung bằng SystemExit
        return {"props": None, "errors": [*errors, str(exc)]}
    except (KeyError, TypeError, ValueError) as exc:
        return {"props": None, "errors": [*errors, f"Không dựng được bản xem trước: {exc}"]}
    return {"props": props, "errors": errors}


def captured(action) -> tuple[int, str]:
    """Chạy hàm in ra terminal (review.approve/reject), trả về mã + thông báo."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = action()
    return code, buffer.getvalue().strip()


# ---------------------------------------------------------------- job nền


class Jobs:
    """Chạy pipeline.make / fact-check như tiến trình con, giữ log để UI đọc."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def start(self, title: str, args: list[str]) -> dict[str, Any]:
        with self._lock:
            if any(job["status"] == "running" for job in self._jobs.values()):
                raise ApiError("Đang có tác vụ chạy, đợi xong rồi thử lại", HTTPStatus.CONFLICT)
            job_id = str(next(self._ids))
            command = [sys.executable, "-u", "-m", *args]
            proc = subprocess.Popen(
                command,
                cwd=paths.ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            job = {"id": job_id, "title": title, "status": "running", "log": [], "code": None,
                   "command": " ".join(["python", "-m", *args])}
            self._jobs[job_id] = job
        threading.Thread(target=self._pump, args=(job, proc), daemon=True).start()
        return self.view(job_id)

    def _pump(self, job: dict[str, Any], proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        partial = ""
        for chunk in iter(lambda: proc.stdout.read(256), ""):
            partial += chunk
            # Thanh tiến trình vẽ lại bằng \r: chỉ giữ trạng thái mới nhất của dòng.
            *lines, partial = partial.replace("\r\n", "\n").split("\n")
            with self._lock:
                for line in lines:
                    job["log"].append(line.split("\r")[-1])
                job["log"] = job["log"][-JOB_LOG_LINES:]
                job["current"] = partial.split("\r")[-1]
        code = proc.wait()
        with self._lock:
            if partial:
                job["log"].append(partial.split("\r")[-1])
            job["current"] = ""
            job["code"] = code
            job["status"] = "done" if code == 0 else "failed"

    def view(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError("Không có tác vụ này", HTTPStatus.NOT_FOUND)
            return {**job, "log": list(job["log"])}


JOBS = Jobs()

# Kiểu xuất → (tên tác vụ, cờ của pipeline.make). Video và CapCut là hai lần
# render khác nhau (CapCut cần clip chưa có phụ đề/chuyển cảnh).
OUTPUTS: dict[str, tuple[str, list[str]]] = {
    "video": ("Tạo video MP4", []),
    "capcut": ("Tạo dự án CapCut", ["--capcut-only"]),
    "both": ("Tạo video MP4 + dự án CapCut", ["--capcut"]),
}


def start_job(body: dict[str, Any]) -> dict[str, Any]:
    pid, fmt = checked(body.get("project"), body.get("format"))
    kind = body.get("kind")
    if kind == "make":
        aspect = body.get("aspect")
        if aspect is not None and aspect not in config.aspect_ids():
            raise ApiError(f"Khung hình không hợp lệ: {aspect!r}")
        output = body.get("output", "video")
        if output not in OUTPUTS:
            raise ApiError(f"Kiểu xuất không hợp lệ: {output!r}")
        args = ["pipeline.make", "--project-id", pid, "--format", fmt, *OUTPUTS[output][1]]
        if aspect:
            args += ["--aspect", aspect]
        return JOBS.start(f"{OUTPUTS[output][0]} · {pid} · {fmt}", args)
    if kind == "factcheck":
        args = ["pipeline.review", "--project-id", pid, "--format", fmt, "--factcheck",
                "--llm", llm.backend()]
        return JOBS.start(f"Fact-check {pid} · {fmt}", args)
    raise ApiError(f"Loại tác vụ không hợp lệ: {kind!r}")


# ---------------------------------------------------------------- HTTP


class Handler(BaseHTTPRequestHandler):
    server_version = "my-studio-ui"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - tên của lớp cha
        pass  # giữ terminal sạch; lỗi vẫn trả về cho UI

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ApiError("Body phải là object JSON")
        return data

    def _handle(self, method: str) -> None:
        url = urlparse(self.path)
        try:
            if url.path.startswith("/api/"):
                self._json(self._api(method, url.path, parse_qs(url.query)))
            elif method == "GET":
                self._static(url.path)
            else:
                raise ApiError("Không hỗ trợ", HTTPStatus.METHOD_NOT_ALLOWED)
        except ApiError as exc:
            self._json({"error": str(exc)}, exc.status)
        except json.JSONDecodeError:
            self._json({"error": "Body không phải JSON"}, HTTPStatus.BAD_REQUEST)
        except SystemExit as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self) -> None:  # noqa: N802 - tên của BaseHTTPRequestHandler
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def _api(self, method: str, path: str, query: dict[str, list[str]]) -> Any:
        one = lambda key: (query.get(key) or [None])[0]  # noqa: E731
        if method == "GET" and path == "/api/projects":
            return list_projects()
        if method == "GET" and path == "/api/review":
            return review_state(*checked(one("project"), one("format")))
        if method == "GET" and path == "/api/research":
            pid, _ = checked(one("project"), one("format"))
            research = paths.research_path(pid)
            if not research.exists():
                raise ApiError("Dự án chưa có research.md", HTTPStatus.NOT_FOUND)
            return {"text": research.read_text(encoding="utf-8")}
        if method == "GET" and path.startswith("/api/jobs/"):
            return JOBS.view(path.rsplit("/", 1)[-1])
        if method != "POST":
            raise ApiError("Không có API này", HTTPStatus.NOT_FOUND)

        body = self._body()
        if path == "/api/jobs":
            return start_job(body)
        pid, fmt = checked(body.get("project"), body.get("format"))
        if path == "/api/check":
            script = body.get("script")
            if not isinstance(script, dict):
                raise ApiError("Thiếu kịch bản")
            return {"errors": validate.validate(script, fmt=fmt, project_id=pid)}
        if path == "/api/preview":
            return draft(pid, fmt, body.get("aspect"))
        if path == "/api/notes":
            notes = body.get("notes")
            if not isinstance(notes, dict):
                raise ApiError("Thiếu ghi chú")
            script = review.load_json(paths.script_path(pid, fmt))
            return motion.save_notes(pid, fmt, notes, [scene["id"] for scene in script["scenes"]])
        if path == "/api/links":
            sources = (review.load_json(paths.script_path(pid, fmt)).get("meta") or {}).get(
                "sources"
            ) or []
            return [
                {"index": index, "url": url, "status": status, "ok": status == "ok"}
                for index, url, status in review.check_sources(sources)
            ]
        if path == "/api/script":
            return save_script(pid, fmt, body.get("script"))
        if path == "/api/approve":
            state = review.collect(pid, fmt, links=False)
            code, message = captured(
                lambda: review.approve(
                    pid,
                    fmt,
                    state,
                    note=str(body.get("note") or ""),
                    skip_factcheck=bool(body.get("skipFactcheck")),
                    force=bool(body.get("force")),
                )
            )
            return {"ok": code == 0, "message": message, "state": review_state(pid, fmt)}
        if path == "/api/reject":
            note = str(body.get("note") or "").strip()
            if not note:
                raise ApiError("Ghi lý do từ chối")
            state = review.collect(pid, fmt, links=False)
            code, message = captured(lambda: review.reject(pid, fmt, state, note=note))
            return {"ok": code == 0, "message": message, "state": review_state(pid, fmt)}
        raise ApiError("Không có API này", HTTPStatus.NOT_FOUND)

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            target = UI_DIR / "index.html"
        else:
            target = (DIST_DIR / path.lstrip("/")).resolve()
            if DIST_DIR.resolve() not in target.parents:
                raise ApiError("Không tìm thấy", HTTPStatus.NOT_FOUND)
        if not target.is_file():
            raise ApiError("Không tìm thấy", HTTPStatus.NOT_FOUND)
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        self._send(HTTPStatus.OK, target.read_bytes(), content_type)


def build_frontend() -> None:
    node = shutil.which("node")
    if not node:
        raise SystemExit("Không tìm thấy node trong PATH (cần để build giao diện).")
    print("Build giao diện…", flush=True)
    code = subprocess.run([node, str(UI_DIR / "build.mjs")], cwd=paths.ROOT / "video").returncode
    if code != 0:
        raise SystemExit("Build giao diện thất bại. Chạy 'npm install' trong video/ rồi thử lại.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.ui",
        description="Giao diện duyệt kịch bản và xem trước animation trước khi tạo video.",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--llm", choices=llm.BACKENDS, help="Chế độ chạy fact-check từ giao diện")
    parser.add_argument("--no-browser", action="store_true", help="Không tự mở trình duyệt")
    parser.add_argument("--skip-build", action="store_true", help="Dùng bản build giao diện có sẵn")
    args = parser.parse_args(argv)
    llm.use(args.llm)

    if not args.skip_build or not (DIST_DIR / "app.js").exists():
        build_frontend()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"✓ Giao diện duyệt: {url}  (Ctrl+C để tắt)", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
