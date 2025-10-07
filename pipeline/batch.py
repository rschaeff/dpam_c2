"""
Batch processing for DPAM pipeline.

Process multiple structures in parallel using multiprocessing.
"""

from pathlib import Path
from typing import List, Dict, Optional
from multiprocessing import Pool, Manager
import traceback

from dpam.pipeline.runner import DPAMPipeline
from dpam.utils.logging_config import get_logger, setup_logging

logger = get_logger('pipeline.batch')


def process_single_structure(args: tuple) -> Dict:
    """
    Process a single structure (worker function).
    
    Args:
        args: Tuple of (prefix, working_dir, data_dir, cpus, resume, log_dir)
    
    Returns:
        Dict with results
    """
    prefix, working_dir, data_dir, cpus, resume, log_dir = args
    
    # Setup logging for this worker
    if log_dir:
        log_file = log_dir / f'{prefix}.log'
    else:
        log_file = None
    
    setup_logging(log_file=log_file, json_format=True)
    
    result = {
        'prefix': prefix,
        'success': False,
        'completed_steps': [],
        'failed_steps': {}
    }
    
    try:
        # Create pipeline
        pipeline = DPAMPipeline(
            working_dir=working_dir,
            data_dir=data_dir,
            cpus=cpus,
            resume=resume
        )
        
        # Run pipeline
        state = pipeline.run(prefix)
        
        result['success'] = len(state.failed_steps) == 0
        result['completed_steps'] = [s.name for s in state.completed_steps]
        result['failed_steps'] = {
            s.name: err for s, err in state.failed_steps.items()
        }
        
    except Exception as e:
        logger.error(f"Failed to process {prefix}: {e}")
        result['failed_steps']['ERROR'] = str(e)
        result['traceback'] = traceback.format_exc()
    
    return result


def run_batch_processing(
    prefixes: List[str],
    working_dir: Path,
    data_dir: Path,
    cpus_per_structure: int = 1,
    num_parallel: int = 1,
    resume: bool = True,
    log_dir: Optional[Path] = None
) -> List[Dict]:
    """
    Run batch processing for multiple structures.
    
    Args:
        prefixes: List of structure prefixes
        working_dir: Working directory
        data_dir: Data directory
        cpus_per_structure: CPUs per structure
        num_parallel: Number of structures to process in parallel
        resume: Resume from checkpoints
        log_dir: Directory for individual log files
    
    Returns:
        List of result dicts
    """
    logger.info(f"Starting batch processing for {len(prefixes)} structures")
    logger.info(f"Parallel: {num_parallel}, CPUs per structure: {cpus_per_structure}")
    
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare arguments
    args_list = [
        (prefix, working_dir, data_dir, cpus_per_structure, resume, log_dir)
        for prefix in prefixes
    ]
    
    # Process in parallel
    if num_parallel > 1:
        with Pool(processes=num_parallel) as pool:
            results = pool.map(process_single_structure, args_list)
    else:
        # Sequential processing
        results = [process_single_structure(args) for args in args_list]
    
    # Summarize results
    n_success = sum(1 for r in results if r['success'])
    n_failed = len(results) - n_success
    
    logger.info(f"Batch complete: {n_success} succeeded, {n_failed} failed")
    
    if n_failed > 0:
        logger.warning("Failed structures:")
        for result in results:
            if not result['success']:
                logger.warning(f"  {result['prefix']}: {result['failed_steps']}")
    
    return results


def get_incomplete_structures(
    prefixes: List[str],
    working_dir: Path
) -> List[str]:
    """
    Find structures that haven't completed successfully.
    
    Args:
        prefixes: List of structure prefixes
        working_dir: Working directory
    
    Returns:
        List of incomplete prefixes
    """
    from dpam.core.models import PipelineState, PipelineStep
    
    incomplete = []
    
    for prefix in prefixes:
        state_file = working_dir / f'.{prefix}.dpam_state.json'
        
        if not state_file.exists():
            incomplete.append(prefix)
            continue
        
        try:
            state = PipelineState.load(state_file)
            
            # Check if all steps completed
            all_steps = set(PipelineStep)
            if state.completed_steps != all_steps:
                incomplete.append(prefix)
            elif state.failed_steps:
                incomplete.append(prefix)
        
        except Exception as e:
            logger.warning(f"Failed to load state for {prefix}: {e}")
            incomplete.append(prefix)
    
    return incomplete


def retry_failed_structures(
    working_dir: Path,
    data_dir: Path,
    cpus_per_structure: int = 1,
    num_parallel: int = 1,
    log_dir: Optional[Path] = None
) -> List[Dict]:
    """
    Retry structures that previously failed.
    
    Args:
        working_dir: Working directory
        data_dir: Data directory
        cpus_per_structure: CPUs per structure
        num_parallel: Parallel structures
        log_dir: Log directory
    
    Returns:
        List of retry results
    """
    # Find state files with failures
    state_files = list(working_dir.glob('.*.dpam_state.json'))
    
    failed_prefixes = []
    for state_file in state_files:
        try:
            from dpam.core.models import PipelineState
            state = PipelineState.load(state_file)
            
            if state.failed_steps:
                failed_prefixes.append(state.prefix)
        
        except Exception as e:
            logger.warning(f"Failed to load {state_file}: {e}")
    
    if not failed_prefixes:
        logger.info("No failed structures to retry")
        return []
    
    logger.info(f"Retrying {len(failed_prefixes)} failed structures")
    
    return run_batch_processing(
        prefixes=failed_prefixes,
        working_dir=working_dir,
        data_dir=data_dir,
        cpus_per_structure=cpus_per_structure,
        num_parallel=num_parallel,
        resume=True,
        log_dir=log_dir
    )
