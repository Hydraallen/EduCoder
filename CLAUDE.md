# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EduCoder** is a minimal local coding agent that runs in the terminal. It reads a workspace, uses constrained tools (read/write/patch files, run shell, search, delegate), and maintains session state in a local `.educoder/` directory. It supports three model backends: Ollama, OpenAI-compatible (Chat Completions API), and Anthropic-compatible (Messages API). The project has zero runtime dependencies — all HTTP calls use `urllib`.

EduCoder operates in three modes via `--mode`: **developer** (default, full tool access), **student** (Socratic tutor with Docker sandboxed code execution, no file write/shell tools), and **teacher** (analytics dashboard from student trace data, no REPL).

## Tech Stack

- **语言**: Python 3.10+
- **HTTP**: `urllib` (stdlib，零第三方依赖)
- **数据库**: `sqlite3` (stdlib，学生模式交互记录)
- **CLI**: `argparse` (stdlib)
- **测试**: pytest
- **Lint**: ruff
- **包管理**: uv / pip
- **沙箱**: Docker SDK (`docker>=7.0`，仅学生模式可选依赖)
- **终端UI**: Rich (`rich>=13.0`，仅教师模式可选依赖)
- **构建**: setuptools
- **运行时依赖**: 无 (`dependencies = []`)

## Build & Run Commands

```bash
# Install (editable)
pip install -e .
# or with uv:
uv sync

# Run agent (interactive REPL)
uv run educoder
uv run educoder --provider ollama --model qwen3.5:4b
uv run educoder --provider openai
uv run educoder --provider anthropic
uv run educoder "one-shot prompt here"

# Educational modes
uv run educoder --mode student          # Socratic REPL, Docker sandbox
uv run educoder --mode teacher          # Analytics dashboard, exits immediately

# Install optional deps (student/teacher modes only)
pip install -e ".[edu]"                 # docker + rich
pip install -e ".[student]"             # docker only
pip install -e ".[teacher]"             # rich only

# Lint
uv run ruff check .

# Tests
uv run pytest -q
uv run pytest tests/test_pico.py -q                                              # single file
uv run pytest tests/test_pico.py::test_agent_runs_tool_then_final -q            # single test
uv run pytest tests/test_modes.py -q                                             # educational mode tests

# Run as module
uv run python -m educoder --help

# Benchmark (scripted/deterministic, no real model needed)
uv run python -m educoder.evaluator

# Experiment scripts
uv run python scripts/collect_resume_metrics.py
uv run python scripts/run_large_scale_experiments.py
uv run python scripts/run_provider_experiments.py
```

## Architecture

The agent loop is: **user input → prompt assembly → model call → parse output → execute tool or return answer → repeat**.

### Core modules (`educoder/`)

