#!/usr/bin/env python3
"""
Create V1 reference file for a validation batch.

Queries the database for domain annotations for all proteins in the batch.

Usage:
    python create_batch_reference.py --batch-dir validation_10k/batch_01
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Create V1 reference file")
    parser.add_argument("--batch-dir", type=Path, required=True,
                        help="Batch directory containing proteins.txt")
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
                    proteins.append((line, parts[1]))  # (prefix, unp_acc)
            else:
                proteins.append((f"AF-{line}-F1", line))

    print(f"Creating reference for {len(proteins)} proteins...")

    import psycopg2
    conn = psycopg2.connect(
        host='dione',
        port=45000,
        user='ecod',
        dbname='ecod_protein'
    )
    cursor = conn.cursor()

    ref_file = args.batch_dir / "v1_reference_domains.tsv"
    domain_count = 0

    with open(ref_file, 'w') as out:
        out.write("# V1 Reference Data from swissprot.domain\n")
        out.write("# Format: unp_acc<tab>prefix<tab>domain_id<tab>range<tab>t_group<tab>dpam_prob\n")

        for prefix, unp_acc in proteins:
            cursor.execute("""
                SELECT domain_id, range, t_group, dpam_prob
                FROM swissprot.domain
                WHERE unp_acc = %s
                ORDER BY domain_id
            """, (unp_acc,))

            for row in cursor.fetchall():
                domain_id, range_str, tgroup, prob = row
                prob = prob if prob else ''
                out.write(f"{unp_acc}\t{prefix}\t{domain_id}\t{range_str}\t{tgroup}\t{prob}\n")
                domain_count += 1

    cursor.close()
    conn.close()

    print(f"Wrote {domain_count} domain entries to {ref_file}")


if __name__ == "__main__":
    main()
