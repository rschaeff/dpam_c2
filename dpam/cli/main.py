"""
DPAM Command Line Interface.

Main entry point for running DPAM pipeline.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from dpam.pipeline.runner import DPAMPipeline
from dpam.core.models import PipelineStep
from dpam.utils.logging_config import setup_logging, get_logger

logger = get_logger('cli')


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='DPAM - Domain Parser for AlphaFold Models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline for single structure
  dpam run AF-P12345 --working-dir ./work --data-dir ./data --cpus 4
  
  # Run specific step
  dpam run-step AF-P12345 --step HHSEARCH --working-dir ./work
  
  # Batch processing
  dpam batch prefixes.txt --working-dir ./work --data-dir ./data --cpus 8
  
  # SLURM submission
  dpam slurm-submit prefixes.txt --partition compute --cpus-per-task 4
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run full pipeline for structure')
    run_parser.add_argument('prefix', help='Structure prefix (e.g., AF-P12345)')
    run_parser.add_argument('--working-dir', type=Path, required=True,
                           help='Working directory')
    run_parser.add_argument('--data-dir', type=Path, required=True,
                           help='Data directory (ECOD databases)')
    run_parser.add_argument('--cpus', type=int, default=1,
                           help='Number of CPUs')
    run_parser.add_argument('--resume', action='store_true',
                           help='Resume from last completed step')
    run_parser.add_argument('--steps', nargs='+',
                           choices=[s.name for s in PipelineStep],
                           help='Specific steps to run (default: all)')
    run_parser.add_argument('--log-file', type=Path,
                           help='Log file path')
    run_parser.add_argument('--json-log', action='store_true',
                           help='Use JSON logging format')
    run_parser.add_argument('--skip-addss', action='store_true',
                           help='Skip addss.pl (requires PSIPRED). Set when PSIPRED unavailable.')
    run_parser.add_argument('--scratch-dir', type=Path, default=None,
                           help='Local scratch dir for DALI temp I/O (default: NFS working dir)')
    run_parser.add_argument('--dali-workers', type=int, default=None,
                           help='DALI worker count (default: same as --cpus). '
                                'DALI is I/O-bound; try 4x CPUs with local scratch.')

    # Run-step command
    step_parser = subparsers.add_parser('run-step', help='Run single pipeline step')
    step_parser.add_argument('prefix', help='Structure prefix')
    step_parser.add_argument('--step', required=True,
                            choices=[s.name for s in PipelineStep],
                            help='Step to run')
    step_parser.add_argument('--working-dir', type=Path, required=True,
                            help='Working directory')
    step_parser.add_argument('--data-dir', type=Path, required=True,
                            help='Data directory')
    step_parser.add_argument('--cpus', type=int, default=1,
                            help='Number of CPUs')
    step_parser.add_argument('--log-file', type=Path,
                            help='Log file path')
    step_parser.add_argument('--skip-addss', action='store_true',
                            help='Skip addss.pl (requires PSIPRED)')
    step_parser.add_argument('--scratch-dir', type=Path, default=None,
                            help='Local scratch dir for DALI temp I/O (default: NFS working dir)')
    step_parser.add_argument('--dali-workers', type=int, default=None,
                            help='DALI worker count (default: same as --cpus). '
                                 'DALI is I/O-bound; try 4x CPUs with local scratch.')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple structures')
    batch_parser.add_argument('prefix_file', type=Path,
                             help='File with structure prefixes (one per line)')
    batch_parser.add_argument('--working-dir', type=Path, required=True,
                             help='Working directory')
    batch_parser.add_argument('--data-dir', type=Path, required=True,
                             help='Data directory')
    batch_parser.add_argument('--cpus', type=int, default=1,
                             help='CPUs per structure')
    batch_parser.add_argument('--parallel', type=int, default=1,
                             help='Number of structures to process in parallel')
    batch_parser.add_argument('--resume', action='store_true',
                             help='Resume failed structures')
    batch_parser.add_argument('--log-dir', type=Path,
                             help='Directory for individual log files')
    
    # Batch-run command (step-first, resource-efficient)
    batch_run_parser = subparsers.add_parser(
        'batch-run',
        help='Process structures step-first (optimized for large batches)')
    batch_run_parser.add_argument('prefix_file', type=Path,
                                  help='File with structure prefixes (one per line)')
    batch_run_parser.add_argument('--working-dir', type=Path, required=True,
                                  help='Working directory')
    batch_run_parser.add_argument('--data-dir', type=Path, required=True,
                                  help='Data directory')
    batch_run_parser.add_argument('--cpus', type=int, default=4,
                                  help='Number of CPUs')
    batch_run_parser.add_argument('--resume', action='store_true',
                                  help='Resume from batch state checkpoint')
    batch_run_parser.add_argument('--steps', nargs='+',
                                  choices=[s.name for s in PipelineStep],
                                  help='Specific steps to run (default: all)')
    batch_run_parser.add_argument('--log-file', type=Path,
                                  help='Log file path')
    batch_run_parser.add_argument('--json-log', action='store_true',
                                  help='Use JSON logging format')
    batch_run_parser.add_argument('--skip-addss', action='store_true',
                                  help='Skip addss.pl (requires PSIPRED)')
    batch_run_parser.add_argument('--scratch-dir', type=Path, default=None,
                                  help='Local scratch dir for DALI temp I/O (default: NFS working dir)')
    batch_run_parser.add_argument('--dali-workers', type=int, default=None,
                                  help='DALI worker count (default: same as --cpus). '
                                       'DALI is I/O-bound; try 4x CPUs with local scratch.')

    # SLURM submit command (protein-first array jobs)
    slurm_parser = subparsers.add_parser('slurm-submit', help='Submit SLURM job array')
    slurm_parser.add_argument('prefix_file', type=Path,
                             help='File with structure prefixes')
    slurm_parser.add_argument('--working-dir', type=Path, required=True,
                             help='Working directory')
    slurm_parser.add_argument('--data-dir', type=Path, required=True,
                             help='Data directory')
    slurm_parser.add_argument('--cpus-per-task', type=int, default=1,
                             help='CPUs per task')
    slurm_parser.add_argument('--mem-per-cpu', default='4G',
                             help='Memory per CPU (e.g., 4G)')
    slurm_parser.add_argument('--time', default='4:00:00',
                             help='Time limit (HH:MM:SS)')
    slurm_parser.add_argument('--partition', help='SLURM partition')
    slurm_parser.add_argument('--array-size', type=int, default=100,
                             help='Maximum concurrent array tasks')

    # SLURM batch command (step-first single node)
    slurm_batch_parser = subparsers.add_parser(
        'slurm-batch',
        help='Submit single-node step-first SLURM job (optimized)')
    slurm_batch_parser.add_argument('prefix_file', type=Path,
                                     help='File with structure prefixes')
    slurm_batch_parser.add_argument('--working-dir', type=Path, required=True,
                                     help='Working directory')
    slurm_batch_parser.add_argument('--data-dir', type=Path, required=True,
                                     help='Data directory')
    slurm_batch_parser.add_argument('--cpus', type=int, default=16,
                                     help='Total CPUs for batch job')
    slurm_batch_parser.add_argument('--mem', default='64G',
                                     help='Total memory (e.g., 64G)')
    slurm_batch_parser.add_argument('--time', default='24:00:00',
                                     help='Time limit (HH:MM:SS)')
    slurm_batch_parser.add_argument('--partition', help='SLURM partition')
    slurm_batch_parser.add_argument('--skip-addss', action='store_true',
                                     help='Skip addss.pl (requires PSIPRED)')
    slurm_batch_parser.add_argument('--dry-run', action='store_true',
                                     help='Generate script without submitting')
    slurm_batch_parser.add_argument('--scratch-dir', type=Path, default=None,
                                     help='Local scratch dir for DALI temp I/O (default: /tmp for SLURM)')
    slurm_batch_parser.add_argument('--dali-workers', type=int, default=None,
                                     help='DALI worker count (default: min(cpus*4, 64) with scratch)')

    # Batch status command
    status_parser = subparsers.add_parser(
        'batch-status', help='Show batch processing status')
    status_parser.add_argument('--working-dir', type=Path, required=True,
                               help='Working directory with _batch_state.json')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    log_file = getattr(args, 'log_file', None)
    json_log = getattr(args, 'json_log', False)
    setup_logging(log_file=log_file, json_format=json_log)
    
    # Execute command
    if args.command == 'run':
        return run_pipeline(args)
    elif args.command == 'run-step':
        return run_single_step(args)
    elif args.command == 'batch':
        return run_batch(args)
    elif args.command == 'batch-run':
        return run_batch_stepwise(args)
    elif args.command == 'slurm-submit':
        return submit_slurm(args)
    elif args.command == 'slurm-batch':
        return submit_slurm_batch(args)
    elif args.command == 'batch-status':
        return show_batch_status(args)

    return 0


def run_pipeline(args) -> int:
    """Run full pipeline for single structure"""
    logger.info(f"Starting DPAM pipeline for {args.prefix}")
    
    # Parse steps
    steps = None
    if args.steps:
        steps = [PipelineStep[s] for s in args.steps]
    
    # Create pipeline
    skip_addss = getattr(args, 'skip_addss', False)
    scratch_dir = getattr(args, 'scratch_dir', None)
    dali_workers = getattr(args, 'dali_workers', None)
    pipeline = DPAMPipeline(
        working_dir=args.working_dir,
        data_dir=args.data_dir,
        cpus=args.cpus,
        resume=args.resume,
        skip_addss=skip_addss,
        scratch_dir=scratch_dir,
        dali_workers=dali_workers
    )

    # Run pipeline
    try:
        state = pipeline.run(args.prefix, steps=steps)
        
        if state.failed_steps:
            logger.error(f"Pipeline completed with failures: {state.failed_steps}")
            return 1
        else:
            logger.info(f"Pipeline completed successfully for {args.prefix}")
            return 0
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


def run_single_step(args) -> int:
    """Run single pipeline step"""
    step = PipelineStep[args.step]
    logger.info(f"Running {step.name} for {args.prefix}")

    skip_addss = getattr(args, 'skip_addss', False)
    scratch_dir = getattr(args, 'scratch_dir', None)
    dali_workers = getattr(args, 'dali_workers', None)
    pipeline = DPAMPipeline(
        working_dir=args.working_dir,
        data_dir=args.data_dir,
        cpus=args.cpus,
        resume=False,
        skip_addss=skip_addss,
        scratch_dir=scratch_dir,
        dali_workers=dali_workers
    )

    try:
        success = pipeline.run_step(step, args.prefix)
        return 0 if success else 1
    
    except Exception as e:
        logger.error(f"Step failed: {e}", exc_info=True)
        return 1


def run_batch(args) -> int:
    """Run batch processing"""
    from dpam.pipeline.batch import run_batch_processing
    
    # Read prefixes
    with open(args.prefix_file, 'r') as f:
        prefixes = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Processing {len(prefixes)} structures")
    
    results = run_batch_processing(
        prefixes=prefixes,
        working_dir=args.working_dir,
        data_dir=args.data_dir,
        cpus_per_structure=args.cpus,
        num_parallel=args.parallel,
        resume=args.resume,
        log_dir=args.log_dir
    )
    
    # Report results
    n_success = sum(1 for r in results if r['success'])
    n_failed = len(results) - n_success
    
    logger.info(f"Batch complete: {n_success} succeeded, {n_failed} failed")
    
    # Write summary
    summary_file = args.working_dir / 'batch_summary.txt'
    with open(summary_file, 'w') as f:
        for result in results:
            status = 'SUCCESS' if result['success'] else 'FAILED'
            f.write(f"{result['prefix']}\t{status}\n")
    
    return 0 if n_failed == 0 else 1


def run_batch_stepwise(args) -> int:
    """Run step-first batch processing (optimized for large batches)"""
    from dpam.pipeline.batch_runner import BatchRunner

    # Read prefixes
    with open(args.prefix_file, 'r') as f:
        proteins = [line.strip() for line in f if line.strip()]

    logger.info(f"Step-first batch processing for {len(proteins)} structures")

    # Parse steps
    steps = None
    if args.steps:
        steps = [PipelineStep[s] for s in args.steps]

    skip_addss = getattr(args, 'skip_addss', False)
    scratch_dir = getattr(args, 'scratch_dir', None)
    dali_workers = getattr(args, 'dali_workers', None)

    try:
        runner = BatchRunner(
            proteins=proteins,
            working_dir=args.working_dir,
            data_dir=args.data_dir,
            cpus=args.cpus,
            resume=args.resume,
            skip_addss=skip_addss,
            scratch_dir=scratch_dir,
            dali_workers=dali_workers
        )

        runner.run(steps=steps)

        # Check for failures
        summary = runner.state.get_summary()
        total_failed = sum(c['failed'] for c in summary.values())
        if total_failed > 0:
            logger.warning(f"Batch completed with {total_failed} step failures")
            return 1
        return 0

    except Exception as e:
        logger.error(f"Batch run failed: {e}", exc_info=True)
        return 1


def submit_slurm(args) -> int:
    """Submit SLURM job array"""
    from dpam.pipeline.slurm import submit_slurm_array
    
    # Read prefixes
    with open(args.prefix_file, 'r') as f:
        prefixes = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Submitting SLURM array for {len(prefixes)} structures")
    
    job_id = submit_slurm_array(
        prefixes=prefixes,
        working_dir=args.working_dir,
        data_dir=args.data_dir,
        cpus_per_task=args.cpus_per_task,
        mem_per_cpu=args.mem_per_cpu,
        time_limit=args.time,
        partition=args.partition,
        array_size=args.array_size
    )
    
    logger.info(f"Submitted job array: {job_id}")
    print(f"Job ID: {job_id}")
    
    return 0


def submit_slurm_batch(args) -> int:
    """Submit single-node step-first SLURM batch job"""
    from dpam.pipeline.slurm import generate_batch_slurm_script, submit_batch_slurm

    with open(args.prefix_file, 'r') as f:
        prefixes = [line.strip() for line in f if line.strip()]

    skip_addss = getattr(args, 'skip_addss', False)
    scratch_dir = getattr(args, 'scratch_dir', None)
    dali_workers = getattr(args, 'dali_workers', None)

    if args.dry_run:
        script = generate_batch_slurm_script(
            prefixes=prefixes,
            working_dir=args.working_dir,
            data_dir=args.data_dir,
            cpus=args.cpus,
            mem=args.mem,
            time_limit=args.time,
            partition=args.partition,
            skip_addss=skip_addss,
            scratch_dir=scratch_dir,
            dali_workers=dali_workers
        )
        script_file = args.working_dir / 'dpam_batch.sh'
        with open(script_file, 'w') as f:
            f.write(script)
        print(f"SLURM script written to {script_file}")
        print(f"Submit with: sbatch {script_file}")
        return 0

    job_id = submit_batch_slurm(
        prefixes=prefixes,
        working_dir=args.working_dir,
        data_dir=args.data_dir,
        cpus=args.cpus,
        mem=args.mem,
        time_limit=args.time,
        partition=args.partition,
        skip_addss=skip_addss,
        scratch_dir=scratch_dir,
        dali_workers=dali_workers
    )

    print(f"Submitted batch job: {job_id}")
    print(f"  Proteins: {len(prefixes)}")
    print(f"  CPUs: {args.cpus}")
    print(f"  Monitor: dpam batch-status --working-dir {args.working_dir}")

    return 0


def show_batch_status(args) -> int:
    """Show batch processing status"""
    import json

    state_file = args.working_dir / '_batch_state.json'
    if not state_file.exists():
        print(f"No batch state found in {args.working_dir}")
        return 1

    with open(state_file) as f:
        state = json.load(f)

    if not state:
        print("Batch state is empty (no steps processed yet)")
        return 0

    # Collect all proteins
    all_proteins = set()
    for step_data in state.values():
        all_proteins.update(step_data.keys())

    print(f"Batch status: {len(all_proteins)} proteins")
    print(f"{'Step':<25} {'Complete':>8} {'Failed':>8} {'Pending':>8}")
    print("-" * 51)

    for step in PipelineStep:
        step_data = state.get(step.name, {})
        if not step_data:
            continue
        complete = sum(1 for s in step_data.values() if s == "complete")
        failed = sum(1 for s in step_data.values()
                     if isinstance(s, str) and s.startswith("failed"))
        pending = len(all_proteins) - complete - failed
        print(f"{step.name:<25} {complete:>8} {failed:>8} {pending:>8}")

    # Show failures if any
    failures = []
    for step_name, step_data in state.items():
        for protein, status in step_data.items():
            if isinstance(status, str) and status.startswith("failed"):
                failures.append((step_name, protein, status))

    if failures:
        print(f"\nFailures ({len(failures)}):")
        for step_name, protein, status in failures[:20]:
            print(f"  {step_name} / {protein}: {status}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")

    return 0


if __name__ == '__main__':
    sys.exit(main())
