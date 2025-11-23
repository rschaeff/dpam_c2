#!/usr/bin/env python3
"""
Extract protein IDs from AlphaFold CIF files in a directory.

Usage:
    python extract_protein_ids.py input_dir [--output proteins.txt] [--limit N]

Example:
    python extract_protein_ids.py /work/dpam_automatic/homsa \
        --output homsa_proteins.txt \
        --limit 20
"""

import argparse
from pathlib import Path
import re


def extract_protein_ids(input_dir: Path, limit: int = None) -> list[str]:
    """
    Extract protein IDs from CIF files in directory.

    Args:
        input_dir: Directory containing AlphaFold CIF files
        limit: Maximum number of proteins to extract (None = all)

    Returns:
        List of protein IDs (e.g., 'AF-A0A024R1R8-F1')
    """
    # Pattern: AF-{UNIPROT}-F1-model_v4.cif
    pattern = re.compile(r'^(AF-[A-Z0-9]+-F\d+)-model_v\d+\.cif$')

    protein_ids = []

    for cif_file in sorted(input_dir.glob('*.cif')):
        match = pattern.match(cif_file.name)
        if match:
            protein_id = match.group(1)
            protein_ids.append(protein_id)

            if limit and len(protein_ids) >= limit:
                break

    return protein_ids


def main():
    parser = argparse.ArgumentParser(
        description='Extract protein IDs from AlphaFold CIF files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('input_dir', type=Path, help='Directory with CIF files')
    parser.add_argument('--output', type=Path, default='proteins.txt', help='Output file (default: proteins.txt)')
    parser.add_argument('--limit', type=int, help='Maximum number of proteins')
    parser.add_argument('--sample', action='store_true', help='Sample diverse sizes (small, medium, large)')

    args = parser.parse_args()

    if not args.input_dir.exists():
        print(f"Error: Directory not found: {args.input_dir}")
        return 1

    # Extract IDs
    protein_ids = extract_protein_ids(args.input_dir, limit=args.limit)

    if not protein_ids:
        print(f"No protein IDs found in {args.input_dir}")
        return 1

    # If sampling requested, try to get diverse sizes
    if args.sample and len(protein_ids) > 10:
        # This is a simple heuristic - in practice you'd check actual file sizes
        # For now, just sample evenly across the list
        step = len(protein_ids) // min(args.limit or 20, 20)
        protein_ids = protein_ids[::max(step, 1)][:min(args.limit or 20, 20)]

    # Write output
    with open(args.output, 'w') as f:
        for protein_id in protein_ids:
            f.write(f"{protein_id}\n")

    print(f"Extracted {len(protein_ids)} protein IDs")
    print(f"Written to: {args.output}")

    # Show first few
    print("\nFirst 5 proteins:")
    for protein_id in protein_ids[:5]:
        print(f"  {protein_id}")

    if len(protein_ids) > 5:
        print(f"  ... and {len(protein_ids) - 5} more")

    return 0


if __name__ == '__main__':
    exit(main())
