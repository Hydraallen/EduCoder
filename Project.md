# EduCoder 项目详细文档

## 1. 项目概述

EduCoder 是一个运行在终端的**轻量级本地编程 Agent**。它读取本地工作区，通过受限的工具集（读/写/修补文件、执行 Shell、搜索、委派子任务）与工作区交互，并将会话状态持久化到本地 `.educoder/` 目录。

核心设计原则：

- **零运行时依赖**：所有 HTTP 调用使用 Python 标准库 `urllib`，不依赖 `requests`、`httpx` 等第三方包
- **XML 工具协议**：模型输出 `<tool>...</tool>` 或 `<final>...</final>` 标签，Agent 解析后执行
- **三模式架构**：Developer（开发者，默认全工具访问）、Student（学生，苏格拉底式导师 + Docker 沙箱）、Teacher（教师，分析仪表盘）
- **三后端模型支持**：Ollama（本地模型）、OpenAI-compatible（Responses API）、Anthropic-compatible（Messages API）

---

## 2. 项目功能

EduCoder 是一个**面向编程教学场景的终端 AI Agent 平台**。它既是一个可以实际使用的编码助手，也是一个研究 Agent 架构的教学工具。

### 2.1 核心功能——本地编码 Agent（Developer 模式）

这是 EduCoder 最基础的功能：一个在终端里运行的 AI 编程助手，能理解你的代码仓库并帮你完成任务。

**能做什么：**

- **代码阅读与理解**：浏览仓库文件结构、按行范围读取文件、全文搜索关键词，快速了解项目全貌
- **代码编写与修改**：创建新文件（`write_file`）、精确替换文件中的代码片段（`patch_file`，要求 old_text 唯一匹配）
- **命令执行**：在仓库目录下运行 Shell 命令，比如跑测试、装依赖、查看 git 状态
- **子任务委派**：当主 Agent 需要调查某个问题时，可以委派一个只读子 Agent 去探索（比如"帮我看看 tests/ 下有哪些测试文件"），子 Agent 步数有限、权限受限，结果汇总回主 Agent
- **多轮对话记忆**：Agent 维护一份轻量工作记忆，记住当前任务、最近接触过的文件、文件内容摘要，这样多轮对话中不需要反复读同一个文件
- **会话持久化与恢复**：每次会话自动保存到 `.educoder/sessions/`，下次可以用 `--resume latest` 恢复，继续上次未完成的工作

**使用场景举例：**

```bash
# 让 Agent 帮你给一个函数写测试
uv run educoder "给 binary_search 函数写单元测试"

# 让 Agent 帮你修 bug
uv run educoder
educoder> README.md 里的安装命令有拼写错误，帮我修复

# 恢复上次会话继续工作
uv run educoder --resume latest
```

### 2.2 教学功能——学生模式（Student 模式）

学生模式把 EduCoder 变成一个**不会直接给答案的编程导师**。它的设计目标是引导学生在思考中学习，而不是复制粘贴 AI 生成的代码。

**能做什么：**

- **苏格拉底式引导**：学生问"怎么写二分查找"，Agent 不会直接输出完整代码，而是反问"你觉得每次比较后应该缩小哪一半的搜索范围？"
- **安全代码执行**：学生在对话中提交的 Python 代码会在 Docker 沙箱中运行（网络禁用、100MB 内存、5 秒超时），学生可以安全地测试自己的思路
- **渐进式提示**：学生卡住 2-3 次后，Agent 才会给出带 TODO 注释的部分代码片段，而不是完整答案
- **隐私保护**：学生输入中的邮箱和电话号码会被自动脱敏，不会发送到模型
- **交互记录**：所有学生提问、代码片段、错误信息、Agent 回复都被记录到 SQLite 数据库，供教师后续查看

**使用场景举例：**

```bash
# 学生启动学习会话
uv run educoder --mode student

educoder> 我怎么把一个列表排序？
# Agent 会引导思考，而不是直接给 sorted(list)

educoder> 我的代码跑出来报错了 IndexError
# Agent 会分析错误原因，提示学生检查边界条件
```

### 2.3 教学分析——教师模式（Teacher 模式）

教师模式是一个**只读的数据分析仪表盘**，不启动 REPL，从 SQLite 数据库中读取学生的交互记录并生成报告。

**能做什么：**

- **查看学生活动概览**：总交互次数、总会话数、平均每会话查询数
- **查看常见错误**：最近 10 条学生遇到的错误，帮助教师识别需要重点讲解的知识点
- **查看最近交互**：最近 10 条学生提问和 Agent 回复
- **教学建议**：基于错误模式自动生成教学建议

**使用场景举例：**

```bash
# 教师查看分析报告
uv run educoder --mode teacher

# 输出 Rich 格式的终端报告，包含表格和面板
```

### 2.4 模型后端切换

EduCoder 支持三种模型后端，可以在本地和云端之间灵活切换：

