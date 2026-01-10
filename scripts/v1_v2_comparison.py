#!/usr/bin/env python3
"""
V1 vs V2 Domain Comparison Analysis

This script performs comprehensive comparison between DPAM V1 and V2 domain
predictions, calculating Jaccard coefficients, classification agreement,
and identifying systematic issues.

Usage:
    python scripts/v1_v2_comparison.py --batch-dir validation_10k/batch_01

Requirements:
    - V1 reference file: {batch_dir}/v1_reference.tsv
    - V2 step24 output: {batch_dir}/step24/*_domains
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

# Add parent directory to path for dpam imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from dpam.utils.ranges import parse_range


def jaccard(set1: Set[int], set2: Set[int]) -> float:
    """Calculate Jaccard coefficient between two residue sets."""
    if not set1 and not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def load_v1_data(v1_file: Path) -> Dict[str, List[dict]]:
    """Load V1 reference data from TSV file."""
    v1_by_protein = defaultdict(list)
    with open(v1_file) as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                unp = parts[0]
                resids = set(parse_range(parts[2]))
                v1_by_protein[unp].append({
                    'range': parts[2],
                    'resids': resids,
                    'tgroup': parts[3],
                    'judge': parts[4],
                    'ecod_ref': parts[7] if len(parts) > 7 else 'na',
                    'size': len(resids)
                })
    return v1_by_protein


def load_v2_data(step24_dir: Path) -> Dict[str, List[dict]]:
    """Load V2 step24 output data."""
    v2_by_protein = defaultdict(list)
    for f in step24_dir.glob('*_domains'):
        prefix = f.stem.replace('_domains', '')
        if prefix.startswith('AF-') and '-F' in prefix:
            unp = prefix.split('-')[1]
        else:
            unp = prefix

        with open(f) as fp:
            next(fp)  # skip header
            for line in fp:
                parts = line.strip().split('\t')
                if len(parts) >= 11:
                    resids = set(parse_range(parts[1]))
                    v2_by_protein[unp].append({
                        'range': parts[1],
                        'resids': resids,
                        'tgroup': parts[4],
                        'judge': parts[10],
                        'ecod_ref': parts[2],
                        'size': len(resids)
                    })
    return v2_by_protein


def calculate_metrics(v1_data: Dict, v2_data: Dict) -> dict:
    """Calculate all comparison metrics."""
    proteins_both = set(v1_data.keys()) & set(v2_data.keys())

    # Domain counts
    v1_total = sum(len(v1_data[p]) for p in proteins_both)
    v2_total = sum(len(v2_data[p]) for p in proteins_both)

    # Per-protein count agreement
    same_count = 0
    within_one = 0
    for p in proteins_both:
        diff = abs(len(v1_data[p]) - len(v2_data[p]))
        if diff == 0:
            same_count += 1
        if diff <= 1:
            within_one += 1

    # Jaccard analysis
    all_jaccards = []
    tgroup_matches = 0
    tgroup_total = 0
    judge_matches = 0
    judge_total = 0

    for unp in proteins_both:
        for v1_dom in v1_data[unp]:
            best_j = 0.0
            best_v2 = None
            for v2_dom in v2_data[unp]:
                j = jaccard(v1_dom['resids'], v2_dom['resids'])
                if j > best_j:
                    best_j = j
                    best_v2 = v2_dom

            all_jaccards.append(best_j)

            if best_j >= 0.8 and best_v2:
                tgroup_total += 1
                if v1_dom['tgroup'] == best_v2['tgroup']:
                    tgroup_matches += 1

                judge_total += 1
                v1_j, v2_j = v1_dom['judge'], best_v2['judge']
                if v1_j == v2_j or (v1_j == 'low_confidence' and v2_j == 'good_domain'):
                    judge_matches += 1

    return {
        'proteins_compared': len(proteins_both),
        'v1_domains': v1_total,
        'v2_domains': v2_total,
        'domain_ratio': v2_total / v1_total if v1_total else 0,
        'exact_count_match': same_count / len(proteins_both) if proteins_both else 0,
        'within_one': within_one / len(proteins_both) if proteins_both else 0,
        'mean_jaccard': sum(all_jaccards) / len(all_jaccards) if all_jaccards else 0,
        'high_jaccard_rate': sum(1 for j in all_jaccards if j >= 0.8) / len(all_jaccards) if all_jaccards else 0,
        'missed_rate': sum(1 for j in all_jaccards if j < 0.2) / len(all_jaccards) if all_jaccards else 0,
        'tgroup_agreement': tgroup_matches / tgroup_total if tgroup_total else 0,
        'judge_agreement': judge_matches / judge_total if judge_total else 0,
        'all_jaccards': all_jaccards,
    }


def print_rubric(metrics: dict, label: str = "ALL DOMAINS"):
    """Print validation rubric with pass/fail status."""
    print("=" * 75)
    print(f"DPAM V2 VALIDATION RUBRIC ({label})")
    print("=" * 75)
    print()
    print(f"Proteins compared: {metrics['proteins_compared']}")
    print(f"V1 domains: {metrics['v1_domains']}")
    print(f"V2 domains: {metrics['v2_domains']}")
    print()
    print("=" * 75)
    print("METRIC                              OBSERVED    THRESHOLD    STATUS")
    print("=" * 75)

    def check(name, observed, threshold, higher_better=True):
        if higher_better:
            status = "PASS" if observed >= threshold else "FAIL"
        else:
            status = "PASS" if observed <= threshold else "FAIL"
        print(f"{name:<35} {observed:>7.1%}    {threshold:>7.1%}       {status}")
        return status == "PASS"

    results = []
    print("\n1. COVERAGE")
    print("-" * 75)
    results.append(check("Domain count ratio (V2/V1)", metrics['domain_ratio'], 0.90))

    print("\n2. DOMAIN COUNT AGREEMENT")
    print("-" * 75)
    results.append(check("Exact same count", metrics['exact_count_match'], 0.80))
    results.append(check("Within +/-1 domain", metrics['within_one'], 0.95))

    print("\n3. DOMAIN BOUNDARY AGREEMENT")
    print("-" * 75)
    results.append(check("High overlap (J>=0.8)", metrics['high_jaccard_rate'], 0.75))
    print(f"{'Mean Jaccard coefficient':<35} {metrics['mean_jaccard']:>7.3f}    {0.800:>7.3f}       ", end="")
    mean_pass = metrics['mean_jaccard'] >= 0.80
    print("PASS" if mean_pass else "FAIL")
    results.append(mean_pass)

    print("\n4. CLASSIFICATION AGREEMENT")
    print("-" * 75)
    results.append(check("T-group agreement", metrics['tgroup_agreement'], 0.90))
    results.append(check("Judge agreement", metrics['judge_agreement'], 0.90))

    print("\n5. MISSED DOMAINS")
    print("-" * 75)
    results.append(check("V1 domains missed (J<0.2)", metrics['missed_rate'], 0.10, higher_better=False))

    print()
    print("=" * 75)
    passed = sum(results)
    total = len(results)
    print(f"OVERALL: {passed}/{total} metrics passed")

    if passed == total:
        print("\nVERDICT: V2 is a SUITABLE REPLACEMENT for V1")
    elif passed >= total - 2:
        print("\nVERDICT: V2 is CONDITIONALLY ACCEPTABLE")
    else:
        print("\nVERDICT: V2 requires FURTHER INVESTIGATION")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description='Compare DPAM V1 and V2 domain predictions')
    parser.add_argument('--batch-dir', type=Path, required=True,
                        help='Directory containing v1_reference.tsv and step24/')
    parser.add_argument('--all-batches', type=Path,
                        help='Parent directory containing batch_* subdirectories')
    args = parser.parse_args()

    if args.all_batches:
        # Process all batches
        v1_data = defaultdict(list)
        v2_data = defaultdict(list)

        for batch_dir in sorted(args.all_batches.glob('batch_*')):
            v1_file = batch_dir / 'v1_reference.tsv'
            step24_dir = batch_dir / 'step24'

            if v1_file.exists():
                batch_v1 = load_v1_data(v1_file)
                for k, v in batch_v1.items():
                    v1_data[k].extend(v)

            if step24_dir.exists():
                batch_v2 = load_v2_data(step24_dir)
                for k, v in batch_v2.items():
                    v2_data[k].extend(v)
    else:
        # Process single batch
        v1_file = args.batch_dir / 'v1_reference.tsv'
        step24_dir = args.batch_dir / 'step24'

        if not v1_file.exists():
            print(f"Error: V1 reference file not found: {v1_file}")
            sys.exit(1)

        if not step24_dir.exists():
            print(f"Error: Step24 directory not found: {step24_dir}")
            sys.exit(1)

        v1_data = load_v1_data(v1_file)
        v2_data = load_v2_data(step24_dir)

    # All domains analysis
    metrics = calculate_metrics(v1_data, v2_data)
    print_rubric(metrics, "ALL DOMAINS")

    # good_domain only analysis
    v1_good = {k: [d for d in v if d['judge'] == 'good_domain'] for k, v in v1_data.items()}
    v2_good = {k: [d for d in v if d['judge'] == 'good_domain'] for k, v in v2_data.items()}

    # Filter to proteins with at least one good_domain
    v1_good = {k: v for k, v in v1_good.items() if v}
    v2_good = {k: v for k, v in v2_good.items() if v}

    if v1_good and v2_good:
        print("\n")
        good_metrics = calculate_metrics(v1_good, v2_good)
        print_rubric(good_metrics, "good_domain ONLY")

        print("\n" + "=" * 75)
        print("COMPARISON: ALL DOMAINS vs good_domain ONLY")
        print("=" * 75)
        print(f"\n{'Metric':<35} {'All':>12} {'good_domain':>12} {'Delta':>10}")
        print("-" * 75)

        comparisons = [
            ("High Jaccard (≥0.8)", 'high_jaccard_rate'),
            ("Mean Jaccard", 'mean_jaccard'),
            ("T-group agreement", 'tgroup_agreement'),
            ("Missed (J<0.2)", 'missed_rate'),
        ]

        for name, key in comparisons:
            all_val = metrics[key]
            good_val = good_metrics[key]
            delta = good_val - all_val
            print(f"{name:<35} {all_val:>11.1%} {good_val:>11.1%} {delta:>+9.1%}")


if __name__ == '__main__':
    main()
