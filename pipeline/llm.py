from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class AgentError(RuntimeError):
    pass


@dataclass
class AgentRun:
    text: str
    session_id: str | None = None
    events: list[dict] = field(default_factory=list)
    duration_sec: float = 0.0


def _launcher() -> list[str]:
    """Trả về prefix lệnh để chạy opencode trên mọi nền tảng."""
    exe = shutil.which("opencode")
    if not exe:
        raise AgentError(
            "Không tìm thấy 'opencode' trong PATH. Cài lại hoặc mở terminal mới."
        )
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        # npm shim trên Windows là file .cmd, phải chạy qua cmd.exe.
        return ["cmd.exe", "/c", exe]
    return [exe]


# Message được truyền qua argv; trên Windows cmd.exe sẽ parse lại chuỗi này.
# Vì vậy mọi message phải là một dòng ASCII, không chứa ký tự đặc biệt.
_UNSAFE = set('&|<>^%"!\n\r\t')


def run_agent(
    agent: str,
    message: str,
    *,
    cwd: Path,
    model: str | None = None,
    timeout: int = 600,
) -> AgentRun:
    """Chạy `opencode run` và gom toàn bộ text của assistant.

    Message phải ngắn, một dòng, không chứa ký tự đặc biệt của shell.
    Nội dung dài (chủ đề, JSON, lỗi validate) phải ghi ra file và
    truyền đường dẫn trong message.
    """
    bad = sorted({c for c in message if c in _UNSAFE})
    if bad:
        raise AgentError(
            f"Message chứa ký tự không an toàn cho shell: {bad!r}. "
            "Hãy ghi nội dung ra file và truyền đường dẫn."
        )
    if "\n" in message or "\r" in message:
        raise AgentError("Message phải là một dòng.")

    cmd = [*_launcher(), "run", message, "--agent", agent, "--format", "json"]
    if model:
        cmd += ["--model", model]

    import time

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AgentError(f"Agent '{agent}' quá thời gian {timeout}s") from exc

    elapsed = time.perf_counter() - started

    texts: list[str] = []
    events: list[dict] = []
    session_id: str | None = None
    errors: list[str] = []

    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event)
        session_id = session_id or event.get("sessionID")
        etype = event.get("type")
        if etype == "text":
            part = event.get("part") or {}
            if isinstance(part.get("text"), str):
                texts.append(part["text"])
        elif etype == "error":
            err = event.get("error") or event.get("part") or {}
            errors.append(str(err.get("message") or err)[:500])

    if proc.returncode != 0 and not texts:
        detail = "; ".join(errors) or (proc.stderr or "").strip()[-800:]
        raise AgentError(f"opencode run thất bại (exit {proc.returncode}): {detail}")

    if not texts:
        detail = "; ".join(errors) or (proc.stderr or "").strip()[-800:]
        raise AgentError(f"Agent '{agent}' không trả về text. {detail}")

    return AgentRun(
        text="".join(texts).strip(),
        session_id=session_id,
        events=events,
        duration_sec=elapsed,
    )
