#!/usr/bin/env python3
"""
Validate dpam_c2 against DPAM v1.0 (dpam_automatic).

Runs dpam_c2 on test proteins and compares outputs with v1.0 reference data
to identify any differences. Generates a detailed validation report.

Usage:
    python validate_against_v1.py proteins.txt v1_output_dir v2_working_dir \\
        --data-dir /path/to/ecod_data \\
        --report validation_report.txt

Arguments:
    proteins.txt: File with one protein ID per line (e.g., AF-P12345)
    v1_output_dir: Directory containing DPAM v1.0 reference outputs
    v2_working_dir: Directory where dpam_c2 will write outputs
    --data-dir: ECOD reference data directory
    --report: Output report file (default: validation_report.txt)
    --stop-on-error: Stop at first major difference
    --steps: Comma-separated list of steps to validate (default: all)

Example:
    python validate_against_v1.py test_proteins.txt \\
        /work/dpam_v1_outputs \\
        /work/dpam_c2_outputs \\
        --data-dir /data/ecod_data \\
        --report validation_report.txt
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import difflib
import json
from datetime import datetime

# Add parent directory to path for dpam imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dpam.pipeline.runner import DPAMPipeline
from dpam.core.models import PipelineStep


class ValidationResult:
    """Container for validation results."""

    def __init__(self, step: str, protein: str):
        self.step = step
        self.protein = protein
        self.files_compared = 0
        self.files_matched = 0
        self.files_differed = 0
        self.files_missing_v1 = 0
        self.files_missing_v2 = 0
        self.differences = []  # List of (file, diff_type, details)
        self.critical_errors = []

    def add_match(self, filename: str):
        self.files_compared += 1
        self.files_matched += 1

    def add_difference(self, filename: str, diff_type: str, details: str, critical: bool = False):
        self.files_compared += 1
        self.files_differed += 1
        self.differences.append((filename, diff_type, details))
        if critical:
            self.critical_errors.append((filename, diff_type, details))

    def add_missing_v1(self, filename: str):
        self.files_missing_v1 += 1

    def add_missing_v2(self, filename: str):
        self.files_missing_v2 += 1

    def is_success(self) -> bool:
        """Check if validation passed (no critical errors)."""
        return len(self.critical_errors) == 0

    def summary(self) -> str:
        """Generate summary string."""
        status = "✅ PASS" if self.is_success() else "❌ FAIL"
        return (
            f"{status} - {self.step} ({self.protein}): "
            f"{self.files_matched}/{self.files_compared} matched, "
            f"{self.files_differed} differed, "
            f"{self.files_missing_v2} missing in v2, "
            f"{len(self.critical_errors)} critical"
        )


# File patterns to compare for each step
# Maps dpam_c2 step names to (v1_files, v2_files) tuples
# v1.0 uses bare UniProt IDs (e.g., A0A024R1R8)
# dpam_c2 uses full AF- prefix (e.g., AF-A0A024R1R8-F1)
STEP_FILES = {
    # v1.0 Steps 1-2 → dpam_c2 Step 1 (PREPARE)
    'PREPARE': {
        'v1': ['{v1_prefix}.fa', '{v1_prefix}.pdb'],
        'v2': ['{v2_prefix}.fasta', '{v2_prefix}.pdb'],
    },
    # v1.0 Step 3 → dpam_c2 Step 2 (HHSEARCH)
    'HHSEARCH': {
        'v1': ['{v1_prefix}.hhsearch'],
        'v2': ['{v2_prefix}.hhsearch'],
    },
    # v1.0 Step 4 → dpam_c2 Step 3 (FOLDSEEK)
    'FOLDSEEK': {
        'v1': ['{v1_prefix}.foldseek'],
        'v2': ['{v2_prefix}.foldseek'],
    },
    # v1.0 Steps 5-6 → dpam_c2 Step 5 (MAP_ECOD)
    'MAP_ECOD': {
        'v1': ['{v1_prefix}_sequence.result', '{v1_prefix}_structure.result'],
        'v2': ['{v2_prefix}.map2ecod.result'],  # v2 merges both
    },
    # v1.0 Step 7 → dpam_c2 Step 6 (DALI_CANDIDATES)
    'DALI_CANDIDATES': {
        'v1': ['{v1_prefix}_good_hits'],
        'v2': ['{v2_prefix}_good_hits'],
    },
    # v1.0 Step 8 → dpam_c2 Step 7 (ITERATIVE_DALI)
    'ITERATIVE_DALI': {
        'v1': ['{v1_prefix}_hits'],
        'v2': ['{v2_prefix}_iterativdDali_hits'],
    },
    # v1.0 Step 9 → dpam_c2 Step 8 (ANALYZE_DALI)
    'ANALYZE_DALI': {
        'v1': ['{v1_prefix}_good_hits'],
        'v2': ['{v2_prefix}_good_hits'],
    },
    # v1.0 Step 10 → dpam_c2 Step 9 (GET_SUPPORT)
    'GET_SUPPORT': {
        'v1': ['{v1_prefix}_sequence.result', '{v1_prefix}_structure.result'],
        'v2': ['{v2_prefix}.support.result'],  # If v2 outputs this
    },
    # v1.0 Step 11 → dpam_c2 Step 10 (FILTER_DOMAINS)
    'FILTER_DOMAINS': {
        'v1': ['{v1_prefix}.goodDomains'],
        'v2': ['{v2_prefix}.goodDomains'],
    },
    # v1.0 Step 12 → dpam_c2 Step 11 (SSE)
    'SSE': {
        'v1': ['{v1_prefix}.sse'],
        'v2': ['{v2_prefix}.sse'],
    },
    # v1.0 Step 13 → dpam_c2 Step 12 (DISORDER)
    'DISORDER': {
        'v1': ['{v1_prefix}.diso'],
        'v2': ['{v2_prefix}.diso'],
    },
    # v1.0 Step 14 → dpam_c2 Step 13 (PARSE_DOMAINS)
    'PARSE_DOMAINS': {
        'v1': ['{v1_prefix}.domains'],
        'v2': ['{v2_prefix}.step13_domains', '{v2_prefix}.finalDPAM.domains'],
    },
    # v1.0 Step 15 → dpam_c2 Step 15 (PREPARE_DOMASS)
    'PREPARE_DOMASS': {
        'v1': ['{v1_prefix}.data'],
        'v2': ['{v2_prefix}.domass_features'],
    },
    # v1.0 Step 16 → dpam_c2 Step 16 (RUN_DOMASS)
    'RUN_DOMASS': {
        'v1': ['{v1_prefix}.result'],  # step16 .result file
        'v2': ['{v2_prefix}.step16_predictions'],
    },
    # v1.0 Step 17 → dpam_c2 Step 17 (GET_CONFIDENT)
    'GET_CONFIDENT': {
        'v1': ['{v1_prefix}.result'],  # step17 .result file
        'v2': ['{v2_prefix}.step17_confident'],
    },
    # v1.0 Step 18 → dpam_c2 Step 18 (GET_MAPPING)
    'GET_MAPPING': {
        'v1': ['{v1_prefix}.data'],  # step18 .data file
        'v2': ['{v2_prefix}.step18_mappings'],
    },
    # v1.0 Step 19 → dpam_c2 Step 19 (GET_MERGE_CANDIDATES)
    'GET_MERGE_CANDIDATES': {
        'v1': ['{v1_prefix}.result'],  # step19 .result file
        'v2': ['{v2_prefix}.step19_merge_candidates'],
    },
    # v1.0 Step 23 → dpam_c2 Step 23 (GET_PREDICTIONS)
    'GET_PREDICTIONS': {
        'v1': ['{v1_prefix}.assign'],
        'v2': ['{v2_prefix}.step23_predictions'],
    },
    # v1.0 Step 24 → dpam_c2 Step 24 (INTEGRATE_RESULTS)
    'INTEGRATE_RESULTS': {
        'v1': ['{v1_prefix}_domains'],
        'v2': ['{v2_prefix}.finalDPAM.domains'],
    },
}


def convert_protein_id(full_id: str) -> str:
    """
    Convert full AlphaFold ID to bare UniProt ID for v1.0 compatibility.

    Args:
        full_id: Full ID like 'AF-A0A024R1R8-F1'

    Returns:
        Bare UniProt ID like 'A0A024R1R8'
    """
    # Remove AF- prefix and -F1 suffix
    if full_id.startswith('AF-'):
        bare_id = full_id[3:]  # Remove 'AF-'
        if '-F' in bare_id:
            bare_id = bare_id[:bare_id.rfind('-F')]  # Remove '-F1'
        return bare_id
    return full_id


def compare_text_files(v1_file: Path, v2_file: Path, ignore_whitespace: bool = False) -> Tuple[bool, str]:
    """
    Compare two text files.

    Returns:
        (is_identical, diff_summary)
    """
    if not v1_file.exists():
        return False, f"V1 file missing: {v1_file}"
    if not v2_file.exists():
        return False, f"V2 file missing: {v2_file}"

    with open(v1_file) as f1, open(v2_file) as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    if ignore_whitespace:
        lines1 = [line.strip() + '\n' for line in lines1]
        lines2 = [line.strip() + '\n' for line in lines2]

    if lines1 == lines2:
        return True, "Identical"

    # Generate diff summary
    differ = difflib.unified_diff(
        lines1, lines2,
        fromfile=str(v1_file),
        tofile=str(v2_file),
        n=0  # No context lines
    )

    diff_lines = list(differ)
    num_changes = sum(1 for line in diff_lines if line.startswith(('+', '-')))

    # Classify difference
    if len(lines1) != len(lines2):
        diff_type = f"Line count differs: v1={len(lines1)}, v2={len(lines2)}"
    elif num_changes < 10:
        diff_type = f"Minor differences: {num_changes} line changes"
    else:
        diff_type = f"Major differences: {num_changes} line changes"

    # Include first few diff lines
    sample = ''.join(diff_lines[:20])

    return False, f"{diff_type}\n{sample}"


def compare_numeric_files(v1_file: Path, v2_file: Path, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """
    Compare files with numeric data (allows small floating-point differences).

    Returns:
        (is_identical, diff_summary)
    """
    if not v1_file.exists() or not v2_file.exists():
        return compare_text_files(v1_file, v2_file)

    with open(v1_file) as f1, open(v2_file) as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    if len(lines1) != len(lines2):
        return False, f"Line count differs: v1={len(lines1)}, v2={len(lines2)}"

    differences = []
    for i, (line1, line2) in enumerate(zip(lines1, lines2)):
        if line1 == line2:
            continue

        # Try numeric comparison
        words1 = line1.split()
        words2 = line2.split()

        if len(words1) != len(words2):
            differences.append(f"Line {i+1}: word count differs")
            continue

        numeric_diff = False
        for w1, w2 in zip(words1, words2):
            if w1 == w2:
                continue
            try:
                val1 = float(w1)
                val2 = float(w2)
                if abs(val1 - val2) > tolerance:
                    differences.append(f"Line {i+1}: {w1} vs {w2} (diff={abs(val1-val2):.2e})")
                    numeric_diff = True
            except ValueError:
                # Not numeric, must match exactly
                differences.append(f"Line {i+1}: '{w1}' vs '{w2}'")

    if not differences:
        return True, "Identical (within tolerance)"

    summary = f"{len(differences)} differences found:\n" + '\n'.join(differences[:10])
    if len(differences) > 10:
        summary += f"\n... and {len(differences) - 10} more"

    return False, summary


def validate_step(
    step_name: str,
    v2_prefix: str,
    v1_protein_dir: Path,
    v2_dir: Path,
    numeric_files: List[str] = None
) -> ValidationResult:
    """
    Validate a single step by comparing output files.

    Args:
        step_name: Step name (e.g., 'HHSEARCH')
        v2_prefix: dpam_c2 protein prefix (e.g., 'AF-A0A024R1R8-F1')
        v1_protein_dir: v1.0 protein-specific directory (e.g., v1_outputs/AF-A0A024R1R8-F1/)
        v2_dir: dpam_c2 working directory
        numeric_files: List of file extensions that contain numeric data

    Returns:
        ValidationResult object
    """
    result = ValidationResult(step_name, v2_prefix)

    if step_name not in STEP_FILES:
        result.add_difference(step_name, 'ERROR', 'Unknown step', critical=True)
        return result

    # Get v1.0 prefix (bare UniProt ID)
    v1_prefix = convert_protein_id(v2_prefix)

    numeric_files = numeric_files or []
    step_patterns = STEP_FILES[step_name]

    v1_patterns = step_patterns['v1']
    v2_patterns = step_patterns['v2']

    # Handle cases where v1 and v2 have different numbers of files
    # E.g., MAP_ECOD: v1 has 2 files (_sequence.result, _structure.result)
    #                 v2 has 1 file (.map2ecod.result)

    if len(v1_patterns) == len(v2_patterns):
        # 1:1 mapping - compare files directly
        file_pairs = list(zip(v1_patterns, v2_patterns))
    elif len(v1_patterns) > len(v2_patterns):
        # v1 has more files (e.g., MAP_ECOD) - check all v1 files exist
        # but only compare first v2 file
        file_pairs = []
        for i, v1_pattern in enumerate(v1_patterns):
            if i < len(v2_patterns):
                file_pairs.append((v1_pattern, v2_patterns[i]))
            else:
                # Check v1 file exists but don't compare (no v2 equivalent)
                file_pairs.append((v1_pattern, None))
    else:
        # v2 has more files - compare what we can
        file_pairs = list(zip(v1_patterns, v2_patterns[:len(v1_patterns)]))

    for v1_pattern, v2_pattern in file_pairs:
        v1_filename = v1_pattern.format(v1_prefix=v1_prefix)
        v1_file = v1_protein_dir / v1_filename

        # Check v1 file exists
        if not v1_file.exists():
            result.add_missing_v1(v1_filename)
            continue

        # If no v2 equivalent, just note v1 file exists
        if v2_pattern is None:
            result.add_match(f"{v1_filename} (v1 only)")
            continue

        v2_filename = v2_pattern.format(v2_prefix=v2_prefix)
        v2_file = v2_dir / v2_filename

        # Check v2 file exists
        if not v2_file.exists():
            result.add_missing_v2(v2_filename)
            # Critical if v1 has output but v2 doesn't
            result.add_difference(
                v2_filename,
                'MISSING_V2',
                f'File exists in v1 ({v1_filename}) but not v2',
                critical=True
            )
            continue

        # Compare files
        is_numeric = any(ext in v2_filename for ext in numeric_files)
        if is_numeric:
            is_match, diff = compare_numeric_files(v1_file, v2_file)
        else:
            is_match, diff = compare_text_files(v1_file, v2_file)

        if is_match:
            result.add_match(f"{v1_filename} ↔ {v2_filename}")
        else:
            # Determine if critical based on diff type
            critical = (
                'MISSING' in diff or
                ('Line count differs' in diff and 'v1=0' not in diff and 'v2=0' not in diff) or
                'Major differences' in diff
            )
            result.add_difference(
                f"{v1_filename} ↔ {v2_filename}",
                'CONTENT_DIFF',
                diff,
                critical=critical
            )

    return result


def run_validation(
    protein_file: Path,
    v1_dir: Path,
    v2_dir: Path,
    data_dir: Path,
    steps: Optional[List[str]] = None,
    stop_on_error: bool = False
) -> List[ValidationResult]:
    """
    Run validation for multiple proteins.

    Args:
        protein_file: File with protein IDs
        v1_dir: DPAM v1.0 output directory
        v2_dir: dpam_c2 working directory
        data_dir: ECOD reference data directory
        steps: List of step names to validate (None = all)
        stop_on_error: Stop at first critical error

    Returns:
        List of ValidationResult objects
    """
    # Read protein list
    with open(protein_file) as f:
        proteins = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Validating {len(proteins)} proteins against DPAM v1.0")
    print(f"V1 directory: {v1_dir}")
    print(f"V2 directory: {v2_dir}")
    print(f"Data directory: {data_dir}")
    print()

    # Determine steps to validate
    if steps is None:
        step_names = list(STEP_FILES.keys())
    else:
        step_names = steps

    # Numeric file patterns (use tolerance for comparison)
    numeric_patterns = [
        '.hhsearch', '.foldseek', '.predictions', '.step23_predictions'
    ]

    all_results = []

    for protein in proteins:
        print(f"\n{'='*60}")
        print(f"Validating: {protein}")
        print(f"{'='*60}")

        # Run dpam_c2
        print(f"\n[1] Running dpam_c2...")
        pipeline = DPAMPipeline(
            working_dir=v2_dir,
            data_dir=data_dir,
            cpus=4
        )

        try:
            success = pipeline.run(protein)
            if not success:
                print(f"❌ dpam_c2 failed for {protein}")
                continue
        except Exception as e:
            print(f"❌ dpam_c2 error for {protein}: {e}")
            continue

        print(f"✅ dpam_c2 completed successfully")

        # Compare each step
        print(f"\n[2] Comparing outputs with v1.0...")

        # v1.0 outputs are in protein-specific subdirectory
        v1_protein_dir = v1_dir / protein

        if not v1_protein_dir.exists():
            print(f"  ⚠️  v1.0 reference directory not found: {v1_protein_dir}")
            print(f"  Skipping validation for {protein}")
            continue

        for step_name in step_names:
            result = validate_step(
                step_name,
                protein,
                v1_protein_dir,
                v2_dir,
                numeric_patterns
            )

            all_results.append(result)
            print(f"  {result.summary()}")

            # Show details if there are differences
            if result.files_differed > 0:
                for filename, diff_type, details in result.differences[:3]:
                    print(f"    - {filename}: {diff_type}")
                    if '\n' in details:
                        # Truncate multi-line details
                        first_line = details.split('\n')[0]
                        print(f"      {first_line}")
                    else:
                        print(f"      {details}")

            # Stop on critical error if requested
            if stop_on_error and not result.is_success():
                print(f"\n❌ Critical error in {step_name} - stopping validation")
                return all_results

    return all_results


def generate_report(results: List[ValidationResult], report_file: Path):
    """
    Generate detailed validation report.

    Args:
        results: List of ValidationResult objects
        report_file: Output report file
    """
    with open(report_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("DPAM v2.0 Validation Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")

        # Summary statistics
        total_steps = len(results)
        passed_steps = sum(1 for r in results if r.is_success())
        failed_steps = total_steps - passed_steps

        total_files = sum(r.files_compared for r in results)
        matched_files = sum(r.files_matched for r in results)
        differed_files = sum(r.files_differed for r in results)

        f.write("SUMMARY\n")
        f.write("-"*80 + "\n")
        f.write(f"Total steps validated: {total_steps}\n")
        f.write(f"Passed (no critical errors): {passed_steps} ({passed_steps/total_steps*100:.1f}%)\n")
        f.write(f"Failed (critical errors): {failed_steps} ({failed_steps/total_steps*100:.1f}%)\n")
        f.write(f"\n")
        f.write(f"Total files compared: {total_files}\n")
        f.write(f"Matched: {matched_files} ({matched_files/total_files*100:.1f}%)\n")
        f.write(f"Differed: {differed_files} ({differed_files/total_files*100:.1f}%)\n")
        f.write("\n\n")

        # Group by protein
        proteins = sorted(set(r.protein for r in results))

        for protein in proteins:
            protein_results = [r for r in results if r.protein == protein]

            f.write(f"PROTEIN: {protein}\n")
            f.write("-"*80 + "\n")

            for result in protein_results:
                f.write(f"\n{result.summary()}\n")

                if result.differences:
                    f.write(f"\nDifferences:\n")
                    for filename, diff_type, details in result.differences:
                        f.write(f"  - {filename} ({diff_type})\n")
                        # Indent details
                        for line in details.split('\n'):
                            if line:
                                f.write(f"    {line}\n")

                if result.files_missing_v2 > 0:
                    f.write(f"\nMissing in v2: {result.files_missing_v2} files\n")

            f.write("\n\n")

        # Critical errors section
        critical_results = [r for r in results if not r.is_success()]
        if critical_results:
            f.write("CRITICAL ERRORS\n")
            f.write("-"*80 + "\n\n")

            for result in critical_results:
                f.write(f"{result.protein} - {result.step}:\n")
                for filename, diff_type, details in result.critical_errors:
                    f.write(f"  ❌ {filename}: {diff_type}\n")
                    f.write(f"     {details}\n")
                f.write("\n")

    print(f"\n✅ Report written to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate dpam_c2 against DPAM v1.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('proteins', type=Path, help='File with protein IDs (one per line)')
    parser.add_argument('v1_dir', type=Path, help='DPAM v1.0 output directory')
    parser.add_argument('v2_dir', type=Path, help='dpam_c2 working directory')
    parser.add_argument('--data-dir', type=Path, required=True, help='ECOD reference data directory')
    parser.add_argument('--report', type=Path, default='validation_report.txt', help='Output report file')
    parser.add_argument('--stop-on-error', action='store_true', help='Stop at first critical error')
    parser.add_argument('--steps', type=str, help='Comma-separated list of steps to validate')

    args = parser.parse_args()

    # Parse steps
    steps = None
    if args.steps:
        steps = [s.strip() for s in args.steps.split(',')]

    # Run validation
    results = run_validation(
        args.proteins,
        args.v1_dir,
        args.v2_dir,
        args.data_dir,
        steps=steps,
        stop_on_error=args.stop_on_error
    )

    # Generate report
    generate_report(results, args.report)

    # Exit code
    failed = sum(1 for r in results if not r.is_success())
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
