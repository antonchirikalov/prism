# RFP Manager — Technical Design

## Overview

Multi-agent pipeline that processes raw stakeholder documents (transcripts, chats, briefs, PDFs) and produces structured requirements with full traceability to source material.

**Two pipelines, composable:**
1. **Requirements Pipeline** — extracts, validates, enriches requirements from source documents
2. **Deliverables Pipeline** — generates solution design, proposal, or other outputs from validated requirements (future, scope TBD)

---

## Architecture

```
Python runner (deterministic)
  │
  ├─ Phase 0: Input Setup (Python only)
  │   scan project root → _artifacts/intake/manifest.json
  │   deterministic parsing (docx/xlsx/pptx → text + images)
  │   PDF/md/txt listed in manifest for direct agent access (Phase 1)
  │
  ├─ Phase 1: Source Extraction (parallel) ────────┐
  │   copilot --agent source_processor -p "file1"   │ 1 per file
  │   copilot --agent source_processor -p "file2"   │ ProcessPoolExecutor
  │   copilot --agent source_processor -p "subdir/" │ 1 per subfolder
  │   wait all → validate extracts                  ┘
  │
  ├─ Phase 2: Requirements Synthesis (sequential)
  │   copilot --agent analyst -p "synthesize requirements"
  │   reads all extracts → _artifacts/final/requirements.md
  │   builds dispute register for conflicting sources
  │
  ├─ Phase 3: Requirements Review (sequential)
  │   copilot --agent critic -p "review requirements"
  │   if APPROVED + no gaps → Done
  │   if APPROVED + gaps → Phase 4
  │   if REVISE → loop Phase 2 (max 2 revisions; Analyst runs up to 3 times total)
  │
  ├─ Phase 4: Gap Research (conditional, parallel) ┐
  │   copilot --agent researcher -p "gap1"          │ ProcessPoolExecutor
  │   copilot --agent researcher -p "gap2"          │
  │   wait all                                      ┘
  │
  ├─ Phase 5: Enrichment (sequential)
  │   copilot --agent analyst -p "enrich with research"
  │
  ├─ Phase 6: Final Review (sequential)
  │   copilot --agent critic -p "final review"
  │   if REVISE → retry Phase 5 (max 1 revision; Analyst runs up to 2 times total)
  │   if APPROVED → Done (or → Phase 7 if illustrations on)
  │
  └─ Phase 7: Illustration (optional, parallel) ──┐
      copilot --agent illustrator -p "fig1"         │ 1 per placeholder
      wait all → embed PNGs in requirements.md      ┘
```

**Core rules:**
- **Python = brain** — decides phase order, branching, retry, parallelism
- **Agents = workers** — receive task via CLI, return structured text. Zero orchestration logic
- **Files = protocol** — every inter-phase handoff is a file on disk, validated by Python
- **Prompts = templates** — Markdown files in `prompts/`, Python fills `{{variables}}`

### Agent Invocation

Every agent call goes through `copilot` CLI as a subprocess:

```python
def run_agent(agent_name: str, prompt: str, model: str = None,
              project_dir: Path = None) -> str:
    cmd = ["copilot", "-p", prompt, "--agent", agent_name,
           "--output-format", "json", "--allow-all", "--no-ask-user"]
    # agent needs access to both tool repo (prompts, exemplars) and project folder
    if project_dir:
        cmd += ["--add-dir", str(project_dir)]
    if model:
        cmd += ["--model", model]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return extract_assistant_text(result.stdout)  # parse JSONL
```

Agents live in `.github/agents/` — each has its own `.agent.md` with tools, model, instructions.

### Parallel Execution

```python
def run_agents_parallel(tasks: list[dict]) -> list:
    with ProcessPoolExecutor() as pool:
        futures = {pool.submit(run_agent, t["agent"], t["prompt"],
                   model=t.get("model"),
                   project_dir=t.get("project_dir")): t for t in tasks}
        return [f.result() for f in as_completed(futures)]
```

### HITL (Human-in-the-Loop)

Two modes:

**Headless:** `python3 runner.py run ./project --no-interactive` — fully autonomous.

