"""Gọi agent viết/kiểm kịch bản qua một trong hai CLI: OpenCode hoặc Claude Code.

Hai chế độ dùng chung định nghĩa agent ở ``.opencode/agents/<agent>.md``:
phần thân là prompt, khối ``permissions`` trong frontmatter là quyền. Với
Claude Code, quyền được dịch sang ``--tools`` / ``--allowedTools`` để agent
chỉ đọc/ghi đúng chỗ như khi chạy bằng OpenCode.

Chọn chế độ: tham số ``--llm`` của pipeline.script / pipeline.review, hoặc
biến môi trường ``MY_STUDIO_LLM`` (``opencode`` | ``claude``); mặc định opencode.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

BACKENDS = ("opencode", "claude")
DEFAULT_BACKEND = "opencode"
AGENTS_DIR = Path(__file__).resolve().parent.parent / ".opencode" / "agents"

_backend: str | None = None


class AgentError(RuntimeError):
    pass


@dataclass
class AgentRun:
    text: str
    session_id: str | None = None
    events: list[dict] = field(default_factory=list)
    duration_sec: float = 0.0


def use(backend: str | None) -> None:
    """Chọn chế độ cho cả tiến trình (None = theo MY_STUDIO_LLM / mặc định)."""
    global _backend
    if backend is not None and backend not in BACKENDS:
        raise AgentError(f"Chế độ LLM không hợp lệ: {backend!r}. Chọn: {', '.join(BACKENDS)}")
    _backend = backend


def backend() -> str:
    chosen = _backend or os.environ.get("MY_STUDIO_LLM") or DEFAULT_BACKEND
    if chosen not in BACKENDS:
        raise AgentError(
            f"MY_STUDIO_LLM={chosen!r} không hợp lệ. Chọn: {', '.join(BACKENDS)}"
        )
    return chosen


def _launcher(name: str) -> list[str]:
    """Trả về prefix lệnh để chạy CLI trên mọi nền tảng."""
    exe = shutil.which(name)
    if not exe:
        raise AgentError(
            f"Không tìm thấy '{name}' trong PATH. Cài lại hoặc mở terminal mới."
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
    """Chạy agent bằng chế độ đang chọn và trả về text cuối của assistant.

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

    if backend() == "claude":
        return _run_claude(agent, message, cwd=cwd, model=model, timeout=timeout)
    return _run_opencode(agent, message, cwd=cwd, model=model, timeout=timeout)


def _run(cmd: list[str], *, cwd: Path, timeout: int, agent: str) -> tuple[subprocess.CompletedProcess, float]:
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
    return proc, time.perf_counter() - started


# ---------------------------------------------------------------- OpenCode


def _run_opencode(
    agent: str, message: str, *, cwd: Path, model: str | None, timeout: int
) -> AgentRun:
    cmd = [*_launcher("opencode"), "run", message, "--agent", agent, "--format", "json"]
    if model:
        cmd += ["--model", model]
    proc, elapsed = _run(cmd, cwd=cwd, timeout=timeout, agent=agent)

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


# ---------------------------------------------------------------- Claude Code

# Quyền OpenCode -> tool của Claude Code. Quyền theo đường dẫn (read/edit) giữ
# nguyên pattern để Claude Code chặn đọc/ghi ngoài vùng cho phép.
_TOOL_FOR = {
    "read": ("Read",),
    "glob": ("Glob",),
    "grep": ("Grep",),
    "webfetch": ("WebFetch",),
    "websearch": ("WebSearch",),
    "edit": ("Edit", "Write"),
}
_SCOPED = {"Read", "Edit", "Write"}


@dataclass
class AgentSpec:
    prompt: str
    permissions: list[dict[str, str]]


def load_agent(agent: str, agents_dir: Path = AGENTS_DIR) -> AgentSpec:
    """Đọc ``<agent>.md``: frontmatter (chỉ khối permissions) + thân prompt."""
    path = agents_dir / f"{agent}.md"
    if not path.exists():
        raise AgentError(f"Không thấy định nghĩa agent: {path}")
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not match:
        return AgentSpec(prompt=text.strip(), permissions=[])
    front, body = match.groups()

    permissions: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_block = False
    for line in front.splitlines():
        if re.match(r"^permissions\s*:", line):
            in_block = True
            continue
        if in_block and line and not line[0].isspace():
            break  # hết khối permissions
        if not in_block:
            continue
        item = re.match(r"^\s*-\s*(\w+)\s*:\s*(.+)$", line)
        field_ = item or re.match(r"^\s+(\w+)\s*:\s*(.+)$", line)
        if not field_:
            continue
        if item:
            current = {}
            permissions.append(current)
        assert current is not None
        current[field_.group(1)] = field_.group(2).strip().strip("\"'")
    return AgentSpec(prompt=body.strip(), permissions=permissions)


def claude_tools(permissions: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    """(tool được bật, luật allow) từ quyền OpenCode. Không có quyền thì không có tool."""
    tools: list[str] = []
    allowed: list[str] = []
    for rule in permissions:
        if rule.get("effect") != "allow":
            continue
        resource = rule.get("resource", "*")
        for tool in _TOOL_FOR.get(rule.get("action", ""), ()):
            if tool not in tools:
                tools.append(tool)
            if tool in _SCOPED and resource not in ("*", "**"):
                entry = f"{tool}({resource})"
            else:
                entry = tool
            if entry not in allowed:
                allowed.append(entry)
    return tools, allowed


def _run_claude(
    agent: str, message: str, *, cwd: Path, model: str | None, timeout: int
) -> AgentRun:
    spec = load_agent(agent)
    tools, allowed = claude_tools(spec.permissions)
    cmd = [
        *_launcher("claude"),
        "-p",
        message,
        "--output-format",
        "json",
        "--append-system-prompt",
        spec.prompt,
        # Chỉ bật đúng tool agent cần; mọi thứ khác (Bash, MCP…) không tồn tại.
        "--tools",
        ",".join(tools) if tools else "",
        "--permission-mode",
        "dontAsk",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    if allowed:
        cmd += ["--allowedTools", *allowed]
    if model:
        # Model kiểu OpenCode "provider/model" không áp dụng; lấy phần sau "/".
        cmd += ["--model", model.split("/")[-1]]
    proc, elapsed = _run(cmd, cwd=cwd, timeout=timeout, agent=agent)

    result: dict | None = None
    for line in reversed(proc.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                result = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if result is None:
        detail = (proc.stderr or proc.stdout or "").strip()[-800:]
        raise AgentError(f"claude -p thất bại (exit {proc.returncode}): {detail}")
    if result.get("is_error"):
        raise AgentError(
            f"Agent '{agent}' (claude) lỗi: {str(result.get('result') or result.get('subtype'))[:800]}"
        )
    text = str(result.get("result") or "").strip()
    if not text:
        raise AgentError(f"Agent '{agent}' (claude) không trả về text.")
    return AgentRun(
        text=text,
        session_id=result.get("session_id"),
        events=[result],
        duration_sec=elapsed,
    )
