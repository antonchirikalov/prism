#!/usr/bin/env python3
"""
RFP Manager — runner.py

Phase 0: scan project directory, parse documents, build manifest.json
Phase 1: run source_processor agents in parallel, save extracts
Phase 2: run requirements_writer agent, produce _requirements.md

Usage:
    python3 runner.py run <project_dir> [--interactive | --no-interactive]
"""

import argparse
import json
from loguru import logger
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parent
AGENT_TIMEOUT_S = 1200  # 20 min — large PDFs can take 8-10 min per agent
MAX_CRITIC_ROUNDS = 5  # safety cap — critic loops until APPROVED or this limit
SUPPORTED_EXT = {".md", ".txt", ".docx", ".xlsx", ".pptx",
                 ".pdf", ".png", ".jpg", ".jpeg", ".webp"}
EXCLUDED_DIRS = {"plan", ".git"}
CONFLUENCE_DOMAINS: set[str] = {"confluence.scnsoft.com"}

logger.remove()  # configured in main() once args are parsed

DEFAULT_PARAMS_YAML = """\
industry: unknown
project_type: software
domain_tags: []

models: {}

trust_policy:
  auto_resolve: true
  escalate_on: [scope, budget, architecture, security]
"""

# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class AgentResult:
    slug: str
    success: bool
    raw_text: str
    parsed_json: dict
    error: str = ""
    jsonl_log: str = ""


@dataclass
class ClarifyRequest:
    slug: str
    source_file: str
    question: str


# ── Phase 0: Slug generation ──────────────────────────────────────────────────
def slugify(name: str) -> str:
    stem = Path(name).stem if "." in name else name
    slug = re.sub(r"[^\w\-]", "_", stem)
    slug = re.sub(r"_+", "_", slug).strip("_").lower()
    return slug or "unnamed"


def unique_slug(name: str, existing: set) -> str:
    base = slugify(name)
    if base not in existing:
        existing.add(base)
        return base
    counter = 2
    while f"{base}_{counter}" in existing:
        counter += 1
    slug = f"{base}_{counter}"
    existing.add(slug)
    return slug


# ── Phase 0: Scan ─────────────────────────────────────────────────────────────
def detect_read_tool(ext: str) -> str:
    if ext == ".pdf":
        return "mcp_pdf-reader"
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        return "vision"
    return "read"


def build_file_entry(path: Path, project_dir: Path, used_slugs: set) -> dict:
    slug = unique_slug(path.name, used_slugs)
    return {
        "kind": "file",
        "slug": slug,
        "original": str(path.relative_to(project_dir)),
        "abs_path": str(path),
        "read_tool": detect_read_tool(path.suffix.lower()),
        "agent_scope": "file",
    }


def build_subfolder_entry(folder: Path, project_dir: Path, used_slugs: set) -> dict:
    rel = folder.relative_to(project_dir)
    slug = unique_slug(folder.name, used_slugs)
    files = []
    read_tools = set()
    max_depth = 0

    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXT:
            continue
        if any(part.startswith(".") for part in path.parts):
            continue

        file_rel = path.relative_to(project_dir)
        depth = len(file_rel.parts) - 1
        max_depth = max(max_depth, depth - 1)

        rt = detect_read_tool(path.suffix.lower())
        read_tools.add(rt)
        files.append({
            "original": str(file_rel),
            "abs_path": str(path),
            "read_tool": rt,
        })

    read_tool = "mixed" if len(read_tools) > 1 else (
        next(iter(read_tools)) if read_tools else "read"
    )

    entry = {
        "kind": "subfolder",
        "slug": slug,
        "original": str(rel) + "/",
        "abs_path": str(folder),
        "read_tool": read_tool,
        "agent_scope": "subfolder",
        "files": files,
    }
    if max_depth > 3:
        entry["depth_warning"] = f"Subfolder nesting depth {max_depth} > 3"
        logger.warning(f"[{slug}] deep subfolder nesting: {max_depth} levels")
    return entry



def is_confluence_url(url: str) -> bool:
    return any(domain in url for domain in CONFLUENCE_DOMAINS)


def extract_url_entries(txt_path: Path, project_dir: Path, used_slugs: set) -> tuple[list, bool]:
    """Parse a .txt file for URLs. Returns (url_entries, has_non_url_content)."""
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    url_entries = []
    non_url_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"https?://", stripped):
            slug = unique_slug(slugify(stripped), used_slugs)
            used_slugs.add(slug)
            read_tool = "mcp_confluence" if is_confluence_url(stripped) else "fetch"
            url_entries.append({
                "kind": "url",
                "slug": slug,
                "url": stripped,
                "original": stripped,
                "read_tool": read_tool,
                "agent_scope": "url",
            })
        else:
            non_url_lines.append(stripped)
    has_non_url_content = bool(non_url_lines)
    return url_entries, has_non_url_content