**Interactive (via orchestrator agent):**
1. User in VS Code chat: `@orchestrator analyze requirements for ./project`
2. Orchestrator extracts `<project>` path from user message, runs `python3 runner.py run <project> --interactive` via `run_in_terminal(mode=async)`
3. Python prints structured prefixes to stdout
4. Orchestrator reads terminal via `get_terminal_output`, parses prefixes
5. Orchestrator reads artifact files (`_artifacts/final/review.md`, `_artifacts/final/requirements.md`) for rich context
6. Orchestrator presents structured decisions via `vscode_askQuestions` (not raw text relay)
7. User decides in VS Code UI — buttons, multiselect, optional free-text
8. Orchestrator formats decision → `send_to_terminal` → Python stdin

**HITL protocol (stdout → stdin):**

| Stdout prefix | Meaning |
|---|---|
| `[PHASE N/M]` | Progress update — orchestrator shows in chat |
| `[HITL:verdict]` | Critic verdict decision required |
| `[HITL:gaps]` | Gap selection for research |
| `[HITL:research_scope]` | Research query review before Phase 4 |
| `[HITL:enrichment]` | Enrichment diff review |
| `[HITL:disputes]` | Unresolved requirement conflicts for user decision |
| `[HITL:clarify]` | Source clarification needed (missing context) |
| `[HITL:confirm]` | Generic confirmation checkpoint |
| `[ERROR]` | Error — orchestrator decides retry or abort |
| `[DONE]` | Pipeline completed |

Stdin responses (structured JSON on one line):
```json
{"action": "continue"}
{"action": "revise", "accept": ["T1","T2","T4"], "reject": ["T3","T5"], "feedback": "T3 is false positive"}
{"action": "research", "gaps": ["gap1","gap3"], "extra_queries": ["SWIFT MT515 Saudi"]}
{"action": "skip_gaps"}
{"action": "abort"}
```

**HITL checkpoints:**

| Checkpoint | After | User decides |
|---|---|---|
| **Source clarification** | Phase 1 | Missing critical context in source — user provides answer or skips |
| **Disputes** | Phase 2 | Unresolved requirement conflicts — user picks winner or marks "ask client" |
| **Critic verdict** | Phase 3 | APPROVED → continue / select gaps for research / skip. REVISE → select which critic findings to accept, override false positives, add feedback |
| **Research scope** | Phase 3 (before Phase 4) | Review proposed search queries per gap, add/remove queries, add domain hints |
| **Enrichment diff** | Phase 5 | Review what changed, accept / request further revision |
| **Final verdict** | Phase 6 | Accept final result / request one more revision |

### Orchestrator Agent

The orchestrator is **not** part of the pipeline — it wraps the pipeline for interactive use in VS Code chat. It bridges Python runner's stdin/stdout protocol with VS Code terminal tools.

**Protocol:**

```
loop:
  output = get_terminal_output(id)
  
  if "[PHASE" in output:
    → show progress in chat ("Phase 2/5 — Requirements Review")
  
  if "[HITL:verdict]" in output:
    → review = read_file("_artifacts/final/review.md")
    → parse critic findings (T1..Tn), gaps, verdict
    → present via vscode_askQuestions:
        - verdict action (continue / revise / skip / abort)
        - if REVISE: multiselect which findings to accept
        - if APPROVED+gaps: multiselect which gaps to research
        - free-text field for additional context
    → format response as JSON → send_to_terminal(id, json)
  
  if "[HITL:research_scope]" in output:
    → parse proposed queries from stdout
    → present via vscode_askQuestions:
        - multiselect queries to keep/drop
        - free-text for extra queries
    → send_to_terminal
  
  if "[HITL:clarify]" in output:
    → parse clarification request from stdout (file name + missing context description)
    → present via vscode_askQuestions:
        - free-text answer (or skip)
    → send_to_terminal

  if "[HITL:disputes]" in output:
    → disputes = read_file("_artifacts/disputes/register.json")
    → present each conflict via vscode_askQuestions:
        - show both sides with source citations
        - options: pick A / pick B / mark "ask client" / keep both
    → send_to_terminal

  if "[HITL:enrichment]" in output:
    → requirements = read_file("_artifacts/final/requirements.md")
    → parse diff summary from stdout
    → present via vscode_askQuestions:
        - accept / request further revision
        - free-text feedback field
    → send_to_terminal

  if "[HITL:confirm]" in output:
    → parse confirmation prompt from stdout
    → present via vscode_askQuestions (Yes / No / Abort)
    → send_to_terminal

  if "[ERROR]" in output:
    → parse error description from stdout
    → present via vscode_askQuestions:
        - retry / skip / abort
    → send_to_terminal

  if "[DONE]" in output:
    → read final _artifacts/final/requirements.md, summarize in chat
    → record run metadata to _artifacts/state.json
    → present graduation checkpoint via vscode_askQuestions:
        - "Graduate to exemplar library?" (Yes / Yes with edits / No)
    → if Yes or Yes with edits: run `runner.py graduate <project>`
```

