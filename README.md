# RFP Manager

Multi-agent pipeline that processes raw client documents — transcripts, PDFs, chats, briefs — and produces either a structured requirements document or a discovery report with architecture questions ready for a workshop.

---

## Pipelines

![Fig. 1. Two processing pipelines — Extract and Discovery](docs/illustrations/pipeline.png)

*Fig. 1. Both pipelines share Phase 0 (scan) and Phase 1 (parallel extraction). Extract mode adds Requirements Writer + Critic loop. Discovery mode adds arch_probe + arch_critic.*

Two modes, same input:

| Mode | Flag | What it produces | When to use |
|---|---|---|---|
| `extract` | `--mode extract` (default) | `_requirements.md` — FR / NFR / BR / conflicts / gaps | When you need a structured spec from raw source docs |
| `discovery` | `--mode discovery` | `discovery_report.md` — curated architect questions per gap, AI-detection assessment | Before a workshop; when you need to understand what's missing |

---

## Quick Start

```bash
# Clone and set up
git clone <repo>
cd rfp-manager
python3 -m venv .venv && .venv/bin/pip install loguru pyyaml

# Configure
cp .env.example .env   # add OPENAI_API_KEY (for Illustrator agent)

# Run requirements extraction (default mode)
python3 runner.py run /path/to/project/input

# Run discovery
python3 runner.py run /path/to/project/input --mode discovery

# Interactive (HITL pauses at checkpoints)
python3 runner.py run /path/to/project/input --interactive

# Verbose logging
python3 runner.py run /path/to/project/input --debug
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--mode` | `extract` | `extract` or `discovery` |
| `--interactive` | off | Pause at HITL checkpoints for clarification |
| `--no-interactive` | — | Explicitly skip all HITL pauses (headless) |
| `--debug` | off | Enable DEBUG-level logging to stderr |

---

## Input: What Goes in `input/`

Drop any combination of:

- `.pdf` — RFP documents, proposals, specs (read via `mcp_pdf-reader`)
- `.docx` / `.pptx` / `.xlsx` — Office documents
- `.md` / `.txt` — meeting notes, briefs, chat exports
- `.png` / `.jpg` / `.jpeg` / `.webp` — screenshots, architecture images (read via vision)
- Subfolders — treated as a single logical source (one agent per folder)
- `.txt` files containing URLs — Confluence pages fetched via MCP; plain URLs fetched directly

**Excluded automatically:** `plan/`, `.git/`, any folder starting with `_artifacts`.

---

## Output Structure

Every run creates a **self-contained timestamped folder** sibling to `input/`:

```
project/
  input/                              ← your source documents (untouched)
  requirements_20260521_152709/       ← or discovery_20260521_...
    _requirements.md                  ← the deliverable
    plan/
      params.yaml                     ← run parameters (editable before re-run)
    _artifacts_20260521_152709/
      runner.log
      intake/
        manifest.json                 ← all scanned entries with extract status
      extracts/
        <slug>/
          extract.json                ← structured output per source
          raw.txt                     ← raw agent response
          agent.jsonl                 ← full copilot CLI JSONL log
        _requirements_writer/
          agent.jsonl
        _requirements_critic_r1/
          verdict.md                  ← VERDICT: APPROVED / REVISE
          agent.jsonl
      prompts/
        <slug>.md                     ← task prompt sent to each agent
        _requirements_writer.md
        _requirements_critic_r1.md
```

---

## Pipeline Details

### Extract Mode — 4 Phases

```
Phase 0 → Phase 1 (parallel) → Phase 2 → Phase 3 (loop)
  scan      source_processor    writer     critic ↔ writer
```

#### Phase 0 — Scan + Manifest

`runner.py` walks `input/`, classifies every item, builds `manifest.json`:

| Entry kind | What it is | Read tool |
|---|---|---|
| `file` | Single `.pdf`, `.docx`, `.md`, image, etc. | `mcp_pdf-reader` / `vision` / `read` |
| `subfolder` | A directory of related files | `mixed` / `read` |
| `url` | URL from a `.txt` file | `mcp_confluence` or `fetch` |

#### Phase 1 — Parallel Source Extraction

One `source_processor` agent per manifest entry, all launched concurrently via `ThreadPoolExecutor`. Each agent:

