"""
SLURM job submission utilities.
"""

from pathlib import Path
from typing import List, Optional
import subprocess
import textwrap

from dpam.utils.logging_config import get_logger

logger = get_logger('pipeline.slurm')


def generate_slurm_script(
    prefixes: List[str],
    working_dir: Path,
    data_dir: Path,
    cpus_per_task: int = 1,
    mem_per_cpu: str = '4G',
    time_limit: str = '4:00:00',
    partition: Optional[str] = None,
    array_size: int = 100,
    log_dir: Optional[Path] = None
) -> str:
    """
    Generate SLURM batch script for DPAM pipeline.
    
    Args:
        prefixes: List of structure prefixes
        working_dir: Working directory
        data_dir: Data directory
        cpus_per_task: CPUs per array task
        mem_per_cpu: Memory per CPU
        time_limit: Time limit (HH:MM:SS)
        partition: SLURM partition
        array_size: Maximum concurrent array tasks
        log_dir: Directory for SLURM logs
    
    Returns:
        SLURM script as string
    """
    if log_dir is None:
        log_dir = working_dir / 'slurm_logs'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Write prefixes to file
    prefix_file = working_dir / 'prefixes_array.txt'
    with open(prefix_file, 'w') as f:
        for prefix in prefixes:
            f.write(f"{prefix}\n")
    
    # Build array specification
    n_tasks = len(prefixes)
    if array_size:
        array_spec = f"0-{n_tasks-1}%{array_size}"
    else:
        array_spec = f"0-{n_tasks-1}"
    
    # Build script
    script_lines = [
        "#!/bin/bash",
        f"#SBATCH --array={array_spec}",
        f"#SBATCH --cpus-per-task={cpus_per_task}",
        f"#SBATCH --mem-per-cpu={mem_per_cpu}",
        f"#SBATCH --time={time_limit}",
        f"#SBATCH --output={log_dir}/%A_%a.out",
        f"#SBATCH --error={log_dir}/%A_%a.err",
        f"#SBATCH --job-name=dpam",
    ]
    
    if partition:
        script_lines.append(f"#SBATCH --partition={partition}")
    
    script_lines.extend([
        "",
        "# Load modules if needed",
        "# module load hhsuite foldseek dali",
        "",
        "# Get prefix for this array task",
        f"PREFIX=$(sed -n \"$((SLURM_ARRAY_TASK_ID + 1))p\" {prefix_file})",
        "",
        "# Run DPAM pipeline",
        f"dpam run $PREFIX \\",
        f"  --working-dir {working_dir} \\",
        f"  --data-dir {data_dir} \\",
        f"  --cpus $SLURM_CPUS_PER_TASK \\",
        f"  --resume \\",
        f"  --log-file {log_dir}/${{PREFIX}}.log \\",
        f"  --json-log",
        "",
        "exit $?",
    ])
    
    return "\n".join(script_lines)


def submit_slurm_array(
    prefixes: List[str],
    working_dir: Path,
    data_dir: Path,
    cpus_per_task: int = 1,
    mem_per_cpu: str = '4G',
    time_limit: str = '4:00:00',
    partition: Optional[str] = None,
    array_size: int = 100
) -> str:
    """
    Submit SLURM job array for DPAM pipeline.
    
    Args:
        prefixes: List of structure prefixes
        working_dir: Working directory
        data_dir: Data directory
        cpus_per_task: CPUs per task
        mem_per_cpu: Memory per CPU
        time_limit: Time limit
        partition: SLURM partition
        array_size: Maximum concurrent tasks
    
    Returns:
        Job ID
    """
    logger.info(f"Submitting SLURM array for {len(prefixes)} structures")
    
    # Generate script
    script = generate_slurm_script(
        prefixes=prefixes,
        working_dir=working_dir,
        data_dir=data_dir,
        cpus_per_task=cpus_per_task,
        mem_per_cpu=mem_per_cpu,
        time_limit=time_limit,
        partition=partition,
        array_size=array_size
    )
    
    # Save script
    script_file = working_dir / 'dpam_array.sh'
    with open(script_file, 'w') as f:
        f.write(script)
    
    logger.info(f"Saved SLURM script: {script_file}")
    
    # Submit
    result = subprocess.run(
        ['sbatch', str(script_file)],
        capture_output=True,
        text=True,
        check=True
    )
    
    # Parse job ID from output
    # Expected: "Submitted batch job 12345"
    output = result.stdout.strip()
    job_id = output.split()[-1]
    
    logger.info(f"Submitted job array: {job_id}")
    
    return job_id


def check_job_status(job_id: str) -> dict:
    """
    Check status of SLURM job.
    
    Args:
        job_id: SLURM job ID
    
    Returns:
        Dict with job status information
    """
    try:
        result = subprocess.run(
            ['squeue', '-j', job_id, '--format=%T', '--noheader'],
            capture_output=True,
            text=True,
            check=True
        )
        
        states = result.stdout.strip().split('\n')
        state_counts = {}
        for state in states:
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            'job_id': job_id,
            'state_counts': state_counts,
            'running': any('RUNNING' in s for s in states)
        }
    
    except subprocess.CalledProcessError:
        return {
            'job_id': job_id,
            'state_counts': {},
            'running': False
        }


def cancel_job(job_id: str) -> bool:
    """
    Cancel SLURM job.
    
    Args:
        job_id: Job ID to cancel
    
    Returns:
        True if successful
    """
    try:
        subprocess.run(
            ['scancel', job_id],
            check=True
        )
        logger.info(f"Cancelled job: {job_id}")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return False
