"""Hai chế độ chạy agent: OpenCode và Claude Code dùng chung định nghĩa agent."""

from __future__ import annotations

import json
import subprocess

import pytest

from pipeline import llm


@pytest.fixture(autouse=True)
def reset_backend(monkeypatch):
    monkeypatch.delenv("MY_STUDIO_LLM", raising=False)
    llm.use(None)
    yield
    llm.use(None)


def test_backend_default_env_and_flag(monkeypatch):
    assert llm.backend() == "opencode"
    monkeypatch.setenv("MY_STUDIO_LLM", "claude")
    assert llm.backend() == "claude"
    llm.use("opencode")  # cờ --llm thắng biến môi trường
    assert llm.backend() == "opencode"


def test_invalid_backend_rejected(monkeypatch):
    with pytest.raises(llm.AgentError):
        llm.use("gpt")
    monkeypatch.setenv("MY_STUDIO_LLM", "gpt")
    with pytest.raises(llm.AgentError):
        llm.backend()


@pytest.mark.parametrize("agent", ["researcher", "scriptwriter", "shortener", "factchecker"])
def test_every_pipeline_agent_loads(agent):
    spec = llm.load_agent(agent)
    assert spec.prompt and not spec.prompt.startswith("---")
    assert {"action": "*", "resource": "*", "effect": "deny"} in spec.permissions


def test_scriptwriter_permissions_map_to_scoped_claude_tools():
    tools, allowed = llm.claude_tools(llm.load_agent("scriptwriter").permissions)
    assert set(tools) == {"Read", "Glob", "Grep", "Edit", "Write"}
    assert "Bash" not in tools and "WebFetch" not in tools
    assert "Read(projects/**)" in allowed
    assert "Edit(projects/**)" in allowed and "Write(projects/**)" in allowed
    assert "Read" not in allowed  # không được đọc ngoài projects/config/schemas


def test_researcher_gets_web_tools():
    tools, allowed = llm.claude_tools(llm.load_agent("researcher").permissions)
    assert {"WebFetch", "WebSearch"} <= set(tools)
    assert "Read" in allowed  # resource "**" = đọc mọi nơi


def fake_run(stdout: str, returncode: int = 0):
    calls: list[list[str]] = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    return run, calls


def test_claude_backend_builds_command_and_reads_result(monkeypatch, tmp_path):
    result = {"type": "result", "is_error": False, "result": "xong", "session_id": "abc"}
    run, calls = fake_run(json.dumps(result))
    monkeypatch.setattr(llm.subprocess, "run", run)
    monkeypatch.setattr(llm, "_launcher", lambda name: [name])
    llm.use("claude")

    out = llm.run_agent("scriptwriter", "projectId=x", cwd=tmp_path, model="anthropic/sonnet")

    assert out.text == "xong" and out.session_id == "abc"
    cmd = calls[0]
    assert cmd[:3] == ["claude", "-p", "projectId=x"]
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert "Bash" not in cmd[cmd.index("--tools") + 1]
    assert cmd[cmd.index("--model") + 1] == "sonnet"


def test_claude_error_raises(monkeypatch, tmp_path):
    run, _ = fake_run(json.dumps({"is_error": True, "result": "hết quota"}), returncode=1)
    monkeypatch.setattr(llm.subprocess, "run", run)
    monkeypatch.setattr(llm, "_launcher", lambda name: [name])
    llm.use("claude")
    with pytest.raises(llm.AgentError, match="hết quota"):
        llm.run_agent("scriptwriter", "projectId=x", cwd=tmp_path)


def test_opencode_backend_still_default(monkeypatch, tmp_path):
    event = {"type": "text", "sessionID": "s1", "part": {"text": "ok"}}
    run, calls = fake_run(json.dumps(event))
    monkeypatch.setattr(llm.subprocess, "run", run)
    monkeypatch.setattr(llm, "_launcher", lambda name: [name])

    out = llm.run_agent("scriptwriter", "projectId=x", cwd=tmp_path)

    assert out.text == "ok"
    assert calls[0][:2] == ["opencode", "run"]