| Module | Role |
|--------|------|
| `cli.py` | Entry point. Parses args (including `--mode`), builds model client, early-exits for teacher mode, creates `EduCoder`, runs REPL or one-shot. |
| `runtime.py` | `EduCoder` class — the agent runtime. Controls the ask loop, prompt building (with Socratic prefix for student mode), tool dispatch, PII filtering, trace/report writing, session management. `parse()` handles `<tool>` / `<final>` XML output parsing. Checkpoint/resume: creates checkpoints on freshness mismatch, workspace drift, context reduction; evaluates resume state on session load. Durable memory: extracts promotions from model output, persists to topic store. Secret env split: `configured_secret_env_items()` (CLI + env var config) vs `detected_secret_env_items()` (runtime scan). |
| `models.py` | Model backend adapters. `OllamaModelClient`, `OpenAICompatibleModelClient`, `AnthropicCompatibleModelClient` — each wraps HTTP differences into a uniform `complete()` interface. Includes prompt cache support for OpenAI-compatible backends. |
| `tools.py` | Tool definitions, validation, and execution. `build_tool_registry(agent, mode)` returns different tool sets per mode. Developer gets all base tools; student gets filtered set + sandbox; tools: `list_files`, `read_file`, `search`, `run_shell`, `write_file`, `patch_file`, `delegate`, `run_sandbox_code` (student only). |
| `memory.py` | `LayeredMemory` — lightweight working memory layered on top of session history. Tracks task summary, recent files, file summaries, and episodic notes. Retrieval uses token overlap (no embeddings). `DurableMemoryStore` persists topic-based notes (project-conventions, key-decisions, dependency-facts, user-preferences) to `.educoder/memory/`. `invalidate_stale_file_summaries()` clears outdated cache. |
| `context_manager.py` | Prompt assembly with character budgets. Sections: prefix → memory → relevant_memory → history → current_request. Reduces sections in priority order when over budget. Compressed history: deduplicates older reads, reuses file summaries from memory, summarizes old tool calls to one line. Checkpoint text injected into prefix section. |
| `workspace.py` | `WorkspaceContext` — captures git facts (branch, status, recent commits) and project docs (README, pyproject.toml, etc.) as a stable snapshot for the prompt prefix. |
| `task_state.py` | State machine per `ask()` call: tracks status, tool steps, attempts, stop reason, checkpoint_id, resume_status. |
| `run_store.py` | Persists run artifacts (`task_state.json`, `trace.jsonl`, `report.json`) per execution in `.educoder/runs/<run_id>/`. |
| `sandbox.py` | Docker sandbox for student mode. `tool_run_sandbox_code()` runs Python in `python:3.13-alpine` container: network disabled, 100MB memory limit, 5-second timeout. |
| `pii_filter.py` | Regex-based PII filter. Redacts emails (`[REDACTED_EMAIL]`) and phone numbers (`[REDACTED_PHONE]`). Applied to student inputs before model processing. |
| `trace_db.py` | `StudentTraceStore` — SQLite store for student interactions. Records query, code snippet, errors, agent response. `query_metrics()` returns analytics for teacher dashboard. Uses parameterized queries. |
| `teacher.py` | Teacher mode entry point. `run_teacher_mode()` reads SQLite trace data and renders Rich terminal analytics (tables, panels) or plain-text fallback. Exits without launching REPL. |
| `evaluator.py` | Benchmark harness. Loads fixture repos, runs scripted or real model tasks, verifies artifacts, writes structured JSON results. Supports checkpoint/resume/freshness/workspace-mismatch task setups. `run_harness_regression_v2()` writes to `artifacts/`. |
| `metrics.py` | Experiment suite: memory dependency, context stress matrix, security scenarios, provider comparisons, resume metrics collection. Recovery ablation: `_RecoveryScenarioModelClient` tests checkpoint resume, stale detection, workspace mismatch scenarios. `write_benchmark_core_report()` generates consolidated markdown report. |

### Key data flow

1. `cli.main()` → `build_agent()` → teacher mode early exit OR `EduCoder` instance
2. `EduCoder.ask()` is the main loop: evaluate resume state → set checkpoint triggers → PII filter (student) → build prompt (with Socratic prefix if student) → call model → parse output → dispatch tool → workspace snapshot (risky tools) → trace logging (student) → promote durable memory → repeat
3. Each tool call goes through: existence check → arg validation → duplicate detection → approval gate → execution → memory update
4. All file operations are sandboxed to workspace root (path escape + symlink prevention)

### Mode-aware behavior

All mode differences are gated on `self.mode` — developer mode is always the else-branch and remains byte-identical to pre-mode code:

- **Tool registry** (`tools.py`): Student mode filters out `write_file`/`patch_file`/`run_shell`, adds `run_sandbox_code`
- **Prompt prefix** (`runtime.py:build_prefix()`): Student mode prepends Socratic Tutor instructions
- **PII filtering** (`runtime.py:_filter_if_student()`): Student mode redacts emails/phones in user input
- **Trace logging** (`runtime.py:_log_student_trace()`): Student mode logs interactions to SQLite
- **Teacher mode** (`cli.py:build_agent()`): Early exit before creating EduCoder instance

