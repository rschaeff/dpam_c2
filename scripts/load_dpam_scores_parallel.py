#!/usr/bin/env python3
"""Load DPAM domain scores into PostgreSQL using parallel NFS reads.

Uses multiprocessing to read multiple info files concurrently from NFS,
reducing the impact of per-file metadata latency by overlapping I/O.

Usage:
    python load_dpam_scores_parallel.py [--workers 16]
    python load_dpam_scores_parallel.py --ecod-nums-file /tmp/batch39_ecod_nums.txt  # subset only
"""
import argparse
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

NFS_DIR = Path('/home/rschaeff_1/data/dpam_reference/ecod_data/ecod_internal')
DB_PARAMS = dict(host='dione', port=45000, dbname='ecod_protein',
                 user='ecod')


def read_info_file(ecod_num):
    """Read a single info file and return parsed rows."""
    shard = ecod_num[-2:]
    fpath = NFS_DIR / shard / f'{ecod_num}.info'
    if not fpath.exists():
        fpath = NFS_DIR / f'{ecod_num}.info'  # flat fallback
    rows = []
    try:
        with open(fpath) as f:
            for line in f:
                words = line.split()
                if len(words) >= 3:
                    rows.append((ecod_num, words[0], float(words[1]), float(words[2])))
    except Exception:
        pass
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--ecod-nums-file', type=Path, default=None,
                        help='File with ecod_nums to load (one per line). Default: all.')
    parser.add_argument('--no-truncate', action='store_true',
                        help='Do not truncate existing data')
    args = parser.parse_args()

    # Get list of ecod_nums
    if args.ecod_nums_file:
        with open(args.ecod_nums_file) as f:
            ecod_nums = [line.strip() for line in f if line.strip()]
        print(f"Loading {len(ecod_nums)} ecod_nums from {args.ecod_nums_file}")
    else:
        # Support both sharded (*/xxx.info) and flat (xxx.info) layouts
        ecod_nums = [f.stem for f in NFS_DIR.glob('*/*.info')]
        if not ecod_nums:
            ecod_nums = [f.stem for f in NFS_DIR.glob('*.info')]
        print(f"Found {len(ecod_nums)} info files")

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    if not args.no_truncate:
        cur.execute("TRUNCATE ecod_commons.dpam_domain_scores")
        conn.commit()

    start = time.time()
    loaded = 0
    file_count = 0

    # Process in chunks using multiprocessing
    chunk_size = args.workers * 10  # Process this many files per batch
    for i in range(0, len(ecod_nums), chunk_size):
        chunk = ecod_nums[i:i + chunk_size]

        with Pool(args.workers) as pool:
            results = pool.map(read_info_file, chunk)

        # Flatten results and insert
        rows = []
        for file_rows in results:
            rows.extend(file_rows)
            if file_rows:
                file_count += 1

        if rows:
            execute_values(
                cur,
                "INSERT INTO ecod_commons.dpam_domain_scores "
                "(ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
                rows, page_size=10000
            )
            loaded += len(rows)
            conn.commit()

        if (i + chunk_size) % 2000 < chunk_size:
            elapsed = time.time() - start
            rate = file_count / elapsed if elapsed > 0 else 0
            eta = (len(ecod_nums) - i - chunk_size) / rate if rate > 0 else 0
            print(f"  {file_count}/{len(ecod_nums)} files, {loaded:,} rows, "
                  f"{rate:.0f} files/s, ETA {max(0,eta)/60:.0f}min", flush=True)

    elapsed = time.time() - start
    print(f"\nDone: {loaded:,} rows from {file_count} files in {elapsed:.0f}s "
          f"({file_count/elapsed:.0f} files/s)")

    # Create/refresh index
    print("Creating index...")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_dpam_domain_scores_ecod_num "
        "ON ecod_commons.dpam_domain_scores(ecod_num)"
    )
    conn.commit()
    print("Index created")
    conn.close()


if __name__ == '__main__':
    main()
