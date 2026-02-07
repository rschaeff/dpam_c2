"""
Step-first batch processing for DPAM pipeline.

Processes proteins step-by-step: run step 1 for all proteins, then step 2 for
all proteins, etc. Expensive resources (TF model, foldseek index) load once
per step rather than once per protein.

Currently batch-optimized steps:
    - Step 3 (FOLDSEEK): Single createdb + search + convertalis instead of
      per-protein easy-search. Target DB index loaded once.
    - Step 7 (ITERATIVE_DALI): Template caching - ECOD70 templates copied
      once to shared cache instead of per-protein per-domain.
    - Step 16 (RUN_DOMASS): TF model loaded once (~22s saved per protein)

All other steps use default per-protein execution via DPAMPipeline.run_step().
"""

import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from dpam.core.models import PipelineStep, PipelineState
from dpam.core.path_resolver import PathResolver
from dpam.pipeline.runner import DPAMPipeline, CRITICAL_STEPS
from dpam.utils.logging_config import get_logger

logger = get_logger('pipeline.batch_runner')


class BatchState:
    """Track batch execution progress at (step, protein) granularity.

    Maintains a single JSON file for fast batch-level status checks.
    Also updates per-protein .dpam_state.json files for compatibility
    with single-protein mode (``dpam run --resume``).
    """

    def __init__(self, working_dir: Path, proteins: Optional[List[str]] = None):
        self.working_dir = working_dir
        self.state_file = working_dir / "_batch_state.json"
        self._state: Dict[str, Dict[str, str]] = self._load()

        # On first run, seed from existing per-protein state files
        if not self._state and proteins:
            self._seed_from_protein_states(proteins)

    def _seed_from_protein_states(self, proteins: List[str]):
        """Initialize batch state from existing per-protein state files."""
        seeded = 0
        for protein in proteins:
            state_file = self.working_dir / f'.{protein}.dpam_state.json'
            if state_file.exists():
                try:
                    pstate = PipelineState.load(state_file)
                    for step in pstate.completed_steps:
                        self._set(step.name, protein, "complete")
                    seeded += 1
                except Exception as e:
                    logger.warning(f"Failed to read state for {protein}: {e}")
        if seeded > 0:
            logger.info(f"Seeded batch state from {seeded} existing protein state files")
            self._save()

    def get_pending(self, step: PipelineStep, proteins: List[str]) -> List[str]:
        """Get proteins that haven't completed this step.

        Also filters out proteins that failed a critical earlier step,
        since downstream steps cannot produce meaningful results.
        """
        step_state = self._state.get(step.name, {})
        pending = []
        for p in proteins:
            if step_state.get(p) == "complete":
                continue
            if self._has_critical_failure(step, p):
                continue
            pending.append(p)
        return pending

    def mark_complete(self, step: PipelineStep, protein: str):
        """Mark (step, protein) as complete."""
        self._set(step.name, protein, "complete")
        self._save()
        self._update_protein_state(protein, step, success=True)

    def mark_failed(self, step: PipelineStep, protein: str, error: str = ""):
        """Mark (step, protein) as failed."""
        self._set(step.name, protein, f"failed: {error}")
        self._save()
        self._update_protein_state(protein, step, success=False, error=error)

    def get_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary counts per step."""
        summary = {}
        for step_name, proteins in self._state.items():
            complete = sum(1 for s in proteins.values() if s == "complete")
            failed = sum(1 for s in proteins.values()
                         if isinstance(s, str) and s.startswith("failed"))
            summary[step_name] = {"complete": complete, "failed": failed}
        return summary

    def _has_critical_failure(self, step: PipelineStep, protein: str) -> bool:
        """Check if protein failed a critical step before this one."""
        for crit_step in CRITICAL_STEPS:
            if crit_step.value < step.value:
                crit_state = self._state.get(crit_step.name, {})
                status = crit_state.get(protein, "")
                if isinstance(status, str) and status.startswith("failed"):
                    return True
        return False

    def _set(self, step_name: str, protein: str, status: str):
        if step_name not in self._state:
            self._state[step_name] = {}
        self._state[step_name][protein] = status

    def _load(self) -> Dict[str, Dict[str, str]]:
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load batch state: {e}")
        return {}

    def _save(self):
        """Atomic write to prevent corruption on crash."""
        tmp = self.state_file.with_suffix('.tmp')
        with open(tmp, 'w') as f:
            json.dump(self._state, f, indent=2)
        tmp.rename(self.state_file)

    def _update_protein_state(self, protein: str, step: PipelineStep,
                               success: bool, error: str = ""):
        """Update per-protein state file for compatibility with dpam run --resume."""
        state_file = self.working_dir / f'.{protein}.dpam_state.json'
        try:
            if state_file.exists():
                pstate = PipelineState.load(state_file)
            else:
                pstate = PipelineState(prefix=protein, working_dir=self.working_dir)

            if success:
                pstate.mark_complete(step)
            else:
                pstate.mark_failed(step, error)
            pstate.save(state_file)
        except Exception as e:
            logger.warning(f"Failed to update protein state for {protein}: {e}")


class BatchRunner:
    """Run DPAM pipeline step-by-step across a batch of proteins.

    Loads expensive resources once per step rather than once per protein.
    Currently optimized for:
        - Step 3 (FOLDSEEK): Batch createdb + search + convertalis
        - Step 7 (ITERATIVE_DALI): Shared template cache across proteins
        - Step 16 (DOMASS): TF model loaded once

    Usage:
        proteins = ["AF-P12345", "AF-P67890", ...]
        runner = BatchRunner(proteins, working_dir, data_dir, cpus=8)
        runner.run()
    """

    def __init__(
        self,
        proteins: List[str],
        working_dir: Path,
        data_dir: Path,
        cpus: int = 1,
        resume: bool = True,
        skip_addss: bool = False,
        scratch_dir: Path = None,
        dali_workers: int = None,
        sharded: bool = None
    ):
        self.proteins = proteins
        self.working_dir = Path(working_dir)
        self.data_dir = Path(data_dir)
        self.cpus = cpus
        self.skip_addss = skip_addss
        self.scratch_dir = scratch_dir
        self.dali_workers = dali_workers

        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Create pipeline for step dispatch (loads reference data once)
        self.pipeline = DPAMPipeline(
            working_dir=self.working_dir,
            data_dir=self.data_dir,
            cpus=self.cpus,
            resume=False,  # We manage resume via BatchState
            skip_addss=self.skip_addss,
            scratch_dir=self.scratch_dir,
            dali_workers=self.dali_workers,
            sharded=sharded
        )

        # Use the pipeline's resolver for consistent path resolution
        self.resolver = self.pipeline.resolver

        # Batch state for resume support
        self.state = BatchState(
            self.working_dir,
            self.proteins if resume else None
        )

    def run(self, steps: Optional[List[PipelineStep]] = None):
        """Execute pipeline step-first across all proteins.

        Args:
            steps: Specific steps to run (None = all steps)
        """
        all_steps = steps or list(PipelineStep)
        total_start = time.time()

        logger.info(
            f"Starting step-first batch run: "
            f"{len(self.proteins)} proteins, {len(all_steps)} steps"
        )

        for step in all_steps:
            pending = self.state.get_pending(step, self.proteins)
            if not pending:
                logger.info(f"Step {step.name}: all proteins complete, skipping")
                continue

            logger.info(f"Step {step.name}: {len(pending)} proteins to process")
            step_start = time.time()

            if step == PipelineStep.FOLDSEEK:
                self._run_foldseek_batch(pending)
            elif step == PipelineStep.ITERATIVE_DALI:
                self._run_dali_batch(pending)
            elif step == PipelineStep.RUN_DOMASS:
                self._run_domass_batch(pending)
            else:
                self._run_default_batch(step, pending)

            step_duration = time.time() - step_start
            still_pending = self.state.get_pending(step, pending)
            n_done = len(pending) - len(still_pending)
            logger.info(
                f"Step {step.name}: {n_done}/{len(pending)} succeeded "
                f"in {step_duration:.1f}s"
            )

        total_duration = time.time() - total_start
        logger.info(f"Batch run complete in {total_duration:.1f}s")

        summary = self.state.get_summary()
        for step_name, counts in sorted(summary.items()):
            if counts['complete'] > 0 or counts['failed'] > 0:
                logger.info(
                    f"  {step_name}: "
                    f"{counts['complete']} complete, {counts['failed']} failed"
                )

    def _run_foldseek_batch(self, proteins: List[str]):
        """Run foldseek with batch createdb + search + convertalis."""
        from dpam.steps.step03_foldseek import run_step3_batch

        logger.info(
            f"Running batch foldseek for {len(proteins)} proteins "
            f"(single DB index load)..."
        )

        try:
            results = run_step3_batch(
                proteins, self.working_dir, self.data_dir,
                threads=self.cpus,
                path_resolver=self.resolver
            )

            for protein, success in results.items():
                if success:
                    self.state.mark_complete(PipelineStep.FOLDSEEK, protein)
                else:
                    self.state.mark_failed(
                        PipelineStep.FOLDSEEK, protein,
                        "Batch foldseek failed"
                    )

        except Exception as e:
            logger.error(f"Batch foldseek failed: {e}")
            for p in proteins:
                self.state.mark_failed(
                    PipelineStep.FOLDSEEK, p, f"Batch error: {e}"
                )

    def _run_dali_batch(self, proteins: List[str]):
        """Run iterative DALI with shared template cache.

        Pre-copies all needed ECOD70 templates to a shared cache directory,
        then runs step 7 per protein using the cache instead of individual
        NFS reads from ECOD70/.
        """
        from dpam.steps.step07_iterative_dali import run_step7

        # Scan _hits4Dali files to collect all needed template domain IDs
        all_templates = set()
        candidates_dir = self.resolver.step_dir(6)
        for protein in proteins:
            hits_file = candidates_dir / f'{protein}_hits4Dali'
            if hits_file.exists():
                with open(hits_file) as f:
                    for line in f:
                        domain = line.strip()
                        if domain:
                            all_templates.add(domain)

        if not all_templates:
            logger.info("No DALI candidates found for any protein, skipping")
            for p in proteins:
                hits_file = candidates_dir / f'{p}_hits4Dali'
                if not hits_file.exists():
                    self.state.mark_failed(
                        PipelineStep.ITERATIVE_DALI, p,
                        "No _hits4Dali file"
                    )
            return

        # Create shared template cache in batch directory
        template_cache = self.resolver.batch_dir() / '_dali_template_cache'
        template_cache.mkdir(exist_ok=True)

        ecod70_dir = self.data_dir / 'ECOD70'
        logger.info(
            f"Caching {len(all_templates)} unique ECOD70 templates "
            f"for {len(proteins)} proteins..."
        )
        cache_start = time.time()

        copied = 0
        missing = 0
        for domain in all_templates:
            src = ecod70_dir / f'{domain}.pdb'
            dst = template_cache / f'{domain}.pdb'
            if not dst.exists():
                if src.exists():
                    shutil.copy2(src, dst)
                    copied += 1
                else:
                    missing += 1

        cache_time = time.time() - cache_start
        logger.info(
            f"Template cache ready: {copied} copied, {missing} missing "
            f"in {cache_time:.1f}s"
        )

        # Run step 7 per protein with shared template cache
        for i, protein in enumerate(proteins):
            try:
                success = run_step7(
                    protein, self.working_dir, self.data_dir,
                    cpus=self.cpus, template_cache=template_cache,
                    scratch_dir=self.scratch_dir,
                    dali_workers=self.dali_workers,
                    path_resolver=self.resolver
                )
                if success:
                    self.state.mark_complete(
                        PipelineStep.ITERATIVE_DALI, protein
                    )
                else:
                    self.state.mark_failed(
                        PipelineStep.ITERATIVE_DALI, protein,
                        "Step returned False"
                    )
            except Exception as e:
                logger.error(f"ITERATIVE_DALI failed for {protein}: {e}")
                self.state.mark_failed(
                    PipelineStep.ITERATIVE_DALI, protein, str(e)
                )

            if (i + 1) % 10 == 0:
                logger.info(
                    f"  DALI progress: {i + 1}/{len(proteins)}"
                )

        # Clean up template cache
        if template_cache.exists():
            shutil.rmtree(template_cache, ignore_errors=True)
            logger.debug("Cleaned up DALI template cache")

    def _run_domass_batch(self, proteins: List[str]):
        """Run DOMASS with shared TensorFlow model (loaded once)."""
        from dpam.steps.step16_run_domass import DomassModel, run_step16

        model_path = self.data_dir / "domass_epo29"
        if not model_path.with_suffix('.meta').exists():
            logger.error(f"Model checkpoint not found: {model_path}")
            for p in proteins:
                self.state.mark_failed(
                    PipelineStep.RUN_DOMASS, p, "Model not found"
                )
            return

        logger.info("Loading DOMASS TF model (once for all proteins)...")
        load_start = time.time()

        try:
            with DomassModel(model_path) as model:
                load_time = time.time() - load_start
                logger.info(f"Model loaded in {load_time:.1f}s")

                for i, protein in enumerate(proteins):
                    try:
                        success = run_step16(
                            protein, self.working_dir, self.data_dir,
                            model=model,
                            path_resolver=self.resolver
                        )
                        if success:
                            self.state.mark_complete(
                                PipelineStep.RUN_DOMASS, protein
                            )
                        else:
                            self.state.mark_failed(
                                PipelineStep.RUN_DOMASS, protein,
                                "Step returned False"
                            )
                    except Exception as e:
                        logger.error(f"DOMASS failed for {protein}: {e}")
                        self.state.mark_failed(
                            PipelineStep.RUN_DOMASS, protein, str(e)
                        )

                    if (i + 1) % 100 == 0:
                        logger.info(
                            f"  DOMASS progress: {i + 1}/{len(proteins)}"
                        )

        except Exception as e:
            logger.error(f"Failed to load DOMASS model: {e}")
            for p in proteins:
                self.state.mark_failed(
                    PipelineStep.RUN_DOMASS, p, f"Model load failed: {e}"
                )

    def _run_default_batch(self, step: PipelineStep, proteins: List[str]):
        """Run step per-protein using the pipeline's step execution."""
        for i, protein in enumerate(proteins):
            try:
                success = self.pipeline.run_step(step, protein)
                if success:
                    self.state.mark_complete(step, protein)
                else:
                    self.state.mark_failed(step, protein, "Step returned False")
            except Exception as e:
                logger.error(f"{step.name} failed for {protein}: {e}")
                self.state.mark_failed(step, protein, str(e))

            if (i + 1) % 100 == 0:
                logger.info(f"  {step.name} progress: {i + 1}/{len(proteins)}")
