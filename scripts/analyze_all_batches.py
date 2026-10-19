#!/usr/bin/env python3
"""
Analyze validation results across all batches.

Aggregates results from multiple validation directories and produces
summary statistics with confidence intervals.

Usage:
    python analyze_all_batches.py \
        validation_1000 \
        validation_1000_round2 \
        validation_10k/batch_01 \
        validation_10k/batch_02 \
        ...
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import math


def parse_range(range_str: str) -> set:
    """Parse range string into set of residues."""
    residues = set()
    if not range_str:
        return residues
    for seg in range_str.split(','):
        seg = seg.strip()
        if '-' in seg:
            parts = seg.split('-')
            if len(parts) == 2:
                try:
                    start, end = int(parts[0]), int(parts[1])
                    residues.update(range(start, end + 1))
                except ValueError:
                    pass
    return residues


def jaccard_overlap(range1: str, range2: str) -> float:
    """Calculate Jaccard overlap between two ranges."""
    set1 = parse_range(range1)
    set2 = parse_range(range2)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def extract_unp_acc(prefix: str) -> str:
    """Extract UniProt accession from AF-XXXXX-F1 format."""
    match = re.match(r'AF-([A-Za-z0-9]+)-F\d+', prefix)
    return match.group(1) if match else prefix


def analyze_batch(batch_dir: Path) -> Dict:
    """Analyze a single batch directory."""
    batch_dir = Path(batch_dir)
    ref_file = batch_dir / "v1_reference_domains.tsv"

    results = {
        'name': batch_dir.name,
        'path': str(batch_dir),
        'total': 0,
        'exact_match': 0,
        'count_mismatch': 0,
        'tgroup_mismatch': 0,
        'overlap_fail': 0,
        'no_v1_ref': 0,
        'no_v2_output': 0,
    }

    if not ref_file.exists():
        print(f"Warning: {ref_file} not found, skipping {batch_dir}")
        return results

    # Load V1 reference
    v1_data = {}
    with open(ref_file) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                unp_acc = parts[0]
                if unp_acc not in v1_data:
                    v1_data[unp_acc] = []
                v1_data[unp_acc].append({
                    'range': parts[3],
                    'tgroup': parts[4]
                })

    # Analyze predictions
    for pred_file in batch_dir.glob("*.step23_predictions"):
        prefix = pred_file.stem.replace('.step23_predictions', '')
        unp_acc = extract_unp_acc(prefix)

        # Read V2 predictions
        v2_domains = []
        with open(pred_file) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    v2_domains.append({
                        'range': parts[2],
                        'tgroup': parts[4]
                    })

        if not v2_domains:
            results['no_v2_output'] += 1
            continue

        if unp_acc not in v1_data:
            results['no_v1_ref'] += 1
            continue

        results['total'] += 1
        v1_domains = v1_data[unp_acc]

        if len(v1_domains) != len(v2_domains):
            results['count_mismatch'] += 1
            continue

        # Match domains
        all_match = True
        matched_v1 = [False] * len(v1_domains)

        for v2 in v2_domains:
            best_match = -1
            best_overlap = 0.0
            for i, v1 in enumerate(v1_domains):
                if matched_v1[i]:
                    continue
                overlap = jaccard_overlap(v1['range'], v2['range'])
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = i

            if best_match >= 0 and best_overlap >= 0.5:
                matched_v1[best_match] = True
                if v1_domains[best_match]['tgroup'] != v2['tgroup']:
                    all_match = False
            else:
                all_match = False

        if all(matched_v1) and all_match:
            results['exact_match'] += 1
        elif not all(matched_v1):
            results['overlap_fail'] += 1
        else:
            results['tgroup_mismatch'] += 1

    return results


def calculate_ci(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson score confidence interval for a proportion."""
    if total == 0:
        return 0.0, 0.0

    z = 1.96  # 95% confidence
    p = successes / total
    n = total

    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator

    return max(0, center - spread), min(1, center + spread)


