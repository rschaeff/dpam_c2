#!/usr/bin/env python3
"""Load DPAM position weights and domain scores into PostgreSQL.

Converts ~117k small NFS files into two database tables for fast lookup:
- dpam_position_weights: position -> weight per ecod_num
- dpam_domain_scores: historical z-scores and q-scores per ecod_num

Usage:
    python load_dpam_reference_to_db.py /path/to/ecod_data [--batch-size 1000]
"""
import argparse
import os
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


def load_weights(data_dir, conn, batch_size=1000):
    """Load all position weight files into dpam_position_weights."""
    weight_dir = data_dir / 'posi_weights'
    files = sorted(weight_dir.glob('*.weight'))
    print(f"Loading {len(files)} weight files...")

    cur = conn.cursor()
    cur.execute("TRUNCATE ecod_commons.dpam_position_weights")

    rows = []
    loaded = 0
    for i, f in enumerate(files):
        ecod_num = f.stem
        with open(f) as fh:
            for line in fh:
                words = line.split()
                if len(words) >= 4:
                    rows.append((ecod_num, int(words[0]), float(words[3])))

        if len(rows) >= batch_size * 200:
            execute_values(
                cur,
                "INSERT INTO ecod_commons.dpam_position_weights (ecod_num, position, weight) VALUES %s",
                rows, page_size=10000
            )
            loaded += len(rows)
            rows = []
            if (i + 1) % 5000 == 0:
                print(f"  {i+1}/{len(files)} files, {loaded:,} rows loaded")

    if rows:
        execute_values(
            cur,
            "INSERT INTO ecod_commons.dpam_position_weights (ecod_num, position, weight) VALUES %s",
            rows, page_size=10000
        )
        loaded += len(rows)

    conn.commit()
    print(f"  Loaded {loaded:,} weight rows from {len(files)} files")
    return loaded


def load_scores(data_dir, conn, batch_size=1000):
    """Load all domain info files into dpam_domain_scores."""
    info_dir = data_dir / 'ecod_internal'
    files = sorted(info_dir.glob('*.info'))
    print(f"Loading {len(files)} info files...")

    cur = conn.cursor()
    cur.execute("TRUNCATE ecod_commons.dpam_domain_scores")

    rows = []
    loaded = 0
    for i, f in enumerate(files):
        ecod_num = f.stem
        with open(f) as fh:
            for line in fh:
                words = line.split()
                if len(words) >= 3:
                    rows.append((ecod_num, words[0], float(words[1]), float(words[2])))

        if len(rows) >= batch_size * 200:
            execute_values(
                cur,
                "INSERT INTO ecod_commons.dpam_domain_scores (ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
                rows, page_size=10000
            )
            loaded += len(rows)
            rows = []
            if (i + 1) % 5000 == 0:
                print(f"  {i+1}/{len(files)} files, {loaded:,} rows loaded")

    if rows:
        execute_values(
            cur,
            "INSERT INTO ecod_commons.dpam_domain_scores (ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
            rows, page_size=10000
        )
        loaded += len(rows)

    conn.commit()
    print(f"  Loaded {loaded:,} score rows from {len(files)} files")
    return loaded


def main():
    parser = argparse.ArgumentParser(description='Load DPAM reference data to database')
    parser.add_argument('data_dir', type=Path, help='Path to ecod_data directory')
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--host', default='dione')
    parser.add_argument('--port', type=int, default=45000)
    parser.add_argument('--dbname', default='ecod_protein')
    parser.add_argument('--user', default='ecod')
    parser.add_argument('--password', default=None,
                        help='Defaults to PGPASSWORD / ~/.pgpass')
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=args.host, port=args.port, dbname=args.dbname,
        user=args.user, password=args.password
    )

    start = time.time()
    w = load_weights(args.data_dir, conn, args.batch_size)
    s = load_scores(args.data_dir, conn, args.batch_size)
    elapsed = time.time() - start

    print(f"\nDone in {elapsed:.0f}s: {w:,} weight rows + {s:,} score rows")
    conn.close()


if __name__ == '__main__':
    main()
