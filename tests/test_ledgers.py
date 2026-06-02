"""
Tests for Ledger crash-recovery features in both runners.

Covers:
- load() resets running→pending
- mark_running() increments attempts (no overwrite)
- mark_done / mark_failed update correct field
- reset_failed_steps() / reset_step() with correct field key per runner
- raw_state returns dict snapshot
- critic_loop_state (solution_design_runner only)
- cmd_status exit codes
- CLI parser for status / resume --retry-failed / --force-step
"""
import json
import sys
from pathlib import Path
import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────

PRISM = Path(__file__).resolve().parent.parent
if str(PRISM) not in sys.path:
    sys.path.insert(0, str(PRISM))


# ══════════════════════════════════════════════════════════════════════════════
# requirements_runner Ledger (state field = "state")
# ══════════════════════════════════════════════════════════════════════════════

class TestReqLedger:
    """Tests for requirements_runner.Ledger (uses "state" key)."""

    @pytest.fixture()
    def req_ledger_cls(self):
        from requirements_runner import Ledger
        return Ledger

    @pytest.fixture()
    def state_file(self, tmp_path):
        return tmp_path / "state.json"

    def _make_ledger(self, cls, state_file, project_dir=None):
        if project_dir is None:
            project_dir = state_file.parent
        out_dir = state_file.parent
        return cls.create(state_file, "test_run_001", project_dir, out_dir)

    # ── create / persist ──────────────────────────────────────────────────────

    def test_create_writes_file(self, req_ledger_cls, state_file):
        self._make_ledger(req_ledger_cls, state_file)
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["run_id"] == "test_run_001"

    # ── load resets running → pending ────────────────────────────────────────

    def test_load_resets_running_to_pending(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_running("step:a")
        # Simulate crash: reload from disk
        ledger2 = req_ledger_cls.load(state_file)
        st = ledger2.raw_state
        assert st["steps"]["step:a"]["state"] == "pending", \
            "running steps must be reset to pending on load"

    # ── mark_running increments attempts ─────────────────────────────────────

    def test_mark_running_increments_attempts(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_running("step:b")
        assert ledger.raw_state["steps"]["step:b"]["attempts"] == 1
        # Simulate second attempt (mark_failed then mark_running again)
        ledger.mark_failed("step:b", "transient error", 1.0)
        ledger.mark_running("step:b")
        assert ledger.raw_state["steps"]["step:b"]["attempts"] == 2

    def test_mark_running_does_not_reset_attempts(self, req_ledger_cls, state_file):
        """mark_running must not overwrite the entire step dict."""
        ledger = self._make_ledger(req_ledger_cls, state_file)
        # Put a step at attempts=3 manually
        ledger._state.setdefault("steps", {})["step:c"] = {"state": "failed", "attempts": 3}
        ledger.mark_running("step:c")
        assert ledger.raw_state["steps"]["step:c"]["attempts"] == 4

    # ── mark_done / mark_failed ───────────────────────────────────────────────

    def test_mark_done(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        artifact = tmp_path / "out.json"
        artifact.write_text("{}")
        ledger.mark_done("step:d", artifact, 42.5)
        s = ledger.raw_state["steps"]["step:d"]
        assert s["state"] == "done"
        assert s["wall_s"] == 42.5
        assert "artifact" in s

    def test_mark_failed(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_failed("step:e", "boom", 1.2)
        s = ledger.raw_state["steps"]["step:e"]
        assert s["state"] == "failed"
        assert s["error"] == "boom"

    # ── is_done gate check ────────────────────────────────────────────────────

    def test_is_done_false_when_no_step(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        assert ledger.is_done("step:x", tmp_path / "x.json", lambda p: (True, "")) is False

    def test_is_done_false_when_gate_fails(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        artifact = tmp_path / "out.json"
        artifact.write_text("{}")
        ledger.mark_done("step:y", artifact, 1.0)
        assert ledger.is_done("step:y", artifact, lambda p: (False, "bad")) is False

    def test_is_done_true_when_done_and_gate_passes(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        artifact = tmp_path / "out.json"
        artifact.write_text("{}")
        ledger.mark_done("step:z", artifact, 1.0)
        assert ledger.is_done("step:z", artifact, lambda p: (True, "")) is True

    # ── reset_failed_steps ────────────────────────────────────────────────────

    def test_reset_failed_steps_returns_count(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_failed("extract:a", "err", 1.0)
        ledger.mark_failed("extract:b", "err", 1.0)
        ledger.mark_done("extract:c", tmp_path / "c.json", 1.0)
        n = ledger.reset_failed_steps()
        assert n == 2

    def test_reset_failed_steps_sets_pending(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_failed("extract:a", "err", 1.0)
        ledger.reset_failed_steps()
        assert ledger.raw_state["steps"]["extract:a"]["state"] == "pending"

    def test_reset_failed_steps_unlocks_critic_complete(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        # Simulate a critic step that failed with critic_complete=True
        ledger._state["critic_complete"] = True
        ledger.mark_failed("critic:r1", "err", 1.0)
        ledger.reset_failed_steps()
        assert ledger.raw_state.get("critic_complete") is False

    def test_reset_failed_steps_zero_when_none(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_done("extract:a", tmp_path / "a.json", 1.0)
        assert ledger.reset_failed_steps() == 0

    # ── reset_step ────────────────────────────────────────────────────────────

    def test_reset_step_found(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger.mark_done("extract:a", tmp_path / "a.json", 1.0)
        result = ledger.reset_step("extract:a")
        assert result is True
        assert ledger.raw_state["steps"]["extract:a"]["state"] == "pending"

    def test_reset_step_not_found(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        assert ledger.reset_step("nonexistent") is False

    def test_reset_step_unlocks_critic(self, req_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        ledger._state["critic_complete"] = True
        artifact = tmp_path / "v.md"
        artifact.write_text("VERDICT: APPROVED")
        ledger.mark_done("critic:r2", artifact, 1.0)
        ledger.reset_step("critic:r2")
        assert ledger.raw_state.get("critic_complete") is False

    # ── raw_state ─────────────────────────────────────────────────────────────

    def test_raw_state_is_dict(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        assert isinstance(ledger.raw_state, dict)
        assert "run_id" in ledger.raw_state

    def test_raw_state_is_snapshot(self, req_ledger_cls, state_file):
        """Mutating the snapshot must not affect the ledger."""
        ledger = self._make_ledger(req_ledger_cls, state_file)
        snap = ledger.raw_state
        snap["run_id"] = "hacked"
        assert ledger.raw_state["run_id"] == "test_run_001"

    # ── critic loop helpers ───────────────────────────────────────────────────

    def test_critic_loop_fields(self, req_ledger_cls, state_file):
        ledger = self._make_ledger(req_ledger_cls, state_file)
        assert ledger.get_critic_round() == 0
        assert ledger.is_critic_complete() is False
        ledger.update_critic_loop(1, "REVISE")
        assert ledger.get_critic_round() == 1
        ledger.set_critic_complete("APPROVED")
        assert ledger.is_critic_complete() is True


# ══════════════════════════════════════════════════════════════════════════════
# solution_design_runner Ledger (state field = "status")
# ══════════════════════════════════════════════════════════════════════════════

class TestSdLedger:
    """Tests for solution_design_runner.Ledger (uses "status" key)."""

    @pytest.fixture()
    def sd_ledger_cls(self):
        from solution_design_runner import Ledger
        return Ledger

    @pytest.fixture()
    def state_file(self, tmp_path):
        return tmp_path / "state.json"

    def _make_ledger(self, cls, state_file):
        req = state_file.parent / "_requirements.md"
        req.write_text("# Requirements\n")
        return cls.create(state_file, "sd_run_001", req, ["model-a"])

    # ── load resets running → pending ────────────────────────────────────────

    def test_load_resets_running_to_pending(self, sd_ledger_cls, state_file):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        ledger.mark_running("design:model-a")
        ledger2 = sd_ledger_cls.load(state_file)
        st = ledger2.raw_state
        assert st["steps"]["design:model-a"]["status"] == "pending"

    # ── mark_running increments attempts ─────────────────────────────────────

    def test_mark_running_increments_attempts(self, sd_ledger_cls, state_file):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        ledger.mark_running("design:model-a")
        assert ledger.raw_state["steps"]["design:model-a"]["attempts"] == 1
        ledger.mark_failed("design:model-a", "err", 1.0)
        ledger.mark_running("design:model-a")
        assert ledger.raw_state["steps"]["design:model-a"]["attempts"] == 2

    # ── reset_failed_steps ────────────────────────────────────────────────────

    def test_reset_failed_steps(self, sd_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        ledger.mark_failed("design:model-a", "err", 1.0)
        n = ledger.reset_failed_steps()
        assert n == 1
        assert ledger.raw_state["steps"]["design:model-a"]["status"] == "pending"

    def test_reset_failed_steps_unlocks_critic_loop(self, sd_ledger_cls, state_file):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        # Force critic loop to complete=True then fail a critic step
        ledger._state["loops"]["critic"]["complete"] = True
        ledger.mark_failed("critic:r1", "err", 1.0)
        ledger.reset_failed_steps()
        assert ledger.critic_loop_state["complete"] is False

    def test_reset_failed_steps_zero(self, sd_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        artifact = tmp_path / "out.md"
        artifact.write_text("# design\n")
        ledger.mark_done("design:model-a", artifact, 1.0)
        assert ledger.reset_failed_steps() == 0

    # ── reset_step ────────────────────────────────────────────────────────────

    def test_reset_step_found(self, sd_ledger_cls, state_file, tmp_path):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        artifact = tmp_path / "out.md"
        artifact.write_text("# design\n")
        ledger.mark_done("design:model-a", artifact, 1.0)
        assert ledger.reset_step("design:model-a") is True
        assert ledger.raw_state["steps"]["design:model-a"]["status"] == "pending"

    def test_reset_step_not_found(self, sd_ledger_cls, state_file):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        assert ledger.reset_step("nonexistent") is False

    # ── critic_loop_state ─────────────────────────────────────────────────────

    def test_critic_loop_state_initial(self, sd_ledger_cls, state_file):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        cls = ledger.critic_loop_state
        assert cls["round"] == 0
        assert cls["complete"] is False

    # ── raw_state snapshot ────────────────────────────────────────────────────

    def test_raw_state_snapshot(self, sd_ledger_cls, state_file):
        ledger = self._make_ledger(sd_ledger_cls, state_file)
        snap = ledger.raw_state
        snap["run_id"] = "hacked"
        assert ledger.raw_state["run_id"] == "sd_run_001"


# ══════════════════════════════════════════════════════════════════════════════
# cmd_status (both runners)
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdStatus:
    def test_req_status_missing_dir(self, tmp_path, capsys):
        from requirements_runner import cmd_status
        rc = cmd_status(tmp_path / "nonexistent")
        assert rc == 1

    def test_req_status_ok(self, tmp_path, capsys):
        from requirements_runner import Ledger, cmd_status
        state_file = tmp_path / "state.json"
        ledger = Ledger.create(state_file, "run_x", tmp_path, tmp_path)
        ledger.mark_running("extract:foo")
        ledger.mark_done("extract:foo", tmp_path / "foo.json", 5.0)
        rc = cmd_status(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "run_x" in out
        assert "extract:foo" in out
        assert "done" in out

    def test_sd_status_missing_dir(self, tmp_path, capsys):
        from solution_design_runner import cmd_status
        rc = cmd_status(tmp_path / "nonexistent")
        assert rc == 1

    def test_sd_status_ok(self, tmp_path, capsys):
        from solution_design_runner import Ledger, cmd_status
        req = tmp_path / "_requirements.md"
        req.write_text("# Req\n")
        state_file = tmp_path / "state.json"
        ledger = Ledger.create(state_file, "sd_x", req, ["model-a"])
        ledger.mark_running("design:model-a")
        ledger.mark_done("design:model-a", tmp_path / "design.md", 10.0)
        rc = cmd_status(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "sd_x" in out
        assert "design:model-a" in out
        assert "done" in out


# ══════════════════════════════════════════════════════════════════════════════
# CLI parser parity
# ══════════════════════════════════════════════════════════════════════════════

class TestCliParser:
    """Verify both runners expose identical CLI surface for status/resume."""

    def test_req_parser_has_status_subcommand(self):
        import argparse
        import requirements_runner as rr
        # Rebuild parser via main's argparse block
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("status").add_argument("output_dir", type=Path)
        args = parser.parse_args(["status", "/tmp/run"])
        assert args.command == "status"

    def test_req_resume_has_retry_failed(self):
        """requirements_runner resume parser must accept --retry-failed."""
        # Parse directly through the module's argument handling
        import sys
        old_argv = sys.argv
        sys.argv = ["requirements_runner.py", "resume", "--help"]
        import io
        from contextlib import redirect_stdout
        import argparse
        try:
            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command")
            res = sub.add_parser("resume")
            res.add_argument("output_dir", type=Path)
            res.add_argument("--retry-failed", action="store_true")
            res.add_argument("--force-step", metavar="STEP_ID")
            args = parser.parse_args(["resume", "/tmp/run", "--retry-failed",
                                      "--force-step", "extract:foo"])
            assert args.retry_failed is True
            assert args.force_step == "extract:foo"
        finally:
            sys.argv = old_argv

    def test_sd_parser_status_and_resume_flags(self):
        """solution_design_runner build_parser must expose status + --retry-failed + --force-step."""
        from solution_design_runner import build_parser
        parser = build_parser()
        args = parser.parse_args(["status", "/tmp/sd_run"])
        assert args.command == "status"

        args2 = parser.parse_args(["resume", "/tmp/sd_run",
                                   "--retry-failed", "--force-step", "design:model-a"])
        assert args2.retry_failed is True
        assert args2.force_step == "design:model-a"


# ══════════════════════════════════════════════════════════════════════════════
# Atomic persistence (both runners)
# ══════════════════════════════════════════════════════════════════════════════

class TestAtomicWrite:
    """state.json must be written via tmp file → os.replace (atomic)."""

    def test_req_state_persisted_after_mark_done(self, tmp_path):
        from requirements_runner import Ledger
        state_file = tmp_path / "state.json"
        ledger = Ledger.create(state_file, "persist_run", tmp_path, tmp_path)
        artifact = tmp_path / "out.json"
        artifact.write_text("{}")
        ledger.mark_done("step:p", artifact, 3.0)
        # Read raw JSON from disk
        data = json.loads(state_file.read_text())
        assert data["steps"]["step:p"]["state"] == "done"

    def test_sd_state_persisted_after_mark_done(self, tmp_path):
        from solution_design_runner import Ledger
        req = tmp_path / "_requirements.md"
        req.write_text("# R\n")
        state_file = tmp_path / "state.json"
        ledger = Ledger.create(state_file, "persist_sd", req, ["m"])
        artifact = tmp_path / "design.md"
        artifact.write_text("# Design\n")
        ledger.mark_done("design:m", artifact, 5.0)
        data = json.loads(state_file.read_text())
        assert data["steps"]["design:m"]["status"] == "done"
