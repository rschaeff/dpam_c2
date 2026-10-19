#!/usr/bin/env python3
"""Prototype: pack DPAM reference data into a single binary file.

Instead of 117k small files or 47M DB rows, pack everything into one
numpy .npz file that can be memory-mapped or loaded in seconds.

Data per ecod_num:
  - weights: Dict[int, float] (position -> weight), median 143 entries
  - zscores: sorted float array for percentile calc, median 252 entries
  - qscores: sorted float array for percentile calc, median 252 entries

File format (npz with pickle protocol):
  - 'ecod_nums': array of ecod_num strings (index)
  - 'weight_positions': list of int arrays (ragged)
  - 'weight_values': list of float arrays (ragged)
  - 'zscores': list of sorted float arrays (ragged)
  - 'qscores': list of sorted float arrays (ragged)

Alternative simpler format using pickle:
  - Dict[ecod_num] -> {
      'weights': {position: weight},
      'zscores': sorted numpy array,
      'qscores': sorted numpy array
    }

Usage:
    # Build from files (one-time):
    python prototype_binary_reference.py build /path/to/ecod_data --output reference.pkl

    # Build from DB:
    python prototype_binary_reference.py build-from-db --output reference.pkl

    # Benchmark load time:
    python prototype_binary_reference.py bench reference.pkl

    # Compare percentile results vs file-based:
    python prototype_binary_reference.py verify reference.pkl /path/to/ecod_data
"""
import argparse
import pickle
import time
import sys
from pathlib import Path

import numpy as np


def build_from_files(data_dir, output_path):
    """Build binary reference from sharded file layout."""
    data_dir = Path(data_dir)
    weights_dir = data_dir / 'posi_weights'
    info_dir = data_dir / 'ecod_internal'

    reference = {}
    count = 0

    # Scan sharded directories
    import os
    for shard in sorted(os.listdir(weights_dir)):
        shard_path = weights_dir / shard
        if not shard_path.is_dir():
            continue
        for fname in os.listdir(str(shard_path)):
            if not fname.endswith('.weight'):
                continue
            ecod_num = fname[:-7]

            # Read weights
            weights = {}
            with open(shard_path / fname) as f:
                for line in f:
                    words = line.split()
                    if len(words) >= 4:
                        weights[int(words[0])] = float(words[3])

            # Read scores
            info_file = info_dir / shard / f'{ecod_num}.info'
            if not info_file.exists():
                info_file = info_dir / f'{ecod_num}.info'

            zscores = []
            qscores = []
            if info_file.exists():
                with open(info_file) as f:
                    for line in f:
                        words = line.split()
                        if len(words) >= 3:
                            zscores.append(float(words[1]))
                            qscores.append(float(words[2]))

            reference[ecod_num] = {
                'weights': weights,
                'zscores': np.array(sorted(zscores), dtype=np.float32),
                'qscores': np.array(sorted(qscores), dtype=np.float32),
            }

            count += 1
            if count % 5000 == 0:
                print(f"  {count} domains processed...")

    print(f"Built reference for {count} domains")

    # Save
    with open(output_path, 'wb') as f:
        pickle.dump(reference, f, protocol=4)

    size_mb = Path(output_path).stat().st_size / 1024 / 1024
    print(f"Saved to {output_path} ({size_mb:.1f} MB)")
    return reference


def build_from_db(output_path):
    """Build binary reference from PostgreSQL."""
    import psycopg2

    conn = psycopg2.connect(
        host='dione', port=45000, dbname='ecod_protein',
        user='ecod'
    )

    reference = {}

    # Load weights
    print("Loading weights from DB...")
    cur = conn.cursor()
    cur.execute("SELECT ecod_num, position, weight FROM ecod_commons.dpam_position_weights ORDER BY ecod_num")

    current_ecod = None
    current_weights = {}
    for ecod_num, position, weight in cur:
        if ecod_num != current_ecod:
            if current_ecod is not None:
                reference[current_ecod] = {'weights': current_weights}
            current_ecod = ecod_num
            current_weights = {}
        current_weights[position] = weight

    if current_ecod is not None:
        reference[current_ecod] = {'weights': current_weights}
    cur.close()
    print(f"  Loaded weights for {len(reference)} domains")

    # Load scores
    print("Loading scores from DB...")
    cur = conn.cursor()
    cur.execute("SELECT ecod_num, zscore, qscore FROM ecod_commons.dpam_domain_scores ORDER BY ecod_num")

    current_ecod = None
    zscores = []
    qscores = []
    score_count = 0
    for ecod_num, zscore, qscore in cur:
        if ecod_num != current_ecod:
            if current_ecod is not None and current_ecod in reference:
                reference[current_ecod]['zscores'] = np.array(sorted(zscores), dtype=np.float32)
                reference[current_ecod]['qscores'] = np.array(sorted(qscores), dtype=np.float32)
                score_count += 1
            current_ecod = ecod_num
            zscores = []
            qscores = []
        zscores.append(zscore)
        qscores.append(qscore)

    if current_ecod is not None and current_ecod in reference:
        reference[current_ecod]['zscores'] = np.array(sorted(zscores), dtype=np.float32)
        reference[current_ecod]['qscores'] = np.array(sorted(qscores), dtype=np.float32)
        score_count += 1
    cur.close()
    conn.close()
    print(f"  Loaded scores for {score_count} domains")

    # Fill in empty scores for domains with weights but no scores yet
    for ecod_num in reference:
        if 'zscores' not in reference[ecod_num]:
            reference[ecod_num]['zscores'] = np.array([], dtype=np.float32)
            reference[ecod_num]['qscores'] = np.array([], dtype=np.float32)

    # Save
    with open(output_path, 'wb') as f:
        pickle.dump(reference, f, protocol=4)

    size_mb = Path(output_path).stat().st_size / 1024 / 1024
    print(f"Saved to {output_path} ({size_mb:.1f} MB)")


