#!/usr/bin/env python3
"""
Head-to-head comparison of Fortran vs Rust DALI backends for DPAM step 07.

Runs step 07 with each backend in isolated work directories, then compares:
- Hit counts and z-scores from _iterativdDali_hits files
- Step 08 _good_hits output (qscore, ztile, rank)
- Wall-clock timing

Usage:
    python scripts/test_dali_backends.py \
        --prefix AF-Q97ZL0-F1 \
        --source-dir validation_swissprot \
        --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data \
        --cpus 4
"""

import argparse
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

# Ensure dpam is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_hits_file(hits_file: Path):
    """Parse _iterativdDali_hits file into structured data.

    Returns list of dicts with keys: hitname, edomain, iteration, zscore,
    n_aligned, q_len, alignments [(qres, tres), ...]
    """
    hits = []
    if not hits_file.exists():
        return hits

    with open(hits_file) as f:
        current = None
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('>'):
                if current:
                    hits.append(current)
                parts = line[1:].split('\t')
                hitname = parts[0]
                # hitname format: {edomain}_{iteration}
                pieces = hitname.rsplit('_', 1)
                edomain = pieces[0]
                iteration = int(pieces[1]) if len(pieces) > 1 else 1
                current = {
                    'hitname': hitname,
                    'edomain': edomain,
                    'iteration': iteration,
                    'zscore': float(parts[1]),
                    'n_aligned': int(parts[2]) if len(parts) > 2 else 0,
                    'q_len': int(parts[3]) if len(parts) > 3 else 0,
                    'alignments': [],
                }
            elif current and not line.startswith('rotation') and not line.startswith('translation'):
                parts = line.split('\t')
                if len(parts) == 2:
                    try:
                        current['alignments'].append((int(parts[0]), int(parts[1])))
                    except ValueError:
                        pass
        if current:
            hits.append(current)

    return hits


def compare_hits(fortran_hits, rust_hits, z_tol=0.5, align_tol=5):
    """Compare hit lists from both backends.

    Returns dict with comparison statistics.
    """
    # Group by edomain
    f_by_domain = defaultdict(list)
    r_by_domain = defaultdict(list)
    for h in fortran_hits:
        f_by_domain[h['edomain']].append(h)
    for h in rust_hits:
        r_by_domain[h['edomain']].append(h)

    all_domains = sorted(set(f_by_domain.keys()) | set(r_by_domain.keys()))

    stats = {
        'total_domains': len(all_domains),
        'both_hit': 0,
        'fortran_only': 0,
        'rust_only': 0,
        'neither': 0,
        'z_match': 0,
        'z_mismatch': 0,
        'align_match': 0,
        'align_mismatch': 0,
        'details': [],
    }

    for domain in all_domains:
        f_hits = f_by_domain.get(domain, [])
        r_hits = r_by_domain.get(domain, [])

        if f_hits and r_hits:
            stats['both_hit'] += 1
            # Compare first hit (highest z-score)
            fh = f_hits[0]
            rh = r_hits[0]
            z_diff = abs(fh['zscore'] - rh['zscore'])
            n_diff = abs(len(fh['alignments']) - len(rh['alignments']))

            if z_diff <= z_tol:
                stats['z_match'] += 1
            else:
                stats['z_mismatch'] += 1
                stats['details'].append(
                    f"  Z-DIFF {domain}: fortran={fh['zscore']:.1f} "
                    f"rust={rh['zscore']:.1f} (diff={z_diff:.1f})"
                )

            if n_diff <= align_tol:
                stats['align_match'] += 1
            else:
                stats['align_mismatch'] += 1
                stats['details'].append(
                    f"  ALIGN-DIFF {domain}: fortran={len(fh['alignments'])} "
                    f"rust={len(rh['alignments'])} (diff={n_diff})"
                )

        elif f_hits and not r_hits:
            stats['fortran_only'] += 1
            if len(stats['details']) < 20:
                stats['details'].append(
                    f"  FORTRAN-ONLY {domain}: z={f_hits[0]['zscore']:.1f} "
                    f"n={len(f_hits[0]['alignments'])}"
                )
        elif r_hits and not f_hits:
            stats['rust_only'] += 1
            if len(stats['details']) < 20:
                stats['details'].append(
                    f"  RUST-ONLY {domain}: z={r_hits[0]['zscore']:.1f} "
                    f"n={len(r_hits[0]['alignments'])}"
                )

    return stats