Orchestrator agent: `.github/agents/orchestrator.agent.md`, `user-invocable: true`.
Tools: `run_in_terminal`, `get_terminal_output`, `send_to_terminal`, `read_file`, `vscode_askQuestions`.

---

## Agents

All forked from [deep-analyst](https://github.com/antonchirikalov/deep-analyst), adapted for RFP domain.

| Agent | Role | Parallelism |
|---|---|---|
| **Orchestrator** | HITL proxy — wraps pipeline for VS Code chat | N/A (wrapper) |
| **Source Processor** | Per-file/subfolder extraction and analysis. Reads PDFs via `mcp_pdf-reader`, pre-parsed docx/xlsx via `read` tool | ✅ 1 per file + 1 per subfolder |
| **Requirements Analyst** | Cross-source synthesis → structured requirements | Sequential |
| **Critic** | Quality gate: APPROVED / REVISE verdict | Sequential |
| **Researcher** | Gap research via MCP tools (Tavily, context7, GitHub, HuggingFace) + extract relevant content | ✅ 1 per gap |
| **Illustrator** | PNG diagrams via PaperBanana (`gpt-image-1.5`) — optional | ✅ 1 per placeholder |

Each agent: `.github/agents/{name}.agent.md` with own tools list, optional model override. All `user-invocable: false` except Orchestrator (`user-invocable: true`).

**Source Processor tools:** `read`, `search`, `mcp` (mcp_pdf-reader for PDFs, mcp_pdf-reader smart_extract for scanned/complex layouts).  
**Researcher tools:** `read`, `search`, `mcp` (mcp_tavily for web, mcp_context7 for library docs, mcp_github for code examples, mcp_huggingface for ML papers).

### Prompt Architecture

Agent `.instructions.md` = identity, reasoning approach (stable).
`prompts/` templates = task context, file paths, criteria (per-invocation).

```
prompts/
├── source_processor/
│   ├── extract.md
│   └── strategies/{transcript,chat,brief,qa,pdf}.md
├── requirements_analyst/
│   ├── synthesize.md       # Phase 2 (requirements synthesis)
│   └── enrich.md           # Phase 5 (enrichment)
├── critic/
│   └── requirements_review.md
├── researcher/
│   └── gap_research.md
├── illustrator/
│   └── diagram.md
├── _auto/                      # generated by meta-learning (Level 3)
│   ├── anti_patterns.md
│   ├── domain_hints.md
│   └── check_weights.md
└── _partials/
    ├── pdf_hint.md
    ├── exemplar_ref.md
    └── output_format.md
```

Template rendering — simple `{{var}}` replacement, no logic. `{{auto_hints}}` injects content from `prompts/_auto/` when available:
```python
def render_prompt(template: Path, variables: dict) -> str:
    text = template.read_text()
    for key, val in variables.items():
        text = text.replace(f"{{{{{key}}}}}", str(val) if not isinstance(val, list)
                            else "\n".join(f"- {v}" for v in val))
    return text
```

### Model Strategy

Different LLMs per agent via `--model`:

```yaml
# plan/params.yaml
models:
  default: claude-sonnet-4-20250514
  critic: o4-mini              # reasoning for verification
  source_processor: claude-sonnet-4-20250514  # fast extraction
  illustrator: gpt-image-1.5   # PaperBanana image generation

illustration_mode: none        # none | direct
```

---

## Pipeline 1: Requirements

### Project Folder Structure

Source documents live in the project root. Subfolders are logical groups. `plan/` and `_artifacts/` are created by the pipeline. Scanner ignores `plan/`, `_artifacts/`, `.git/`, and dotfiles — everything else is source material.

```
{project}/                          # external folder, can be its own git repo
├── transcript-kickoff.md           # source documents — right in root
├── client-chat.txt
├── tech-spec.docx
├── budget.xlsx
├── architecture.pdf
├── onboarding/                     # subfolder = logical group
│   ├── flow-diagram.png
│   └── onboarding-notes.md
├── plan/
│   └── params.yaml                 # project config (industry, models, trust policy)
└── _artifacts/                     # created by pipeline, all working data
    ├── intake/
    │   └── manifest.json           # file inventory, types, sizes, parsing status
    ├── parsed/                     # deterministic extraction output
    │   ├── tech-spec.md            # docx → markdown
    │   ├── budget.json             # xlsx → structured JSON
    │   └── assets/                 # extracted images from documents
    ├── extracts/                   # agent output (1 per file + 1 per subfolder)
    │   ├── {source-name}/
    │   │   └── extract.json
    │   └── {subfolder}/
    │       └── extract.json
    ├── disputes/
    │   └── register.json           # conflicting requirements + resolution status
    ├── research/
    │   └── {gap}/                  # Phase 4 research per gap
    ├── illustrations/              # Phase 7 PNGs (if illustration_mode: direct)
    ├── final/
    │   ├── requirements.md         # final artifact
    │   └── review.md               # critic verdict
    ├── state.json                  # run history + meta-learning data
    ├── meta/
    │   ├── insights.json           # accumulated cross-run insights
    │   └── anti_patterns.json      # critic false positives
    └── logs/
```

### Source Parsing (Phase 0 — Python only, deterministic)

Before agents see anything, Python converts binary Office formats to text. **PDF files are not pre-parsed** — Source Processor agents read them directly via `mcp_pdf-reader` in Phase 1 (better quality: semantic extraction, OCR, tables).

| Format | Phase | Tool | Output |
|---|---|---|---|
| `.docx` | Phase 0 | python-docx | markdown + embedded images → `assets/` |
| `.xlsx` | Phase 0 | openpyxl | JSON per sheet (headers, rows, formulas) |
| `.pptx` | Phase 0 | python-pptx | markdown per slide + images → `assets/` |
| `.pdf` | Phase 1 | `mcp_pdf-reader` (agent tool) | read directly by Source Processor — no pre-parse |
| `.png/.jpg` | Phase 1 | agent vision | passed through directly to agent with vision |
| `.md/.txt` | Phase 1 | agent `read` tool | no conversion needed |

Images extracted from docx/pptx are saved to `_artifacts/parsed/assets/`. Only content-bearing images (diagrams, screenshots, tables) are sent for vision analysis — decorative images are skipped based on size/aspect ratio heuristics.

Result: `_artifacts/parsed/` contains pre-converted docx/xlsx/pptx. PDF and plain text files are listed in `manifest.json` with their original paths for direct agent access.

### Source Extraction (Phase 1 — parallel agents)

One source processor per file **and** one per subfolder, running in parallel.

Each agent receives either the pre-parsed text (docx/xlsx/pptx from `_artifacts/parsed/`) or the original file path (PDF, md, txt — read directly). Manifest tells the agent which path to use:

```json
// manifest.json entry (files)
{"file": "architecture.pdf", "parsed": null, "original": "architecture.pdf", "tool": "mcp_pdf-reader"}
{"file": "tech-spec.docx", "parsed": "_artifacts/parsed/tech-spec.md", "original": null, "tool": "read"}
// manifest.json entry (subfolder — agent receives full file list for unified extract)
{"subfolder": "onboarding", "files": ["onboarding/flow-diagram.png", "onboarding/onboarding-notes.md"]}
```

Each agent extracts (all fields optional — extract what's available):

```json
{
  "source_file": "transcript-kickoff.md",
  "source_type": "transcript",
  "date": "2026-03-15",
  "participants": ["Ahmad (CTO)", "Sara (PM)"],
  "topics": ["custody workflow", "settlement"],
  "requirements": [
    {
      "id": "SRC-TK-001",
      "text": "System must support T+1 settlement",
      "type": "FR",
      "confidence": "high",
      "speaker": "Ahmad (CTO)"
    }
  ],
  "decisions": ["Go with on-premise deployment"],
  "constraints": ["Must integrate with existing SWIFT gateway"],
  "open_questions": ["Custody fee structure unclear"],
  "potential_conflicts": ["Ahmad says T+1 but tech-spec says T+2"]
}
```

Subfolder agents receive all files in the subfolder and produce a **unified extract** for the group — catching cross-file patterns and conflicts within the subfolder.

If a source lacks critical context that blocks extraction (e.g., unnamed participants in a transcript, undated document), the agent flags it and runner triggers `[HITL:clarify]` — user provides the missing info or skips.

### Requirements Synthesis (Phase 2 — sequential)

Analyst reads all extracts from `_artifacts/extracts/` and produces:
- `_artifacts/final/requirements.md` — FR/NFR/BR with `[Source: filename]` citations, MoSCoW priorities
- `_artifacts/disputes/register.json` — conflicting requirements
- illustration placeholders in `requirements.md` — only when `illustration_mode: direct` in `plan/params.yaml`

**Trust Policy** for resolving conflicts — configurable in `plan/params.yaml`:

```yaml
# plan/params.yaml
trust_policy:
  # priority order (highest first)
  source_priority:
    - formal_decision      # signed-off documents, formal meeting decisions
    - explicit_statement    # direct requirements from product owner / client
    - transcript            # meeting recordings and transcripts  
    - chat                  # informal discussions
    - notes                 # analyst notes, inferred requirements
  # auto-resolve if newer + higher priority + explicit wording
  auto_resolve: true
  # escalate to HITL if conflict affects these areas
  escalate_on: [scope, budget, architecture, security]
```

Conflict resolution rules:
- **Auto-resolve**: source is higher priority AND newer AND wording is explicit → mark loser as `superseded`
- **Escalate to HITL**: sources are equal priority, or conflict touches scope/budget/architecture
- **Never hide**: even auto-resolved conflicts stay in `register.json` with full audit trail

Dispute register entry:
```json
{
  "id": "DSP-001",
  "requirement_a": {"text": "Web only", "source": "tech-spec.docx", "date": "2026-01", "trust": "formal_decision"},
  "requirement_b": {"text": "Web + mobile", "source": "client-chat.txt", "date": "2026-03", "trust": "chat"},
  "status": "auto_resolved",
  "winner": "b",
  "reason": "Newer explicit statement from client, confirmed in follow-up",
  "resolved_by": "system"
}
```

Statuses: `auto_resolved`, `user_resolved`, `pending`, `ask_client`.

### Requirements Review (Phase 3 — sequential)

Critic reviews: traceability, source coverage, domain coherence, completeness, conflict handling. Outputs verdict + `_artifacts/final/review.md`.

### Gap Research (Phase 4 — conditional, parallel)

Only for researchable gaps (not "client must provide"). One Researcher per gap. Each Researcher has access to MCP tools: **Tavily** (web search), **context7** (library/framework docs), **GitHub MCP** (code examples, issues), **HuggingFace MCP** (ML papers and models). Tools used depend on gap domain — not every gap requires all of them.

### Enrichment (Phase 5 — sequential)

Analyst re-runs with originals + research extracts. Enriches, doesn't rewrite.

### Final Review (Phase 6 — sequential)

Same Critic, same criteria. APPROVED → Done.

### Illustration (Phase 7 — optional, parallel)

Enabled via `illustration_mode: direct` in `plan/params.yaml`. Forked from [deep-analyst](https://github.com/antonchirikalov/deep-analyst) PaperBanana system (`gpt-image-1.5`).

Analyst inserts placeholders in `requirements.md` during Phase 2:
```
<!-- ILLUSTRATION: type="architecture", section="§3.5", description="..." -->
```

Illustrator generates PNG per placeholder → `_artifacts/illustrations/`. Results embedded in final document. Visual style: flat vector, white background, pastel palette.

When `illustration_mode: none` (default) — Phase 7 skipped, no placeholders inserted.

---

### Requirements Document Template

Output `requirements.md` follows a fixed section structure:

| # | Section | Status | Description |
|---|---------|--------|-------------|
| — | YAML front matter | Mandatory | Exemplar metadata: industry, domain_tags, project_type, complexity, source_types, sections, quality_score |
| — | Document Index | Mandatory | Source file table: #, filename, type |
| 1 | Domain Grounding | Mandatory | Project domain, business model, key actors (1–2 paragraphs) |
| 2 | Stakeholders & Roles | Mandatory | Role table with descriptions |
| 3 | Business Context | Mandatory | Revenue model, timeline, geography, competitive refs, constraints |
| 4 | Functional Requirements | Mandatory | Grouped by domain area. Table: ID, text, priority (MoSCoW), source citation |
| 5 | Non-Functional Requirements | Mandatory | Table: ID, text, category (perf / security / compliance / ops), source |
| 6 | Open Questions, Conflicts & Assumptions | Mandatory | Sub-sections: conflicts (with resolution), gaps (with impact), assumptions (with basis) |
| 7 | Business Rules & Constraints | Optional | Invariants spanning multiple FRs — only if sources contain explicit rules |
| 8 | Domain Entities (derived) | Optional | Entities referenced across sources — domain vocabulary, not DB schema |
| 9 | Integration Points | Optional | External systems referenced in sources — APIs, payment providers, etc. |
| 10 | Out of MVP Scope | Optional | Explicitly deferred features — only if sources describe phased delivery |

**Conventions:**
- Every FR/NFR row has `[Source: filename]` — traceability is non-negotiable
- IDs: `FR-NNN`, `NFR-NNN`, `BR-NNN` — sequential within section
- Priorities: MUST / SHOULD / COULD / WON'T (MoSCoW)
- Conflicts section always present, even if empty
- Assumptions clearly marked as unconfirmed

See `docs/reqs/_requirements.md` for a complete exemplar.

---

## Run History & Meta-Learning

Every pipeline run produces structured metadata. Over multiple runs the system accumulates data for prompt adaptation — a practical subset of HyperAgents' self-improvement loop.

### Level 1: Data Collection (built into runner)

After each run, Python runner writes to `_artifacts/state.json`:

```json
{
  "runs": [{
    "id": "run-001",
    "timestamp": "2026-04-17T10:00:00Z",
    "session_log": "~/.../debug-logs/ca882476-...",
    "phases_executed": [0, 1, 2, 3, 4, 5, 6],
    "revision_loops": 1,
    "critic_verdicts": [
      {
        "phase": 2, "verdict": "REVISE",
        "checks": {
          "traceability": {"pass": false, "detail": "12 reqs without source"},
          "coverage": {"pass": true},
          "domain_coherence": {"pass": true},
          "completeness": {"pass": false, "detail": "8 FR no acceptance criteria"},
          "conflicts": {"pass": false, "detail": "NFR-003 vs FR-017"}
        }
      }
    ],
    "hitl_decisions": [
      {"checkpoint": "phase2", "action": "revise_selected",
       "overrides": ["T3", "T5"], "reason": "false positives"},
      {"checkpoint": "research_scope", "added_queries": ["SWIFT MT515"]}
    ],
    "gaps_found": 3,
    "gaps_researched": 2,
    "final_verdict": "APPROVED",
    "duration_seconds": 340,
    "agent_timings": {
      "source_processor": [12, 8, 15],
      "analyst_phase2": 45,
      "critic_phase3": 22,
      "researcher": [30, 25],
      "analyst_phase5": 38,
      "critic_phase6": 18
    }
  }]
}
```

Cost: zero extra agent calls — Python runner already knows all of this.

VS Code Agent Debug Logs (setting: `github.copilot.chat.agentDebugLog.fileLogging.enabled`) provide full session trace — every tool call, agent response, timings. Logs persist across sessions (VS Code 1.116+). Path stored in `session_log` for post-mortem.

### Level 2: Pattern Analysis

Script `meta_analyze.py` reads `_artifacts/state.json` from registered project paths (stored in `_global_meta/projects.json`), surfaces:

| Signal | Source | Insight |
|---|---|---|
| Critic check effectiveness | `critic_verdicts[].checks` + `hitl_decisions[].overrides` | If a check is frequently overridden by user → false positive for this domain |
| Revision loop count by domain | `revision_loops` across runs | High loops → analyst prompt weak for this domain |
| Critic bias | ratio APPROVED/REVISE on Phase 5 across runs | >90% approve on final review → critic too lenient |
| Agent timings | `agent_timings` | Bottleneck identification |
| Gap researchability | `gaps_found` vs `gaps_researched` | How often gaps are skipped → quality of gap classification |

### Level 3: Prompt Adaptation

Meta-agent (or script) reads accumulated data, generates supplementary prompt fragments:

```
prompts/_auto/
├── anti_patterns.md        # "In fintech projects, common mistakes: ..."
├── domain_hints.md         # "For custody workflows: always verify SWIFT MT5xx"
└── check_weights.md        # critic check priority adjustments
```

These are **injected** into existing prompts via `{{auto_hints}}` variable — agents and their `.agent.md` files stay stable. Changes are transparent: auto-generated files are in git, human reviews diffs.

**What gets adapted:**
- Anti-patterns from HITL overrides → injected into Analyst prompt as negative examples
- Domain-specific hints from accumulated research → injected into Researcher prompt
- Check priority weights → injected into Critic prompt (de-prioritize checks with high false-positive rate)
- Model selection in `params.yaml` → if critic too lenient, escalate to stronger reasoning model

### Level 4: Agent Evolution (future, with safeguards)

Inspired by HyperAgents: meta-agent gets permission to modify `.agent.md` files and veto rules in Python runner.

Safeguards:
- All changes via git commit → human reviews diff before next run
- A/B testing: new agent version runs parallel with old on same inputs, compare outputs
- Auto-rollback if key metrics (revision loops, HITL override rate) degrade
- Budget cap: meta-agent can modify prompts and check lists, **not** pipeline control flow

### Persistent Memory (`_artifacts/meta/insights.json`)

Cross-run insights in the style of HyperAgents' persistent memory:

```json
{
  "insights": [
    {
      "id": "ins-001",
      "created": "run-003",
      "domain": "fintech",
      "type": "anti_pattern",
      "text": "Critic flags NFR↔FR conflicts in custody workflows that are actually complementary constraints. Override rate: 4/5 runs.",
      "action": "Added to prompts/_auto/anti_patterns.md"
    },
    {
      "id": "ins-002",
      "created": "run-005",
      "type": "bias_alert",
      "text": "Phase 5 critic approved 9/10 last runs. Possible leniency drift.",
      "action": "Switched critic model to o4-mini for final review"
    }
  ]
}
```

### Session Log Post-Mortem

VS Code persists Agent Debug Logs on disk and shows previous sessions in the Debug Log panel. Runner stores the path in `state.json` → `session_log`, enabling post-mortem:

```
User: @orchestrator what went wrong in the last run?
Orchestrator:
  1. Reads _artifacts/state.json → last run metadata + session_log path
  2. Reads VS Code debug log → full tool call trace
  3. Identifies root cause (e.g., analyst prompt missing [Source:] citation)
  4. Reports diagnosis + suggests prompt fix
```

### Runner CLI

`<project>` is a path to an external project folder.

```
python3 runner.py init <project>                       # scaffold plan/ in project folder
python3 runner.py run <project> [--interactive | --no-interactive]
python3 runner.py next <project>                       # one phase (debug)
python3 runner.py status <project>
python3 runner.py graduate <project>                   # copy artifact to exemplars/
python3 runner.py meta-analyze [--domain fintech]      # cross-project analysis
```

---

## Pipeline 2: Deliverables (future, scope TBD)

Takes validated `_artifacts/final/requirements.md` as input. Output format to be defined per use case:
- Slide-based proposal / presentation
- Solution design document
- Technical architecture overview
- Other deliverable types as needed

Will be designed after Pipeline 1 is stable and battle-tested on real projects. Reuses agents and infrastructure from Pipeline 1.

---

## Workspace Layout

Projects are external folders (separate repos or directories). `prism` is the tool — contains agents, prompts, exemplar library, and runner. Connected via VS Code multi-root workspace.

```
# VS Code multi-root workspace
prism.code-workspace                # lists prism + active project(s)

# Tool repo (one instance, shared)
prism/
├── .github/agents/                 # agent definitions
├── prompts/                        # prompt templates
│   ├── _auto/                      # meta-learning generated
│   └── _partials/
├── exemplars/                      # graduated requirements library
│   ├── _index.json                 # searchable index with profiles
│   └── jadwa-2026/                 # one entry per graduated project
│       ├── requirements.md         # the artifact
│       └── profile.json            # quality + domain metadata
├── _global_meta/                   # cross-project aggregated data
│   ├── projects.json               # registered project paths for meta-analysis
│   ├── insights.json               # merged insights from all projects
│   └── check_stats.json            # critic check effectiveness
├── poc/pipeline_sim.py
├── meta_analyze.py
└── runner.py

# Project folder (external, one per engagement)
jadwa-2026/                         # can be its own git repo
├── *.md, *.docx, *.pdf, ...       # source documents in root
├── subfolders/                     # optional logical groups
├── plan/params.yaml                # project config
└── _artifacts/                     # created by pipeline (see Pipeline 1 section)
```

Runner resolves paths: `--tool-root` defaults to `prism/` (auto-detected from workspace), `<project>` is the external folder path. Exemplars and prompts live in the tool repo and are version-controlled there.

---

## Exemplar System

Completed requirements docs become few-shot references for future runs. This is the primary self-improvement mechanism — the system gets better as the library grows.

### Graduation Flow

Not every completed project becomes an exemplar. Graduation is explicit:

```
Pipeline finishes → final verdict APPROVED
  │
  ├─ HITL checkpoint: "Graduate to exemplar library?"
  │   User reviews requirements.md quality
  │   ○ Yes — graduate (recommended if quality_score ≥ 0.7)
  │   ○ Yes, with edits — user polishes before graduation
  │   ○ No — project stays as-is, not indexed
  │
  └─ Runner:
      1. Copies _artifacts/final/requirements.md → exemplars/{project}/
      2. Generates profile.json from _artifacts/state.json + plan/params.yaml
      3. Updates exemplars/_index.json
```

### Exemplar Profile (`profile.json`)

Auto-generated from run data — objective quality signals, not vibes:

```json
{
  "project": "jadwa-2026",
  "industry": "fintech",
  "project_type": "agentic_ai",
  "domain_tags": ["investment", "custody", "trading", "on-premise"],
  "source_types": ["transcript", "chat", "brief"],
  "complexity": "high",
  "quality_signals": {
    "revision_loops": 1,
    "hitl_overrides": 2,
    "critic_first_pass_score": 0.6,
    "critic_final_score": 0.95,
    "gaps_found": 3,
    "gaps_researched": 2,
    "source_count": 4,
    "requirements_count": {"FR": 28, "NFR": 12, "BR": 5}
  },
  "quality_score": 0.85,
  "graduated": "2026-04-17",
  "notes": "User polished acceptance criteria before graduation"
}
```

`quality_score` formula (deterministic, computed by Python):
- Base: 1.0
- −0.1 per revision loop (more loops = analyst needed more help)
- −0.05 per HITL override (overrides = critic was wrong)
- +0.1 if zero gaps on final review
- −0.15 if manually edited before graduation (good doc but pipeline didn't get there alone)
- Clamped to [0.0, 1.0]

### Exemplar Retrieval

Before Phase 2 (Requirements Synthesis), Python runner:

1. Reads `plan/params.yaml` → project `industry`, `project_type`, `domain_tags`
2. Reads `exemplars/_index.json` → all profiles
3. Scores each exemplar by match:
   - Same `industry` → +3
   - Overlapping `domain_tags` → +1 per tag
   - Same `project_type` → +2
   - Same `source_types` → +1 per type
   - `quality_score` as tiebreaker
4. Selects top 1-3 exemplars
5. Injects into analyst prompt via `{{exemplar_refs}}` (uses `_partials/exemplar_ref.md` template)

Analyst sees: "Here are 2 examples of high-quality requirements docs from similar projects" + the actual docs. Not told to copy — told to match the quality bar and structure.

### Cold Start

When exemplar pool is empty — agents work from `.instructions.md` only, degrades gracefully. First 3-5 projects are "bootstrap" runs — expected to need more revision loops. After that, the system has enough exemplars to stabilize quality.

### Feedback Loop

```
Project run → _artifacts/state.json (run data)
  │
  ├─ Graduation → exemplar (if quality OK)
  │   → future projects get better few-shot examples
  │
  ├─ HITL overrides → _artifacts/meta/anti_patterns.json
  │   → meta_analyze.py → prompts/_auto/anti_patterns.md
  │   → future critics make fewer false-positive errors
  │
  ├─ Agent timings → _global_meta/check_stats.json
  │   → identifies bottlenecks, informs model selection
  │
  └─ Accumulated insights → _global_meta/insights.json
      → cross-domain patterns, prompt improvements
```

Two improvement loops running simultaneously:
- **Exemplar loop** (Level 3 in meta-learning): better examples → better analyst output → fewer revision loops
- **Anti-pattern loop** (Level 2-3): HITL overrides → fewer false critic findings → less noise for user

---

## Key Principles

1. **Python controls everything** — phases, branching, retry, parallelism. LLM never decides "what's next"
2. **Agents are stateless workers** — receive task, return result. No inter-agent communication except through files
3. **Source normalization first** — heterogeneous inputs → consistent extracts before synthesis
4. **Anti-hallucination chain** — Domain Grounding → Traceability check → Source verification
5. **Iterative refinement** — Critic-Analyst loop (max 2 revisions), HITL overrides false positives
6. **Exemplar-driven quality** — past docs as few-shot references
7. **Model per agent** — reasoning models for Critic, fast models for extraction
8. **Structured HITL** — user decisions via VS Code UI (buttons, multiselect), not free-text stdin relay
9. **Run history as learning signal** — every run contributes data for prompt adaptation; system improves over time without changing agent code
10. **Meta-learning with guardrails** — auto-generated prompt fragments, not self-modifying agents; all changes in git, human reviews diffs
11. **Graceful degradation** — no exemplars, no HITL, no VS Code → pipeline works headless via CLI