```bash
# 本地模型（完全离线，隐私安全）
uv run educoder --provider ollama --model qwen3.5:4b

# OpenAI 兼容 API（GPT 系列）
uv run educoder --provider openai

# Anthropic 兼容 API（Claude 系列）
uv run educoder --provider anthropic
```

这意味着学生可以在没有网络的环境下使用 Ollama 本地模型学习，也可以在有 API Key 的情况下使用更强的云端模型。

### 2.5 基准测试与实验框架

EduCoder 内置了一套完整的自动化基准测试和实验框架，用于量化 Agent 各子系统的效果。

**能做什么：**

- **固定基准测试**：6 个预定义的编程任务（修改 README、修改文本文件），使用确定性模型输出，完全可复现
- **记忆系统实验**：对比"有记忆"vs"无记忆"vs"无关记忆"三种配置下 Agent 的重复工具调用次数，量化工作记忆的价值
- **上下文压力测试**：12 种配置组合（历史长度 × 笔记数量 × 请求长度），测试 prompt 预算压缩的有效性
- **安全场景测试**：10 种攻击/误用场景（路径逃逸、符号链接攻击、权限绕过等），验证安全护栏的可靠性
- **多后端对比实验**：在 GPT 和 Claude 上运行相同任务，对比 pass rate、cache hit rate、平均步数等指标

```bash
# 运行基准测试（不需要真实模型）
uv run python -m educoder.evaluator

# 运行完整实验套件
uv run python scripts/collect_resume_metrics.py
uv run python scripts/run_large_scale_experiments.py
uv run python scripts/run_provider_experiments.py
```

### 2.6 功能总览

| 功能 | Developer | Student | Teacher |
|------|-----------|---------|---------|
| 浏览文件结构 | ✅ | ✅ | — |
| 读取文件内容 | ✅ | ✅ | — |
| 搜索代码/文本 | ✅ | ✅ | — |
| 创建/写入文件 | ✅ | ❌ | — |
| 修改文件片段 | ✅ | ❌ | — |
| 执行 Shell 命令 | ✅ | ❌ | — |
| 委派子任务 | ✅ | ✅ | — |
| Docker 沙箱执行 | ❌ | ✅ | — |
| 苏格拉底式引导 | ❌ | ✅ | — |
| PII 隐私过滤 | ❌ | ✅ | — |
| 交互记录存储 | ❌ | ✅ | — |
| 学习分析仪表盘 | ❌ | ❌ | ✅ |
| 会话持久化/恢复 | ✅ | ✅ | — |
| 多模型后端切换 | ✅ | ✅ | — |

---

## 3. 整体架构

```
用户输入
  │
  ▼
cli.py (参数解析 + Agent 装配)
  │
  ▼
EduCoder.ask() ← runtime.py (Agent 控制循环核心)
  │
  ├── ContextManager.build() ← context_manager.py (Prompt 组装 + 预算控制)
  │     ├── prefix (稳定工作手册 + 工具说明)
  │     ├── memory (LayeredMemory 工作记忆摘要)
  │     ├── relevant_memory (按相关性召回的笔记)
  │     ├── history (最近会话历史)
  │     └── current_request (当前用户请求)
  │
  ├── ModelClient.complete() ← models.py (模型调用)
  │     ├── OllamaModelClient
  │     ├── OpenAICompatibleModelClient
  │     └── AnthropicCompatibleModelClient
  │
  ├── EduCoder.parse() (解析模型 XML 输出)
  │     ├── "tool" → run_tool()
  │     ├── "final" → 返回最终答案
  │     └── "retry" → 提示模型重试
  │
  ├── run_tool() (工具执行流水线)
  │     ├── 工具存在性检查
  │     ├── 参数校验
  │     ├── 重复调用检测
  │     ├── 审批门控
  │     ├── 执行 + 结果裁剪
  │     └── 工作记忆更新
  │
  └── 持久化
        ├── SessionStore → .educoder/sessions/<id>.json
        ├── RunStore → .educoder/runs/<run_id>/ (task_state.json, trace.jsonl, report.json)
        └── StudentTraceStore → .educoder/traces.db (SQLite, 学生模式)
```

---

## 4. 核心模块详解

### 4.1 cli.py — 命令行入口

**职责**：把用户启动参数翻译成 runtime 能理解的对象。

**关键函数**：

- `build_arg_parser()`：定义所有 CLI 参数，包括 `--provider`、`--model`、`--mode`（developer/student/teacher）、`--approval`（ask/auto/never）、`--resume` 等
- `_build_model_client(args)`：根据 `--provider` 选择创建 `OllamaModelClient`、`OpenAICompatibleModelClient` 或 `AnthropicCompatibleModelClient`
- `build_agent(args)`：核心装配函数。先处理 teacher 模式的早期退出，再收集 secret 环境变量名，采集工作区快照，创建或恢复 session，最终返回 `EduCoder` 实例
- `main()`：解析参数 → 装配 Agent → 打印欢迎画面 → 进入 one-shot 或交互式 REPL 循环