def setup_workdir(prefix, source_dir, work_dir):
    """Copy step 1-6 outputs into a clean working directory."""
    work_dir.mkdir(parents=True, exist_ok=True)

    # Files needed for step 07: PDB (step 1) and _hits4Dali (step 6)
    needed = [
        f'{prefix}.pdb',
        f'{prefix}_hits4Dali',
        # Also copy CIF and JSON for step 01 (PREPARE) if step 07 needs them
        f'{prefix}.cif',
        f'{prefix}.json',
    ]

    for fname in needed:
        src = source_dir / fname
        if src.exists():
            shutil.copy2(src, work_dir / fname)

    # Seed state file: mark steps 1-6 as complete
    state = {
        'prefix': prefix,
        'working_dir': str(work_dir),
        'completed_steps': [
            'PREPARE', 'HHSEARCH', 'FOLDSEEK', 'FILTER_FOLDSEEK',
            'MAP_ECOD', 'DALI_CANDIDATES',
        ],
        'failed_steps': {},
        'metadata': {},
    }
    state_file = work_dir / f'.{prefix}.dpam_state.json'
    with open(state_file, 'w') as f:
        json.dump(state, f)


def run_step7(prefix, work_dir, data_dir, cpus, backend, template_dat_dir=None):
    """Run step 07 with specified backend. Returns (success, elapsed_seconds)."""
    os.environ['DPAM_DALI_BACKEND'] = backend

    from dpam.steps.step07_iterative_dali import run_step7 as _run_step7

    t0 = time.perf_counter()
    kwargs = dict(
        prefix=prefix,
        working_dir=work_dir,
        data_dir=Path(data_dir),
        cpus=cpus,
    )
    if template_dat_dir:
        kwargs['template_dat_dir'] = Path(template_dat_dir)
    success = _run_step7(**kwargs)
    elapsed = time.perf_counter() - t0

    # Clean up env var
    del os.environ['DPAM_DALI_BACKEND']

    return success, elapsed


def run_step8(prefix, work_dir, data_dir):
    """Run step 08 on existing step 07 output. Returns success."""
    from dpam.io.reference_data import load_ecod_data
    from dpam.steps.step08_analyze_dali import run_step8 as _run_step8

    ref_data = load_ecod_data(Path(data_dir))
    return _run_step8(
        prefix=prefix,
        working_dir=work_dir,
        reference_data=ref_data,
        data_dir=Path(data_dir),
    )


def compare_good_hits(fortran_file, rust_file, q_tol=0.05):
    """Compare _good_hits files from step 08."""
    if not fortran_file.exists() or not rust_file.exists():
        return {'error': 'missing files'}

    def parse_good_hits(path):
        hits = {}
        with open(path) as f:
            header = f.readline()
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 9:
                    hitname = parts[0]
                    hits[hitname] = {
                        'zscore': float(parts[4]),
                        'qscore': float(parts[5]),
                        'ztile': float(parts[6]),
                        'qtile': float(parts[7]),
                        'rank': float(parts[8]),
                    }
        return hits

    f_hits = parse_good_hits(fortran_file)
    r_hits = parse_good_hits(rust_file)

    common = set(f_hits.keys()) & set(r_hits.keys())
    q_match = 0
    q_mismatch = 0

    for hit in common:
        if abs(f_hits[hit]['qscore'] - r_hits[hit]['qscore']) <= q_tol:
            q_match += 1
        else:
            q_mismatch += 1

    return {
        'fortran_count': len(f_hits),
        'rust_count': len(r_hits),
        'common': len(common),
        'fortran_only': len(f_hits) - len(common),
        'rust_only': len(r_hits) - len(common),
        'qscore_match': q_match,
        'qscore_mismatch': q_mismatch,
    }


