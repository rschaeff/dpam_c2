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


class DPAMPipeline:
    """
    DPAM pipeline orchestrator with checkpointing and error handling.
    """
    
    def __init__(
        self,
        working_dir: Path,
        data_dir: Path,
        cpus: int = 1,
        resume: bool = True
    ):
        """
        Initialize pipeline.
        
        Args:
            working_dir: Working directory for processing
            data_dir: Directory containing reference data
            cpus: Number of CPUs to use
            resume: Resume from checkpoints if available
        """
        self.working_dir = Path(working_dir)
        self.data_dir = Path(data_dir)
        self.cpus = cpus
        self.resume = resume
        
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
                
                # Continue to next step (don't break)
                logger.warning(f"Continuing despite failure in {step.name}")
        
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
            return run_step2(prefix, self.working_dir, self.data_dir, self.cpus)
        
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
            from dpam.steps.step06_dali_candidates import run_step6
            return run_step6(prefix, self.working_dir)
        
        elif step == PipelineStep.ITERATIVE_DALI:
            from dpam.steps.step07_iterative_dali import run_step7
            return run_step7(prefix, self.working_dir, self.data_dir, self.cpus)
        
        elif step == PipelineStep.ANALYZE_DALI:
            from dpam.steps.step08_analyze_dali import run_step8
            return run_step8(prefix, self.working_dir, self.reference_data)
        
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
            return run_step13(prefix, self.working_dir, self.reference_data)
        
        else:
            logger.error(f"Unknown step: {step}")
            return False
