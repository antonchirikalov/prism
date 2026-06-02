#!/usr/bin/env python3
"""
Solution Design Runner

Phase 0: Read requirements document, create output directory, initialise ledger.
Phase 1: Run solution_designer agent twice in parallel (claude-sonnet-4.6, gpt-5.5).
Phase 2: Run solution_design_selector — picks best candidate as _solution_design.md.
Phase 3: Critic loop (max 3 rounds) — review, revise if REVISE verdict, stop on APPROVED.
Phase 4: Print final output summary.

Usage:
    python3 solution_design_runner.py run <path_to/_requirements.md> [--verbose]
    python3 solution_design_runner.py status <output_dir>
    python3 solution_design_runner.py resume <output_dir>            [--verbose]
    python3 solution_design_runner.py resume <output_dir>            [--retry-failed] [--verbose]
    python3 solution_design_runner.py resume <output_dir>            [--force-step STEP_ID] [--verbose]

Step IDs (for --force-step):
    designer-<model>   e.g. designer-claude-sonnet-4_6
    selector
    critic:r1  critic:r2  critic:r3
    revision:r1  revision:r2
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
AGENT_TIMEOUT_S = 3600  # 60 min per agent call
MAX_CRITIC_ROUNDS = 3
MIN_OUTPUT_BYTES = 200

DESIGNER_MODELS = [
    "claude-sonnet-4.6",
    "gpt-5.5",
]

logger.remove()


# ── Validation gates ──────────────────────────────────────────────────────────

def gate_design_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "file not found"
    size = path.stat().st_size
    if size < MIN_OUTPUT_BYTES:
        return False, f"file too small ({size} bytes < {MIN_OUTPUT_BYTES})"
    return True, "ok"


def gate_verdict_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "file not found"
    text = path.read_text().strip()
    if not text:
        return False, "empty file"
    first_line = text.splitlines()[0]
    if first_line.startswith(("VERDICT: APPROVED", "VERDICT: REVISE")):
        return True, "ok"
    return False, f"unexpected first line: {first_line!r}"


# ── Ledger ────────────────────────────────────────────────────────────────────

class Ledger:
    """Crash-safe state tracker — state.json is the single source of truth."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self._path = path
        self._state: dict = {}
        self._lock = threading.Lock()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _save(self) -> None:
        """Atomic write via tmp → os.replace. Caller must hold self._lock."""
        self._state["updated_at"] = self._now()
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._state, indent=2, ensure_ascii=False))
        os.replace(tmp, self._path)

    # ── constructors ──────────────────────────────────────────────────────────

    @classmethod
    def create(cls, path: Path, run_id: str, requirements_path: Path, designer_models: list[str]) -> "Ledger":
        l = cls(path)
        l._state = {
            "schema_version": cls.SCHEMA_VERSION,
            "run_id": run_id,
            "requirements_path": str(requirements_path),
            "designer_models": designer_models,
            "created_at": l._now(),
            "updated_at": l._now(),
            "steps": {},
            "loops": {
                "critic": {
                    "round": 0,
                    "max_rounds": MAX_CRITIC_ROUNDS,
                    "last_verdict": None,
                    "complete": False,
                }
            },
            "winning_model": None,
        }
        l._save()
        return l

    @classmethod
    def load(cls, path: Path) -> "Ledger":
        """Load existing state; reset any 'running' steps to 'pending' (crash recovery)."""
        l = cls(path)
        l._state = json.loads(path.read_text())
        for sid, step in l._state.get("steps", {}).items():
            if step.get("status") == "running":
                logger.warning(f"[ledger] '{sid}' was running at crash → reset to pending")
                step["status"] = "pending"
        l._save()
        return l

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def run_id(self) -> str:
        return self._state["run_id"]

    @property
    def requirements_path(self) -> Path:
        return Path(self._state["requirements_path"])

    @property
    def designer_models(self) -> list[str]:
        return self._state.get("designer_models", DESIGNER_MODELS)

    @property
    def winning_model(self) -> str | None:
        return self._state.get("winning_model")

    @winning_model.setter
    def winning_model(self, value: str) -> None:
        with self._lock:
            self._state["winning_model"] = value
            self._save()

    def get_critic_round(self) -> int:
        return self._state["loops"]["critic"]["round"]

    def get_last_critic_verdict(self) -> str | None:
        return self._state["loops"]["critic"].get("last_verdict")

    def is_critic_complete(self) -> bool:
        return self._state["loops"]["critic"]["complete"]

    def update_critic_loop(self, round_num: int, last_verdict: str) -> None:
        with self._lock:
            self._state["loops"]["critic"]["round"] = round_num
            self._state["loops"]["critic"]["last_verdict"] = last_verdict
            self._save()

    def set_critic_complete(self, last_verdict: str) -> None:
        with self._lock:
            self._state["loops"]["critic"]["complete"] = True
            self._state["loops"]["critic"]["last_verdict"] = last_verdict
            self._save()

    # ── resume helpers ────────────────────────────────────────────────────────

    def reset_failed_steps(self) -> int:
        """Mark all failed steps as pending so they retry on resume. Returns count reset."""
        with self._lock:
            count = 0
            has_failed_critic = False
            for sid, step in self._state["steps"].items():
                if step.get("status") == "failed":
                    step["status"] = "pending"
                    count += 1
                    if sid.startswith(("critic:", "revision:")):
                        has_failed_critic = True
            # If a critic/revision step failed the loop may be stuck; un-complete it
            if has_failed_critic and self._state["loops"]["critic"].get("complete"):
                self._state["loops"]["critic"]["complete"] = False
            if count:
                self._save()
            return count

    def reset_step(self, step_id: str) -> bool:
        """Force-reset a single step to pending. Returns True if the step was found."""
        with self._lock:
            step = self._state["steps"].get(step_id)
            if step is None:
                return False
            step["status"] = "pending"
            if step_id.startswith(("critic:", "revision:")):
                self._state["loops"]["critic"]["complete"] = False
            self._save()
            return True

    @property
    def critic_loop_state(self) -> dict:
        return self._state["loops"]["critic"]

    @property
    def raw_state(self) -> dict:
        """Read-only snapshot of full state for display."""
        return dict(self._state)

    # ── step transitions ──────────────────────────────────────────────────────

    def is_done(self, step_id: str, artifact_path: Path, gate_fn) -> bool:
        with self._lock:
            step = self._state["steps"].get(step_id, {})
            if step.get("status") != "done":
                return False
        passed, _ = gate_fn(artifact_path)
        return passed

    def mark_running(self, step_id: str) -> None:
        with self._lock:
            step = self._state["steps"].setdefault(step_id, {})
            step["status"] = "running"
            step["started_at"] = self._now()
            step["attempts"] = step.get("attempts", 0) + 1
            self._save()

    def mark_done(self, step_id: str, artifact_path: Path, wall_s: float) -> None:
        with self._lock:
            step = self._state["steps"].setdefault(step_id, {})
            step.update({
                "status": "done",
                "artifact": str(artifact_path),
                "finished_at": self._now(),
                "wall_s": round(wall_s, 1),
            })
            self._save()

    def mark_failed(self, step_id: str, error: str, wall_s: float) -> None:
        with self._lock:
            step = self._state["steps"].setdefault(step_id, {})
            step.update({
                "status": "failed",
                "error": error,
                "finished_at": self._now(),
                "wall_s": round(wall_s, 1),
            })
            self._save()


