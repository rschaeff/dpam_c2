#!/usr/bin/env python3
"""
Select proteins for large-scale validation.

Selects N proteins from swissprot.domain that:
1. Are NOT in any existing validation sets
2. Have valid UniProt accessions
3. Are randomly sampled for unbiased selection

Usage:
    python select_validation_proteins.py \
        --output-dir validation_10k \
        --num-proteins 10000 \
        --batch-size 1000 \
        --exclude-dirs validation_1000 validation_1000_round2
"""

import argparse
import os
import random
import re
import sys
from pathlib import Path

def get_existing_proteins(exclude_dirs: list) -> set:
    """Collect all protein accessions from existing validation directories."""
    existing = set()

    for dir_path in exclude_dirs:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            print(f"Warning: {dir_path} does not exist, skipping")
            continue

        # Look for .cif files (AF-XXXXX-F1.cif format)
        for cif_file in dir_path.glob("AF-*-F*.cif"):
            # Extract UniProt accession from filename
            match = re.match(r'AF-([A-Za-z0-9]+)-F\d+\.cif', cif_file.name)
            if match:
                existing.add(match.group(1))

        # Also check protein list files
        for txt_file in dir_path.glob("proteins*.txt"):
            with open(txt_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Handle both AF-XXXXX-F1 and plain accession formats
                    match = re.match(r'AF-([A-Za-z0-9]+)-F\d+', line)
                    if match:
                        existing.add(match.group(1))
                    elif re.match(r'^[A-Za-z0-9]+$', line):
                        existing.add(line)

    return existing


def query_available_proteins(exclude_set: set, limit: int) -> list:
    """Query database for available proteins not in exclude set."""
    import psycopg2

    conn = psycopg2.connect(
        host='dione',
        port=45000,
        user='ecod',
        dbname='ecod_protein'
    )
    cursor = conn.cursor()

    # Get all unique proteins from database
    print("Querying database for available proteins...")
    cursor.execute("SELECT DISTINCT unp_acc FROM swissprot.domain")
    all_proteins = [row[0] for row in cursor.fetchall()]
    print(f"Total proteins in database: {len(all_proteins)}")

    # Filter out excluded proteins
    available = [p for p in all_proteins if p not in exclude_set]
    print(f"After excluding existing: {len(available)}")

    # Randomly sample
    random.seed(42)  # Reproducible selection
    if len(available) < limit:
        print(f"Warning: Only {len(available)} proteins available, less than requested {limit}")
        selected = available
    else:
        selected = random.sample(available, limit)

    cursor.close()
    conn.close()

    return selected


def create_batches(proteins: list, batch_size: int, output_dir: Path):
    """Split proteins into batches and create directory structure."""
    num_batches = (len(proteins) + batch_size - 1) // batch_size

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write master list
    master_file = output_dir / "all_proteins.txt"
    with open(master_file, 'w') as f:
        f.write(f"# {len(proteins)} proteins for validation\n")
        f.write(f"# Generated with seed=42 for reproducibility\n")
        for p in proteins:
            f.write(f"{p}\n")
    print(f"Wrote master list: {master_file}")

    # Create batches
    for i in range(num_batches):
        batch_num = i + 1
        batch_dir = output_dir / f"batch_{batch_num:02d}"
        batch_dir.mkdir(exist_ok=True)
        (batch_dir / "slurm_logs").mkdir(exist_ok=True)

        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(proteins))
        batch_proteins = proteins[start_idx:end_idx]

        # Write batch protein list (as AF-XXXXX-F1 format)
        proteins_file = batch_dir / "proteins.txt"
        with open(proteins_file, 'w') as f:
            for p in batch_proteins:
                f.write(f"AF-{p}-F1\n")

        print(f"Batch {batch_num:02d}: {len(batch_proteins)} proteins -> {batch_dir}")

    return num_batches


def main():
    parser = argparse.ArgumentParser(description="Select proteins for validation")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Output directory for validation batches")
    parser.add_argument("--num-proteins", type=int, default=10000,
                        help="Total number of proteins to select")
    parser.add_argument("--batch-size", type=int, default=1000,
                        help="Number of proteins per batch")
    parser.add_argument("--exclude-dirs", nargs="+", default=[],
                        help="Directories containing proteins to exclude")
    args = parser.parse_args()

    # Collect existing proteins to exclude
    print("Collecting existing proteins to exclude...")
    exclude_set = get_existing_proteins(args.exclude_dirs)
    print(f"Excluding {len(exclude_set)} existing proteins")

    # Save excluded proteins list
    args.output_dir.mkdir(parents=True, exist_ok=True)
    excluded_file = args.output_dir / "excluded_proteins.txt"
    with open(excluded_file, 'w') as f:
        f.write(f"# {len(exclude_set)} proteins excluded from selection\n")
        for p in sorted(exclude_set):
            f.write(f"{p}\n")

    # Query available proteins
    proteins = query_available_proteins(exclude_set, args.num_proteins)
    print(f"Selected {len(proteins)} proteins")

    # Create batches
    num_batches = create_batches(proteins, args.batch_size, args.output_dir)
    print(f"\nCreated {num_batches} batches in {args.output_dir}")

    print("\nNext steps:")
    print("1. Run download_batch_structures.py for each batch")
    print("2. Run create_batch_reference.py for each batch")
    print("3. Submit SLURM jobs for each batch")


if __name__ == "__main__":
    main()