**模式路由**：

```
--mode teacher  → run_teacher_mode() → 打印分析报告 → 退出
--mode student  → EduCoder(mode="student") → 苏格拉底式 REPL
--mode developer → EduCoder(mode="developer") → 标准 REPL (默认)
```

### 3.2 runtime.py — Agent 运行时核心

**核心类 `EduCoder`**，是整个系统的调度中心。

#### 4.2.1 初始化 (`__init__`)

构建完整的 Agent 运行现场：

1. 保存模型客户端、工作区、审批策略、模式配置
2. 初始化 `LayeredMemory`（工作记忆）
3. 调用 `build_tools()` 根据模式构建工具注册表
4. 调用 `build_prefix()` 构建稳定前缀（含苏格拉底指令，若学生模式）
5. 创建 `ContextManager` 负责后续 prompt 组装
6. 保存初始 session 到磁盘

#### 4.2.2 主循环 `ask(user_message)`

这是整个 Agent 最关键的函数，执行一次完整的"用户请求 → 最终答案"回合：

```
1. PII 过滤（学生模式）
2. 设置任务摘要到工作记忆
3. 记录用户消息到 history
4. 创建 TaskState + RunStore run 目录
5. 进入主循环（tool_steps < max_steps 且 attempts < max_attempts）：
   a. 重新组装 prompt（含前缀刷新）
   b. 调用 model_client.complete() 获取模型输出
   c. 解析模型输出（parse()）：
      - "tool" → 执行工具 → 记录结果 → 更新记忆 → 继续
      - "final" → 记录 → 写报告 → 返回答案
      - "retry" → 记录 → 继续
6. 超出限制时返回停止原因说明
```

#### 4.2.3 工具执行流水线 `run_tool(name, args)`

工具执行不是"直接调函数"，而是一条带护栏的流水线：

```
工具是否存在 → 参数校验 → 重复调用检测 → 审批门控 → 执行 → 结果裁剪 → 记忆更新
```

每一步都会产生 `_last_tool_result_metadata`，记录 `tool_status`（ok/rejected/error）、`tool_error_code`、`security_event_type`。

#### 4.2.4 输出解析 `parse(raw)`

支持两种 XML 格式：

1. **JSON 格式**：`<tool>{"name":"read_file","args":{"path":"README.md"}}</tool>` — 适合简短调用
2. **XML 属性格式**：`<tool name="write_file" path="file.py"><content>...</content></tool>` — 适合多行内容

解析优先级：`<tool>` > XML 风格 `<tool` > `<final>` > 裸文本

#### 4.2.5 前缀管理

- `build_prefix()`：构建 agent 的"工作手册"——身份、工具说明、工作区状态
- `refresh_prefix()`：检查工作区指纹是否变化，按需重建前缀（避免频繁重建）
- `PromptPrefix` 数据类：携带文本、哈希、工作区指纹、工具签名，用于判断前缀是否可复用

#### 4.2.6 安全机制

- **路径沙箱**：`path()` 方法将所有文件操作锚定在 workspace root 下，防止 `../` 逃逸和符号链接攻击
- **Secret 脱敏**：`redact_text()` / `redact_artifact()` 在 trace 和 report 中自动替换敏感环境变量值
- **审批策略**：`approve()` 根据策略（ask/auto/never）决定是否放行高风险工具
- **只读模式**：`read_only=True` 时完全阻止所有写操作
- **重复调用检测**：`repeated_tool_call()` 检测连续两次完全相同的工具调用

### 4.3 models.py — 模型后端适配层

抹平不同 provider 的 HTTP 接口、响应结构差异，对外暴露统一的 `complete(prompt, max_new_tokens)` 接口。

#### 4.3.1 OllamaModelClient

- 端点：`POST /api/generate`
- 请求体：`{model, prompt, stream:false, options:{num_predict, temperature, top_p}}`
- 不支持 prompt cache

#### 4.3.2 OpenAICompatibleModelClient

- 端点：`POST {base_url}/v1/responses`（Responses API）
- 请求体：`{model, input:[{role:"user", content:[{type:"input_text", text:prompt}]}], max_output_tokens}`
- **Prompt Cache 支持**：当 base_url 包含 `openai.com` 或 `right.codes` 时启用，传递 `prompt_cache_key`（稳定前缀的 SHA256）和 `prompt_cache_retention`
- 同时处理 SSE 流式响应和普通 JSON 响应
- 内置重试（3 次，仅 500 错误和连接错误）

**SSE 解析链路**：`_extract_openai_text_from_sse()` → 按优先级尝试提取 `response.output_text.done`、`response.completed`、delta 聚合等

**Usage 提取**：`_extract_usage_cache_details()` → 统一提取 `input_tokens`、`output_tokens`、`cached_tokens`