def benchmark(ref_path):
    """Benchmark load time and query speed."""
    ref_path = Path(ref_path)
    size_mb = ref_path.stat().st_size / 1024 / 1024

    # Load benchmark
    print(f"File size: {size_mb:.1f} MB")
    start = time.time()
    with open(ref_path, 'rb') as f:
        reference = pickle.load(f)
    load_time = time.time() - start
    print(f"Load time: {load_time:.2f}s ({size_mb/load_time:.0f} MB/s)")
    print(f"Domains: {len(reference)}")

    # Memory estimate
    total_weights = sum(len(d['weights']) for d in reference.values())
    total_zscores = sum(len(d['zscores']) for d in reference.values())
    total_qscores = sum(len(d['qscores']) for d in reference.values())
    print(f"Total weight entries: {total_weights:,}")
    print(f"Total zscore entries: {total_zscores:,}")
    print(f"Total qscore entries: {total_qscores:,}")

    # Query benchmark: simulate step08 for a protein with 200 unique hits
    import random
    ecod_nums = list(reference.keys())
    test_ecods = random.sample(ecod_nums, min(200, len(ecod_nums)))

    start = time.time()
    for _ in range(100):  # 100 proteins worth
        for ecod_num in test_ecods:
            d = reference[ecod_num]
            weights = d['weights']
            zscores = d['zscores']
            qscores = d['qscores']
            # Simulate percentile lookup with binary search
            if len(zscores) > 0:
                idx = np.searchsorted(zscores, 5.0)
                ztile = (len(zscores) - idx) / len(zscores)
            if len(qscores) > 0:
                idx = np.searchsorted(qscores, 0.5)
                qtile = (len(qscores) - idx) / len(qscores)
    query_time = time.time() - start
    proteins_per_sec = 100 / query_time
    print(f"\nQuery benchmark (200 hits × 100 proteins): {query_time:.2f}s")
    print(f"  = {proteins_per_sec:.0f} proteins/sec")
    print(f"  = {100 * 200 / query_time:.0f} lookups/sec")


def verify(ref_path, data_dir):
    """Verify binary reference matches file-based loading."""
    from dpam.io.reference_data import load_ecod_weights, load_ecod_domain_info

    data_dir = Path(data_dir)
    with open(ref_path, 'rb') as f:
        reference = pickle.load(f)

    # Test a sample of domains
    import random
    test_ecods = random.sample(list(reference.keys()), min(50, len(reference)))

    mismatches = 0
    for ecod_num in test_ecods:
        # Compare weights
        file_weights = load_ecod_weights(data_dir, ecod_num)
        ref_weights = reference[ecod_num]['weights']
        if file_weights != ref_weights:
            print(f"  MISMATCH weights for {ecod_num}")
            mismatches += 1

        # Compare scores (sorted)
        file_info = load_ecod_domain_info(data_dir, ecod_num)
        if file_info:
            file_z = sorted(file_info[0])
            file_q = sorted(file_info[1])
            ref_z = reference[ecod_num]['zscores'].tolist()
            ref_q = reference[ecod_num]['qscores'].tolist()
            if len(file_z) != len(ref_z):
                print(f"  MISMATCH score count for {ecod_num}: {len(file_z)} vs {len(ref_z)}")
                mismatches += 1

    print(f"Verified {len(test_ecods)} domains, {mismatches} mismatches")


def main():
    parser = argparse.ArgumentParser(description='Binary reference data prototype')
    sub = parser.add_subparsers(dest='command')

    p = sub.add_parser('build', help='Build from files')
    p.add_argument('data_dir', type=Path)
    p.add_argument('--output', type=Path, default=Path('dpam_reference.pkl'))

    p = sub.add_parser('build-from-db', help='Build from PostgreSQL')
    p.add_argument('--output', type=Path, default=Path('dpam_reference.pkl'))

    p = sub.add_parser('bench', help='Benchmark load and query')
    p.add_argument('ref_path', type=Path)

    p = sub.add_parser('verify', help='Verify against files')
    p.add_argument('ref_path', type=Path)
    p.add_argument('data_dir', type=Path)

    args = parser.parse_args()

    if args.command == 'build':
        build_from_files(args.data_dir, args.output)
    elif args.command == 'build-from-db':
        build_from_db(args.output)
    elif args.command == 'bench':
        benchmark(args.ref_path)
    elif args.command == 'verify':
        verify(args.ref_path, args.data_dir)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
