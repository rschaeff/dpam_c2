#!/usr/bin/env python3
"""
Download AlphaFold structures for a validation batch.

Downloads .cif and .json files from AlphaFold DB for each protein in the batch.

Usage:
    python download_batch_structures.py \
        --batch-dir validation_10k/batch_01 \
        --parallel 10
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def download_structure(unp_acc: str, output_dir: Path, af_version: int = 4) -> tuple:
    """Download CIF and JSON files for a protein."""
    prefix = f"AF-{unp_acc}-F1"
    cif_file = output_dir / f"{prefix}.cif"
    json_file = output_dir / f"{prefix}.json"

    # Skip if already downloaded
    if cif_file.exists() and json_file.exists():
        return unp_acc, "exists", None

    base_url = f"https://alphafold.ebi.ac.uk/files/{prefix}"

    errors = []

    # Download CIF
    if not cif_file.exists():
        cif_url = f"{base_url}-model_v{af_version}.cif"
        result = subprocess.run(
            ["curl", "-s", "-f", "-o", str(cif_file), cif_url],
            capture_output=True
        )
        if result.returncode != 0:
            errors.append(f"CIF download failed")
            cif_file.unlink(missing_ok=True)

    # Download JSON (PAE data)
    if not json_file.exists():
        json_url = f"{base_url}-predicted_aligned_error_v{af_version}.json"
        result = subprocess.run(
            ["curl", "-s", "-f", "-o", str(json_file), json_url],
            capture_output=True
        )
        if result.returncode != 0:
            errors.append(f"JSON download failed")
            json_file.unlink(missing_ok=True)

    if errors:
        return unp_acc, "failed", "; ".join(errors)

    return unp_acc, "downloaded", None


def main():
    parser = argparse.ArgumentParser(description="Download AlphaFold structures")
    parser.add_argument("--batch-dir", type=Path, required=True,
                        help="Batch directory containing proteins.txt")
    parser.add_argument("--parallel", type=int, default=10,
                        help="Number of parallel downloads")
    parser.add_argument("--af-version", type=int, default=6,
                        help="AlphaFold DB version (default: 6)")
    args = parser.parse_args()

    proteins_file = args.batch_dir / "proteins.txt"
    if not proteins_file.exists():
        print(f"Error: {proteins_file} not found")
        sys.exit(1)

    # Read proteins
    proteins = []
    with open(proteins_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Extract accession from AF-XXXXX-F1 format
            if line.startswith("AF-"):
                parts = line.split("-")
                if len(parts) >= 2:
                    proteins.append(parts[1])
            else:
                proteins.append(line)

    print(f"Downloading structures for {len(proteins)} proteins...")
    print(f"Output directory: {args.batch_dir}")
    print(f"Parallel downloads: {args.parallel}")

    downloaded = 0
    existed = 0
    failed = 0
    failed_proteins = []

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(download_structure, p, args.batch_dir, args.af_version): p
            for p in proteins
        }

        for i, future in enumerate(as_completed(futures)):
            unp_acc, status, error = future.result()
            if status == "downloaded":
                downloaded += 1
            elif status == "exists":
                existed += 1
            else:
                failed += 1
                failed_proteins.append((unp_acc, error))

            if (i + 1) % 100 == 0:
                print(f"Progress: {i + 1}/{len(proteins)} "
                      f"(downloaded: {downloaded}, existed: {existed}, failed: {failed})")

    print(f"\nComplete!")
    print(f"  Downloaded: {downloaded}")
    print(f"  Already existed: {existed}")
    print(f"  Failed: {failed}")

    if failed_proteins:
        failed_file = args.batch_dir / "download_failures.txt"
        with open(failed_file, 'w') as f:
            for unp_acc, error in failed_proteins:
                f.write(f"{unp_acc}\t{error}\n")
        print(f"  Failed proteins written to: {failed_file}")


if __name__ == "__main__":
    main()
