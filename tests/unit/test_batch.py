"""
Unit tests for batch processing infrastructure.

Tests BatchState, foldseek result splitting, DALI args handling,
and CLI commands that don't require external tools.
"""

import json
import pytest
from pathlib import Path

from dpam.core.models import PipelineStep, PipelineState
from dpam.pipeline.batch_runner import BatchState, BatchRunner


# ============================================================
# BatchState
# ============================================================

@pytest.mark.unit
class TestBatchState:
    """Unit tests for BatchState."""

    def test_create_empty_state(self, tmp_path):
        """New state file created on first access."""
        state = BatchState(tmp_path)
        assert state._state == {}

    def test_mark_complete(self, tmp_path):
        """mark_complete persists to disk."""
        state = BatchState(tmp_path)
        state.mark_complete(PipelineStep.FOLDSEEK, "protein_A")

        # Verify in-memory
        assert state._state["FOLDSEEK"]["protein_A"] == "complete"

        # Verify on disk
        with open(tmp_path / "_batch_state.json") as f:
            disk = json.load(f)
        assert disk["FOLDSEEK"]["protein_A"] == "complete"

    def test_mark_failed(self, tmp_path):
        """mark_failed records error message."""
        state = BatchState(tmp_path)
        state.mark_failed(PipelineStep.HHSEARCH, "protein_B", "timeout")

        assert state._state["HHSEARCH"]["protein_B"] == "failed: timeout"

    def test_get_pending_filters_complete(self, tmp_path):
        """Completed proteins excluded from pending list."""
        proteins = ["pA", "pB", "pC"]
        state = BatchState(tmp_path)
        state.mark_complete(PipelineStep.FOLDSEEK, "pA")
        state.mark_complete(PipelineStep.FOLDSEEK, "pC")

        pending = state.get_pending(PipelineStep.FOLDSEEK, proteins)
        assert pending == ["pB"]

    def test_get_pending_all_complete(self, tmp_path):
        """Returns empty list when all proteins complete."""
        proteins = ["pA", "pB"]
        state = BatchState(tmp_path)
        state.mark_complete(PipelineStep.FOLDSEEK, "pA")
        state.mark_complete(PipelineStep.FOLDSEEK, "pB")

        pending = state.get_pending(PipelineStep.FOLDSEEK, proteins)
        assert pending == []

    def test_get_pending_none_complete(self, tmp_path):
        """Returns full list when nothing done."""
        proteins = ["pA", "pB"]
        state = BatchState(tmp_path)

        pending = state.get_pending(PipelineStep.FOLDSEEK, proteins)
        assert pending == ["pA", "pB"]

    def test_critical_failure_skips_downstream(self, tmp_path):
        """Protein with critical step failure is excluded from later steps."""
        state = BatchState(tmp_path)
        state.mark_failed(PipelineStep.FOLDSEEK, "pA", "db not found")

        # FOLDSEEK is critical; steps after it should skip pA
        pending = state.get_pending(PipelineStep.ITERATIVE_DALI, ["pA", "pB"])
        assert "pA" not in pending
        assert "pB" in pending

    def test_non_critical_failure_does_not_skip(self, tmp_path):
        """Non-critical failure does not skip downstream steps."""
        state = BatchState(tmp_path)
        # SSE (step 11) is NOT critical
        state.mark_failed(PipelineStep.SSE, "pA", "dssp failed")

        pending = state.get_pending(PipelineStep.DISORDER, ["pA"])
        assert "pA" in pending

    def test_get_summary(self, tmp_path):
        """Summary counts complete and failed."""
        state = BatchState(tmp_path)
        state.mark_complete(PipelineStep.FOLDSEEK, "pA")
        state.mark_complete(PipelineStep.FOLDSEEK, "pB")
        state.mark_failed(PipelineStep.FOLDSEEK, "pC", "error")

        summary = state.get_summary()
        assert summary["FOLDSEEK"]["complete"] == 2
        assert summary["FOLDSEEK"]["failed"] == 1

    def test_reload_from_disk(self, tmp_path):
        """State survives process restart."""
        state1 = BatchState(tmp_path)
        state1.mark_complete(PipelineStep.PREPARE, "pA")

        # Simulate restart
        state2 = BatchState(tmp_path)
        pending = state2.get_pending(PipelineStep.PREPARE, ["pA"])
        assert pending == []

    def test_atomic_write(self, tmp_path):
        """State file written atomically (no .tmp left behind)."""
        state = BatchState(tmp_path)
        state.mark_complete(PipelineStep.PREPARE, "pA")

        assert (tmp_path / "_batch_state.json").exists()
        assert not (tmp_path / "_batch_state.tmp").exists()

    def test_seed_from_protein_states(self, tmp_path):
        """Seed batch state from existing per-protein state files."""
        # Create a per-protein state file with a completed step
        pstate = PipelineState(prefix="pA", working_dir=tmp_path)
        pstate.mark_complete(PipelineStep.PREPARE)
        pstate.mark_complete(PipelineStep.HHSEARCH)
        pstate.save(tmp_path / ".pA.dpam_state.json")

        # Create batch state with seeding
        state = BatchState(tmp_path, proteins=["pA", "pB"])

        # pA should have PREPARE and HHSEARCH seeded
        pending_prep = state.get_pending(PipelineStep.PREPARE, ["pA", "pB"])
        assert "pA" not in pending_prep
        assert "pB" in pending_prep

        pending_hh = state.get_pending(PipelineStep.HHSEARCH, ["pA", "pB"])
        assert "pA" not in pending_hh

    def test_seed_does_not_overwrite_existing(self, tmp_path):
        """Seeding only happens when batch state file doesn't exist."""
        # Create batch state file first
        state1 = BatchState(tmp_path)
        state1.mark_complete(PipelineStep.PREPARE, "pX")

        # Create a per-protein state that has more info
        pstate = PipelineState(prefix="pA", working_dir=tmp_path)
        pstate.mark_complete(PipelineStep.PREPARE)
        pstate.save(tmp_path / ".pA.dpam_state.json")

        # Re-create BatchState - should NOT seed since file exists
        state2 = BatchState(tmp_path, proteins=["pA"])

        # pA should NOT be seeded (batch state already exists)
        pending = state2.get_pending(PipelineStep.PREPARE, ["pA"])
        assert "pA" in pending  # Not seeded because state file existed

    def test_updates_per_protein_state(self, tmp_path):
        """Batch state updates create per-protein state files."""
        state = BatchState(tmp_path)
        state.mark_complete(PipelineStep.FOLDSEEK, "pA")

        # Per-protein state file should be created
        pstate_file = tmp_path / ".pA.dpam_state.json"
        assert pstate_file.exists()

        pstate = PipelineState.load(pstate_file)
        assert PipelineStep.FOLDSEEK in pstate.completed_steps


