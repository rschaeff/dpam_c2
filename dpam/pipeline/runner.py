"""
DPAM Pipeline Runner.

Orchestrates execution of pipeline steps with checkpointing and error handling.
"""

from pathlib import Path
from typing import List, Optional
import time

from dpam.core.models import PipelineStep, PipelineState
from dpam.utils.logging_config import (
    get_logger,
    log_step_start,
    log_step_complete,
    log_step_failed
)

logger = get_logger('pipeline')

# Critical steps that halt the pipeline on failure
# These steps have no fallback - if they fail, downstream steps cannot proceed
CRITICAL_STEPS = {
    PipelineStep.HHSEARCH,      # Step 2: No sequence homology = no HHsearch hits
    PipelineStep.FOLDSEEK,      # Step 3: No structure search = no Foldseek hits
    PipelineStep.ITERATIVE_DALI # Step 7: No DALI alignments = incomplete domain info
}


class DPAMPipeline:
    """
    DPAM pipeline orchestrator with checkpointing and error handling.
    """
    
    def __init__(
        self,
        working_dir: Path,
        data_dir: Path,
        cpus: int = 1,
        resume: bool = True,
        skip_addss: bool = False,
        scratch_dir: Path = None,
        dali_workers: int = None
    ):
        """
        Initialize pipeline.

        Args:
            working_dir: Working directory for processing
            data_dir: Directory containing reference data
            cpus: Number of CPUs to use
            resume: Resume from checkpoints if available
            skip_addss: Skip addss.pl secondary structure (PSIPRED not available)
            scratch_dir: Local scratch dir for DALI temp I/O (default: NFS working dir)
            dali_workers: DALI worker count (default: same as cpus)
        """
        self.working_dir = Path(working_dir)
        self.data_dir = Path(data_dir)
        self.cpus = cpus
        self.resume = resume
        self.skip_addss = skip_addss
        self.scratch_dir = scratch_dir
        self.dali_workers = dali_workers
        
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        # Load reference data once
        from dpam.io.reference_data import load_ecod_data
        logger.info("Loading ECOD reference data...")
        self.reference_data = load_ecod_data(data_dir)
        logger.info("Reference data loaded")
    
    def run(
        self,
        prefix: str,
        steps: Optional[List[PipelineStep]] = None
    ) -> PipelineState:
        """
        Run pipeline for a structure.
        
        Args:
            prefix: Structure prefix
            steps: Specific steps to run (None = all steps)
        
        Returns:
            PipelineState with execution status
        """
        logger.info(f"Starting pipeline for {prefix}")
        
        state_file = self.working_dir / f'.{prefix}.dpam_state.json'
        
        # Load or create state
        if self.resume and state_file.exists():
            logger.info(f"Resuming from checkpoint: {state_file}")
            state = PipelineState.load(state_file)
        else:
            state = PipelineState(
                prefix=prefix,
                working_dir=self.working_dir
            )
        
        # Determine steps to run
        all_steps = steps if steps else list(PipelineStep)
        pending_steps = [
            s for s in all_steps
            if not state.is_complete(s)
        ]
        
        logger.info(
            f"Running {len(pending_steps)} steps "
            f"({len(state.completed_steps)} already completed)"
        )
        
        # Execute steps
        for step in pending_steps:
            success = self.run_step(step, prefix)
            
            if success:
                state.mark_complete(step)
                state.save(state_file)
            else:
                error_msg = f"Step {step.name} failed"
                state.mark_failed(step, error_msg)
                state.save(state_file)

                # Critical steps halt the pipeline - no fallback possible
                if step in CRITICAL_STEPS:
                    logger.error(
                        f"CRITICAL STEP {step.name} FAILED - halting pipeline. "
                        f"This step has no fallback; downstream steps cannot proceed."
                    )
                    break
                else:
                    # Non-critical steps: log warning and continue
                    logger.warning(f"Non-critical step {step.name} failed, continuing...")
        
        logger.info(
            f"Pipeline completed for {prefix}: "
            f"{len(state.completed_steps)} succeeded, "
            f"{len(state.failed_steps)} failed"
        )
        
        return state
    
    def run_step(self, step: PipelineStep, prefix: str) -> bool:
        """
        Execute a single pipeline step.
        
        Args:
            step: Pipeline step to execute
            prefix: Structure prefix
        
        Returns:
            True if successful, False otherwise
        """
        log_step_start(logger, step.name, prefix)
        start_time = time.time()
        
        try:
            # Import and run step function
            success = self._execute_step(step, prefix)
            
            duration = time.time() - start_time
            
            if success:
                log_step_complete(logger, step.name, prefix, duration)
            else:
                log_step_failed(logger, step.name, prefix, "Step returned False")
            
            return success
        
        except Exception as e:
            duration = time.time() - start_time
            log_step_failed(logger, step.name, prefix, str(e))
            logger.exception(f"Exception in {step.name}")
            return False
    
    def _execute_step(self, step: PipelineStep, prefix: str) -> bool:
        """
        Execute specific step.
        
        Args:
            step: Pipeline step
            prefix: Structure prefix
        
        Returns:
            True if successful
        """
        # Import step modules dynamically
        if step == PipelineStep.PREPARE:
            from dpam.steps.step01_prepare import run_step1
            return run_step1(prefix, self.working_dir)
        
        elif step == PipelineStep.HHSEARCH:
            from dpam.steps.step02_hhsearch import run_step2
            return run_step2(prefix, self.working_dir, self.data_dir, self.cpus,
                             skip_addss=self.skip_addss)
        
        elif step == PipelineStep.FOLDSEEK:
            from dpam.steps.step03_foldseek import run_step3
            return run_step3(prefix, self.working_dir, self.data_dir, self.cpus)
        
        elif step == PipelineStep.FILTER_FOLDSEEK:
            from dpam.steps.step04_filter_foldseek import run_step4
            return run_step4(prefix, self.working_dir)
        
        elif step == PipelineStep.MAP_ECOD:
            from dpam.steps.step05_map_ecod import run_step5
            return run_step5(prefix, self.working_dir, self.reference_data)
        
        elif step == PipelineStep.DALI_CANDIDATES:
            from dpam.steps.step06_get_dali_candidates import run_step6
            return run_step6(prefix, self.working_dir)
        
        elif step == PipelineStep.ITERATIVE_DALI:
            from dpam.steps.step07_iterative_dali import run_step7
            return run_step7(prefix, self.working_dir, self.data_dir, self.cpus,
                             scratch_dir=self.scratch_dir,
                             dali_workers=self.dali_workers)
        
        elif step == PipelineStep.ANALYZE_DALI:
            from dpam.steps.step08_analyze_dali import run_step8
            return run_step8(prefix, self.working_dir, self.reference_data, self.data_dir)
        
        elif step == PipelineStep.GET_SUPPORT:
            from dpam.steps.step09_get_support import run_step9
            return run_step9(prefix, self.working_dir, self.reference_data)
        
        elif step == PipelineStep.FILTER_DOMAINS:
            from dpam.steps.step10_filter_domains import run_step10
            return run_step10(prefix, self.working_dir, self.reference_data)
        
        elif step == PipelineStep.SSE:
            from dpam.steps.step11_sse import run_step11
            return run_step11(prefix, self.working_dir)
        
        elif step == PipelineStep.DISORDER:
            from dpam.steps.step12_disorder import run_step12
            return run_step12(prefix, self.working_dir)
        
        elif step == PipelineStep.PARSE_DOMAINS:
            from dpam.steps.step13_parse_domains import run_step13
            return run_step13(prefix, self.working_dir)

        elif step == PipelineStep.PREPARE_DOMASS:
            from dpam.steps.step15_prepare_domass import run_step15
            return run_step15(prefix, self.working_dir, self.data_dir)

        elif step == PipelineStep.RUN_DOMASS:
            from dpam.steps.step16_run_domass import run_step16
            return run_step16(prefix, self.working_dir, self.data_dir)

        elif step == PipelineStep.GET_CONFIDENT:
            from dpam.steps.step17_get_confident import run_step17
            return run_step17(prefix, self.working_dir)

        elif step == PipelineStep.GET_MAPPING:
            from dpam.steps.step18_get_mapping import run_step18
            return run_step18(prefix, self.working_dir, self.data_dir)

        elif step == PipelineStep.GET_MERGE_CANDIDATES:
            from dpam.steps.step19_get_merge_candidates import run_step19
            return run_step19(prefix, self.working_dir, self.data_dir)

        elif step == PipelineStep.EXTRACT_DOMAINS:
            from dpam.steps.step20_extract_domains import run_step20
            return run_step20(prefix, self.working_dir)

        elif step == PipelineStep.COMPARE_DOMAINS:
            from dpam.steps.step21_compare_domains import run_step21
            return run_step21(prefix, self.working_dir)

        elif step == PipelineStep.MERGE_DOMAINS:
            from dpam.steps.step22_merge_domains import run_step22
            return run_step22(prefix, self.working_dir)

        elif step == PipelineStep.GET_PREDICTIONS:
            from dpam.steps.step23_get_predictions import run_step23
            return run_step23(prefix, self.working_dir, self.data_dir)

        elif step == PipelineStep.INTEGRATE_RESULTS:
            from dpam.steps.step24_integrate_results import run_step24
            return run_step24(prefix, self.working_dir, self.data_dir)

        elif step == PipelineStep.GENERATE_PDBS:
            # Step 25 is optional visualization - skip for now
            logger.warning(f"Step 25 (GENERATE_PDBS) not yet implemented - skipping")
            return True

        else:
            logger.error(f"Unknown step: {step}")
            return False
