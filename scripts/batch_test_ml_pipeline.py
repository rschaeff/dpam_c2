#!/usr/bin/env python3
"""
Batch Test ML Pipeline (Steps 15-24)

Test the ML pipeline on multiple validation proteins and generate a comprehensive report.
"""

import sys
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import time

# Add dpam to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dpam.steps.step15_prepare_domass import run_step15
from dpam.steps.step16_run_domass import run_step16
from dpam.steps.step17_get_confident import run_step17
from dpam.steps.step18_get_mapping import run_step18
from dpam.steps.step19_get_merge_candidates import run_step19
from dpam.steps.step20_extract_domains import run_step20
from dpam.steps.step21_compare_domains import run_step21
from dpam.steps.step22_merge_domains import run_step22
from dpam.steps.step23_get_predictions import run_step23
from dpam.steps.step24_integrate_results import run_step24

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def count_lines(file_path: Path) -> int:
    """Count lines in file (excluding header)."""
    if not file_path.exists():
        return 0

    with open(file_path, 'r') as f:
        lines = [l for l in f if not l.startswith('#')]
        return max(0, len(lines) - 1)  # Subtract header


def get_final_domains(file_path: Path) -> List[str]:
    """Get final domain definitions."""
    if not file_path.exists():
        return []

    domains = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                domains.append(line.strip())

    return domains


def run_ml_pipeline(
    prefix: str,
    working_dir: Path,
    data_dir: Path
) -> Tuple[bool, Dict[str, any]]:
    """
    Run complete ML pipeline (steps 15-24) on a single protein.

    Returns:
        (success, stats_dict)
    """
    stats = {
        'prefix': prefix,
        'step_results': {},
        'step_times': {},
        'feature_count': 0,
        'prediction_count': 0,
        'confident_count': 0,
        'mapping_count': 0,
        'merge_count': 0,
        'final_domain_count': 0,
        'final_domains': [],
        'error': None
    }

    steps = [
        (15, 'PREPARE_DOMASS', run_step15, True),   # needs data_dir
        (16, 'RUN_DOMASS', run_step16, True),
        (17, 'GET_CONFIDENT', run_step17, False),
        (18, 'GET_MAPPING', run_step18, True),
        (19, 'GET_MERGE_CANDIDATES', run_step19, True),
        (20, 'EXTRACT_DOMAINS', run_step20, False),
        (21, 'COMPARE_DOMAINS', run_step21, False),
        (22, 'MERGE_DOMAINS', run_step22, False),
        (23, 'GET_PREDICTIONS', run_step23, True),
        (24, 'INTEGRATE_RESULTS', run_step24, True),
    ]

    try:
        for step_num, step_name, step_func, needs_data_dir in steps:
            start_time = time.time()

            try:
                if needs_data_dir:
                    result = step_func(prefix, working_dir, data_dir)
                else:
                    result = step_func(prefix, working_dir)

                elapsed = time.time() - start_time
                stats['step_results'][step_name] = result
                stats['step_times'][step_name] = elapsed

                if not result:
                    logger.warning(f"  Step {step_num} ({step_name}) returned False")

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"  Step {step_num} ({step_name}) failed: {e}")
                stats['step_results'][step_name] = False
                stats['step_times'][step_name] = elapsed
                stats['error'] = f"Step {step_num} failed: {str(e)}"
                return False, stats

        # Collect output statistics
        stats['feature_count'] = count_lines(working_dir / f"{prefix}.step15_features")
        stats['prediction_count'] = count_lines(working_dir / f"{prefix}.step16_predictions")
        stats['confident_count'] = count_lines(working_dir / f"{prefix}.step17_confident_predictions")
        stats['mapping_count'] = count_lines(working_dir / f"{prefix}.step18_mappings")
        stats['merge_count'] = count_lines(working_dir / f"{prefix}.step19_merge_candidates")

        final_domains = get_final_domains(working_dir / f"{prefix}.finalDPAM.domains")
        stats['final_domain_count'] = len(final_domains)
        stats['final_domains'] = final_domains

        return True, stats

    except Exception as e:
        logger.error(f"Pipeline failed for {prefix}: {e}")
        stats['error'] = str(e)
        return False, stats