def main():
    parser = argparse.ArgumentParser(description='Compare Fortran vs Rust DALI backends')
    parser.add_argument('--prefix', required=True, help='Protein prefix (e.g. AF-Q97ZL0-F1)')
    parser.add_argument('--source-dir', required=True, help='Directory with existing step 1-6 outputs')
    parser.add_argument('--data-dir', required=True, help='ECOD reference data directory')
    parser.add_argument('--cpus', type=int, default=4, help='Number of worker processes')
    parser.add_argument('--output-dir', default='/tmp/dali_backend_test',
                        help='Base directory for test working dirs')
    parser.add_argument('--skip-step8', action='store_true', help='Skip step 08 comparison')
    parser.add_argument('--template-dat-dir', default=None,
                        help='Directory with pre-computed Fortran .dat files for templates')
    args = parser.parse_args()

    prefix = args.prefix
    source_dir = Path(args.source_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    output_base = Path(args.output_dir) / prefix

    # Check prerequisites
    candidates_file = source_dir / f'{prefix}_hits4Dali'
    if not candidates_file.exists():
        print(f"ERROR: {candidates_file} not found")
        sys.exit(1)

    n_candidates = sum(1 for line in open(candidates_file) if line.strip())
    pdb_file = source_dir / f'{prefix}.pdb'
    if not pdb_file.exists():
        print(f"ERROR: {pdb_file} not found")
        sys.exit(1)

    print("=" * 70)
    print(f"DALI Backend Comparison: {prefix}")
    print("=" * 70)
    print(f"  Source:     {source_dir}")
    print(f"  Data:       {data_dir}")
    print(f"  CPUs:       {args.cpus}")
    print(f"  Candidates: {n_candidates}")
    print(f"  Output:     {output_base}")
    if args.template_dat_dir:
        dat_count = len(list(Path(args.template_dat_dir).glob('*.dat')))
        print(f"  .dat dir:   {args.template_dat_dir} ({dat_count} files)")

    # ---- Fortran backend ----
    print(f"\n--- Fortran Backend ---")
    fortran_dir = output_base / 'fortran'
    if fortran_dir.exists():
        shutil.rmtree(fortran_dir)
    setup_workdir(prefix, source_dir, fortran_dir)

    f_success, f_time = run_step7(prefix, fortran_dir, data_dir, args.cpus, 'fortran',
                                   template_dat_dir=args.template_dat_dir)
    f_hits_file = fortran_dir / f'{prefix}_iterativdDali_hits'
    f_hits = parse_hits_file(f_hits_file)
    print(f"  Success:  {f_success}")
    print(f"  Time:     {f_time:.1f}s")
    print(f"  Hits:     {len(f_hits)}")
    f_domains = len(set(h['edomain'] for h in f_hits))
    print(f"  Domains:  {f_domains} (of {n_candidates})")

    # ---- Rust backend ----
    print(f"\n--- Rust Backend ---")
    rust_dir = output_base / 'rust'
    if rust_dir.exists():
        shutil.rmtree(rust_dir)
    setup_workdir(prefix, source_dir, rust_dir)

    r_success, r_time = run_step7(prefix, rust_dir, data_dir, args.cpus, 'rust',
                                   template_dat_dir=args.template_dat_dir)
    r_hits_file = rust_dir / f'{prefix}_iterativdDali_hits'
    r_hits = parse_hits_file(r_hits_file)
    print(f"  Success:  {r_success}")
    print(f"  Time:     {r_time:.1f}s")
    print(f"  Hits:     {len(r_hits)}")
    r_domains = len(set(h['edomain'] for h in r_hits))
    print(f"  Domains:  {r_domains} (of {n_candidates})")

    # ---- Hit comparison ----
    print(f"\n--- Hit Comparison ---")
    stats = compare_hits(f_hits, r_hits)
    print(f"  Total domains checked: {stats['total_domains']}")
    print(f"  Both found hits:       {stats['both_hit']}")
    print(f"  Fortran only:          {stats['fortran_only']}")
    print(f"  Rust only:             {stats['rust_only']}")
    print(f"  Z-score match (±0.5):  {stats['z_match']}/{stats['both_hit']}")
    print(f"  Align match (±5):      {stats['align_match']}/{stats['both_hit']}")

    if stats['details']:
        print(f"\n  Differences (first 20):")
        for d in stats['details'][:20]:
            print(d)

    # ---- Step 08 comparison ----
    if not args.skip_step8:
        print(f"\n--- Step 08 Comparison ---")
        s8_f = run_step8(prefix, fortran_dir, data_dir)
        s8_r = run_step8(prefix, rust_dir, data_dir)
        print(f"  Fortran step8: {'OK' if s8_f else 'FAILED'}")
        print(f"  Rust step8:    {'OK' if s8_r else 'FAILED'}")

        if s8_f and s8_r:
            gh_stats = compare_good_hits(
                fortran_dir / f'{prefix}_good_hits',
                rust_dir / f'{prefix}_good_hits',
            )
            print(f"  Fortran hits:    {gh_stats.get('fortran_count', 0)}")
            print(f"  Rust hits:       {gh_stats.get('rust_count', 0)}")
            print(f"  Common:          {gh_stats.get('common', 0)}")
            print(f"  Qscore match:    {gh_stats.get('qscore_match', 0)}/{gh_stats.get('common', 0)}")

    # ---- Summary ----
    print(f"\n{'=' * 70}")
    print(f"Summary: {prefix}")
    print(f"{'=' * 70}")
    speedup = f_time / r_time if r_time > 0 else float('inf')
    print(f"  {'Backend':<12} {'Time':>8} {'Hits':>6} {'Domains':>8}")
    print(f"  {'fortran':<12} {f_time:>7.1f}s {len(f_hits):>6} {f_domains:>8}")
    print(f"  {'rust':<12} {r_time:>7.1f}s {len(r_hits):>6} {r_domains:>8}")
    print(f"  Speedup: {speedup:.2f}x {'(rust faster)' if speedup > 1 else '(fortran faster)'}")
    print(f"  Z-score agreement: {stats['z_match']}/{stats['both_hit']}")
    print(f"  Output dirs: {output_base}")
    print()


if __name__ == '__main__':
    from dpam.utils.logging_config import setup_logging
    setup_logging(json_format=False)
    main()