# ── Data class ────────────────────────────────────────────────────────────────
@dataclass
class AgentRun:
    slug: str
    success: bool
    raw_stdout: str = ""
    error: str = ""


# ── Agent runner helpers ──────────────────────────────────────────────────────
def _heartbeat(slug: str, stop: threading.Event) -> None:
    t0 = datetime.now()
    while not stop.wait(10):
        elapsed = int((datetime.now() - t0).total_seconds())
        print(
            f"[{datetime.now():%H:%M:%S}] [{slug}] running... {elapsed}s elapsed, timeout in {AGENT_TIMEOUT_S - elapsed}s",
            flush=True,
        )


def run_agent_write_mode(
    agent_name: str,
    prompt_file: Path,
    slug: str,
    output_path: Path,
    model: str = None,
    extra_dirs: list[Path] = None,
    logs_dir: Path = None,
) -> AgentRun:
    """Run agent; agent writes output via write tool to output_path."""
    cmd = [
        "copilot",
        "-p", f"Read your task from: {prompt_file}",
        "--agent", agent_name,
        "--output-format", "json",
        "--allow-all",
        "--no-ask-user",
        "--add-dir", str(REPO_ROOT),
    ]
    for d in (extra_dirs or []):
        if Path(d).resolve() != REPO_ROOT:
            cmd += ["--add-dir", str(d)]
    if model:
        cmd += ["--model", model]

    logger.info(f"[{slug}] Starting agent → {output_path.name}")
    logger.debug(f"[{slug}] cmd: {' '.join(cmd)}")
    print(f"[{datetime.now():%H:%M:%S}] [{slug}] start", flush=True)

    stop = threading.Event()
    threading.Thread(target=_heartbeat, args=(slug, stop), daemon=True).start()

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        stop.set()
        logger.error(f"[{slug}] Timed out after {AGENT_TIMEOUT_S}s")
        return AgentRun(slug=slug, success=False, error="timeout")
    finally:
        stop.set()

    # Save JSONL log + stderr for diagnostics
    if logs_dir:
        logs_dir.mkdir(parents=True, exist_ok=True)
        if proc.stdout:
            (logs_dir / f"{slug}.jsonl").write_text(proc.stdout)
        if proc.stderr:
            (logs_dir / f"{slug}.stderr.txt").write_text(proc.stderr)

    logger.debug(f"[{slug}] exit code: {proc.returncode}, stdout: {len(proc.stdout)} chars")
    if proc.returncode != 0:
        err = proc.stderr.strip() or f"exit code {proc.returncode}"
        logger.error(f"[{slug}] Agent failed: {err}")
        if logs_dir:
            logger.error(f"[{slug}] Stderr saved to: {logs_dir / f'{slug}.stderr.txt'}")
        return AgentRun(slug=slug, success=False, raw_stdout=proc.stdout, error=err)

    success = output_path.exists() and output_path.stat().st_size > 0
    if not success:
        logger.warning(f"[{slug}] Exit 0 but output missing: {output_path}")
    else:
        logger.info(f"[{slug}] Done; {output_path.stat().st_size} bytes")
    return AgentRun(slug=slug, success=success, raw_stdout=proc.stdout)


