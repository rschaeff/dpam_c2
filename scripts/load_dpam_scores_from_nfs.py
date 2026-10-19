#!/usr/bin/env python3
"""Load DPAM domain scores directly from NFS into PostgreSQL.

Weights are already loaded. This only loads info files (scores).
Reads directly from NFS - designed for when NFS is not under heavy load.

Usage:
    python load_dpam_scores_from_nfs.py
"""
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

NFS_DIR = Path('/home/rschaeff_1/data/dpam_reference/ecod_data')
DB_PARAMS = dict(host='dione', port=45000, dbname='ecod_protein',
                 user='ecod')


def main():
    info_dir = NFS_DIR / 'ecod_internal'
    files = sorted(info_dir.glob('*.info'))
    print(f"Found {len(files)} info files to load")

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # Truncate and reload
    cur.execute("TRUNCATE ecod_commons.dpam_domain_scores")
    conn.commit()

    rows = []
    loaded = 0
    start = time.time()

    for i, f in enumerate(files):
        ecod_num = f.stem
        try:
            with open(f) as fh:
                for line in fh:
                    words = line.split()
                    if len(words) >= 3:
                        rows.append((ecod_num, words[0], float(words[1]), float(words[2])))
        except Exception as e:
            print(f"  Error reading {f}: {e}", file=sys.stderr)
            continue

        # Flush every 200k rows
        if len(rows) >= 200000:
            execute_values(
                cur,
                "INSERT INTO ecod_commons.dpam_domain_scores (ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
                rows, page_size=10000
            )
            loaded += len(rows)
            rows = []
            conn.commit()

        if (i + 1) % 2000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(files) - i - 1) / rate
            print(f"  {i+1}/{len(files)} files ({loaded:,} rows), "
                  f"{rate:.1f} files/s, ETA {eta/60:.0f}min")

    if rows:
        execute_values(
            cur,
            "INSERT INTO ecod_commons.dpam_domain_scores (ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
            rows, page_size=10000
        )
        loaded += len(rows)

    conn.commit()
    elapsed = time.time() - start
    print(f"\nDone: {loaded:,} score rows from {len(files)} files in {elapsed:.0f}s")
    conn.close()


if __name__ == '__main__':
    main()