### Key design decisions

- **Zero dependencies**: `dependencies = []` stays empty. Optional deps (`docker`, `rich`) only for student/teacher modes via `[project.optional-dependencies]`
- **Lazy imports**: `docker` and `rich` are imported inside function bodies so developer mode never loads them
- **XML-based tool protocol**: Model outputs `<tool>...</tool>` or `<final>...</final>` tags (JSON inside or XML attributes for multi-line content). `parse()` also accepts fallback formats: `<tool_name>{json}</tool_name>` and malformed `<delegate>` tags for models that don't follow the standard format
- **Base URL normalization**: `_normalize_versioned_base_url()` only strips trailing `/` — it does NOT append `/v1`. Provider base URLs must include their own version path (e.g. `/v1`, `/v4`)
- **Environment config**: `.env` file loaded at startup via `load_dotenv()` (stdlib-only). Values set first; `os.environ.get()` used as fallback. `OPENAI_API_BASE` overrides `DEFAULT_OPENAI_BASE_URL`
- **Approval policy**: `ask` (interactive), `auto` (approve all), `never` (block all risky tools)
- **Delegate**: Spawn read-only child agents with reduced step budget for investigation tasks
- **Session persistence**: Sessions saved to `.educoder/sessions/<id>.json`, resumable with `--resume`
- **Secret redaction**: Env vars with `API_KEY`/`TOKEN`/`SECRET`/`PASSWORD` in name are redacted from traces/reports
- **Feature flags**: `memory`, `relevant_memory`, `context_reduction`, `prompt_cache`, `checkpoint`, `durable_memory`, `compressed_history` — all on by default
- **Checkpoint/resume**: Sessions carry checkpoint state (goal, completed steps, next step, key files, freshness, workspace fingerprint). On resume: validates schema version, workspace fingerprint, file freshness; re-anchors stale entries
- **Durable memory**: Model output scanned for promotion patterns ("Project convention:", "Decision:", "Dependency:"). Promoted notes persisted to `.educoder/memory/` topic files. Secret-shaped text auto-rejected
- **Compressed history**: Older history entries deduplicated (duplicate reads collapsed to one), file summaries reused from memory, old tool calls summarized to single lines
- **Secret env split**: `_configured_secret_names()` reads CLI args + `EDUCODER_SECRET_ENV_NAMES` (primary), `PICO_SECRET_ENV_NAMES`, `MINI_CODING_AGENT_SECRET_ENV_NAMES` (legacy fallback) + defaults. `detected_secret_env_items()` scans runtime env. `secret_env_items()` returns union

### Tests (`tests/`)

Tests use `FakeModelClient` (returns predetermined outputs) and `tmp_path` fixtures. No real model calls needed for the core test suite. Test files mirror module names: `test_pico.py`, `test_memory.py`, `test_context_manager.py`, `test_evaluator.py`, `test_run_store.py`, `test_task_state.py`, `test_safety_invariants.py`, `test_modes.py` (educational modes).

### Benchmarks (`benchmarks/`)

`coding_tasks.json` defines scripted benchmark tasks with fixture repos (`tests/fixtures/`), step budgets, and shell verifiers. The evaluator copies fixtures to temp dirs, runs deterministic model outputs, and checks artifacts.

## Pre-existing test failures

There are 4 pre-existing test failures — NOT caused by the educational modes or upstream merge:
- `test_evaluator.py::test_run_fixed_benchmark_reports_metadata_and_success_definition` — locale environment mismatch (`en_US.UTF-8` vs `C.UTF-8`)
- `test_pico.py::test_build_agent_uses_anthropic_provider_and_openai_key_fallback` — anthropic base URL mismatch
- `test_pico.py::test_trace_and_report_redact_secret_env_values` — secret env count mismatch
- `test_pico.py::test_reviewer_skeleton_docs_exist` — `docs/review-pack/` does not exist