def main():
    """Run batch testing on all validation proteins."""

    # Configuration
    validation_dir = Path('validation/working')
    data_dir = Path('/home/rschaeff_1/data/dpam_reference/ecod_data')

    # Find all validation proteins
    protein_dirs = sorted([d for d in validation_dir.iterdir() if d.is_dir()])

    logger.info(f"Found {len(protein_dirs)} validation proteins")
    logger.info(f"Data directory: {data_dir}")
    logger.info("")

    # Run ML pipeline on each protein
    results = []
    success_count = 0

    for i, protein_dir in enumerate(protein_dirs, 1):
        prefix = f"AF-{protein_dir.name}"

        logger.info(f"[{i}/{len(protein_dirs)}] Processing {prefix}...")

        start_time = time.time()
        success, stats = run_ml_pipeline(prefix, protein_dir, data_dir)
        total_time = time.time() - start_time

        stats['total_time'] = total_time
        results.append(stats)

        if success:
            success_count += 1
            logger.info(f"  ✓ Success ({total_time:.1f}s)")
            logger.info(f"    Features: {stats['feature_count']}, "
                       f"Predictions: {stats['prediction_count']}, "
                       f"Confident: {stats['confident_count']}, "
                       f"Final domains: {stats['final_domain_count']}")
        else:
            logger.error(f"  ✗ Failed ({total_time:.1f}s): {stats['error']}")

        logger.info("")

    # Generate summary report
    logger.info("=" * 80)
    logger.info("BATCH TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total proteins: {len(results)}")
    logger.info(f"Successful: {success_count}/{len(results)} ({100*success_count/len(results):.1f}%)")
    logger.info(f"Failed: {len(results) - success_count}/{len(results)}")
    logger.info("")

    # Step-by-step success rates
    logger.info("Step Success Rates:")
    step_names = ['PREPARE_DOMASS', 'RUN_DOMASS', 'GET_CONFIDENT', 'GET_MAPPING',
                  'GET_MERGE_CANDIDATES', 'EXTRACT_DOMAINS', 'COMPARE_DOMAINS',
                  'MERGE_DOMAINS', 'GET_PREDICTIONS', 'INTEGRATE_RESULTS']

    for step_name in step_names:
        step_success = sum(1 for r in results if r['step_results'].get(step_name, False))
        logger.info(f"  {step_name:25s}: {step_success}/{len(results)} ({100*step_success/len(results):.1f}%)")

    logger.info("")

    # Output statistics
    logger.info("Output Statistics (successful runs only):")
    successful = [r for r in results if all(r['step_results'].values())]

    if successful:
        avg_features = sum(r['feature_count'] for r in successful) / len(successful)
        avg_predictions = sum(r['prediction_count'] for r in successful) / len(successful)
        avg_confident = sum(r['confident_count'] for r in successful) / len(successful)
        avg_mappings = sum(r['mapping_count'] for r in successful) / len(successful)
        avg_merges = sum(r['merge_count'] for r in successful) / len(successful)
        avg_domains = sum(r['final_domain_count'] for r in successful) / len(successful)
        avg_time = sum(r['total_time'] for r in successful) / len(successful)

        logger.info(f"  Average features: {avg_features:.1f}")
        logger.info(f"  Average predictions: {avg_predictions:.1f}")
        logger.info(f"  Average confident: {avg_confident:.1f}")
        logger.info(f"  Average mappings: {avg_mappings:.1f}")
        logger.info(f"  Average merge candidates: {avg_merges:.1f}")
        logger.info(f"  Average final domains: {avg_domains:.1f}")
        logger.info(f"  Average processing time: {avg_time:.1f}s")

    logger.info("")

    # Detailed results table
    logger.info("Detailed Results:")
    logger.info(f"{'Protein':<12} {'Features':>8} {'Predictions':>12} {'Confident':>10} "
               f"{'Mappings':>9} {'Merges':>7} {'Domains':>8} {'Time':>7} {'Status':<10}")
    logger.info("-" * 100)

    for r in results:
        protein = r['prefix'].replace('AF-', '')
        status = "✓ OK" if all(r['step_results'].values()) else "✗ FAIL"
        logger.info(f"{protein:<12} {r['feature_count']:>8} {r['prediction_count']:>12} "
                   f"{r['confident_count']:>10} {r['mapping_count']:>9} "
                   f"{r['merge_count']:>7} {r['final_domain_count']:>8} "
                   f"{r['total_time']:>6.1f}s {status:<10}")

    logger.info("")

    # Failed proteins details
    failed = [r for r in results if not all(r['step_results'].values())]
    if failed:
        logger.info("Failed Proteins:")
        for r in failed:
            logger.info(f"  {r['prefix']}: {r['error']}")
            failed_steps = [k for k, v in r['step_results'].items() if not v]
            if failed_steps:
                logger.info(f"    Failed steps: {', '.join(failed_steps)}")
        logger.info("")

    # Write detailed report to file
    report_file = Path('validation/ml_pipeline_batch_test_report.txt')
    with open(report_file, 'w') as f:
        f.write("ML Pipeline Batch Test Report\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total proteins: {len(results)}\n")
        f.write(f"Successful: {success_count}/{len(results)} ({100*success_count/len(results):.1f}%)\n")
        f.write(f"Failed: {len(results) - success_count}/{len(results)}\n\n")

        f.write("Per-Protein Results:\n")
        f.write("-" * 80 + "\n")

        for r in results:
            f.write(f"\n{r['prefix']}:\n")
            f.write(f"  Total time: {r['total_time']:.2f}s\n")
            f.write(f"  Features: {r['feature_count']}\n")
            f.write(f"  Predictions: {r['prediction_count']}\n")
            f.write(f"  Confident: {r['confident_count']}\n")
            f.write(f"  Mappings: {r['mapping_count']}\n")
            f.write(f"  Merge candidates: {r['merge_count']}\n")
            f.write(f"  Final domains: {r['final_domain_count']}\n")

            if r['final_domains']:
                f.write(f"  Domain definitions:\n")
                for domain in r['final_domains']:
                    f.write(f"    {domain}\n")

            f.write(f"  Step results:\n")
            for step, result in r['step_results'].items():
                status = "✓" if result else "✗"
                time_str = f"{r['step_times'].get(step, 0):.2f}s"
                f.write(f"    {status} {step}: {time_str}\n")

            if r['error']:
                f.write(f"  ERROR: {r['error']}\n")

    logger.info(f"Detailed report written to: {report_file}")
    logger.info("")

    return 0 if success_count == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
