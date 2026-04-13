# EduCoder Educational Modes — Progress Tracker

> Harness for implementing the 7-phase plan in `plan.md`.
> Based on Anthropic's harness design principles: decompose into tractable chunks,
> structured artifacts for context handoff, generator/evaluator separation, git checkpoints.

## Status Legend

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Pending — not started |
| `[~]` | In Progress — currently working |
| `[x]` | Complete — verified and committed |
| `[!]` | Blocked — needs attention |
| `[-]` | Skipped — with documented reason |

---

## Overall Progress

```
Phase 1: Mode Flag & Constructor Wiring     [x]  commit: eb0dec3
Phase 2: Mode-Aware Tool Registry           [x]  commit: 7c488bf
Phase 3: Docker Sandbox Implementation      [x]  commit: 9144446
Phase 4: Socratic Prompt & Student Prefix   [x]  commit: 167bfd8
Phase 5: PII Filtering & SQLite Trace Store [x]  commit: 0758ed4
Phase 6: Teacher Mode Analytics Dashboard   [x]  commit: 5fc91ae
Phase 7: Final Validation & Tests           [x]  commit: e2cc51a
```

## Commit Convention

Each phase ends with a git commit. Format:

```
feat(edu): <phase description>

Phase <N> of educational modes implementation.
- <change 1>
- <change 2>

Verified: pytest passes, <specific check>
```

---

## Phase 1: Mode Flag & Constructor Wiring

**Sprint Contract**: Add `--mode` CLI arg and `mode` param to `EduCoder.__init__`. Zero behavioral change. All existing tests must pass identically.

### Checklist

- [ ] 1.1 Add `--mode` arg to `build_arg_parser()` in `educoder/cli.py`
- [ ] 1.2 Add `mode="developer"` param to `EduCoder.__init__()` in `educoder/runtime.py`
- [ ] 1.3 Extract mode and pass to `EduCoder(...)` in `build_agent()` in `educoder/cli.py`
- [ ] 1.4 Pass mode to `EduCoder.from_session(...)` in `build_agent()`

### Verification (Evaluator)

- [ ] `uv run pytest -q` — all existing tests pass (zero regression)
- [ ] `uv run educoder --help` — shows `--mode developer|student|teacher` in output
- [ ] `uv run educoder "hello"` — works identically to before (developer mode default)
- [ ] `uv run ruff check .` — no lint errors

### Commit

```
feat(edu): add --mode CLI flag and constructor wiring

Phase 1 — no behavioral change, developer mode is default.
Verified: all existing tests pass, --help shows --mode.
```

Commit hash: _____________

---

## Phase 2: Mode-Aware Tool Registry

**Sprint Contract**: In student mode, remove `write_file`, `patch_file`, `run_shell`. Add `run_sandbox_code` stub. Developer mode produces identical tool set.

### Checklist

- [ ] 2.1 Change `build_tool_registry()` signature to accept `mode` param in `educoder/tools.py`
- [ ] 2.2 Add student-mode branch: filter blocked tools, import sandbox stub
- [ ] 2.3 Update `build_tools()` in `educoder/runtime.py` to pass `mode=self.mode`
- [ ] 2.4 Create `educoder/sandbox.py` with `SANDBOX_TOOL_SPEC` and stub runner

### Verification (Evaluator)

- [ ] `uv run pytest -q` — all existing tests pass (developer mode unchanged)
- [ ] Developer mode tools match `BASE_TOOL_SPECS` keys exactly
- [ ] Student mode tools: no `write_file`, `patch_file`, `run_shell`
- [ ] Student mode tools: has `run_sandbox_code`
- [ ] Student mode `run_sandbox_code` spec has correct schema and description
- [ ] `uv run ruff check .` — no lint errors

### Commit

```
feat(edu): mode-aware tool registry with student filtering

Phase 2 — student mode blocks write/patch/shell, adds sandbox stub.
Verified: developer tools unchanged, student tools filtered correctly.
```

Commit hash: _____________

---

## Phase 3: Docker Sandbox Implementation

**Sprint Contract**: Implement real `run_sandbox_code` with Docker SDK. Container: `python:3.13-alpine`, network disabled, 100MB mem limit, 5s timeout. Add optional deps to pyproject.toml.