#### 4.3.3 AnthropicCompatibleModelClient

- 端点：`POST {base_url}/v1/messages`（Messages API）
- 请求体：`{model, messages:[{role:"user", content:[{type:"text", text:prompt}]}], max_tokens}`
- 不支持 prompt cache（显式丢弃缓存参数）

#### 4.3.4 FakeModelClient

测试用伪造客户端，按预设队列返回固定输出，同时记录所有收到的 prompt。

### 4.4 tools.py — 工具定义与执行

#### 4.4.1 工具注册表

`build_tool_registry(agent, mode)` 根据模式返回不同的工具集：

| 工具 | Schema | 风险 | Developer | Student |
|------|--------|------|-----------|---------|
| `list_files` | `{path:str='.'}` | 安全 | ✅ | ✅ |
| `read_file` | `{path:str, start:int=1, end:int=200}` | 安全 | ✅ | ✅ |
| `search` | `{pattern:str, path:str='.'}` | 安全 | ✅ | ✅ |
| `run_shell` | `{command:str, timeout:int=20}` | 高危 | ✅ | ❌ |
| `write_file` | `{path:str, content:str}` | 高危 | ✅ | ❌ |
| `patch_file` | `{path:str, old_text:str, new_text:str}` | 高危 | ✅ | ❌ |
| `delegate` | `{task:str, max_steps:int=3}` | 安全 | ✅ (depth<N) | ✅ (depth<N) |
| `run_sandbox_code` | `{code:str}` | 安全 | ❌ | ✅ |

#### 4.4.2 各工具实现细节

**list_files**：列出指定目录下 200 个以内的文件/目录，按 (is_file, name) 排序，过滤掉 `.git`、`.educoder`、`__pycache__` 等。

**read_file**：按行范围读取 UTF-8 文件，输出格式为 `行号: 内容`。

**search**：优先使用 `rg`（ripgrep）进行智能大小写搜索；回退到 Python 逐文件逐行匹配。

**run_shell**：在 workspace root 执行 shell 命令，使用过滤后的环境变量（仅白名单），返回 exit_code + stdout + stderr。

**write_file**：写入文件，自动创建父目录。

**patch_file**：精确替换——`old_text` 必须在文件中**恰好出现一次**，否则拒绝。这是刻意的设计，确保修改行为是确定的。

**delegate**：创建一个**只读子 Agent**（depth+1），以 `never` 审批策略运行，步数更少。子 Agent 只做调查，不做修改。

**run_sandbox_code**（学生模式专属）：见 sandbox.py。

### 4.5 memory.py — 轻量工作记忆

`LayeredMemory` 是一层轻量的工作集，叠加在完整 session history 之上。设计目标是"让下一轮 prompt 还能接上上一轮，但不被整段历史塞满"。

#### 4.5.1 状态结构

```python
{
    "working": {
        "task_summary": str,       # 当前任务摘要 (≤300字)
        "recent_files": [str],     # 最近接触的文件路径 (≤8个)
    },
    "episodic_notes": [dict],      # 情景笔记 (≤12条)
    "file_summaries": {            # 文件摘要 (≤6个)
        "path": {
            "summary": str,
            "created_at": str,
            "freshness": str,      # SHA256，用于判断摘要是否过期
        }
    },
}
```

#### 4.5.2 记忆更新时机

在 `update_memory_after_tool()` 中触发：

- **read_file**：记住文件路径 + 生成文件摘要 + 添加情景笔记
- **write_file / patch_file**：记住文件路径 + 使旧摘要失效（因为内容已变）

#### 4.5.3 记忆检索

`retrieval_candidates(query, limit=3)`：基于 token 重叠的简单检索——先看 tag 精确命中，再看关键词重叠，最后看时间新旧。不引入 embedding。

### 4.6 context_manager.py — Prompt 组装与预算控制

#### 4.6.1 五段式 Prompt 结构

按固定顺序组装：

1. **prefix**（3600 字符预算）：稳定的工作手册——身份、规则、工具说明、工作区状态
2. **memory**（1600 字符预算）：工作记忆摘要——任务、文件列表、笔记数量
3. **relevant_memory**（1200 字符预算）：按相关性召回的笔记详情
4. **history**（5200 字符预算）：最近会话历史
5. **current_request**（无预算限制）：当前用户请求

总预算：12000 字符。

#### 4.6.2 超预算压缩策略

当 prompt 超出总预算时，按优先级从低到高压缩：

```
relevant_memory → history → memory → prefix
```

`current_request` 永远不裁剪。

#### 4.6.3 历史段渲染

- 优先保留最近 6 条历史
- 最近条目每条最多 900 字符，旧条目最多 60 字符
- 从旧到新逐步尝试塞入预算

### 4.7 workspace.py — 工作区快照

在 Agent 读文件之前，先给它一份便宜的"仓库第一印象"。

**收集内容**：

