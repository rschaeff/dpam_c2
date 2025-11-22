"""
DPAM cleanup utility - removes intermediate files while preserving inputs.

Usage:
    dpam-clean work/ --dry-run  # Show what would be deleted
    dpam-clean work/             # Actually delete intermediate files
"""

import argparse
from pathlib import Path
from typing import List


# Patterns for files that can be safely regenerated
INTERMEDIATE_PATTERNS = [
    '*.a3m',                    # HHblits MSA (can regenerate)
    '*.hmm',                    # HMM profiles (can regenerate)
    '*.hhr',                    # HHsearch raw results (can regenerate)
    '*.hhsearch.log',           # HHsearch logs
    '*.hhblits.log',            # HHblits logs
    '*.hhmake.log',             # HHmake logs
    '*.sse',                    # SSE assignments (can regenerate)
    '*.diso',                   # Disorder predictions (can regenerate)
    '*.dssp',                   # DSSP output (can regenerate)
    '*.foldseek.tmp',           # Foldseek temp files
    'iterativeDali_*/',         # DALI temp directories
]

# Patterns for files that should ALWAYS be preserved
PRESERVE_PATTERNS = [
    '*.cif',                    # Input structures
    '*.pdb',                    # Input structures or standardized output
    '*.json',                   # PAE matrices (input)
    '*.fa',                     # Sequences (input or extracted)
    '*.fasta',                  # Sequences (input)
    '*.map2ecod.result',        # Step 5 output (needed by Step 9)
    '*_good_hits',              # Step 8 output (needed by Step 9)
    '*_sequence.result',        # Step 9 output (needed by Step 10)
    '*_structure.result',       # Step 9 output (needed by Step 10)
    '*.goodDomains',            # Step 10 output (needed by Step 15)
    '*.step13_domains',         # Step 13 output
    '*.step15_features',        # Step 15 ML features
    '*.step16_predictions',     # Step 16 ML predictions
    '*.step17_confident_predictions',  # Step 17 filtered predictions
    '*.step18_mappings',        # Step 18 template mappings
    '*.step22_merged_domains',  # Step 22 merged domains
    '*.step23_predictions',     # Step 23 classifications
    '*.finalDPAM.domains',      # Final domain boundaries
    'step24/*_domains',         # Final assignments
    '.*.dpam_state.json',       # Checkpoint files (optional to preserve)
]


def clean_working_dir(
    working_dir: Path,
    dry_run: bool = False,
    remove_checkpoints: bool = False
) -> None:
    """
    Remove intermediate files while preserving inputs and key outputs.

    Args:
        working_dir: Working directory to clean
        dry_run: If True, only show what would be deleted
        remove_checkpoints: If True, also remove checkpoint files
    """
    if not working_dir.exists():
        print(f"Error: Directory does not exist: {working_dir}")
        return

    # Build set of files to preserve
    preserved_files = set()
    for pattern in PRESERVE_PATTERNS:
        for filepath in working_dir.glob(pattern):
            preserved_files.add(filepath)

    # If not removing checkpoints, add them to preserved set
    if not remove_checkpoints:
        for filepath in working_dir.glob('.*.dpam_state.json'):
            preserved_files.add(filepath)

    # Find and remove intermediate files
    removed_count = 0
    removed_size = 0

    for pattern in INTERMEDIATE_PATTERNS:
        for filepath in working_dir.glob(pattern):
            # Skip if in preserved set
            if filepath in preserved_files:
                continue

            # Get file size before deleting
            try:
                size = filepath.stat().st_size if filepath.is_file() else 0
            except OSError:
                size = 0

            if dry_run:
                print(f"Would remove: {filepath.relative_to(working_dir)} ({size:,} bytes)")
            else:
                try:
                    if filepath.is_dir():
                        import shutil
                        shutil.rmtree(filepath)
                    else:
                        filepath.unlink()
                    print(f"Removed: {filepath.relative_to(working_dir)} ({size:,} bytes)")
                    removed_count += 1
                    removed_size += size
                except OSError as e:
                    print(f"Error removing {filepath}: {e}")

    # Summary
    if dry_run:
        print(f"\n[DRY RUN] Would remove {removed_count} files")
    else:
        print(f"\nRemoved {removed_count} files ({removed_size:,} bytes)")
        print(f"Preserved {len(preserved_files)} important files")


def main():
    """Command-line interface for cleanup utility."""
    parser = argparse.ArgumentParser(
        description='Clean DPAM intermediate files while preserving inputs and key outputs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Preview what would be deleted
  dpam-clean work/ --dry-run

  # Actually delete intermediate files
  dpam-clean work/

  # Also remove checkpoint files (requires full re-run)
  dpam-clean work/ --remove-checkpoints

Preserved Files:
  - Input structures (*.cif, *.pdb)
  - PAE matrices (*.json)
  - Sequences (*.fa, *.fasta)
  - Step outputs needed by later steps
  - Final domain definitions
  - Checkpoint files (unless --remove-checkpoints)

Removed Files:
  - HHblits MSA files (*.a3m)
  - HMM profiles (*.hmm)
  - Log files (*.log)
  - Temporary DALI directories
        '''
    )
    parser.add_argument(
        'working_dir',
        type=Path,
        help='Working directory to clean'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--remove-checkpoints',
        action='store_true',
        help='Also remove checkpoint files (WARNING: requires full re-run)'
    )

    args = parser.parse_args()

    if args.remove_checkpoints and not args.dry_run:
        response = input(
            "WARNING: Removing checkpoints requires full pipeline re-run. "
            "Continue? [y/N] "
        )
        if response.lower() != 'y':
            print("Cancelled.")
            return

    clean_working_dir(
        args.working_dir,
        dry_run=args.dry_run,
        remove_checkpoints=args.remove_checkpoints
    )


if __name__ == '__main__':
    main()