### Checklist

- [ ] 3.1 Implement `tool_run_sandbox_code()` in `educoder/sandbox.py` with Docker SDK
- [ ] 3.2 Add 5-second hard timeout via `threading.Timer`
- [ ] 3.3 Add `[project.optional-dependencies]` to `pyproject.toml`
- [ ] 3.4 Handle Docker unavailable gracefully (returns error string, not exception)

### Verification (Evaluator)

- [ ] `uv run pytest -q` — all existing tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] Sandbox raises `ValueError` on empty code
- [ ] Sandbox returns error string when Docker unavailable (tested with mock)
- [ ] Sandbox returns stdout on success (tested with mock)
- [ ] Sandbox returns stderr on container error (tested with mock)
- [ ] `pyproject.toml` has optional deps but `dependencies` still empty `[]`

### Commit

```
feat(edu): Docker sandbox implementation for student mode

Phase 3 — sandboxed Python execution with Docker SDK.
Verified: mocked Docker tests pass, zero-dep developer mode preserved.
```

Commit hash: _____________

---

## Phase 4: Socratic Prompt & Student Mode Prefix

**Sprint Contract**: Inject Socratic constraint into system prompt when `mode == "student"`. Developer mode prefix must be byte-identical to pre-change output.

### Checklist

- [ ] 4.1 Add Socratic header block to `build_prefix()` in `educoder/runtime.py`
- [ ] 4.2 Socratic header prepended before standard agent instructions
- [ ] 4.3 Developer mode prefix is unchanged (no Socratic text)

### Verification (Evaluator)

- [ ] `uv run pytest -q` — all existing tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] Student mode prefix contains "Socratic Tutor"
- [ ] Student mode prefix contains "NEVER output complete"
- [ ] Developer mode prefix does NOT contain "Socratic"
- [ ] Developer mode prefix is identical to pre-change output

### Commit

```
feat(edu): Socratic tutor prompt injection for student mode

Phase 4 — student mode gets guiding-question persona.
Verified: student prefix has Socratic text, developer prefix unchanged.
```

Commit hash: _____________

---

## Phase 5: PII Filtering & SQLite Trace Store

**Sprint Contract**: PII filter redacts emails/phones. SQLite trace store records student interactions. Both wired into `ask()` in student mode only. Developer mode is completely unaffected.

### Checklist

- [ ] 5.1 Create `educoder/pii_filter.py` with email/phone regex
- [ ] 5.2 Create `educoder/trace_db.py` with `StudentTraceStore` class
- [ ] 5.3 Implement `record()` method with parameterized queries
- [ ] 5.4 Implement `query_metrics()` method (total_traces, top_errors, avg_queries)
- [ ] 5.5 Add `_filter_if_student()` method to `EduCoder` in `educoder/runtime.py`
- [ ] 5.6 Add `_log_student_trace()` method to `EduCoder` in `educoder/runtime.py`
- [ ] 5.7 Wire PII filter into `ask()` after user message recorded
- [ ] 5.8 Wire trace logging into `ask()` at return points

### Verification (Evaluator)

- [ ] `uv run pytest -q` — all existing tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `filter_pii("test@example.com")` returns `[REDACTED_EMAIL]`
- [ ] `filter_pii("555-123-4567")` returns `[REDACTED_PHONE]`
- [ ] `filter_pii("hello world")` returns `"hello world"` unchanged
- [ ] `StudentTraceStore` with in-memory SQLite: record + query works
- [ ] `_filter_if_student()` is no-op in developer mode
- [ ] `_log_student_trace()` is no-op in developer mode
- [ ] SQLite uses parameterized queries (no SQL injection)

### Commit

```
feat(edu): PII filtering and SQLite trace store for student mode

Phase 5 — emails/phones redacted, interactions logged to SQLite.
Verified: PII filter works, trace store works, developer mode unaffected.
```

Commit hash: _____________

---

## Phase 6: Teacher Mode — Analytics Dashboard

**Sprint Contract**: When `--mode teacher`, run analytics from SQLite and exit. No REPL. Rich terminal UI with tables and panels. Graceful handling when no data exists.

### Checklist