- Git 事实：cwd、repo_root、branch、default_branch、status、最近 5 条 commit
- 项目文档：从 `AGENTS.md`、`README.md`、`pyproject.toml`、`package.json` 中各截取最多 1200 字符

**指纹机制**：`fingerprint()` 返回整个快照的 SHA256，用于判断工作区是否发生了足够大的变化来触发前缀重建。

### 4.8 task_state.py — 运行状态机

跟踪一次 `ask()` 调用的完整生命周期：

| 字段 | 含义 |
|------|------|
| `status` | running / completed / stopped / failed |
| `tool_steps` | 真正执行的工具次数 |
| `attempts` | 模型被调用的总轮次（含 retry） |
| `stop_reason` | final_answer_returned / step_limit_reached / retry_limit_reached / ... |

### 4.9 run_store.py — 运行工件落盘

每次 `ask()` 生成一个 run 目录 `.educoder/runs/<run_id>/`，包含：

| 文件 | 格式 | 内容 |
|------|------|------|
| `task_state.json` | JSON | 状态机快照，运行中不断更新 |
| `trace.jsonl` | JSONL | 逐事件时间线（run_started、prompt_built、model_requested、tool_executed、run_finished） |
| `report.json` | JSON | 最终摘要（状态、步数、prompt 元数据、secret 脱敏统计） |

**原子写**：`_write_json_atomic()` 先写临时文件再 replace，防止中途异常留下半截 JSON。

### 4.10 sandbox.py — Docker 沙箱（学生模式）

学生模式专属的安全代码执行环境。

**实现**：

- 使用 `docker` SDK 在 `python:3.13-alpine` 容器中执行 Python 代码
- 安全限制：网络禁用、100MB 内存上限、5 秒硬超时
- 使用独立线程 + `thread.join(timeout=5)` 实现超时控制
- 返回 stdout 或 stderr（容器错误时）

### 4.11 pii_filter.py — PII 过滤（学生模式）

使用正则表达式脱敏两类个人信息：

- 邮箱：`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` → `[REDACTED_EMAIL]`
- 电话号码：美国格式 `(?\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}` → `[REDACTED_PHONE]`

在学生模式中，用户输入在进入模型之前先经过此过滤器。

### 4.12 trace_db.py — SQLite 交互记录（学生模式）

使用 SQLite 存储学生交互记录，供教师模式查询分析。

**表结构 `student_traces`**：

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | INTEGER PK | 自增 ID |
| `timestamp` | TEXT | UTC 时间戳 |
| `session_id` | TEXT | 会话 ID |
| `student_id` | TEXT | 学生 ID（默认 student_01） |
| `query` | TEXT | 学生提问 |
| `code_snippet` | TEXT | 代码片段 |
| `error_traceback` | TEXT | 错误信息 |
| `agent_response` | TEXT | Agent 回复 |

**分析查询 `query_metrics()`**：返回总交互数、总会话数、平均每会话查询数、最近 10 条错误、最近 10 条交互记录。

### 4.13 teacher.py — 教师分析仪表盘

从 SQLite 读取学生交互数据，渲染终端分析报告，然后退出（无 REPL）。

**渲染方式**：

- **Rich 模式**（安装了 `rich>=13.0`）：彩色面板 + 表格，包含 Session Summary、Recent Errors、Recent Interactions、Teaching Suggestions
- **纯文本回退**：无 Rich 时的简单文本输出

### 4.14 evaluator.py — 基准测试框架

自动化测试 Agent 在固定任务上的表现。

**工作流**：

1. 从 `benchmarks/coding_tasks.json` 加载任务定义
2. 为每个任务复制 fixture repo 到临时目录
3. 创建 `FakeModelClient`（返回预设输出）或真实模型客户端
4. 运行 `agent.ask(task_prompt)`
5. 检查：产物是否存在、verifier 是否通过、是否在步数预算内、停止原因是否正常
6. 写出结构化 JSON 结果到 `benchmarks/benchmark-v1.json`

**确定性设计**：使用 `FakeModelClient` + 预设输出，基准测试完全可复现，不需要真实模型。

### 4.15 metrics.py — 实验套件

包含多组实验，用于量化 Agent 各子系统的效果：

| 实验 | 度量目标 | 方法 |
|------|----------|------|
| Memory Dependency | 工作记忆是否减少重复工具调用 | 对比 memory_on / memory_off / memory_irrelevant 三种配置下的重复读取次数 |
| Large-Scale Memory | 12 种任务 × 3 种配置的扩展验证 | fact_lookup / edit_dependency / history_reference 三类任务 |
| Context Stress Matrix | 上下文预算压缩的有效性 | 3×2×2 = 12 种配置组合（history × notes × request 长度） |
| Security Experiment | 10 种安全场景是否被正确拦截 | path_escape / symlink_escape / approval_denied / read_only / repeated_call 等 |
| Provider Experiment | 不同模型后端的性能对比 | GPT vs Claude，比较 pass_rate、cache_hit_rate、avg_attempts |
| Resume Metrics | 汇总所有实验为可展示的指标 | 收集 benchmark、runs、stress、memory、context、security 数据 |