# ============================================================
# Foldseek result splitting
# ============================================================

@pytest.mark.unit
class TestSplitFoldseekResults:
    """Unit tests for _split_foldseek_results."""

    def test_split_basic(self, tmp_path):
        """Split combined output by query name."""
        from dpam.steps.step03_foldseek import _split_foldseek_results

        combined = tmp_path / "combined.tsv"
        combined.write_text(
            "protA\ttarget1\t0.95\n"
            "protA\ttarget2\t0.80\n"
            "protB\ttarget3\t0.70\n"
            "protB\ttarget4\t0.65\n"
            "protB\ttarget5\t0.50\n"
        )

        counts = _split_foldseek_results(
            combined, tmp_path, ["protA", "protB"]
        )

        assert counts["protA"] == 2
        assert counts["protB"] == 3

        # Verify file contents
        with open(tmp_path / "protA.foldseek") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert lines[0].startswith("protA\ttarget1")

    def test_split_empty_combined(self, tmp_path):
        """Empty combined file produces empty per-protein files."""
        from dpam.steps.step03_foldseek import _split_foldseek_results

        combined = tmp_path / "combined.tsv"
        combined.write_text("")

        counts = _split_foldseek_results(
            combined, tmp_path, ["protA"]
        )

        assert counts["protA"] == 0
        assert (tmp_path / "protA.foldseek").exists()

    def test_split_unknown_query_ignored(self, tmp_path):
        """Lines with unknown query names are ignored."""
        from dpam.steps.step03_foldseek import _split_foldseek_results

        combined = tmp_path / "combined.tsv"
        combined.write_text(
            "protA\ttarget1\t0.95\n"
            "unknown\ttarget2\t0.80\n"
        )

        counts = _split_foldseek_results(
            combined, tmp_path, ["protA"]
        )

        assert counts["protA"] == 1

    def test_split_many_proteins(self, tmp_path):
        """Split works with many proteins."""
        from dpam.steps.step03_foldseek import _split_foldseek_results

        proteins = [f"prot{i}" for i in range(10)]
        lines = []
        for p in proteins:
            for j in range(5):
                lines.append(f"{p}\ttarget_{j}\t0.{j}\n")

        combined = tmp_path / "combined.tsv"
        combined.write_text("".join(lines))

        counts = _split_foldseek_results(combined, tmp_path, proteins)

        for p in proteins:
            assert counts[p] == 5
            assert (tmp_path / f"{p}.foldseek").exists()


# ============================================================
# DALI args tuple handling
# ============================================================