- [ ] 6.1 Create `educoder/teacher.py` with `run_teacher_mode()` function
- [ ] 6.2 Implement `_render_report()` with Rich (Console, Table, Panel)
- [ ] 6.3 Wire teacher mode early exit into `build_agent()` in `educoder/cli.py`
- [ ] 6.4 Handle missing `traces.db` gracefully (print message, exit 0)

### Verification (Evaluator)

- [ ] `uv run pytest -q` — all tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `uv run educoder --mode teacher` — prints "no data" message and exits (no DB)
- [ ] `uv run educoder --mode teacher --cwd /path` — reads correct workspace DB
- [ ] Rich report renders: total interactions, top errors, avg queries, suggestions
- [ ] Teacher mode does NOT launch REPL

### Commit

```
feat(edu): teacher mode analytics dashboard with Rich UI

Phase 6 — teacher mode queries SQLite and renders analytics report.
Verified: report renders, no REPL, graceful no-data handling.
```

Commit hash: _____________

---

## Phase 7: Final Validation & Tests

**Sprint Contract**: Comprehensive test coverage in `tests/test_modes.py`. Full end-to-end verification of all modes. Lint clean.

### Checklist

- [ ] 7.1 Create `tests/test_modes.py`
- [ ] 7.2 Test: CLI `--mode` parsing (student/teacher/developer/default)
- [ ] 7.3 Test: Developer mode tools match `BASE_TOOL_SPECS` keys
- [ ] 7.4 Test: Student mode tools lack write/patch/shell, has sandbox
- [ ] 7.5 Test: Student prefix contains Socratic text
- [ ] 7.6 Test: Developer prefix does NOT contain Socratic text
- [ ] 7.7 Test: `filter_pii()` redacts emails and phones
- [ ] 7.8 Test: `StudentTraceStore` in-memory record + query_metrics
- [ ] 7.9 Test: `_filter_if_student()` no-op in developer mode
- [ ] 7.10 Test: Sandbox tool with mocked Docker client

### Final Verification (Evaluator)

```bash
uv run pytest -q                      # zero regression
uv run pytest tests/test_modes.py -q  # new tests all pass
uv run ruff check .                   # lint clean
uv run educoder "hello"               # one-shot developer mode works
uv run educoder --help                # shows --mode
uv run educoder --mode student        # REPL with Socratic prompt (manual smoke test)
uv run educoder --mode teacher        # analytics report + exit
```

- [ ] All above commands succeed

### Commit

```
test(edu): comprehensive test coverage for educational modes

Phase 7 — tests for all mode-specific behavior.
Verified: all tests pass, lint clean, all modes functional.
```

Commit hash: _____________

---

## Handoff Artifact

> Filled in at the end of implementation for future context.

### What was built
- Three operating modes for EduCoder: developer (unchanged), student (Socratic tutor with sandboxed code execution), teacher (analytics dashboard)
- Docker-based sandbox for safe Python code execution in student mode
- PII filtering (email/phone redaction) for student inputs
- SQLite trace store for logging student interactions
- Rich terminal UI for teacher analytics dashboard

### Files modified
- `educoder/cli.py` — --mode arg, teacher early exit, mode passthrough
- `educoder/runtime.py` — mode param, Socratic prefix, PII filter, trace logging
- `educoder/tools.py` — mode param on registry, sandbox tool registration
- `pyproject.toml` — optional dependencies (docker, rich)

### Files created
- `educoder/sandbox.py` — Docker sandbox tool
- `educoder/pii_filter.py` — PII regex filter
- `educoder/trace_db.py` — SQLite trace store + analytics queries
- `educoder/teacher.py` — Teacher mode: Rich analytics report
- `tests/test_modes.py` — 24 mode-specific tests

### Known limitations
- Sandbox requires Docker to be installed and running (graceful error when unavailable)
- Teacher mode requires `rich` package for full UI (falls back to plain text)
- Phone regex is US-centric (matches North American number format)
- Student mode does not track code_snippet/error_traceback from sandbox runs yet (only query/response logged)

### Future improvements
- Extract code_snippet and error_traceback from sandbox tool results in ask()
- Add per-student analytics with student_id parameter
- Support multi-language PII patterns
- Add export functionality for teacher dashboard data
