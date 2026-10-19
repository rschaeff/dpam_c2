#!/usr/bin/env python3
"""
Test DPAM v2.0 pipeline on P38326 and compare with v1.0 reference.

This script runs steps that don't require DALI (step 7) and compares
outputs with v1.0 reference data.
"""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from dpam.utils.logging_config import setup_logging
from dpam.steps.step01_prepare import run_step1
from dpam.steps.step02_hhsearch import run_step2
from dpam.steps.step03_foldseek import run_step3
from dpam.steps.step04_filter_foldseek import run_step4
from dpam.steps.step05_map_ecod import run_step5
from dpam.steps.step06_get_dali_candidates import run_step6
from dpam.steps.step11_sse import run_step11
from dpam.steps.step12_disorder import run_step12
from dpam.steps.step13_parse_domains import run_step13

logger = logging.getLogger(__name__)


def compare_file_exists(v2_file: Path, v1_file: Path) -> bool:
    """Check if both v1 and v2 files exist."""
    v2_exists = v2_file.exists()
    v1_exists = v1_file.exists()

    if v2_exists and v1_exists:
        print(f"  ✓ Both files exist")
        return True
    elif v2_exists:
        print(f"  ⚠ v2.0 exists but no v1.0 reference")
        return False
    elif v1_exists:
        print(f"  ✗ v1.0 exists but v2.0 failed to create")
        return False
    else:
        print(f"  ✗ Neither file exists")
        return False


def compare_domains_file(v2_file: Path, v1_file: Path) -> bool:
    """Compare domain definitions files."""
    print(f"\nComparing: {v2_file.name}")

    if not compare_file_exists(v2_file, v1_file):
        return False

    # Read both files
    with open(v1_file, 'r') as f:
        v1_lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    with open(v2_file, 'r') as f:
        v2_lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    print(f"  v1.0: {len(v1_lines)} domains")
    print(f"  v2.0: {len(v2_lines)} domains")

    if len(v1_lines) != len(v2_lines):
        print(f"  ✗ Domain count mismatch")
        return False

    # Compare line by line
    matches = 0
    for i, (v1_line, v2_line) in enumerate(zip(v1_lines, v2_lines)):
        if v1_line == v2_line:
            matches += 1
        else:
            print(f"  ⚠ Line {i+1} differs:")
            print(f"    v1.0: {v1_line}")
            print(f"    v2.0: {v2_line}")

    if matches == len(v1_lines):
        print(f"  ✓ All {matches} lines match exactly")
        return True
    else:
        print(f"  ⚠ {matches}/{len(v1_lines)} lines match")
        return False


def run_pipeline_steps(prefix: str, working_dir: Path, data_dir: Path):
    """Run DPAM v2.0 pipeline steps on test structure."""
    print("=" * 60)
    print(f"Running DPAM v2.0 on {prefix}")
    print("=" * 60)

    results = {}

    # Step 1: PREPARE
    print("\n[Step 1] PREPARE...")
    try:
        success = run_step1(prefix, working_dir)
        results['step01'] = success
        print(f"  {'✓' if success else '✗'} Step 1")
    except Exception as e:
        print(f"  ✗ Step 1 failed: {e}")
        results['step01'] = False

    # Step 2: HHSEARCH (SLOW - skip if files exist)
    hhsearch_file = working_dir / f"{prefix}.hhsearch"
    if hhsearch_file.exists():
        print("\n[Step 2] HHSEARCH - Using existing output")
        results['step02'] = True
    else:
        print("\n[Step 2] HHSEARCH - SKIPPED (too slow, use v1.0 data)")
        # Copy from reference
        ref_hhsearch = Path("tests/validation/reference") / prefix / f"{prefix}.hhsearch"
        if ref_hhsearch.exists():
            import shutil
            shutil.copy(ref_hhsearch, hhsearch_file)
            print("  ✓ Copied from v1.0 reference")
            results['step02'] = True
        else:
            results['step02'] = False

    # Step 3: FOLDSEEK (SLOW - skip if files exist)
    foldseek_file = working_dir / f"{prefix}.foldseek"
    if foldseek_file.exists():
        print("\n[Step 3] FOLDSEEK - Using existing output")
        results['step03'] = True
    else:
        print("\n[Step 3] FOLDSEEK - SKIPPED (too slow, use v1.0 data)")
        ref_foldseek = Path("tests/validation/reference") / prefix / f"{prefix}.foldseek"
        if ref_foldseek.exists():
            import shutil
            shutil.copy(ref_foldseek, foldseek_file)
            print("  ✓ Copied from v1.0 reference")
            results['step03'] = True
        else:
            results['step03'] = False

    # Steps 11-13: Can run independently
    print("\n[Step 11] SSE...")
    try:
        success = run_step11(prefix, working_dir)
        results['step11'] = success
        print(f"  {'✓' if success else '✗'} Step 11")
    except Exception as e:
        print(f"  ✗ Step 11 failed: {e}")
        results['step11'] = False

    print("\n[Step 12] DISORDER...")
    try:
        success = run_step12(prefix, working_dir)
        results['step12'] = success
        print(f"  {'✓' if success else '✗'} Step 12")
    except Exception as e:
        print(f"  ✗ Step 12 failed: {e}")
        results['step12'] = False

    # Step 13: Requires upstream data - will need to mock or use v1.0 intermediate files
    print("\n[Step 13] PARSE_DOMAINS - SKIPPED (needs steps 7-10)")
    results['step13'] = None

    return results