def main():
    parser = argparse.ArgumentParser(description="Analyze validation batches")
    parser.add_argument("batch_dirs", nargs="+", type=Path,
                        help="Batch directories to analyze")
    parser.add_argument("--output", "-o", type=Path,
                        help="Output file for results (optional)")
    args = parser.parse_args()

    all_results = []
    for batch_dir in args.batch_dirs:
        if batch_dir.exists():
            results = analyze_batch(batch_dir)
            all_results.append(results)
        else:
            print(f"Warning: {batch_dir} does not exist, skipping")

    # Print per-batch results
    print("\n" + "=" * 80)
    print("PER-BATCH RESULTS")
    print("=" * 80)
    print(f"{'Batch':<30} {'Total':>8} {'Exact':>8} {'Count':>8} {'T-grp':>8} {'Ovlp':>8}")
    print("-" * 80)

    for r in all_results:
        if r['total'] > 0:
            exact_pct = 100 * r['exact_match'] / r['total']
            count_pct = 100 * r['count_mismatch'] / r['total']
            tgrp_pct = 100 * r['tgroup_mismatch'] / r['total']
            ovlp_pct = 100 * r['overlap_fail'] / r['total']
            print(f"{r['name']:<30} {r['total']:>8} {exact_pct:>7.1f}% {count_pct:>7.1f}% "
                  f"{tgrp_pct:>7.1f}% {ovlp_pct:>7.1f}%")
        else:
            print(f"{r['name']:<30} {'N/A':>8}")

    # Aggregate results
    total = sum(r['total'] for r in all_results)
    exact = sum(r['exact_match'] for r in all_results)
    count_mm = sum(r['count_mismatch'] for r in all_results)
    tgroup_mm = sum(r['tgroup_mismatch'] for r in all_results)
    overlap_f = sum(r['overlap_fail'] for r in all_results)

    print("\n" + "=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)
    print(f"Total batches analyzed: {len(all_results)}")
    print(f"Total proteins: {total}")
    print()

    if total > 0:
        # Calculate confidence intervals
        exact_ci = calculate_ci(exact, total)
        count_ci = calculate_ci(count_mm, total)
        tgroup_ci = calculate_ci(tgroup_mm, total)
        overlap_ci = calculate_ci(overlap_f, total)

        print(f"{'Metric':<20} {'Count':>8} {'Percent':>10} {'95% CI':>20}")
        print("-" * 60)
        print(f"{'Exact match':<20} {exact:>8} {100*exact/total:>9.1f}% "
              f"[{100*exact_ci[0]:.1f}% - {100*exact_ci[1]:.1f}%]")
        print(f"{'Count mismatch':<20} {count_mm:>8} {100*count_mm/total:>9.1f}% "
              f"[{100*count_ci[0]:.1f}% - {100*count_ci[1]:.1f}%]")
        print(f"{'T-group mismatch':<20} {tgroup_mm:>8} {100*tgroup_mm/total:>9.1f}% "
              f"[{100*tgroup_ci[0]:.1f}% - {100*tgroup_ci[1]:.1f}%]")
        print(f"{'Overlap fail':<20} {overlap_f:>8} {100*overlap_f/total:>9.1f}% "
              f"[{100*overlap_ci[0]:.1f}% - {100*overlap_ci[1]:.1f}%]")

    # Write output file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write("# Validation Results Summary\n")
            f.write(f"# Batches: {len(all_results)}\n")
            f.write(f"# Total proteins: {total}\n\n")
            f.write("batch\ttotal\texact_match\tcount_mismatch\ttgroup_mismatch\toverlap_fail\n")
            for r in all_results:
                f.write(f"{r['name']}\t{r['total']}\t{r['exact_match']}\t"
                        f"{r['count_mismatch']}\t{r['tgroup_mismatch']}\t{r['overlap_fail']}\n")
        print(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    main()
