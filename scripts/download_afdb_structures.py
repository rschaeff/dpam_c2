#!/usr/bin/env python3
"""
Download AlphaFold structure files (CIF and PAE) for validation set.

Uses AlphaFold REST API:
- CIF: https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v4.cif
- PAE: https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-predicted_aligned_error_v4.json
"""

import sys
import csv
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
import time

def download_file(url: str, output_path: Path, max_retries: int = 3) -> Tuple[bool, str]:
    """Download file from URL with retries."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                output_path.write_bytes(response.content)
                return True, f"Downloaded {output_path.name}"
            elif response.status_code == 404:
                return False, f"Not found: {url}"
            else:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return False, f"HTTP {response.status_code}: {url}"

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return False, f"Error: {str(e)}"

    return False, f"Failed after {max_retries} attempts"


def download_protein(afdb_id: str, output_dir: Path) -> Tuple[str, bool, str]:
    """Download CIF and PAE for single protein."""
    # Convert P64202_F1 to AF-P64202-F1
    uniprot = afdb_id.replace('_', '-')
    full_id = f"AF-{uniprot}"

    # AlphaFold API URLs (v6 models)
    cif_url = f"https://alphafold.ebi.ac.uk/files/{full_id}-model_v6.cif"
    pae_url = f"https://alphafold.ebi.ac.uk/files/{full_id}-predicted_aligned_error_v6.json"

    # Output paths
    cif_path = output_dir / f"{full_id}.cif"
    pae_path = output_dir / f"{full_id}.json"

    # Download CIF
    cif_success, cif_msg = download_file(cif_url, cif_path)
    if not cif_success:
        return afdb_id, False, f"CIF failed: {cif_msg}"

    # Download PAE
    pae_success, pae_msg = download_file(pae_url, pae_path)
    if not pae_success:
        cif_path.unlink()  # Clean up CIF if PAE fails
        return afdb_id, False, f"PAE failed: {pae_msg}"

    return afdb_id, True, "Success"


def main():
    if len(sys.argv) < 3:
        print("Usage: download_afdb_structures.py <input_csv> <output_dir> [max_workers]")
        print("  input_csv: CSV file with alphafold_id in first column")
        print("  output_dir: Directory to save downloaded files")
        print("  max_workers: Number of parallel downloads (default: 10)")
        sys.exit(1)

    input_csv = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read protein IDs
    protein_ids = []
    with open(input_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0]:
                protein_ids.append(row[0])

    print(f"Found {len(protein_ids)} proteins to download")
    print(f"Output directory: {output_dir}")
    print(f"Using {max_workers} parallel workers")
    print()

    # Download in parallel
    success_count = 0
    fail_count = 0
    failed_proteins = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(download_protein, protein_id, output_dir): protein_id
            for protein_id in protein_ids
        }

        # Process results as they complete
        for i, future in enumerate(as_completed(futures), 1):
            protein_id = futures[future]
            try:
                afdb_id, success, message = future.result()

                if success:
                    success_count += 1
                    status = "✓"
                else:
                    fail_count += 1
                    status = "✗"
                    failed_proteins.append((afdb_id, message))

                # Print progress every 50 proteins
                if i % 50 == 0 or not success:
                    print(f"[{i}/{len(protein_ids)}] {status} {afdb_id}: {message}")

            except Exception as e:
                fail_count += 1
                failed_proteins.append((protein_id, str(e)))
                print(f"[{i}/{len(protein_ids)}] ✗ {protein_id}: Exception: {e}")

    # Summary
    print()
    print("=" * 60)
    print(f"Download complete!")
    print(f"  Success: {success_count}/{len(protein_ids)} ({100*success_count/len(protein_ids):.1f}%)")
    print(f"  Failed:  {fail_count}/{len(protein_ids)} ({100*fail_count/len(protein_ids):.1f}%)")
    print("=" * 60)

    # Write failed proteins to file
    if failed_proteins:
        fail_file = output_dir / "download_failures.txt"
        with open(fail_file, 'w') as f:
            for afdb_id, message in failed_proteins:
                f.write(f"{afdb_id}\t{message}\n")
        print(f"Failed proteins written to: {fail_file}")

    # Write successful protein list
    success_file = output_dir.parent / "validation_afdb_downloaded.txt"
    cif_files = sorted(output_dir.glob("*.cif"))
    with open(success_file, 'w') as f:
        for cif_file in cif_files:
            # Extract AF-P64202-F1 from AF-P64202-F1.cif
            protein_id = cif_file.stem
            f.write(f"{protein_id}\n")

    print(f"Successfully downloaded protein IDs written to: {success_file}")
    print()


if __name__ == "__main__":
    main()
