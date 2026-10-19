#!/usr/bin/env python3
"""Shard DPAM reference data directories by last 2 digits of ecod_num.

Moves files from flat layout:
    posi_weights/000000003.weight
    ecod_internal/000000003.info

To sharded layout:
    posi_weights/03/000000003.weight
    ecod_internal/03/000000003.info

This fixes NFS readdir issues with 58k+ files in a single directory.

Usage:
    python shard_reference_data.py /path/to/ecod_data [--dry-run]
"""
import argparse
import os
import sys
import time
from pathlib import Path


def shard_directory(base_dir, extension, dry_run=False):
    """Shard files in a directory by last 2 digits of the stem."""
    files = []
    # Use os.scandir which handles large directories better than glob
    with os.scandir(base_dir) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith(extension):
                files.append(entry.name)

    print(f"  Found {len(files)} {extension} files")

    if not files:
        return 0

    # Create shard directories
    shards = set()
    for fname in files:
        stem = fname.replace(extension, '')
        shard = stem[-2:]
        shards.add(shard)

    for shard in sorted(shards):
        shard_dir = base_dir / shard
        if not dry_run:
            shard_dir.mkdir(exist_ok=True)

    print(f"  Created {len(shards)} shard directories")

    # Move files
    moved = 0
    for fname in files:
        stem = fname.replace(extension, '')
        shard = stem[-2:]
        src = base_dir / fname
        dst = base_dir / shard / fname

        if dry_run:
            if moved < 5:
                print(f"    {src} -> {dst}")
        else:
            os.rename(str(src), str(dst))

        moved += 1
        if moved % 10000 == 0:
            print(f"    Moved {moved}/{len(files)}...")

    print(f"  Moved {moved} files")
    return moved


def main():
    parser = argparse.ArgumentParser(description='Shard DPAM reference data')
    parser.add_argument('data_dir', type=Path, help='Path to ecod_data directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    args = parser.parse_args()

    data_dir = args.data_dir

    start = time.time()

    print(f"Sharding reference data in {data_dir}")
    if args.dry_run:
        print("  DRY RUN - no files will be moved")

    # Shard posi_weights
    weights_dir = data_dir / 'posi_weights'
    if weights_dir.exists():
        print(f"\nSharding posi_weights/")
        w = shard_directory(weights_dir, '.weight', args.dry_run)
    else:
        print(f"\nWARNING: {weights_dir} not found")
        w = 0

    # Shard ecod_internal
    info_dir = data_dir / 'ecod_internal'
    if info_dir.exists():
        print(f"\nSharding ecod_internal/")
        i = shard_directory(info_dir, '.info', args.dry_run)
    else:
        print(f"\nWARNING: {info_dir} not found")
        i = 0

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s: {w} weight files + {i} info files sharded")


if __name__ == '__main__':
    main()