- identifies the document type (transcript / chat / brief / PDF / spreadsheet / QA)
- applies the matching extraction strategy
- outputs `extract.json` with: `requirements`, `decisions`, `constraints`, `open_questions`, `trust_level`

Agent timeout: **20 minutes** per agent. Heartbeat printed every 10 s:

```
[16:09:10] [rfp-doc] start
[16:09:20] [rfp-doc] running... 10s elapsed, timeout in 1190s
[16:09:41] [rfp-doc] done
```

**HITL:clarify (if `--interactive`).** If any agent returns `needs_clarification: true`, runner pauses and prompts the user in terminal. Answered agents are re-run with the clarification appended to the prompt. Up to **2 clarification rounds**.

#### Phase 2 — Requirements Writer

`requirements_writer` reads all successful `extract.json` files and synthesises `_requirements.md`:

- Functional requirements (FR-001, FR-002, …)
- Non-functional requirements (NFR-001, …)
- Business requirements (BR-001, …)
- Conflict register — contradictions between sources
- Gap register — unanswered questions
- Assumptions

Output validated: must contain `# Requirements:` title and at least one `FR-` entry.

#### Phase 3 — Critic ↔ Writer Loop

`requirements_critic` reads `_requirements.md`, cross-checks against source extracts, writes a verdict:

```
VERDICT: APPROVED          ← loop ends, document is final
VERDICT: REVISE
- Section 2.1: missing NFR for ...
- Conflict FR-004 vs FR-017 unresolved
```

If `REVISE` — verdict is injected into the writer's next prompt and `requirements_writer` runs a revision. This repeats until **`APPROVED`** or the **safety cap of 5 rounds** (`MAX_CRITIC_ROUNDS`). Hitting the cap is a warning, not a failure — the document is kept as-is.

---

### Discovery Mode — 4 Phases

```
Phase 0 → Phase 1 (parallel) → Phase D1 → Phase D2
  scan      source_processor    probe      critic
```

Phases 0 and 1 are identical to Extract mode.

#### Phase D1 — arch_probe

Reads all `extract.json` files and:

- scores each source for AI-generation signals (produces `ai_detection` section)
- runs Tavily web searches for domain context
- generates **20–30 raw discovery questions** — each tied to a specific gap or contradiction
- writes structured JSON to `_arch_probe/probe_output.json`

#### Phase D2 — arch_critic

Reads `probe_output.json` and:

- rejects generic or answerable questions
- curates **8–15 questions** that block architecture decisions if unanswered
- writes `discovery_report.md` directly to the output folder

---

## Architecture

![Fig. 2. runner.py orchestrates agents as copilot CLI subprocesses](docs/illustrations/agents.png)

*Fig. 2. Python runner is the brain — deterministic control flow, retry logic, parallelism. Agents are stateless copilot CLI subprocesses. Files on disk are the protocol between phases.*

### Three principles

**Python = brain.** All phase ordering, branching, retry limits, and parallelism live in `runner.py`. Agents have zero orchestration logic.

**Agents = stateless workers.** Each agent is a `.agent.md` file in `.github/agents/`. Invoked as a `copilot` CLI subprocess — reads a task prompt from disk, writes output to disk, exits.

**Files = protocol.** Every inter-phase handoff is a file on disk. `runner.py` validates each file before proceeding to the next phase.

### Agent invocation

```python
cmd = [
    "copilot",
    "-p", f"Read your task from: {prompt_file}",
    "--agent", agent_name,
    "--output-format", "json",
    "--allow-all",
    "--no-ask-user",
    "--add-dir", str(REPO_ROOT),   # gives agent access to prompts/ and .github/
]
if model:
    cmd += ["--model", model]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
```

---

## Agents

### `source_processor`
Reads one file, folder, or URL. Identifies document type, applies the matching strategy from `prompts/source_processor/strategies/`, outputs `extract.json`.

**Strategies:** `brief`, `chat`, `pdf`, `qa`, `spreadsheet`, `transcript`

**Tools:** `read`, `bash`, `mcp_pdf-reader`

### `arch_probe`
Reads all `extract.json` files. Scores sources for AI-generation signals. Runs Tavily web searches. Generates 20–30 raw questions as structured JSON.