def scan_project(project_dir: Path) -> list:
    used_slugs: set = set()
    entries = []

    for item in sorted(project_dir.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            if item.name not in EXCLUDED_DIRS and not item.name.startswith("_artifacts"):
                entry = build_subfolder_entry(item, project_dir, used_slugs)
                if entry["files"]:
                    entries.append(entry)
        elif item.is_file():
            if item.suffix.lower() in SUPPORTED_EXT:
                if item.suffix.lower() == ".txt":
                    url_entries, has_text = extract_url_entries(item, project_dir, used_slugs)
                    if url_entries:
                        logger.debug(f"[phase0] Extracted {len(url_entries)} URL(s) from {item.name}")
                        entries.extend(url_entries)
                    # keep the file entry only if it has non-URL content
                    if not url_entries or has_text:
                        entries.append(build_file_entry(item, project_dir, used_slugs))
                else:
                    entries.append(build_file_entry(item, project_dir, used_slugs))
            else:
                logger.warning(f"Skipped unsupported file: {item.relative_to(project_dir)}")

    return entries


def build_manifest(project_dir: Path, entries: list) -> dict:
    return {
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runner_version": VERSION,
        "entries": entries,
    }


# ── Phase 0: Pre-flight ───────────────────────────────────────────────────────
def check_copilot_cli() -> bool:
    try:
        result = subprocess.run(
            ["copilot", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_mcp_pdf_reader() -> bool:
    config_paths = [
        # VS Code user-level MCP config
        Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json",
        # Linux / Windows WSL fallback
        Path.home() / ".config" / "Code" / "User" / "mcp.json",
        # Copilot CLI config
        Path.home() / ".config" / "copilot" / "mcp.json",
    ]
    for p in config_paths:
        if p.exists():
            try:
                cfg = json.loads(p.read_text())
                if "pdf-reader" in cfg.get("servers", {}):
                    return True
            except Exception:
                pass
    return False


def any_pdf_in_manifest(entries: list) -> bool:
    for e in entries:
        if e.get("read_tool") == "mcp_pdf-reader":
            return True
        for f in e.get("files", []):
            if f.get("read_tool") == "mcp_pdf-reader":
                return True
    return False


def create_default_params(plan_dir: Path):
    params_path = plan_dir / "params.yaml"
    if not params_path.exists():
        plan_dir.mkdir(parents=True, exist_ok=True)
        params_path.write_text(DEFAULT_PARAMS_YAML, encoding="utf-8")
        print(f"[INFO] Created {params_path} with defaults. Edit before proceeding.")


def load_params(plan_dir: Path) -> dict:
    try:
        import yaml
        params_path = plan_dir / "params.yaml"
        if params_path.exists():
            return yaml.safe_load(params_path.read_text()) or {}
    except ImportError:
        pass
    return {}


# ── Phase 1: JSONL parsing ────────────────────────────────────────────────────
def extract_assistant_text(jsonl_output: str) -> str:
    """Extract final assistant message from copilot CLI --output-format json output."""
    last_message = ""
    n_lines = 0
    for line in jsonl_output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        n_lines += 1
        try:
            obj = json.loads(line)
            msg_type = obj.get("type", "")
            if msg_type == "assistant.message":
                # content is nested under data.content
                content = (obj.get("data") or {}).get("content", "") or obj.get("content", "")
                if content:
                    last_message = content
            elif not last_message and isinstance(obj.get("message"), str):
                last_message = obj["message"]
        except json.JSONDecodeError:
            pass
    logger.debug(f"extract_assistant_text: {n_lines} JSONL lines, message length: {len(last_message)}")
    # If no structured output found, return the raw text as-is
    return last_message or jsonl_output.strip()


def parse_json_from_agent_text(text: str) -> dict:
    """Extract the first JSON object from agent response text."""
    decoder = json.JSONDecoder()

    # 1. Look for ```json ... ``` block
    m = re.search(r"```json\s*(\{.*?)\s*```", text, re.DOTALL)
    if m:
        candidate = m.group(1)
        try:
            obj, _ = decoder.raw_decode(candidate)
            logger.debug(f"parse_json_from_agent_text: found JSON in ```json block, {len(obj)} keys")
            return obj
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error from agent response: {e}")
            logger.debug(f"parse_json_from_agent_text: failed candidate (first 200): {candidate[:200]}")
            return {}

    # 2. Fallback: find first '{' and raw_decode from there
    start = text.find("{")
    if start == -1:
        logger.debug(f"parse_json_from_agent_text: no '{{' found in text ({len(text)} chars)")
        return {}
    try:
        obj, _ = decoder.raw_decode(text, start)
        logger.debug(f"parse_json_from_agent_text: found JSON via fallback at pos {start}, {len(obj)} keys")
        return obj
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error from agent response: {e}")
        logger.debug(f"parse_json_from_agent_text: failed text slice (first 200): {text[start:start + 200]}")
        return {}


# ── Phase 1: Prompt rendering ─────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
# Source Extraction Task

## Source Document

{document_instruction}

{assets_block}{clarification_block}## Manifest Entry

```json
{manifest_entry_json}
```
"""


def render_prompt(entry: dict, clarification: str = "") -> str:
    if entry.get("kind") == "subfolder":
        files = entry.get("files", [])
        paths = [f["abs_path"] for f in files if f.get("abs_path")]
        if paths:
            file_list = "\n".join(f"- `{p}`" for p in paths)
            document_instruction = f"Read all files in this folder group:\n{file_list}"
        else:
            document_instruction = f"Read files from: `{entry.get('abs_path', '')}`"
    elif entry.get("kind") == "url":
        url = entry.get("url", "")
        if entry.get("read_tool") == "mcp_confluence":
            document_instruction = (
                f"Fetch this Confluence page using the "
                f"`mcp_mcp-atlassian_confluence_get_page` tool:\n`{url}`"
            )
        else:
            document_instruction = f"Fetch the content at this URL: `{url}`"
    else:
        document_instruction = f"Read the file at this path: `{entry.get('abs_path', '')}`"

    assets = entry.get("assets", [])
    assets_block = ""
    if assets:
        asset_list = "\n".join(f"  - {a}" for a in assets)
        assets_block = (
            f"This document has **{len(assets)} associated image(s)**. "
            f"Read each using your vision capability:\n{asset_list}\n\n"
        )

    clarification_block = ""
    if clarification:
        clarification_block = f"**User clarification:** {clarification}\n\n"

    prompt_entry = {k: v for k, v in entry.items() if k != "abs_path"}
    if prompt_entry.get("files"):
        prompt_entry["files"] = [
            {k: v for k, v in f.items() if k != "abs_path"}
            for f in prompt_entry["files"]
        ]

    return PROMPT_TEMPLATE.format(
        manifest_entry_json=json.dumps(prompt_entry, indent=2, ensure_ascii=False),
        document_instruction=document_instruction,
        assets_block=assets_block,
        clarification_block=clarification_block,
    )


# ── Phase 1: Agent runner ─────────────────────────────────────────────────────
def run_agent(agent_name: str, prompt_file: Path, slug: str,
              model: str = None, project_dir: Path = None) -> AgentResult:
    cmd = [
        "copilot",
        "-p", f"Read your task from: {prompt_file}",
        "--agent", agent_name,
        "--output-format", "json",
        "--allow-all",
        "--no-ask-user",
        "--add-dir", str(REPO_ROOT),
    ]
    if model:
        cmd += ["--model", model]

    logger.info(f"[{slug}] Starting agent")
    logger.debug(f"[{slug}] cmd: {' '.join(cmd)}")
    print(f"[{datetime.now():%H:%M:%S}] [{slug}] start", flush=True)

    _stop = threading.Event()
    def _heartbeat():
        t0 = datetime.now()
        while not _stop.wait(10):
            elapsed = int((datetime.now() - t0).total_seconds())
            remaining = AGENT_TIMEOUT_S - elapsed
            print(f"[{datetime.now():%H:%M:%S}] [{slug}] running... {elapsed}s elapsed, timeout in {remaining}s", flush=True)
    threading.Thread(target=_heartbeat, daemon=True).start()

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        _stop.set()
        logger.error(f"[{slug}] Agent timed out after {AGENT_TIMEOUT_S}s")
        return AgentResult(slug=slug, success=False, raw_text="",
                           parsed_json={}, error="timeout")
    finally:
        _stop.set()

    logger.debug(f"[{slug}] exit code: {proc.returncode}, stdout: {len(proc.stdout)} chars")
    if proc.returncode != 0:
        err = proc.stderr.strip() or f"exit code {proc.returncode}"
        logger.error(f"[{slug}] Agent failed: {err}")
        logger.debug(f"[{slug}] stderr: {proc.stderr[:500]}")
        return AgentResult(slug=slug, success=False, raw_text=proc.stdout,
                           parsed_json={}, error=err, jsonl_log=proc.stdout)

    raw = extract_assistant_text(proc.stdout)
    parsed = parse_json_from_agent_text(raw)
    logger.info(f"[{slug}] Agent finished; JSON found: {bool(parsed)}")
    logger.debug(f"[{slug}] raw_text (first 300): {raw[:300]}")
    return AgentResult(
        slug=slug,
        success=bool(parsed),
        raw_text=raw,
        parsed_json=parsed,
        error="" if parsed else "no valid JSON in response",
        jsonl_log=proc.stdout,
    )


# ── Phase 1: Parallel execution ───────────────────────────────────────────────
def run_agents_parallel(tasks: list, project_dir: Path) -> list:
    results = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        future_to_task = {
            pool.submit(
                run_agent,
                t["agent"],
                t["prompt_file"],
                t["slug"],
                model=t.get("model"),
                project_dir=project_dir,
            ): t
            for t in tasks
        }
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                status = "ok" if result.success else f"failed ({result.error})"
                print(f"[PHASE:1] {result.slug}: {status}")
            except Exception as e:
                slug = task["slug"]
                logger.error(f"[{slug}] Unexpected exception: {e}")
                results.append(AgentResult(
                    slug=slug, success=False, raw_text="",
                    parsed_json={}, error=str(e),
                ))
                print(f"[PHASE:1] {slug}: failed (exception)")
    return results


# ── Phase 1: Save extracts ────────────────────────────────────────────────────
def save_extract(result: AgentResult, artifacts_dir: Path):
    extract_dir = artifacts_dir / "extracts" / result.slug
    extract_dir.mkdir(parents=True, exist_ok=True)

    if result.success and result.parsed_json:
        (extract_dir / "extract.json").write_text(
            json.dumps(result.parsed_json, ensure_ascii=False, indent=2)
        )
    else:
        (extract_dir / "extract.json").write_text(
            json.dumps({
                "error": result.error,
                "source_file": result.slug,
                "partial_raw": result.raw_text[:2000],
            }, ensure_ascii=False, indent=2)
        )
    (extract_dir / "raw.txt").write_text(result.raw_text or "")
    if result.jsonl_log:
        (extract_dir / "agent.jsonl").write_text(result.jsonl_log)


# ── Phase 2: Prompt template ──────────────────────────────────────────────────
PHASE2_PROMPT_TEMPLATE = """\
# Requirements Writing Task

**Project directory:** `{project_dir}`
**Sources analysed:** {source_count}

## Extract Files

{extract_list}

## Output File

`{output_path}`
"""


def render_phase2_prompt(extracts_dir: Path, results: list, project_dir: Path,
                         output_path: Path) -> str:
    successful = [r for r in results if r.success]
    extract_paths = []
    for r in successful:
        ep = extracts_dir / r.slug / "extract.json"
        if ep.exists():
            extract_paths.append(ep)

    extract_list = "\n".join(f"- `{p}`" for p in extract_paths)
    return PHASE2_PROMPT_TEMPLATE.format(
        project_dir=project_dir,
        source_count=len(extract_paths),
        extract_list=extract_list,
        output_path=output_path,
    )


def run_agent_write_mode(agent_name: str, prompt_file: Path, slug: str,
                         output_path: Path, model: str = None,
                         project_dir: Path = None) -> tuple[bool, str]:
    """Run agent without capturing stdout; agent writes output directly to output_path.
    Returns (success, jsonl_log)."""
    cmd = [
        "copilot",
        "-p", f"Read your task from: {prompt_file}",
        "--agent", agent_name,
        "--output-format", "json",
        "--allow-all",
        "--no-ask-user",
        "--add-dir", str(REPO_ROOT),
    ]
    if model:
        cmd += ["--model", model]

    logger.info(f"[{slug}] Starting agent (write mode, output → {output_path})")
    logger.debug(f"[{slug}] cmd: {' '.join(cmd)}")
    print(f"[{datetime.now():%H:%M:%S}] [{slug}] start", flush=True)

    _stop = threading.Event()
    def _heartbeat():
        t0 = datetime.now()
        while not _stop.wait(10):
            elapsed = int((datetime.now() - t0).total_seconds())
            remaining = AGENT_TIMEOUT_S - elapsed
            print(f"[{datetime.now():%H:%M:%S}] [{slug}] running... {elapsed}s elapsed, timeout in {remaining}s", flush=True)
    threading.Thread(target=_heartbeat, daemon=True).start()

    jsonl_lines = []
    try:
        # capture stdout for JSONL log; agent writes the document via write tool
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT_S
        )
        jsonl_lines = proc.stdout
    except subprocess.TimeoutExpired:
        _stop.set()
        logger.error(f"[{slug}] Agent timed out after {AGENT_TIMEOUT_S}s")
        return False, ""
    finally:
        _stop.set()

    logger.debug(f"[{slug}] exit code: {proc.returncode}, stdout: {len(proc.stdout)} chars")
    if proc.returncode != 0:
        err = proc.stderr.strip() or f"exit code {proc.returncode}"
        logger.error(f"[{slug}] Agent failed: {err}")
        logger.debug(f"[{slug}] stderr: {proc.stderr[:500]}")
        return False, proc.stdout

    logger.info(f"[{slug}] Agent process finished")
    return True, jsonl_lines


def run_phase2(results: list, artifacts_dir: Path, project_dir: Path,
               params: dict, output_dir: Path = None) -> bool:
    """Run requirements_writer agent; agent writes _requirements.md directly."""
    successful = [r for r in results if r.success]
    if not successful:
        logger.warning("[phase2] No successful extracts — skipping Phase 2")
        print("[PHASE:2] Skipped — no successful extracts from Phase 1")
        return False

    print(f"[PHASE:2] Synthesising {len(successful)} extract(s) into _requirements.md ...")

    extracts_dir = artifacts_dir / "extracts"
    prompts_dir = artifacts_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    if output_dir is None:
        output_dir = project_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "_requirements.md"

    prompt_content = render_phase2_prompt(extracts_dir, results, project_dir, output_path)
    prompt_file = prompts_dir / "_requirements_writer.md"
    prompt_file.write_text(prompt_content, encoding="utf-8")

    ok, jsonl_log = run_agent_write_mode(
        "requirements_writer",
        prompt_file,
        "_requirements_writer",
        output_path=output_path,
        model=None,
        project_dir=project_dir,
    )

    # Save agent log
    agent_log_dir = artifacts_dir / "extracts" / "_requirements_writer"
    agent_log_dir.mkdir(parents=True, exist_ok=True)
    if jsonl_log:
        (agent_log_dir / "agent.jsonl").write_text(jsonl_log)

    if not ok:
        print("[PHASE:2] FAILED — agent process error")
        return False

    if not output_path.exists() or output_path.stat().st_size < 200:
        logger.error(f"[phase2] Output file missing or too small: {output_path}")
        print("[PHASE:2] FAILED — agent did not write output file")
        return False

    requirements_md = output_path.read_text(encoding="utf-8")

    # Validate content
    has_title = "# Requirements:" in requirements_md
    has_fr = "FR-" in requirements_md
    if not (has_title and has_fr):
        logger.warning("[phase2] Output may be incomplete (missing title or FR entries)")
        print("[PHASE:2] WARNING — output may be incomplete, check _requirements.md")

    fr_count = requirements_md.count("| FR-")
    nfr_count = requirements_md.count("| NFR-")
    br_count = requirements_md.count("| BR-")
    print(f"[PHASE:2] Done → {output_path.name} "
          f"({fr_count} FR, {nfr_count} NFR, {br_count} BR)")
    return True


# ── Phase 3: Requirements Critic ─────────────────────────────────────────────
PHASE_CRITIC_PROMPT_TEMPLATE = """\
# Requirements Critic Task

**Requirements document:** `{requirements_path}`
**Extracts directory:** `{extracts_dir}`
**Verdict output file:** `{verdict_path}`

Read the requirements document, load the output schema and conflict rules, \
cross-check against the source extracts, then write your verdict to the verdict output file.
"""

PHASE_WRITER_REVISION_TEMPLATE = """\
# Requirements Writing Task — Revision Round {round_num}

**Project directory:** `{project_dir}`
**Sources analysed:** {source_count}

## Extract Files

{extract_list}

## Output File

`{output_path}`

## Critic Feedback (must be fully addressed in this revision)

{verdict_content}
"""


def run_phase_requirements_critic(
    requirements_path: Path,
    extracts_dir: Path,
    artifacts_dir: Path,
    project_dir: Path,
    params: dict,
    output_dir: Path,
    results: list,
    max_rounds: int = MAX_CRITIC_ROUNDS,
) -> bool:
    """Run requirements_critic → requirements_writer revision loop.

    Loops until the critic issues APPROVED or the safety cap (MAX_CRITIC_ROUNDS)
    is reached. Always returns True — a safety-cap stop is a quality warning,
    not a fatal pipeline failure.
    """
    prompts_dir = artifacts_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for round_num in range(1, max_rounds + 1):
        verdict_path = artifacts_dir / "extracts" / f"_requirements_critic_r{round_num}" / "verdict.md"
        verdict_path.parent.mkdir(parents=True, exist_ok=True)

        critic_prompt = PHASE_CRITIC_PROMPT_TEMPLATE.format(
            requirements_path=requirements_path,
            extracts_dir=extracts_dir,
            verdict_path=verdict_path,
        )
        critic_prompt_file = prompts_dir / f"_requirements_critic_r{round_num}.md"
        critic_prompt_file.write_text(critic_prompt, encoding="utf-8")

        print(f"[PHASE:3] Round {round_num}/{max_rounds} — running requirements_critic ...")
        ok, jsonl_log = run_agent_write_mode(
            "requirements_critic", critic_prompt_file,
            f"_requirements_critic_r{round_num}",
            output_path=verdict_path, model=None, project_dir=project_dir,
        )
        if jsonl_log:
            (verdict_path.parent / "agent.jsonl").write_text(jsonl_log)

        if not ok or not verdict_path.exists():
            logger.warning(f"[phase3] Critic did not produce verdict file (round {round_num})")
            print(f"[PHASE:3] WARNING — critic failed to write verdict (round {round_num}), skipping")
            return True  # non-fatal

        verdict_text = verdict_path.read_text(encoding="utf-8").strip()
        if verdict_text.startswith("VERDICT: APPROVED"):
            print(f"[PHASE:3] APPROVED on round {round_num}")
            return True

        print(f"[PHASE:3] REVISE requested (round {round_num})")
        logger.info(f"[phase3] Critic verdict (round {round_num}): REVISE")

        if round_num == max_rounds:
            print(f"[PHASE:3] Safety cap ({max_rounds} rounds) reached without APPROVED — stopping with warnings")
            logger.warning(f"[phase3] Critic safety cap hit ({max_rounds} rounds); document may still have unresolved findings")
            return True

        # Revision: feed verdict back to requirements_writer
        successful = [r for r in results if r.success]
        extract_paths = [
            extracts_dir / r.slug / "extract.json"
            for r in successful
            if (extracts_dir / r.slug / "extract.json").exists()
        ]
        extract_list = "\n".join(f"- `{p}`" for p in extract_paths)

        writer_revision_prompt = PHASE_WRITER_REVISION_TEMPLATE.format(
            round_num=round_num + 1,
            project_dir=project_dir,
            source_count=len(extract_paths),
            extract_list=extract_list,
            output_path=requirements_path,
            verdict_content=verdict_text,
        )
        revision_prompt_file = prompts_dir / f"_requirements_writer_r{round_num + 1}.md"
        revision_prompt_file.write_text(writer_revision_prompt, encoding="utf-8")

        print(f"[PHASE:3] Running requirements_writer revision {round_num + 1} ...")
        w_ok, w_log = run_agent_write_mode(
            "requirements_writer", revision_prompt_file,
            f"_requirements_writer_r{round_num + 1}",
            output_path=requirements_path, model=None, project_dir=project_dir,
        )
        w_log_dir = artifacts_dir / "extracts" / f"_requirements_writer_r{round_num + 1}"
        w_log_dir.mkdir(parents=True, exist_ok=True)
        if w_log:
            (w_log_dir / "agent.jsonl").write_text(w_log)

        if not w_ok:
            logger.warning(f"[phase3] Revision writer failed on round {round_num + 1}")
            print(f"[PHASE:3] WARNING — writer revision failed (round {round_num + 1})")
            return True  # non-fatal

    return True


# ── Phase 1: HITL:clarify ─────────────────────────────────────────────────────
def collect_clarifications(results: list) -> list:
    flagged = []
    for r in results:
        if r.parsed_json.get("needs_clarification"):
            flagged.append(ClarifyRequest(
                slug=r.slug,
                source_file=r.parsed_json.get("source_file", r.slug),
                question=r.parsed_json.get("clarification_request",
                                            "No details provided"),
            ))
    return flagged


def hitl_clarify(flagged: list, interactive: bool) -> dict:
    """Ask clarification questions in terminal or skip in headless mode. Returns {slug: answer}."""
    if not flagged:
        return {}

    if not interactive:
        for r in flagged:
            logger.info(f"[HITL] Skipping clarification for {r.slug}: {r.question}")
        return {}

    answers = {}
    print("\n" + "─" * 60)
    print(f"[HITL] Агент запрашивает уточнения ({len(flagged)} шт.)")
    print("─" * 60)
    for r in flagged:
        print(f"\nФайл: {r.source_file}")
        print(f"Вопрос: {r.question}")
        try:
            answer = input("Ваш ответ (Enter — пропустить): ").strip()
        except EOFError:
            break
        if answer:
            answers[r.slug] = answer
    print("─" * 60 + "\n")
    sys.stdout.flush()
    return answers


# ── Phase 1: Main flow ────────────────────────────────────────────────────────
def run_phase1(entries: list, project_dir: Path, artifacts_dir: Path,
               params: dict, interactive: bool) -> list:
    prompts_dir = artifacts_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for entry in entries:
        slug = entry["slug"]
        prompt_content = render_prompt(entry)
        prompt_file = prompts_dir / f"{slug}.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")
        tasks.append({
            "agent": "source_processor",
            "slug": slug,
            "prompt_file": prompt_file,
            "model": None,
        })

    print(f"[PHASE:1] Running {len(tasks)} agents in parallel")
    results = run_agents_parallel(tasks, project_dir)

    for r in results:
        save_extract(r, artifacts_dir)

    # HITL:clarify — up to 2 rounds
    for round_num in range(1, 3):
        flagged = collect_clarifications(results)
        if not flagged:
            break

        print(f"[PHASE:1] {len(flagged)} agent(s) need clarification "
              f"(round {round_num}/2)")
        answers = hitl_clarify(flagged, interactive)
        if not answers:
            logger.info(f"Skipped clarifications: {[r.slug for r in flagged]}")
            break

        retry_tasks = []
        for slug, answer in answers.items():
            entry = next((e for e in entries if e["slug"] == slug), None)
            if not entry:
                continue
            prompt_content = render_prompt(entry, clarification=answer)
            prompt_file = prompts_dir / f"{slug}_retry{round_num}.md"
            prompt_file.write_text(prompt_content, encoding="utf-8")
            retry_tasks.append({
                "agent": "source_processor",
                "slug": slug,
                "prompt_file": prompt_file,
                "model": model,
            })

        if retry_tasks:
            retry_results = run_agents_parallel(retry_tasks, project_dir)
            for rr in retry_results:
                save_extract(rr, artifacts_dir)
            result_map = {r.slug: r for r in results}
            for rr in retry_results:
                result_map[rr.slug] = rr
            results = list(result_map.values())

    return results


def update_manifest_with_extracts(manifest: dict, results: list, artifacts_dir: Path) -> dict:
    result_map = {r.slug: r for r in results}
    for entry in manifest["entries"]:
        slug = entry["slug"]
        r = result_map.get(slug)
        if not r:
            entry["extract_status"] = "not_run"
            continue
        if r.success:
            entry["extract_status"] = "ok"
        elif r.parsed_json.get("needs_clarification"):
            entry["extract_status"] = "needs_clarification"
        else:
            entry["extract_status"] = "failed"
        entry["extract_path"] = f"{artifacts_dir.name}/extracts/{slug}/extract.json"
    return manifest


# ── Discovery: Prompt templates ───────────────────────────────────────────────
DISCOVERY_PROBE_PROMPT_TEMPLATE = """\
# arch_probe Task

**Project directory:** `{project_dir}`
**Sources analysed:** {source_count}

## Extract Files

{extract_list}
"""

DISCOVERY_CRITIC_PROMPT_TEMPLATE = """\
# arch_critic Task

**Project directory:** `{project_dir}`
**arch_probe output:** `{arch_probe_output_path}`
**Write report to:** `{output_path}`
"""


# ── Discovery: Phase arch_probe ───────────────────────────────────────────────
def run_phase_arch_probe(results: list, artifacts_dir: Path,
                         project_dir: Path, params: dict) -> AgentResult | None:
    """Run arch_probe agent; returns AgentResult with parsed JSON or None on failure."""
    successful = [r for r in results if r.success]
    if not successful:
        logger.warning("[discovery:probe] No successful extracts — skipping arch_probe")
        print("[PHASE:D1] Skipped — no successful extracts from Phase 1")
        return None

    print(f"[PHASE:D1] Running arch_probe on {len(successful)} extract(s) ...")

    extracts_dir = artifacts_dir / "extracts"
    prompts_dir = artifacts_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    extract_paths = []
    for r in successful:
        ep = extracts_dir / r.slug / "extract.json"
        if ep.exists():
            extract_paths.append(ep)

    extract_list = "\n".join(f"- `{p}`" for p in extract_paths)
    prompt_content = DISCOVERY_PROBE_PROMPT_TEMPLATE.format(
        project_dir=project_dir,
        source_count=len(extract_paths),
        extract_list=extract_list,
    )
    prompt_file = prompts_dir / "_arch_probe.md"
    prompt_file.write_text(prompt_content, encoding="utf-8")

    result = run_agent("arch_probe", prompt_file, "arch_probe", model=None,
                       project_dir=project_dir)

    # Save arch_probe output
    probe_dir = artifacts_dir / "extracts" / "_arch_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    (probe_dir / "raw.txt").write_text(result.raw_text or "")
    if result.jsonl_log:
        (probe_dir / "agent.jsonl").write_text(result.jsonl_log)

    if not result.success or not result.parsed_json:
        print(f"[PHASE:D1] FAILED — {result.error}")
        return None

    probe_output_path = probe_dir / "probe_output.json"
    probe_output_path.write_text(
        json.dumps(result.parsed_json, ensure_ascii=False, indent=2)
    )
    q_count = len(result.parsed_json.get("raw_questions", []))
    ai_score = (result.parsed_json.get("ai_detection") or {}).get("overall_assessment", "?")
    print(f"[PHASE:D1] Done — {q_count} raw question(s), AI score: {ai_score}")
    result.slug = "_arch_probe"
    return result


# ── Discovery: Phase arch_critic ──────────────────────────────────────────────
def run_phase_arch_critic(probe_result: AgentResult, artifacts_dir: Path,
                          project_dir: Path, params: dict,
                          output_dir: Path = None) -> bool:
    """Run arch_critic agent; agent writes discovery_report.md directly."""
    probe_dir = artifacts_dir / "extracts" / "_arch_probe"
    probe_output_path = probe_dir / "probe_output.json"
    if not probe_output_path.exists():
        print("[PHASE:D2] FAILED — arch_probe output not found")
        return False

    print("[PHASE:D2] Running arch_critic ...")

    prompts_dir = artifacts_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    if output_dir is None:
        output_dir = project_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "discovery_report.md"

    prompt_content = DISCOVERY_CRITIC_PROMPT_TEMPLATE.format(
        project_dir=project_dir,
        arch_probe_output_path=probe_output_path,
        output_path=output_path,
    )
    prompt_file = prompts_dir / "_arch_critic.md"
    prompt_file.write_text(prompt_content, encoding="utf-8")

    ok, jsonl_log = run_agent_write_mode(
        "arch_critic", prompt_file, "_arch_critic",
        output_path=output_path, model=None, project_dir=project_dir,
    )

    critic_dir = artifacts_dir / "extracts" / "_arch_critic"
    critic_dir.mkdir(parents=True, exist_ok=True)
    if jsonl_log:
        (critic_dir / "agent.jsonl").write_text(jsonl_log)

    if not ok:
        print("[PHASE:D2] FAILED — agent process error")
        return False

    if not output_path.exists() or output_path.stat().st_size < 200:
        logger.error(f"[discovery:critic] Output file missing or too small: {output_path}")
        print("[PHASE:D2] FAILED — agent did not write discovery_report.md")
        return False

    q_count = output_path.read_text(encoding="utf-8").count("\n**Q-")
    print(f"[PHASE:D2] Done → discovery_report.md ({q_count} question(s))")
    return True


# ── Discovery: Main flow ──────────────────────────────────────────────────────
def run_discovery(project_dir: Path, interactive: bool) -> int:
    """Run discovery pipeline: scan → extract → arch_probe → arch_critic."""
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_dir.parent / f"discovery_{run_ts}"
    artifacts_dir = output_dir / f"_artifacts_{run_ts}"
    plan_dir = output_dir / "plan"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(artifacts_dir / "runner.log"), level="DEBUG", encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    )

    if not check_copilot_cli():
        print("[ERROR] 'copilot' CLI not found in PATH.", file=sys.stderr)
        return 1

    create_default_params(plan_dir)
    params = load_params(plan_dir)

    # Phase 0
    print(f"[PHASE:0] Scanning {project_dir} ...")
    entries = scan_project(project_dir)
    if not entries:
        print("[ERROR] No supported files found.", file=sys.stderr)
        return 1

    print(f"[PHASE:0] Found {len(entries)} entries "
          f"({sum(1 for e in entries if e['kind']=='file')} files, "
          f"{sum(1 for e in entries if e['kind']=='subfolder')} folders, "
          f"{sum(1 for e in entries if e['kind']=='url')} URLs)")

    manifest = build_manifest(project_dir, entries)
    intake_dir = artifacts_dir / "intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = intake_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[PHASE:0] Manifest written → {manifest_path}")

    # Phase 1
    print("[PHASE:1] Starting source extraction ...")
    results = run_phase1(entries, project_dir, artifacts_dir, params, interactive)

    manifest = update_manifest_with_extracts(manifest, results, artifacts_dir)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    ok = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    print(f"[PHASE:1] Extraction complete: {ok} ok, {failed} failed.")

    # Phase D1: arch_probe
    probe_result = run_phase_arch_probe(results, artifacts_dir, project_dir, params)
    if probe_result is None:
        print("[DONE] Discovery aborted — arch_probe failed.")
        return 1

    # Phase D2: arch_critic
    critic_ok = run_phase_arch_critic(probe_result, artifacts_dir, project_dir, params, output_dir)
    if critic_ok:
        print(f"[DONE] Discovery report → {output_dir / 'discovery_report.md'}")
        return 0
    else:
        print("[DONE] Discovery failed at arch_critic — check logs.")
        return 1


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="RFP Manager Runner — Phase 0 + 1 + 2"
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the extraction pipeline")
    run_parser.add_argument("project_dir", type=Path,
                            help="Path to folder with RFP documents")
    run_parser.add_argument("--interactive", action="store_true", default=False,
                            help="Pause at HITL checkpoints (requires terminal)")
    run_parser.add_argument("--no-interactive", action="store_true",
                            dest="no_interactive",
                            help="Skip HITL pauses, use defaults (default)")
    run_parser.add_argument(
        "--mode",
        choices=["extract", "discovery"],
        default="extract",
        help="'extract' (default) — produce _requirements.md; "
             "'discovery' — produce discovery_report.md with SA questions",
    )
    run_parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Enable DEBUG-level logging for troubleshooting",
    )

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return 1

    _stderr_level = "DEBUG" if args.debug else "INFO"
    logger.add(
        sys.stderr, level=_stderr_level, colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    if args.debug:
        logger.debug("Debug logging enabled")

    interactive = args.interactive and not args.no_interactive
    project_dir = args.project_dir.resolve()

    if not project_dir.exists() or not project_dir.is_dir():
        print(f"[ERROR] Not a directory: {project_dir}", file=sys.stderr)
        return 1

    if args.mode == "discovery":
        return run_discovery(project_dir, interactive)

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_dir.parent / f"requirements_{run_ts}"
    artifacts_dir = output_dir / f"_artifacts_{run_ts}"
    plan_dir = output_dir / "plan"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(artifacts_dir / "runner.log"), level="DEBUG", encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    )

    # Pre-flight checks
    if not check_copilot_cli():
        print("[ERROR] 'copilot' CLI not found in PATH. "
              "Install GitHub Copilot CLI first.", file=sys.stderr)
        return 1

    create_default_params(plan_dir)
    params = load_params(plan_dir)

    # ── Phase 0 ──────────────────────────────────────────────────────────────
    print(f"[PHASE:0] Scanning {project_dir} ...")
    entries = scan_project(project_dir)

    if not entries:
        print("[ERROR] No supported files found in project directory.",
              file=sys.stderr)
        return 1

    print(f"[PHASE:0] Found {len(entries)} entries "
          f"({sum(1 for e in entries if e['kind']=='file')} files, "
          f"{sum(1 for e in entries if e['kind']=='subfolder')} folders, "
          f"{sum(1 for e in entries if e['kind']=='url')} URLs)")

    manifest = build_manifest(project_dir, entries)
    intake_dir = artifacts_dir / "intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = intake_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"[PHASE:0] Manifest written → {manifest_path}")

    if any_pdf_in_manifest(entries) and not check_mcp_pdf_reader():
        print("[WARN] pdf-reader MCP not found in mcp.json — "
              "PDF files may fail in Phase 1.")

    # ── Phase 1 ──────────────────────────────────────────────────────────────
    print("[PHASE:1] Starting source extraction ...")
    results = run_phase1(entries, project_dir, artifacts_dir, params, interactive)

    manifest = update_manifest_with_extracts(manifest, results, artifacts_dir)
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    ok = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    print(f"[DONE] Extraction complete: {ok} ok, {failed} failed.")
    print(f"[DONE] Extracts → {artifacts_dir / 'extracts'}")

    # ── Phase 2 ──────────────────────────────────────────────────────────────
    phase2_ok = run_phase2(results, artifacts_dir, project_dir, params, output_dir)
    if not phase2_ok:
        print("[DONE] Phase 2 failed — check logs above.")
        return 1

    requirements_path = output_dir / "_requirements.md"
    extracts_dir = artifacts_dir / "extracts"

    # ── Phase 3 ──────────────────────────────────────────────────────────────
    run_phase_requirements_critic(
        requirements_path=requirements_path,
        extracts_dir=extracts_dir,
        artifacts_dir=artifacts_dir,
        project_dir=project_dir,
        params=params,
        output_dir=output_dir,
        results=results,
    )

    print(f"[DONE] Requirements document → {requirements_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