@pytest.mark.unit
class TestDaliArgsTuple:
    """Test that run_dali handles both 4-tuple and 5-tuple args."""

    def test_args_tuple_unpacking_4(self):
        """4-tuple args set template_cache to None."""
        from dpam.steps.step07_iterative_dali import run_dali

        # We can't run the full function without DALI, but we can test
        # the unpacking logic by checking the function signature accepts both.
        # run_dali will fail early (missing PDB), but the unpacking should work.
        args = ("prefix", "domain", Path("/nonexistent"), Path("/nonexistent"))
        result = run_dali(args)
        assert result is False  # Fails on missing PDB

    def test_args_tuple_unpacking_5(self):
        """5-tuple args correctly extract template_cache."""
        from dpam.steps.step07_iterative_dali import run_dali

        args = ("prefix", "domain", Path("/nonexistent"), Path("/nonexistent"),
                Path("/tmp/cache"))
        result = run_dali(args)
        assert result is False  # Fails on missing PDB


# ============================================================
# CLI commands
# ============================================================

@pytest.mark.unit
class TestBatchCLI:
    """Test batch CLI command parsing and dry-run."""

    def test_batch_status_empty(self, tmp_path):
        """batch-status with no state file returns error."""
        from dpam.cli.main import show_batch_status

        class Args:
            working_dir = tmp_path

        ret = show_batch_status(Args())
        assert ret == 1

    def test_batch_status_with_state(self, tmp_path):
        """batch-status reads and displays state."""
        from dpam.cli.main import show_batch_status

        state = {
            "PREPARE": {"pA": "complete", "pB": "complete"},
            "FOLDSEEK": {"pA": "complete", "pB": "failed: timeout"},
        }
        with open(tmp_path / "_batch_state.json", "w") as f:
            json.dump(state, f)

        class Args:
            working_dir = tmp_path

        ret = show_batch_status(Args())
        assert ret == 0

    def test_slurm_batch_dry_run(self, tmp_path):
        """slurm-batch --dry-run generates script without submitting."""
        from dpam.pipeline.slurm import generate_batch_slurm_script

        prefixes = ["pA", "pB", "pC"]
        script = generate_batch_slurm_script(
            prefixes=prefixes,
            working_dir=tmp_path,
            data_dir=Path("/data/ecod"),
            cpus=8,
            mem="32G",
            time_limit="12:00:00",
            partition="compute",
            skip_addss=True
        )

        assert "#!/bin/bash" in script
        assert "#SBATCH --cpus-per-task=8" in script
        assert "#SBATCH --mem=32G" in script
        assert "#SBATCH --partition=compute" in script
        assert "dpam batch-run" in script
        assert "--skip-addss" in script
        assert "unset OMP_PROC_BIND" in script

        # Verify prefix file was written
        prefix_file = tmp_path / "prefixes_batch.txt"
        assert prefix_file.exists()
        with open(prefix_file) as f:
            written = [l.strip() for l in f]
        assert written == prefixes

    def test_slurm_batch_no_partition(self, tmp_path):
        """slurm-batch without partition omits partition line."""
        from dpam.pipeline.slurm import generate_batch_slurm_script

        script = generate_batch_slurm_script(
            prefixes=["pA"],
            working_dir=tmp_path,
            data_dir=Path("/data"),
            partition=None
        )

        assert "#SBATCH --partition" not in script

    def test_slurm_batch_no_skip_addss(self, tmp_path):
        """slurm-batch without skip_addss omits flag."""
        from dpam.pipeline.slurm import generate_batch_slurm_script

        script = generate_batch_slurm_script(
            prefixes=["pA"],
            working_dir=tmp_path,
            data_dir=Path("/data"),
            skip_addss=False
        )

        assert "--skip-addss" not in script


# ============================================================
# BatchRunner construction
# ============================================================

@pytest.mark.unit
class TestBatchRunnerConstruction:
    """Test BatchRunner initialization (no external tools needed)."""

    def test_creates_working_dir(self, tmp_path):
        """BatchRunner creates working directory if missing."""
        work = tmp_path / "new_dir"
        assert not work.exists()

        # This will fail loading reference data, but working_dir should be created
        try:
            BatchRunner(
                proteins=["pA"],
                working_dir=work,
                data_dir=tmp_path,
                cpus=1,
                resume=False
            )
        except Exception:
            pass  # Expected - no reference data

        assert work.exists()

    def test_resume_false_does_not_seed(self, tmp_path):
        """resume=False skips seeding from per-protein state."""
        # Create per-protein state
        pstate = PipelineState(prefix="pA", working_dir=tmp_path)
        pstate.mark_complete(PipelineStep.PREPARE)
        pstate.save(tmp_path / ".pA.dpam_state.json")

        state = BatchState(tmp_path, proteins=None)  # resume=False → None
        pending = state.get_pending(PipelineStep.PREPARE, ["pA"])
        assert "pA" in pending  # Not seeded
