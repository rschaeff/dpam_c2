#!/usr/bin/env python3
"""Load DPAM domain scores into PostgreSQL via tar streaming.

Reads ecod_internal/*.info files via tar to avoid NFS per-file metadata overhead.
Uses tarfile module which reads members sequentially from a single tar stream.

Usage:
    cd /home/rschaeff_1/data/dpam_reference/ecod_data && \
    tar cf - ecod_internal/ | python load_dpam_scores_tar.py

Or from local /tmp:
    cd /tmp && tar cf - ecod_internal/ | python load_dpam_scores_tar.py
"""
import sys
import tarfile
import time
import io

import psycopg2
from psycopg2.extras import execute_values

DB_PARAMS = dict(host='dione', port=45000, dbname='ecod_protein',
                 user='ecod')

FLUSH_SIZE = 200000  # Rows to accumulate before flushing


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    cur.execute("TRUNCATE ecod_commons.dpam_domain_scores")
    conn.commit()

    rows = []
    loaded = 0
    file_count = 0
    start = time.time()

    # Read tar from stdin
    with tarfile.open(fileobj=sys.stdin.buffer, mode='r|') as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith('.info'):
                continue

            # Extract ecod_num from filename
            ecod_num = member.name.split('/')[-1].replace('.info', '')

            f = tar.extractfile(member)
            if f is None:
                continue

            content = f.read().decode('utf-8', errors='replace')
            for line in content.splitlines():
                words = line.split()
                if len(words) >= 3:
                    rows.append((ecod_num, words[0], float(words[1]), float(words[2])))

            file_count += 1

            if len(rows) >= FLUSH_SIZE:
                execute_values(
                    cur,
                    "INSERT INTO ecod_commons.dpam_domain_scores "
                    "(ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
                    rows, page_size=10000
                )
                loaded += len(rows)
                rows = []
                conn.commit()

            if file_count % 2000 == 0:
                elapsed = time.time() - start
                rate = file_count / elapsed
                eta = (58692 - file_count) / rate if rate > 0 else 0
                print(f"  {file_count}/58692 files, {loaded:,} rows, "
                      f"{rate:.0f} files/s, ETA {eta/60:.0f}min",
                      flush=True)

    # Final flush
    if rows:
        execute_values(
            cur,
            "INSERT INTO ecod_commons.dpam_domain_scores "
            "(ecod_num, hit_ecod_num, zscore, qscore) VALUES %s",
            rows, page_size=10000
        )
        loaded += len(rows)
    conn.commit()

    elapsed = time.time() - start
    print(f"\nDone: {loaded:,} score rows from {file_count} files in {elapsed:.0f}s")

    # Create index
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
