"""
Integration tests for batch processing infrastructure.

Tests BatchRunner with real tools (foldseek, DALI, DOMASS) and
validates step-first orchestration, template caching, and
cross-mode state compatibility.
"""

import json
import shutil
import pytest
from pathlib import Path

from dpam.core.models import PipelineStep, PipelineState
from dpam.pipeline.batch_runner import BatchRunner, BatchState


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="session")
def ecod_data():
    """Find ECOD reference data or skip."""
    import os
    env_dir = os.getenv("DPAM_TEST_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p

    for loc in [
        Path('/home/rschaeff_1/data/dpam_reference/ecod_data'),
        Path('/home/rschaeff/data/dpam_reference/ecod_data'),
    ]:
        if loc.exists():
            return loc

    pytest.skip("ECOD data directory not found")


@pytest.fixture(scope="session")
def validation_dir():
    """Find validation data with pre-computed intermediate files."""
    vdir = Path('/home/rschaeff/dev/dpam_c2/validation_swissprot')
    if not vdir.exists():
        pytest.skip("validation_swissprot directory not found")
    return vdir


@pytest.fixture(scope="session")
def validation_proteins(validation_dir):
    """Select small validation proteins for testing."""
    # Use proteins with smallest DALI candidate counts for speed
    candidates = ['AF-Q97ZL0-F1', 'AF-Q4L889-F1', 'AF-P06596-F1']
    available = [p for p in candidates if (validation_dir / f'{p}.pdb').exists()]
    if len(available) < 2:
        pytest.skip("Need at least 2 validation proteins")
    return available[:2]  # Use 2 for fast tests


def _setup_protein_dir(validation_dir, proteins, dest_dir):
    """Copy validation protein files to test directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for p in proteins:
        for f in validation_dir.glob(f'{p}*'):
            if not f.name.startswith('.'):  # Skip state files
                shutil.copy2(f, dest_dir / f.name)


# ============================================================
# BatchRunner construction
# ============================================================

@pytest.mark.integration
class TestBatchRunnerInit:
    """Test BatchRunner initialization with real reference data."""

    def test_loads_reference_data(self, tmp_path, ecod_data):
        """BatchRunner loads ECOD reference data on init."""
        runner = BatchRunner(
            proteins=["AF-TEST-F1"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )
        assert runner.pipeline is not None
        assert runner.state is not None

    def test_resume_seeds_from_protein_state(self, tmp_path, ecod_data):
        """resume=True seeds batch state from per-protein state files."""
        # Create a per-protein state with a completed step
        pstate = PipelineState(prefix="pA", working_dir=tmp_path)
        pstate.mark_complete(PipelineStep.PREPARE)
        pstate.save(tmp_path / ".pA.dpam_state.json")

        runner = BatchRunner(
            proteins=["pA"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=True,
            skip_addss=True,
        )

        pending = runner.state.get_pending(PipelineStep.PREPARE, ["pA"])
        assert "pA" not in pending, "Seeded step should not be pending"

    def test_resume_false_ignores_protein_state(self, tmp_path, ecod_data):
        """resume=False does not seed from per-protein state."""
        pstate = PipelineState(prefix="pA", working_dir=tmp_path)
        pstate.mark_complete(PipelineStep.PREPARE)
        pstate.save(tmp_path / ".pA.dpam_state.json")

        runner = BatchRunner(
            proteins=["pA"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        pending = runner.state.get_pending(PipelineStep.PREPARE, ["pA"])
        assert "pA" in pending, "Without resume, step should be pending"


# ============================================================
# Batch foldseek
# ============================================================

@pytest.mark.integration
@pytest.mark.requires_foldseek
@pytest.mark.slow
class TestBatchFoldseek:
    """Test BatchRunner foldseek batch optimization."""

    def test_batch_foldseek_produces_per_protein_output(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        foldseek_available,
    ):
        """Batch foldseek creates per-protein .foldseek files."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=False,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.FOLDSEEK])

        for p in validation_proteins:
            out = tmp_path / f"{p}.foldseek"
            assert out.exists(), f"Missing foldseek output for {p}"
            assert out.stat().st_size > 0, f"Empty foldseek output for {p}"

    def test_batch_foldseek_marks_state_complete(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        foldseek_available,
    ):
        """Batch foldseek marks proteins complete in batch state."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=False,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.FOLDSEEK])

        for p in validation_proteins:
            pending = runner.state.get_pending(
                PipelineStep.FOLDSEEK, [p]
            )
            assert p not in pending, f"{p} should be complete"

    def test_batch_foldseek_updates_per_protein_state(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        foldseek_available,
    ):
        """Batch foldseek creates per-protein .dpam_state.json files."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=False,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.FOLDSEEK])

        for p in validation_proteins:
            state_file = tmp_path / f".{p}.dpam_state.json"
            assert state_file.exists(), f"Per-protein state missing for {p}"
            pstate = PipelineState.load(state_file)
            assert PipelineStep.FOLDSEEK in pstate.completed_steps

    def test_batch_foldseek_matches_single_protein(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        foldseek_available,
    ):
        """Batch foldseek results match validation data line counts."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=False,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.FOLDSEEK])

        for p in validation_proteins:
            batch_file = tmp_path / f"{p}.foldseek"
            orig_file = validation_dir / f"{p}.foldseek"
            if not orig_file.exists():
                continue

            batch_lines = len(batch_file.read_text().strip().splitlines())
            orig_lines = len(orig_file.read_text().strip().splitlines())
            assert batch_lines == orig_lines, (
                f"{p}: batch={batch_lines} vs orig={orig_lines}"
            )


# ============================================================
# Batch DALI with template caching
# ============================================================

@pytest.mark.integration
@pytest.mark.requires_dali
@pytest.mark.slow
class TestBatchDali:
    """Test BatchRunner DALI template caching optimization."""

    def test_batch_dali_creates_output(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        dali_available,
    ):
        """Batch DALI with template cache creates output files."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=True,  # Skip already-complete steps
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.ITERATIVE_DALI])

        for p in validation_proteins:
            hits_input = tmp_path / f"{p}_hits4Dali"
            if not hits_input.exists():
                continue  # No candidates for this protein

            out = tmp_path / f"{p}_iterativdDali_hits"
            assert out.exists(), f"Missing DALI output for {p}"

    def test_batch_dali_cleans_up_cache(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        dali_available,
    ):
        """Template cache directory is removed after batch DALI."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=True,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.ITERATIVE_DALI])

        cache_dir = tmp_path / "_dali_template_cache"
        assert not cache_dir.exists(), "Template cache should be cleaned up"

    def test_batch_dali_marks_state_complete(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        dali_available,
    ):
        """Batch DALI marks proteins as complete."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=2,
            resume=True,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.ITERATIVE_DALI])

        for p in validation_proteins:
            hits_input = tmp_path / f"{p}_hits4Dali"
            if not hits_input.exists():
                continue
            pending = runner.state.get_pending(
                PipelineStep.ITERATIVE_DALI, [p]
            )
            assert p not in pending, f"{p} should be complete"