---

## 5. 三种运行模式

### 5.1 Developer 模式（默认）

完整的本地编码 Agent，拥有全部工具访问权限。

**数据流**：

```
用户输入 → ask() → build prompt → 调用模型 → 解析输出 → 执行工具 → 返回答案
```

### 5.2 Student 模式

苏格拉底式教学导师，安全地引导学生学习编程。

**与 Developer 模式的差异**：

| 维度 | Developer | Student |
|------|-----------|---------|
| 工具集 | 全部 7 个 | list_files + read_file + search + delegate + run_sandbox_code |
| 写文件/Shell | ✅ | ❌ |
| Prompt 前缀 | 标准 Agent 指令 | 苏格拉底教学指令（禁止直接给出完整答案） |
| PII 过滤 | 无 | 自动脱敏邮箱和电话号码 |
| 交互记录 | JSONL trace | SQLite traces.db |
| 代码执行 | run_shell | run_sandbox_code（Docker 沙箱） |

**苏格拉底指令核心**：

- 不输出完整可复制粘贴的代码
- 当学生遇到错误时，提问引导而非直接解答
- 学生卡住 2-3 次后，可以给出带 TODO 的部分代码片段
- 使用 `run_sandbox_code` 让学生安全测试代码

### 5.3 Teacher 模式

只读分析仪表盘，不启动 REPL。

**数据流**：

```
--mode teacher → build_agent() → run_teacher_mode()
  → 读取 .educoder/traces.db
  → query_metrics()
  → 渲染 Rich/纯文本报告
  → 退出
```

---

## 6. 模型后端支持

### 6.1 Ollama（本地模型）

```bash
uv run educoder --provider ollama --model qwen3.5:4b
```

- 调用 `/api/generate` 端点
- 支持 `temperature` 和 `top_p` 参数
- 不支持 prompt cache

### 6.2 OpenAI-Compatible（远程 API）

```bash
uv run educoder --provider openai
```

- 调用 Responses API（`/v1/responses`）
- 自动识别 SSE 流式响应和普通 JSON 响应
- 支持 prompt cache（通过 `prompt_cache_key` 复用稳定前缀）
- 默认模型：`gpt-5.4`，默认 base URL：`https://www.right.codes/codex/v1`

### 6.3 Anthropic-Compatible（远程 API）

```bash
uv run educoder --provider anthropic
```

- 调用 Messages API（`/v1/messages`）
- 不支持 prompt cache（当前版本）
- 默认模型：`claude-sonnet-4-6`，默认 base URL：`https://www.right.codes/claude/v1`

---

## 7. 持久化与会话管理

### 7.1 Session（会话）

- 存储路径：`.educoder/sessions/<timestamp>-<uuid>.json`
- 内容：session ID、workspace root、完整 history、memory state
- 支持 `--resume latest` 恢复最近的会话
- REPL 中 `/reset` 清空 history 和 memory

### 7.2 Run（单次运行）

- 存储路径：`.educoder/runs/<run_id>/`
- 每次 `ask()` 生成一个独立的 run 目录
- 包含三个工件：task_state.json、trace.jsonl、report.json
- trace 采用 JSONL 追加写入，适合调试和审计

---

## 8. 安全设计

### 8.1 工具执行护栏

所有工具调用必须经过 `run_tool()` 的五层防护：

1. **工具存在性**：未知工具直接拒绝
2. **参数校验**：路径必须是合法文件、行范围合理、命令不为空等
3. **重复检测**：连续两次完全相同的调用被拦截
4. **审批门控**：高风险工具需要确认（ask 策略）、自动放行（auto）、全部拒绝（never）
5. **只读保护**：子 Agent 和学生模式禁止写操作

### 8.2 路径沙箱

`path()` 方法确保所有文件操作被锚定在 workspace root 下：

- 解析相对路径为绝对路径
- 使用 `resolve()` 处理 `..` 和符号链接
- 通过 `os.path.commonpath()` 检查是否逃逸

### 8.3 环境变量保护

- Shell 执行时只传递白名单环境变量（HOME、PATH、LANG 等）
- Secret 变量（包含 `API_KEY`、`TOKEN`、`SECRET`、`PASSWORD`）的值在 trace/report 中被替换为 `<redacted>`

### 8.4 PII 过滤（学生模式）

用户输入中的邮箱和电话号码在进入模型之前被自动脱敏。

---

## 9. 特性开关

通过 `feature_flags` 控制四个特性，默认全部开启：

| 开关 | 作用 |
|------|------|
| `memory` | 启用/禁用工作记忆系统 |
| `relevant_memory` | 启用/禁用相关性记忆召回 |
| `context_reduction` | 启用/禁用 prompt 超预算压缩 |
| `prompt_cache` | 启用/禁用稳定前缀缓存复用 |