# ── Step runner with idempotency ──────────────────────────────────────────────
def run_step(
    step_id: str,
    ledger: Ledger,
    gate_fn,
    artifact_path: Path,
    run_fn,
) -> bool:
    """Run a step; skip if already done and artifact passes gate."""
    if ledger.is_done(step_id, artifact_path, gate_fn):
        print(f"[SKIP] {step_id} (already done)", flush=True)
        return True
    ledger.mark_running(step_id)
    t0 = datetime.now()
    result: AgentRun = run_fn()
    wall_s = (datetime.now() - t0).total_seconds()
    passed, detail = gate_fn(artifact_path)
    if result.success and passed:
        ledger.mark_done(step_id, artifact_path, wall_s)
        return True
    err = result.error or f"gate failed: {detail}"
    ledger.mark_failed(step_id, err, wall_s)
    return False


# ── Prompt file writers ───────────────────────────────────────────────────────
def write_designer_prompt(
    prompt_file: Path,
    requirements_path: Path,
    output_file: Path,
    revision_instructions: str = "",
) -> None:
    lines = [
        f"Requirements document: {requirements_path}",
        f"Output file: {output_file}",
    ]
    if revision_instructions:
        lines.append(f"Revision instructions: {revision_instructions}")
    prompt_file.write_text("\n".join(lines))