# ============================================================
# Batch DOMASS
# ============================================================

@pytest.mark.integration
@pytest.mark.slow
class TestBatchDomass:
    """Test BatchRunner DOMASS shared-model optimization."""

    def test_batch_domass_creates_output(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        tensorflow_available, domass_model_available,
    ):
        """Batch DOMASS with shared TF model creates score files."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=True,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.RUN_DOMASS])

        for p in validation_proteins:
            features_file = tmp_path / f"{p}_step15.domass_features"
            if not features_file.exists():
                continue  # No features = no scores expected

            out = tmp_path / f"{p}_step16.domass_scores"
            assert out.exists(), f"Missing DOMASS output for {p}"

    def test_batch_domass_marks_state_complete(
        self, tmp_path, ecod_data, validation_dir, validation_proteins,
        tensorflow_available, domass_model_available,
    ):
        """Batch DOMASS marks proteins as complete."""
        _setup_protein_dir(validation_dir, validation_proteins, tmp_path)

        runner = BatchRunner(
            proteins=validation_proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=True,
            skip_addss=True,
        )
        runner.run(steps=[PipelineStep.RUN_DOMASS])

        for p in validation_proteins:
            features_file = tmp_path / f"{p}_step15.domass_features"
            if not features_file.exists():
                continue
            pending = runner.state.get_pending(
                PipelineStep.RUN_DOMASS, [p]
            )
            assert p not in pending


# ============================================================
# Resume behavior
# ============================================================

@pytest.mark.integration
class TestBatchResume:
    """Test BatchRunner resume and skip-when-complete behavior."""

    def test_resume_skips_completed_steps(self, tmp_path, ecod_data):
        """BatchRunner skips steps already marked complete."""
        proteins = ["pA", "pB"]

        runner = BatchRunner(
            proteins=proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        # Manually mark a step complete
        runner.state.mark_complete(PipelineStep.PREPARE, "pA")
        runner.state.mark_complete(PipelineStep.PREPARE, "pB")

        pending = runner.state.get_pending(PipelineStep.PREPARE, proteins)
        assert pending == [], "All should be complete"

    def test_resume_runs_only_pending_proteins(self, tmp_path, ecod_data):
        """Only pending proteins are processed on resume."""
        proteins = ["pA", "pB", "pC"]

        runner = BatchRunner(
            proteins=proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        runner.state.mark_complete(PipelineStep.PREPARE, "pA")

        pending = runner.state.get_pending(PipelineStep.PREPARE, proteins)
        assert pending == ["pB", "pC"]

    def test_critical_failure_skips_downstream(self, tmp_path, ecod_data):
        """Critical step failure skips downstream steps for that protein."""
        proteins = ["pA", "pB"]

        runner = BatchRunner(
            proteins=proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        # FOLDSEEK is critical
        runner.state.mark_failed(PipelineStep.FOLDSEEK, "pA", "test error")

        # ITERATIVE_DALI should skip pA
        pending = runner.state.get_pending(
            PipelineStep.ITERATIVE_DALI, proteins
        )
        assert "pA" not in pending
        assert "pB" in pending


# ============================================================
# Cross-mode state compatibility
# ============================================================

@pytest.mark.integration
class TestCrossModeCompat:
    """Test that batch and per-protein modes share state correctly."""

    def test_batch_state_creates_per_protein_files(
        self, tmp_path, ecod_data,
    ):
        """Marking complete in batch also creates per-protein state."""
        runner = BatchRunner(
            proteins=["pA"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        runner.state.mark_complete(PipelineStep.PREPARE, "pA")

        state_file = tmp_path / ".pA.dpam_state.json"
        assert state_file.exists()
        pstate = PipelineState.load(state_file)
        assert PipelineStep.PREPARE in pstate.completed_steps

    def test_per_protein_state_seeds_batch(self, tmp_path, ecod_data):
        """Existing per-protein state is picked up by new batch run."""
        # Simulate a dpam run that completed PREPARE
        pstate = PipelineState(prefix="pA", working_dir=tmp_path)
        pstate.mark_complete(PipelineStep.PREPARE)
        pstate.mark_complete(PipelineStep.HHSEARCH)
        pstate.save(tmp_path / ".pA.dpam_state.json")

        # New batch run with resume picks up the state
        runner = BatchRunner(
            proteins=["pA"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=True,
            skip_addss=True,
        )

        pending_prep = runner.state.get_pending(
            PipelineStep.PREPARE, ["pA"]
        )
        pending_hh = runner.state.get_pending(
            PipelineStep.HHSEARCH, ["pA"]
        )
        assert "pA" not in pending_prep
        assert "pA" not in pending_hh

    def test_batch_state_file_format(self, tmp_path, ecod_data):
        """Batch state file is valid JSON with expected structure."""
        runner = BatchRunner(
            proteins=["pA", "pB"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        runner.state.mark_complete(PipelineStep.PREPARE, "pA")
        runner.state.mark_failed(PipelineStep.PREPARE, "pB", "test error")

        state_file = tmp_path / "_batch_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)

        assert "PREPARE" in data
        assert data["PREPARE"]["pA"] == "complete"
        assert data["PREPARE"]["pB"].startswith("failed:")

    def test_dpam_run_resume_sees_batch_state(self, tmp_path, ecod_data):
        """Per-protein dpam run --resume sees state set by batch mode."""
        runner = BatchRunner(
            proteins=["pA"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        runner.state.mark_complete(PipelineStep.PREPARE, "pA")
        runner.state.mark_complete(PipelineStep.HHSEARCH, "pA")

        # Simulate what dpam run --resume does: load per-protein state
        state_file = tmp_path / ".pA.dpam_state.json"
        pstate = PipelineState.load(state_file)

        assert pstate.is_complete(PipelineStep.PREPARE)
        assert pstate.is_complete(PipelineStep.HHSEARCH)


# ============================================================
# Default (per-protein) step execution via BatchRunner
# ============================================================

@pytest.mark.integration
class TestBatchDefaultSteps:
    """Test non-optimized steps run per-protein correctly."""

    def test_default_step_marks_state(self, tmp_path, ecod_data):
        """Default per-protein step updates both batch and protein state."""
        proteins = ["pA"]

        runner = BatchRunner(
            proteins=proteins,
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        # PREPARE is a non-optimized step; it should fail (no PDB)
        # but the failure should be recorded in state
        runner.run(steps=[PipelineStep.PREPARE])

        # Check that state was updated (either complete or failed)
        with open(tmp_path / "_batch_state.json") as f:
            data = json.load(f)

        assert "PREPARE" in data
        assert "pA" in data["PREPARE"]

    def test_summary_after_batch_run(self, tmp_path, ecod_data):
        """get_summary returns correct counts after batch run."""
        runner = BatchRunner(
            proteins=["pA", "pB"],
            working_dir=tmp_path,
            data_dir=ecod_data,
            cpus=1,
            resume=False,
            skip_addss=True,
        )

        runner.state.mark_complete(PipelineStep.PREPARE, "pA")
        runner.state.mark_failed(PipelineStep.PREPARE, "pB", "no PDB")

        summary = runner.state.get_summary()
        assert summary["PREPARE"]["complete"] == 1
        assert summary["PREPARE"]["failed"] == 1