---

## 10. 测试与基准

### 10.1 测试

测试使用 `FakeModelClient`（返回预设输出）和 `tmp_path` fixture，不需要真实模型调用。

| 文件 | 覆盖模块 |
|------|----------|
| `test_pico.py` | runtime.py 核心流程 |
| `test_memory.py` | memory.py 工作记忆 |
| `test_context_manager.py` | context_manager.py prompt 组装 |
| `test_evaluator.py` | evaluator.py 基准测试 |
| `test_run_store.py` | run_store.py 持久化 |
| `test_task_state.py` | task_state.py 状态机 |
| `test_safety_invariants.py` | 安全不变量 |
| `test_modes.py` | 三种教育模式 |

### 10.2 基准测试

`benchmarks/coding_tasks.json` 定义了 6 个固定任务：

- 3 个 documentation 类别（README 修改）
- 3 个 text-edit 类别（sample.txt 修改）

每个任务指定：prompt、fixture repo、允许工具、步数预算、预期产物、shell verifier。

---

## 11. 项目结构

```
EduCoder/
├── educoder/                    # 核心代码包
│   ├── __init__.py              # 导出 cli.main
│   ├── __main__.py              # python -m educoder 入口
│   ├── cli.py                   # CLI 参数解析 + Agent 装配
│   ├── runtime.py               # EduCoder Agent 运行时
│   ├── models.py                # 三后端模型适配层
│   ├── tools.py                 # 工具定义、校验与执行
│   ├── memory.py                # LayeredMemory 工作记忆
│   ├── context_manager.py       # Prompt 组装与预算控制
│   ├── workspace.py             # 工作区快照（Git + 文档）
│   ├── task_state.py            # 运行状态机
│   ├── run_store.py             # 运行工件落盘
│   ├── sandbox.py               # Docker 沙箱（学生模式）
│   ├── pii_filter.py            # PII 脱敏（学生模式）
│   ├── trace_db.py              # SQLite 交互记录（学生模式）
│   ├── teacher.py               # 教师分析仪表盘
│   ├── evaluator.py             # 基准测试框架
│   └── metrics.py               # 实验套件
├── tests/                       # 测试目录
│   ├── fixtures/                # 基准测试 fixture repo
│   ├── test_pico.py
│   ├── test_memory.py
│   ├── test_context_manager.py
│   ├── test_evaluator.py
│   ├── test_run_store.py
│   ├── test_task_state.py
│   ├── test_safety_invariants.py
│   └── test_modes.py
├── benchmarks/                  # 基准任务定义
│   └── coding_tasks.json
├── scripts/                     # 实验脚本
│   ├── collect_resume_metrics.py
│   ├── run_large_scale_experiments.py
│   └── run_provider_experiments.py
├── pyproject.toml               # 项目配置（零依赖 + 可选依赖）
├── CLAUDE.md                    # 开发指南
├── README.md                    # 项目介绍
└── PROGRESS.md                  # 开发进度
```

---

## 12. 技术栈总结

| 类别 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | 核心开发语言 |
| HTTP | `urllib` (stdlib) | 零第三方依赖的模型调用 |
| 数据库 | `sqlite3` (stdlib) | 学生模式交互记录 |
| CLI | `argparse` (stdlib) | 命令行参数解析 |
| 测试 | pytest | 单元测试 + 集成测试 |
| Lint | ruff | 代码风格检查 |
| 包管理 | uv / pip | 依赖管理与构建 |
| 沙箱 | Docker SDK (`docker>=7.0`) | 学生模式可选依赖 |
| 终端 UI | Rich (`rich>=13.0`) | 教师模式可选依赖 |
| 构建 | setuptools | 包构建 |
| 运行时依赖 | **无** | `dependencies = []` |

---

## 13. 简历写法建议

以下提供多个版本，按投递方向和个人风格选择。关键是**用数据说话、突出设计决策、少写"做了什么"、多写"为什么这么做"**。

### 13.1 简短版（适合项目列表，3-4 行）

> **EduCoder — 轻量级终端 AI 编程 Agent** | Python | [GitHub 链接]
>
> 从零构建了一个零第三方依赖的本地编码 Agent，支持 Ollama / OpenAI / Anthropic 三种模型后端，实现工具调用循环（文件读写、Shell 执行、子任务委派）、分层工作记忆、Prompt 预算压缩和稳定前缀缓存复用。扩展了苏格拉底式教学模式（Docker 沙箱 + PII 过滤 + SQLite 交互追踪），以及教师分析仪表盘。

### 13.2 中等版（适合项目经历主体，5-8 行）