**Tools:** `read`, `mcp_tavily-remote_tavily_search`

### `arch_critic`
Filters `probe_output.json` down to 8–15 decision-blocking questions. Writes `discovery_report.md`.

**Tools:** `read`, `write`

### `requirements_writer`
Synthesises all extracts into `_requirements.md` with FR / NFR / BR tables, conflict register, gap register, assumptions. On revision rounds receives critic feedback in the prompt.

**Tools:** `read`, `write`, `mcp_tavily-remote_tavily_search`

### `requirements_critic`
Reviews `_requirements.md` against source extracts. Writes `verdict.md` starting with `VERDICT: APPROVED` or `VERDICT: REVISE` followed by per-section feedback.

**Tools:** `read`, `write`

### `orchestrator`
VS Code chat wrapper. Starts `runner.py` via `run_in_terminal`, presents HITL checkpoints via `vscode_askQuestions`, sends answers back via `send_to_terminal`.

### `illustrator`
Generates publication-quality PNG diagrams using PaperBanana (Retriever → Planner → Stylist → Visualizer ↔ Critic). Embeds PNGs into documents with numbered captions.

---

## Interactive Mode (HITL)

Run via the `@orchestrator` agent in VS Code chat:

```
@orchestrator analyze /path/to/project/input
```

The orchestrator starts the pipeline and surfaces decision points:

| Checkpoint | Phase | What happens |
|---|---|---|
| Source clarification | Phase 1 | Agent flagged `needs_clarification` — user provides context, agent re-runs |
| Conflicts | Phase 2 | User picks winner between contradicting sources |
| Final review | Phase 3 | User can accept APPROVED verdict or force another revision |

Headless (default):

```bash
python3 runner.py run /path/to/input           # --no-interactive is default
python3 runner.py run /path/to/input --debug   # verbose logs to stderr
```

---

## Configuration

`plan/params.yaml` is created on first run with defaults. Edit before re-running:

```yaml
industry: fintech
project_type: software
domain_tags: [payments, SWIFT, KYC]

models: {}   # override per-agent model if needed

trust_policy:
  auto_resolve: true
  escalate_on: [scope, budget, architecture, security]
```

---

## Required MCP Servers

MCP servers are configured in VS Code (`mcp.json`) and used by agents as copilot tools.

| MCP Server | Used by | When needed |
|---|---|---|
| `pdf-reader` | `source_processor` | Any PDF files in `input/` |
| `tavily-remote` | `arch_probe`, `requirements_writer` | Always — web searches for domain context enrichment |
| `mcp-atlassian` (Confluence) | `source_processor` | `.txt` files containing `confluence.scnsoft.com` URLs |

Configure in VS Code: **Settings → MCP** or `~/.config/copilot/mcp.json`.

---

`.env` (required for Illustrator agent only):

```
OPENAI_API_KEY=sk-...
```

---

## Project Structure

```
rfp-manager/
  runner.py                          ← orchestrator — all phase logic lives here
  .env                               ← secrets (gitignored)
  .github/
    agents/
      source_processor.agent.md
      arch_probe.agent.md
      arch_critic.agent.md
      requirements_writer.agent.md
      requirements_critic.agent.md
      orchestrator.agent.md
      illustrator.agent.md
    instructions/
      illustrator/
        generation-pipeline.instructions.md
        style-guidelines.instructions.md
      shared/
        artifact-management.instructions.md
    skills/
      image-generator/
        SKILL.md
        scripts/
          paperbanana_generate.py
  prompts/
    source_processor/
      output_schema.md
      strategies/          ← brief / chat / pdf / qa / spreadsheet / transcript
    requirements_writer/
      output_schema.md
      conflict_rules.md
    arch_critic/
      report_schema.md
  docs/
    illustrations/
      pipeline.png          ← Fig. 1
      agents.png            ← Fig. 2
```

---

## Dependencies

```bash
pip install loguru pyyaml                          # runner.py dependencies
pip install "paperbanana[openai]" python-dotenv   # for Illustrator agent only
```

> `loguru` is required. `pyyaml` is optional — needed only if you edit `plan/params.yaml` before re-running.

Requires `copilot` CLI (GitHub Copilot CLI) in `PATH`.