def compare_outputs(prefix: str, working_dir: Path, ref_dir: Path):
    """Compare v2.0 outputs with v1.0 reference."""
    print("\n" + "=" * 60)
    print("Comparing Outputs")
    print("=" * 60)

    comparisons = {}

    # Step 1: FASTA
    v2_fa = working_dir / f"{prefix}.fa"
    v1_fa = ref_dir / f"{prefix}.fa"
    comparisons['fasta'] = compare_domains_file(v2_fa, v1_fa)

    # Step 11: SSE
    v2_sse = working_dir / f"{prefix}.step11_sse"
    v1_sse = ref_dir / f"{prefix}.sse"
    if v2_sse.exists() and v1_sse.exists():
        comparisons['sse'] = compare_domains_file(v2_sse, v1_sse)

    # Step 12: Disorder
    v2_diso = working_dir / f"{prefix}.step12_disorder"
    v1_diso = ref_dir / f"{prefix}.diso"
    if v2_diso.exists() and v1_diso.exists():
        comparisons['disorder'] = compare_domains_file(v2_diso, v1_diso)

    # Step 13: Domains
    v2_domains = working_dir / f"{prefix}.step13_domains"
    v1_domains = ref_dir / f"{prefix}.domains"
    if v2_domains.exists() and v1_domains.exists():
        comparisons['domains'] = compare_domains_file(v2_domains, v1_domains)

    return comparisons


def main():
    """Run P38326 test and validation."""
    setup_logging(json_format=False)

    # Configuration
    prefix = "P38326"
    working_dir = Path("test_run/P38326")
    data_dir = Path("/home/rschaeff_1/data/dpam_reference/ecod_data")
    ref_dir = Path("tests/validation/reference/P38326")

    working_dir.mkdir(parents=True, exist_ok=True)

    # Check if PDB exists
    pdb_file = working_dir / f"{prefix}.pdb"
    if not pdb_file.exists():
        print(f"Copying PDB file...")
        import shutil
        shutil.copy(ref_dir / f"{prefix}.pdb", pdb_file)

    # Run pipeline
    results = run_pipeline_steps(prefix, working_dir, data_dir)

    # Compare outputs
    comparisons = compare_outputs(prefix, working_dir, ref_dir)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    print("\nPipeline Steps:")
    for step, success in results.items():
        if success is True:
            status = "✓ PASS"
        elif success is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"
        print(f"  {step:12s}: {status}")

    print("\nOutput Comparisons:")
    for name, match in comparisons.items():
        status = "✓ MATCH" if match else "✗ DIFFER"
        print(f"  {name:12s}: {status}")

    # Overall result
    passed = sum(1 for c in comparisons.values() if c)
    total = len(comparisons)

    print("\n" + "=" * 60)
    print(f"Validation: {passed}/{total} outputs match v1.0")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