def _safe_model_slug(model: str) -> str:
    """Turn a model name into a filesystem-safe slug."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", model)


def write_selector_prompt(
    prompt_file: Path,
    candidates: list[tuple[str, str, Path]],  # [(label, model, path), ...]
    output_path: Path,
    report_path: Path,
) -> None:
    lines = [f"Candidate {label} ({model}): {path}" for label, model, path in candidates]
    lines += [
        f"Output file: {output_path}",
        f"Selection report: {report_path}",
    ]
    prompt_file.write_text("\n".join(lines) + "\n")


def write_critic_prompt(
    prompt_file: Path,
    design_path: Path,
    verdict_path: Path,
) -> None:
    prompt_file.write_text(
        f"Solution design document: {design_path}\n"
        f"Verdict output: {verdict_path}\n"
    )


def write_revision_prompt(
    prompt_file: Path,
    requirements_path: Path,
    output_file: Path,
    verdict_path: Path,
) -> None:
    verdict_text = verdict_path.read_text() if verdict_path.exists() else ""
    # Extract issues block from verdict
    issues_match = re.search(r"## Issues\n(.+?)(?=\n## |\Z)", verdict_text, re.DOTALL)
    issues_text = issues_match.group(1).strip() if issues_match else verdict_text.strip()

    prompt_file.write_text(
        f"Requirements document: {requirements_path}\n"
        f"Output file: {output_file}\n"
        f"Revision instructions: Address the following issues from the critic review:\n"
        f"{issues_text}\n"
    )


# ── Verdict parser ────────────────────────────────────────────────────────────
def parse_verdict(verdict_path: Path) -> str:
    """Returns 'APPROVED' or 'REVISE'."""
    if not verdict_path.exists():
        return "REVISE"
    text = verdict_path.read_text()
    if "VERDICT: APPROVED" in text:
        return "APPROVED"
    return "REVISE"


# ── Status display ────────────────────────────────────────────────────────────

_STATUS_ICON = {"done": "✓", "failed": "✗", "running": "⟳", "pending": "○"}


def _print_run_state(ledger: Ledger, out_dir: Path) -> None:
    """Print a human-readable summary of run state to stdout."""
    st = ledger.raw_state
    critic = ledger.critic_loop_state

    print(f"\n{'─' * 70}", flush=True)
    print(f"  Run:      {st['run_id']}", flush=True)
    print(f"  Created:  {st['created_at']}", flush=True)
    print(f"  Updated:  {st['updated_at']}", flush=True)
    print(f"  Models:   {', '.join(st.get('designer_models', []))}", flush=True)
    if st.get("winning_model"):
        print(f"  Winner:   {st['winning_model']}", flush=True)
    print(
        f"  Critic:   round {critic.get('round', 0)}/{critic.get('max_rounds', MAX_CRITIC_ROUNDS)}"
        f"  verdict={critic.get('last_verdict') or 'N/A'}"
        f"  complete={critic.get('complete', False)}",
        flush=True,
    )
    print(flush=True)

    steps = st.get("steps", {})
    if not steps:
        print("  (no steps recorded yet)", flush=True)
    else:
        hdr = f"  {'Step':<32} {'Status':<10} {'Elapsed':>8}  {'Tries':>5}  Info"
        print(hdr, flush=True)
        print(f"  {'─' * 66}", flush=True)
        for sid, s in steps.items():
            icon = _STATUS_ICON.get(s.get("status", ""), "?")
            wall = f"{s['wall_s']:.0f}s" if s.get("wall_s") else "  -"
            tries = s.get("attempts", 1)
            info = s.get("error") or (Path(s["artifact"]).name if s.get("artifact") else "")
            print(
                f"  {icon} {sid:<31} {s.get('status','?'):<10} {wall:>8}  {tries:>5}  {info}",
                flush=True,
            )

    logs_dir = out_dir / "logs"
    if logs_dir.exists():
        stderr_logs = sorted(logs_dir.glob("*.stderr.txt"))
        if stderr_logs:
            print(flush=True)
            print(f"  Stderr logs ({len(stderr_logs)}):", flush=True)
            for f in stderr_logs:
                size = f.stat().st_size
                print(f"    {f.name}  ({size} bytes)", flush=True)

    print(f"{'─' * 70}\n", flush=True)


def cmd_status(output_dir: Path) -> int:
    state_path = output_dir / "state.json"
    if not state_path.exists():
        print(f"[ERROR] No state.json found in {output_dir}", file=sys.stderr)
        return 1
    ledger = Ledger.load(state_path)
    _print_run_state(ledger, output_dir)
    return 0


def parse_winning_model(report_path: Path, designer_models: list[str]) -> str:
    """Parses WINNING_MODEL: <value> from selection report."""
    fallback = designer_models[0]
    if not report_path.exists():
        return fallback
    m = re.search(r"WINNING_MODEL:\s*(.+)", report_path.read_text())
    return m.group(1).strip() if m else fallback


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _run_designer_task(
    task: dict,
    ledger: Ledger,
    logs_dir: Path,
    extra_dirs: list[Path],
) -> bool:
    return run_step(
        task["step_id"], ledger, gate_design_file, task["artifact"],
        lambda: run_agent_write_mode(
            "solution_designer",
            task["prompt_file"],
            task["step_id"],
            task["artifact"],
            model=task["model"],
            extra_dirs=extra_dirs,
            logs_dir=logs_dir,
        ),
    )


def _execute_pipeline(out_dir: Path, requirements_path: Path, ledger: Ledger, designer_models: list[str]) -> int:
    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    extra_dirs = [requirements_path.parent, out_dir]

    print(f"[PHASE:0] Output dir:     {out_dir}", flush=True)
    print(f"[PHASE:0] Requirements:   {requirements_path}", flush=True)
    print(f"[PHASE:0] Designer models: {', '.join(designer_models)}", flush=True)

    design_paths = {
        model: out_dir / f"_design_{_safe_model_slug(model)}.md"
        for model in designer_models
    }

    # ── Phase 1: parallel generation ─────────────────────────────────────────
    print("\n[PHASE:1] Generating solution designs...", flush=True)
    tasks = []
    for model in designer_models:
        step_id = f"designer-{model}"
        artifact = design_paths[model]
        if ledger.is_done(step_id, artifact, gate_design_file):
            print(f"[SKIP] {step_id} (already done)", flush=True)
            continue
        prompt_file = prompts_dir / f"designer_{model.replace('.', '_')}_prompt.txt"
        write_designer_prompt(prompt_file, requirements_path, artifact)
        tasks.append({
            "step_id": step_id,
            "model": model,
            "prompt_file": prompt_file,
            "artifact": artifact,
        })

    if tasks:
        with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            future_to_task = {
                pool.submit(_run_designer_task, t, ledger, logs_dir, extra_dirs): t
                for t in tasks
            }
            for future in as_completed(future_to_task):
                t = future_to_task[future]
                try:
                    ok = future.result()
                    print(f"[PHASE:1] {t['model']}: {'ok' if ok else 'FAILED'}", flush=True)
                except Exception as exc:
                    logger.error(f"[{t['step_id']}] Exception: {exc}")
                    ledger.mark_failed(t["step_id"], str(exc), 0.0)
                    print(f"[PHASE:1] {t['model']}: FAILED (exception)", flush=True)

    successful_models = [
        m for m in designer_models
        if ledger.is_done(f"designer-{m}", design_paths[m], gate_design_file)
    ]
    if not successful_models:
        print("[ERROR] No successful design candidates. Aborting.", file=sys.stderr)
        return 1

    # ── Phase 2: selection ────────────────────────────────────────────────────
    print("\n[PHASE:2] Selecting best design...", flush=True)
    final_design_path = out_dir / "_solution_design.md"
    selection_report_path = out_dir / "_selection_report.md"

    if not ledger.is_done("selector", final_design_path, gate_design_file):
        if len(successful_models) == 1:
            winning_model = successful_models[0]
            shutil.copy2(design_paths[winning_model], final_design_path)
            selection_report_path.write_text(
                f"WINNING_MODEL: {winning_model}\n\n"
                f"## Selection Rationale\n\nOnly one candidate succeeded in Phase 1.\n"
            )
            ledger.mark_done("selector", final_design_path, 0.0)
            print(f"[PHASE:2] Only one candidate; selected: {winning_model}", flush=True)
        else:
            selector_prompt = prompts_dir / "selector_prompt.txt"
            candidates = [
                (chr(65 + i), m, design_paths[m])
                for i, m in enumerate(successful_models)
            ]
            write_selector_prompt(
                selector_prompt,
                candidates,
                final_design_path, selection_report_path,
            )
            ok = run_step(
                "selector", ledger, gate_design_file, final_design_path,
                lambda: run_agent_write_mode(
                    "solution_design_selector", selector_prompt, "selector",
                    final_design_path, extra_dirs=extra_dirs, logs_dir=logs_dir,
                ),
            )
            if not ok:
                print("[WARNING] Selector failed; falling back to first candidate.", flush=True)
                shutil.copy2(design_paths[successful_models[0]], final_design_path)
                selection_report_path.write_text(f"WINNING_MODEL: {successful_models[0]}\n")
                ledger.mark_done("selector", final_design_path, 0.0)
    else:
        print("[SKIP] selector (already done)", flush=True)

    winning_model = ledger.winning_model or parse_winning_model(selection_report_path, designer_models)
    if not ledger.winning_model:
        ledger.winning_model = winning_model
    print(f"[PHASE:2] Winning model: {winning_model}", flush=True)

    # ── Phase 3: critic loop ──────────────────────────────────────────────────
    print("\n[PHASE:3] Critic review loop...", flush=True)
    final_verdict = ledger.get_last_critic_verdict() or "REVISE"
    final_round = ledger.get_critic_round()

    if ledger.is_critic_complete():
        print(f"[SKIP] Critic loop (already complete: {final_verdict})", flush=True)
    else:
        for round_num in range(1, MAX_CRITIC_ROUNDS + 1):
            print(f"[PHASE:3] Round {round_num}/{MAX_CRITIC_ROUNDS}", flush=True)
            final_round = round_num

            verdict_path = out_dir / f"_verdict_round{round_num}.md"
            critic_prompt = prompts_dir / f"critic_prompt_r{round_num}.txt"
            write_critic_prompt(critic_prompt, final_design_path, verdict_path)

            ok = run_step(
                f"critic:r{round_num}", ledger, gate_verdict_file, verdict_path,
                lambda rn=round_num: run_agent_write_mode(
                    "solution_design_critic",
                    prompts_dir / f"critic_prompt_r{rn}.txt",
                    f"critic-r{rn}",
                    out_dir / f"_verdict_round{rn}.md",
                    logs_dir=logs_dir,
                ),
            )
            if not ok:
                final_verdict = "REVISE"
                print(f"[PHASE:3] Round {round_num}: critic failed → treating as REVISE", flush=True)
            else:
                final_verdict = parse_verdict(verdict_path)
                print(f"[PHASE:3] Round {round_num}: verdict = {final_verdict}", flush=True)

            ledger.update_critic_loop(round_num, final_verdict)

            if final_verdict == "APPROVED":
                ledger.set_critic_complete("APPROVED")
                break

            if round_num < MAX_CRITIC_ROUNDS:
                revised_output = out_dir / f"_design_revised_r{round_num}.md"
                revision_prompt = prompts_dir / f"revision_prompt_r{round_num}.txt"
                write_revision_prompt(revision_prompt, requirements_path, revised_output, verdict_path)

                rev_ok = run_step(
                    f"revision:r{round_num}", ledger, gate_design_file, revised_output,
                    lambda rn=round_num: run_agent_write_mode(
                        "solution_designer",
                        prompts_dir / f"revision_prompt_r{rn}.txt",
                        f"revision-r{rn}",
                        out_dir / f"_design_revised_r{rn}.md",
                        model=winning_model,
                        extra_dirs=extra_dirs,
                        logs_dir=logs_dir,
                    ),
                )
                if rev_ok:
                    shutil.copy2(revised_output, final_design_path)
                    print(f"[PHASE:3] Revised design → {final_design_path.name}", flush=True)
                else:
                    print("[PHASE:3] Revision failed; keeping current design", flush=True)
            else:
                ledger.set_critic_complete(final_verdict)
                print(f"[PHASE:3] Max rounds reached with verdict {final_verdict}", flush=True)

    # ── Phase 4: summary ──────────────────────────────────────────────────────
    print("\n[PHASE:4] Pipeline complete.", flush=True)
    print(f"[DONE] Output dir:       {out_dir}", flush=True)
    print(f"[DONE] Final design:     {final_design_path}", flush=True)
    print(f"[DONE] Selection report: {selection_report_path}", flush=True)
    print(f"[DONE] Winning model:    {winning_model}", flush=True)
    print(f"[DONE] Critic verdict:   {final_verdict} (after {final_round} round(s))", flush=True)
    if final_design_path.exists():
        n = final_design_path.read_text().count("<!-- ILLUSTRATION:")
        print(f"[DONE] Illustration placeholders: {n}", flush=True)

    return 0 if final_verdict == "APPROVED" else 1


def cmd_run(requirements_path: Path, designer_models: list[str]) -> int:
    if not requirements_path.exists():
        print(f"[ERROR] Requirements file not found: {requirements_path}", file=sys.stderr)
        return 1

    run_id = datetime.now().strftime("solution_design_%Y%m%d_%H%M%S")
    out_dir = requirements_path.parent.parent / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    ledger = Ledger.create(out_dir / "state.json", run_id, requirements_path, designer_models)
    return _execute_pipeline(out_dir, requirements_path, ledger, designer_models)


def cmd_resume(output_dir: Path, retry_failed: bool = False, force_step: str | None = None) -> int:
    state_path = output_dir / "state.json"
    if not state_path.exists():
        print(f"[ERROR] No state.json found in {output_dir}", file=sys.stderr)
        return 1

    ledger = Ledger.load(state_path)

    if retry_failed:
        n = ledger.reset_failed_steps()
        if n:
            print(f"[RESUME] Reset {n} failed step(s) to pending", flush=True)
        else:
            print("[RESUME] No failed steps to reset", flush=True)

    if force_step:
        if ledger.reset_step(force_step):
            print(f"[RESUME] Force-reset step '{force_step}' to pending", flush=True)
        else:
            print(f"[WARNING] Step '{force_step}' not found in ledger", flush=True)

    print(f"[RESUME] Resuming run: {ledger.run_id}", flush=True)
    _print_run_state(ledger, output_dir)

    requirements_path = ledger.requirements_path
    if not requirements_path.exists():
        print(f"[ERROR] Requirements file not found: {requirements_path}", file=sys.stderr)
        return 1

    designer_models = ledger.designer_models
    print(f"[RESUME] Designer models: {', '.join(designer_models)}", flush=True)
    return _execute_pipeline(output_dir, requirements_path, ledger, designer_models)


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solution_design_runner",
        description="Solution Design generation pipeline",
    )
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Generate solution design from requirements document")
    run_cmd.add_argument("requirements_path", type=Path, help="Path to the _requirements.md file")
    run_cmd.add_argument(
        "--models", nargs="+", default=DESIGNER_MODELS, metavar="MODEL",
        help="Models for parallel design generation (default: %(default)s)",
    )
    run_cmd.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    resume_cmd = sub.add_parser("resume", help="Resume a previously interrupted run")
    resume_cmd.add_argument("output_dir", type=Path, help="Path to the output directory (contains state.json)")
    resume_cmd.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    resume_cmd.add_argument(
        "--retry-failed", action="store_true",
        help="Reset all failed steps to pending so they are retried",
    )
    resume_cmd.add_argument(
        "--force-step", metavar="STEP_ID",
        help="Force-reset a specific step to pending even if it completed successfully",
    )

    status_cmd = sub.add_parser("status", help="Show the current state of a run")
    status_cmd.add_argument("output_dir", type=Path, help="Path to the output directory (contains state.json)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    log_level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
    logger.add(sys.stderr, level=log_level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    if args.command == "run":
        sys.exit(cmd_run(args.requirements_path.resolve(), args.models))
    elif args.command == "resume":
        sys.exit(cmd_resume(
            args.output_dir.resolve(),
            retry_failed=args.retry_failed,
            force_step=args.force_step,
        ))
    elif args.command == "status":
        sys.exit(cmd_status(args.output_dir.resolve()))


if __name__ == "__main__":
    main()

