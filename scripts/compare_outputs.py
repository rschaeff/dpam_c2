#!/usr/bin/env python3
"""
Compare dpam_c2 outputs with DPAM v1.0 outputs (without running pipeline).

Use this when you already have outputs from both versions and just want to compare them.

Usage:
    python compare_outputs.py protein_id v1_dir v2_dir [--report report.txt]

Example:
    python compare_outputs.py AF-P12345 \\
        /work/dpam_v1/AF-P12345 \\
        /work/dpam_c2/AF-P12345 \\
        --report comparison.txt
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import difflib

# Import validation functions from validate_against_v1
from validate_against_v1 import (
    STEP_FILES,
    ValidationResult,
    compare_text_files,
    compare_numeric_files,
    validate_step,
    generate_report
)


def compare_all_steps(
    prefix: str,
    v1_dir: Path,
    v2_dir: Path,
    verbose: bool = True
) -> List[ValidationResult]:
    """
    Compare outputs for all steps.

    Args:
        prefix: Protein prefix
        v1_dir: DPAM v1.0 output directory
        v2_dir: dpam_c2 output directory
        verbose: Print progress

    Returns:
        List of ValidationResult objects
    """
    results = []

    # Numeric file patterns
    numeric_patterns = [
        '.hhsearch', '.foldseek', '.predictions', '.step23_predictions'
    ]

    if verbose:
        print(f"Comparing outputs for {prefix}")
        print(f"V1 directory: {v1_dir}")
        print(f"V2 directory: {v2_dir}")
        print()

    for step_name in STEP_FILES.keys():
        if verbose:
            print(f"  Checking {step_name}...", end=' ')

        result = validate_step(
            step_name,
            prefix,
            v1_dir,
            v2_dir,
            numeric_patterns
        )

        results.append(result)

        if verbose:
            if result.is_success():
                print(f"✅ {result.files_matched} files matched")
            else:
                print(f"❌ {len(result.critical_errors)} critical errors")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Compare dpam_c2 and DPAM v1.0 outputs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('protein', type=str, help='Protein ID (e.g., AF-P12345)')
    parser.add_argument('v1_dir', type=Path, help='DPAM v1.0 output directory')
    parser.add_argument('v2_dir', type=Path, help='dpam_c2 output directory')
    parser.add_argument('--report', type=Path, default='comparison_report.txt', help='Output report file')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')

    args = parser.parse_args()

    # Run comparison
    results = compare_all_steps(
        args.protein,
        args.v1_dir,
        args.v2_dir,
        verbose=not args.quiet
    )

    # Generate report
    generate_report(results, args.report)

    # Print summary
    passed = sum(1 for r in results if r.is_success())
    total = len(results)

    print(f"\nSummary: {passed}/{total} steps passed")
    print(f"Report written to: {args.report}")

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