> **EduCoder — 终端 AI 编程 Agent 平台** | Python, Docker, SQLite, Rich | [GitHub 链接]
>
> - 设计并实现了一个零运行时依赖（`dependencies = []`）的 Agent 运行时，用 `urllib` 直连 Ollama / GPT / Claude 三种 API，通过 XML 协议解析模型输出的工具调用
> - 构建 7 种工具的执行流水线（五层安全护栏：存在性→校验→去重→审批→沙箱），路径操作锚定 workspace root 防止逃逸和符号链接攻击
> - 实现 `LayeredMemory` 分层工作记忆 + 基于关键词重叠的记忆召回，配合 12 字符总预算的五段式 Prompt 组装器，在超预算时按优先级自动裁剪
> - 扩展教育场景：学生模式（苏格拉底式引导 + Docker 沙箱代码执行 + PII 脱敏）、教师模式（SQLite 追踪 + Rich 终端分析仪表盘）
> - 内置确定性基准测试框架（6 任务 × 可复现 FakeModelClient）和 5 组实验（记忆依赖、上下文压力矩阵、10 种安全场景、多后端对比），量化各子系统效果

### 13.3 按投递方向定制的侧重点

#### 偏 AI / LLM 工程岗

强调 Prompt 工程、Agent 架构、模型集成：

> - 设计了五段式 Prompt 组装管线（prefix → memory → relevant_memory → history → request），总预算 12K 字符，超预算时按 `relevant_memory → history → memory → prefix` 优先级自动压缩
> - 实现稳定前缀缓存复用机制：将工具说明和工作区快照的 SHA256 作为 `prompt_cache_key`，避免因动态 history 变化导致缓存失效
> - 抹平 Ollama / OpenAI Responses API / Anthropic Messages API 的 HTTP 和响应格式差异（含 SSE 流式解析），对外暴露统一的 `complete()` 接口
> - 实现 XML 工具协议解析器，支持 JSON 和 XML 属性两种格式，含 retry 机制处理模型格式错误

#### 偏后端 / 系统工程岗

强调安全设计、持久化、零依赖架构：

> - 从零实现 Agent 运行时控制循环，零第三方运行时依赖（纯 `urllib` HTTP、`sqlite3` 存储、`argparse` CLI），`dependencies = []`
> - 设计五层工具执行护栏（存在性→参数校验→重复检测→审批门控→只读保护），路径沙箱通过 `resolve()` + `commonpath()` 防止 `../` 逃逸和符号链接攻击
> - 实现原子写持久化（临时文件 + replace）、JSONL 追加写入 trace、SQLite 参数化查询存储学生交互
> - Docker 沙箱隔离执行：网络禁用、100MB 内存上限、5 秒硬超时、独立线程控制

#### 偏教育科技岗

强调教学模式设计、学生隐私、数据分析：

> - 设计三模式架构：Developer（全功能 Agent）、Student（苏格拉底式引导 + 安全沙箱）、Teacher（分析仪表盘），三种模式共享核心运行时，通过 `mode` 字段差异化管理工具集、Prompt 前缀和 PII 过滤
> - 学生模式实现正则 PII 脱敏（邮箱/电话）、Docker 沙箱安全执行、SQLite 全量交互追踪（提问、代码、错误、回复），教师模式通过 Rich 终端 UI 展示学习分析报告
> - 苏格拉底式 Prompt 注入：禁止直接输出完整答案，引导 2-3 轮后渐进给出带 TODO 的部分代码片段

### 13.4 面试可能被问到的问题（提前准备）

**架构层面：**

- 为什么选择 XML 协议而不是 JSON 协议来做工具调用？（多行内容不需要 JSON 转义、XML 属性天然适合文件路径等元数据）
- 记忆系统为什么不用 embedding？（项目追求零依赖、轻量级；token overlap 在小规模工作记忆下足够；可以聊如果规模增大怎么升级）
- 为什么 prompt 分五段而不是一股脑拼进去？（不同段的更新频率不同——prefix 几乎不变、history 每轮都变；分段才能做有优先级的预算裁剪）

**工程层面：**

- 零依赖是怎么做到的？有哪些取舍？（`urllib` 处理 SSE 需要手动解析、没有连接池、没有自动重试——但代码里手动实现了重试和 SSE 解析）
- 路径沙箱的具体实现？（`resolve()` 处理 `..` 和 symlink → `commonpath()` 检查是否在 root 下）
- 原子写怎么做的？为什么不用 `json.dump` 直接写？（`tempfile` + `replace`，防止中途崩溃留下半截文件）

**AI/Agent 层面：**

- prompt cache 的 key 为什么是 prefix 的 hash 而不是整个 prompt 的 hash？（prefix 是稳定段，history 是动态段；缓存 prefix 才能跨轮复用，如果 key 包含 history 则每轮都失效）
- delegate 子 Agent 和主 Agent 有什么区别？（depth+1、只读、步数更少、approval_policy="never"、共享 model_client）
- 怎么防止 Agent 陷入死循环？（重复调用检测：最近两次完全相同则拒绝；步数上限 + 重试上限双保险）
