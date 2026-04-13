"""Tests for educational modes (student, teacher, developer).

Covers: CLI parsing, tool filtering, Socratic prompt, PII filtering,
SQLite trace store, sandbox tool, and developer mode invariance.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from educoder.cli import build_arg_parser
from educoder.pii_filter import filter_pii
from educoder.runtime import EduCoder
from educoder.trace_db import StudentTraceStore


def _build_dev_agent(tmp_path):
    from educoder.workspace import WorkspaceContext
    from educoder.runtime import SessionStore

    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    workspace = WorkspaceContext.build(str(tmp_path))
    store = SessionStore(str(tmp_path / ".educoder" / "sessions"))

    class FakeModel:
        pass

    return EduCoder(
        model_client=FakeModel(),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        mode="developer",
    )


def _build_student_agent(tmp_path):
    from educoder.workspace import WorkspaceContext
    from educoder.runtime import SessionStore

    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    workspace = WorkspaceContext.build(str(tmp_path))
    store = SessionStore(str(tmp_path / ".educoder" / "sessions"))

    class FakeModel:
        pass

    return EduCoder(
        model_client=FakeModel(),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        mode="student",
    )


class TestCLIModeParsing:
    def test_default_mode_is_developer(self):
        args = build_arg_parser().parse_args([])
        assert args.mode == "developer"

    def test_student_mode(self):
        args = build_arg_parser().parse_args(["--mode", "student"])
        assert args.mode == "student"

    def test_teacher_mode(self):
        args = build_arg_parser().parse_args(["--mode", "teacher"])
        assert args.mode == "teacher"

    def test_developer_mode_explicit(self):
        args = build_arg_parser().parse_args(["--mode", "developer"])
        assert args.mode == "developer"


class TestDeveloperToolsUnchanged:
    def test_developer_mode_has_all_base_tools(self, tmp_path):
        agent = _build_dev_agent(tmp_path)
        from educoder.tools import BASE_TOOL_SPECS

        for name in BASE_TOOL_SPECS:
            assert name in agent.tools, f"developer mode missing tool: {name}"

    def test_developer_mode_has_no_sandbox(self, tmp_path):
        agent = _build_dev_agent(tmp_path)
        assert "run_sandbox_code" not in agent.tools


class TestStudentToolFiltering:
    def test_student_mode_lacks_blocked_tools(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        for blocked in ("write_file", "patch_file", "run_shell"):
            assert blocked not in agent.tools, f"student mode has blocked tool: {blocked}"

    def test_student_mode_has_sandbox(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        assert "run_sandbox_code" in agent.tools

    def test_student_mode_has_safe_tools(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        for safe in ("list_files", "read_file", "search"):
            assert safe in agent.tools


class TestSocraticPrompt:
    def test_student_prefix_contains_socratic(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        assert "Socratic Tutor" in agent.prefix

    def test_student_prefix_contains_never(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        assert "NEVER output complete" in agent.prefix

    def test_developer_prefix_no_socratic(self, tmp_path):
        agent = _build_dev_agent(tmp_path)
        assert "Socratic" not in agent.prefix


class TestPIIFilter:
    def test_redacts_email(self):
        assert filter_pii("contact test@example.com please") == "contact [REDACTED_EMAIL] please"

    def test_redacts_phone(self):
        assert filter_pii("call 555-123-4567 now") == "call [REDACTED_PHONE] now"

    def test_no_redaction_on_plain_text(self):
        assert filter_pii("hello world") == "hello world"

    def test_redacts_both(self):
        result = filter_pii("email: a@b.com phone: 555-123-4567")
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_PHONE]" in result
        assert "a@b.com" not in result
        assert "555-123-4567" not in result


class TestStudentTraceStore:
    def test_record_and_query(self, tmp_path):
        db_path = tmp_path / "traces.db"
        store = StudentTraceStore(db_path)
        store.record(session_id="sess-1", query="how do loops work?", agent_response="Think about iteration...")
        store.record(session_id="sess-1", query="syntax error help", error_traceback="SyntaxError: invalid syntax", agent_response="Check your colons...")
        metrics = store.query_metrics()
        assert metrics["total_traces"] == 2
        assert metrics["total_sessions"] == 1
        assert metrics["avg_queries_per_session"] == 2.0
        assert len(metrics["top_errors"]) == 1

    def test_uses_parameterized_queries(self):
        import inspect

        src = inspect.getsource(StudentTraceStore.record)
        assert "?" in src


class TestFilterIfStudent:
    def test_developer_mode_is_noop(self, tmp_path):
        agent = _build_dev_agent(tmp_path)
        result = agent._filter_if_student("test@example.com")
        assert result == "test@example.com"

    def test_student_mode_filters(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        result = agent._filter_if_student("test@example.com")
        assert "[REDACTED_EMAIL]" in result


class TestLogStudentTrace:
    def test_developer_mode_is_noop(self, tmp_path):
        agent = _build_dev_agent(tmp_path)
        agent._log_student_trace("query", "response")

    def test_student_mode_creates_trace(self, tmp_path):
        agent = _build_student_agent(tmp_path)
        agent._log_student_trace("test query", "test response")
        db_path = Path(agent.workspace.repo_root) / ".educoder" / "traces.db"
        assert db_path.exists()
        store = StudentTraceStore(db_path)
        metrics = store.query_metrics()
        assert metrics["total_traces"] == 1


class TestSandboxTool:
    def test_empty_code_raises(self, tmp_path):
        from educoder.sandbox import tool_run_sandbox_code

        agent = _build_student_agent(tmp_path)
        with pytest.raises(ValueError, match="code must not be empty"):
            tool_run_sandbox_code(agent, {"code": ""})

    def test_docker_unavailable_returns_error(self, tmp_path):
        from educoder.sandbox import tool_run_sandbox_code

        agent = _build_student_agent(tmp_path)
        with patch.dict("sys.modules", {"docker": None}):
            result = tool_run_sandbox_code(agent, {"code": "print(1)"})
        assert "error" in result.lower()
