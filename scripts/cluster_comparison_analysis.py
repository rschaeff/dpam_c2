#!/usr/bin/env python3
"""
V1 vs V2 Cluster Comparison Analysis

This script compares V1 and V2 domain assignments by checking if they map
to ECOD templates within the same F99 clusters.

Key questions:
1. Do V1 and V2 assign domains to the same ECOD templates?
2. If different templates, are they in the same F99 cluster?
3. Do V2 T-group labels match the cluster's T-group?

Usage:
    python scripts/cluster_comparison_analysis.py --validation-dir validation_10k
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 required")
    sys.exit(1)


def get_db_connection():
    """Get connection to ecod_protein database."""
    return psycopg2.connect(
        host='dione',
        port=45000,
        database='ecod_protein',
        user='ecod'
    )


def load_ecod_cluster_mapping() -> Tuple[Dict[str, int], Dict[int, Set[str]], Dict[str, str]]:
    """
    Load ECOD domain → F99 cluster mapping.

    Returns:
        domain_to_cluster: ECOD domain_id → cluster_id
        cluster_to_domains: cluster_id → set of domain_ids
        domain_to_tgroup: ECOD domain_id → T-group
    """
    print("Loading ECOD F99 cluster mappings...")
    conn = get_db_connection()
    cur = conn.cursor()

    # Get F99 clustering data
    cur.execute("""
        SELECT
            d.domain_id,
            dc.cluster_id,
            cr.id as run_id,
            fga.t_group_id
        FROM ecod_commons.domain_clusters dc
        JOIN ecod_commons.clustering_runs cr ON dc.clustering_run_id = cr.id
        JOIN ecod_commons.clustering_parameters cp ON cr.parameter_set_id = cp.id
        JOIN ecod_commons.domains d ON dc.domain_id = d.id
        JOIN ecod_commons.f_group_assignments fga ON dc.f_group_assignment_id = fga.id
        WHERE cp.parameter_set_name = 'F99'
        AND d.is_obsolete = FALSE
    """)

    domain_to_cluster = {}
    cluster_to_domains = defaultdict(set)
    domain_to_tgroup = {}

    for row in cur.fetchall():
        domain_id, cluster_id, run_id, t_group = row
        # Use (run_id, cluster_id) as unique cluster key since cluster_id is per-run
        cluster_key = (run_id, cluster_id)
        domain_to_cluster[domain_id] = cluster_key
        cluster_to_domains[cluster_key].add(domain_id)
        domain_to_tgroup[domain_id] = t_group

    conn.close()

    print(f"  Loaded {len(domain_to_cluster)} domains in {len(cluster_to_domains)} clusters")
    return domain_to_cluster, cluster_to_domains, domain_to_tgroup


def load_validation_data(validation_dir: Path) -> Tuple[Dict[str, List[dict]], Dict[str, List[dict]]]:
    """
    Load V1 and V2 domain data from validation batches.

    Returns:
        v1_data: unp_acc → list of domain dicts
        v2_data: unp_acc → list of domain dicts
    """
    print("Loading validation data...")
    v1_data = defaultdict(list)
    v2_data = defaultdict(list)

    for batch_dir in sorted(validation_dir.glob('batch_*')):
        # Load V1 reference
        v1_file = batch_dir / 'v1_reference.tsv'
        if v1_file.exists():
            with open(v1_file) as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 8:
                        unp = parts[0]
                        v1_data[unp].append({
                            'domain_id': parts[1],
                            'range': parts[2],
                            't_group': parts[3],
                            'judge': parts[4],
                            'ecod_ref': parts[7] if parts[7] != 'na' else None
                        })

        # Load V2 results
        step24_dir = batch_dir / 'step24'
        if step24_dir.exists():
            for domain_file in step24_dir.glob('*_domains'):
                prefix = domain_file.stem.replace('_domains', '')
                if prefix.startswith('AF-') and '-F' in prefix:
                    unp = prefix.split('-')[1]
                else:
                    unp = prefix

                with open(domain_file) as f:
                    next(f)  # skip header
                    for i, line in enumerate(f):
                        parts = line.strip().split('\t')
                        if len(parts) >= 11:
                            v2_data[unp].append({
                                'domain_id': f'd{i}',
                                'range': parts[1],
                                't_group': parts[4],
                                'judge': parts[10],
                                'ecod_ref': parts[2] if parts[2] != 'na' else None
                            })

    print(f"  V1: {sum(len(v) for v in v1_data.values())} domains in {len(v1_data)} proteins")
    print(f"  V2: {sum(len(v) for v in v2_data.values())} domains in {len(v2_data)} proteins")

    return v1_data, v2_data


def jaccard(set1: Set[int], set2: Set[int]) -> float:
    """Calculate Jaccard coefficient."""
    if not set1 and not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def parse_range(range_str: str) -> Set[int]:
    """Parse range string like '1-50,60-100' into set of residue numbers."""
    resids = set()
    for part in range_str.split(','):
        if '-' in part:
            try:
                start, end = part.split('-')
                resids.update(range(int(start), int(end) + 1))
            except ValueError:
                pass
        else:
            try:
                resids.add(int(part))
            except ValueError:
                pass
    return resids


def analyze_template_consistency(v1_data: Dict, v2_data: Dict,
                                  domain_to_cluster: Dict,
                                  domain_to_tgroup: Dict) -> dict:
    """
    Analyze whether V1 and V2 assign domains to templates in the same cluster.
    """
    print("\nAnalyzing template and cluster consistency...")

    results = {
        'proteins_both': 0,
        'v1_domains': 0,
        'v2_domains': 0,
        'matched_pairs': 0,
        'same_template': 0,
        'same_cluster': 0,
        'different_cluster': 0,
        'v1_no_cluster': 0,  # V1 template not in F99 clustering
        'v2_no_cluster': 0,  # V2 template not in F99 clustering
        'tgroup_agreement': 0,
        'tgroup_disagreement': 0,
        'cluster_tgroup_matches_v2': 0,
        'cluster_tgroup_differs_v2': 0,
        'disagreement_details': [],
    }

    proteins_both = set(v1_data.keys()) & set(v2_data.keys())
    results['proteins_both'] = len(proteins_both)

    for unp in proteins_both:
        v1_doms = v1_data[unp]
        v2_doms = v2_data[unp]

        results['v1_domains'] += len(v1_doms)
        results['v2_domains'] += len(v2_doms)

        # Match V1 to V2 domains by overlap
        for v1_dom in v1_doms:
            v1_resids = parse_range(v1_dom['range'])

            best_j = 0.0
            best_v2 = None
            for v2_dom in v2_doms:
                v2_resids = parse_range(v2_dom['range'])
                j = jaccard(v1_resids, v2_resids)
                if j > best_j:
                    best_j = j
                    best_v2 = v2_dom

            if best_j >= 0.5 and best_v2:  # Decent overlap
                results['matched_pairs'] += 1

                v1_ref = v1_dom['ecod_ref']
                v2_ref = best_v2['ecod_ref']

                # T-group comparison (direct labels)
                if v1_dom['t_group'] == best_v2['t_group']:
                    results['tgroup_agreement'] += 1
                else:
                    results['tgroup_disagreement'] += 1

                # Template comparison
                if v1_ref == v2_ref:
                    results['same_template'] += 1
                elif v1_ref and v2_ref:
                    # Check if in same cluster
                    v1_cluster = domain_to_cluster.get(v1_ref)
                    v2_cluster = domain_to_cluster.get(v2_ref)

                    if v1_cluster is None:
                        results['v1_no_cluster'] += 1
                    elif v2_cluster is None:
                        results['v2_no_cluster'] += 1
                    elif v1_cluster == v2_cluster:
                        results['same_cluster'] += 1
                    else:
                        results['different_cluster'] += 1
                        results['disagreement_details'].append({
                            'unp': unp,
                            'v1_range': v1_dom['range'],
                            'v2_range': best_v2['range'],
                            'v1_ref': v1_ref,
                            'v2_ref': v2_ref,
                            'v1_tgroup': v1_dom['t_group'],
                            'v2_tgroup': best_v2['t_group'],
                            'jaccard': best_j,
                        })

                    # Check if V2 T-group matches the cluster's T-group
                    if v2_ref and v2_ref in domain_to_tgroup:
                        cluster_tgroup = domain_to_tgroup[v2_ref]
                        # Parse T-group for comparison
                        v2_tg_parts = best_v2['t_group'].split('.')
                        cluster_tg_parts = str(cluster_tgroup).split('.')
                        if v2_tg_parts[:2] == cluster_tg_parts[:2]:  # X.T level
                            results['cluster_tgroup_matches_v2'] += 1
                        else:
                            results['cluster_tgroup_differs_v2'] += 1

    return results


def print_results(results: dict):
    """Print analysis results."""
    print("\n" + "=" * 75)
    print("V1 vs V2 CLUSTER COMPARISON ANALYSIS")
    print("=" * 75)

    print(f"\nProteins compared: {results['proteins_both']}")
    print(f"V1 domains: {results['v1_domains']}")
    print(f"V2 domains: {results['v2_domains']}")
    print(f"Matched pairs (J≥0.5): {results['matched_pairs']}")

    print("\n" + "-" * 75)
    print("TEMPLATE AGREEMENT (matched pairs)")
    print("-" * 75)

    matched = results['matched_pairs']
    if matched > 0:
        print(f"Same template:      {results['same_template']:>6} ({100*results['same_template']/matched:>5.1f}%)")
        print(f"Same F99 cluster:   {results['same_cluster']:>6} ({100*results['same_cluster']/matched:>5.1f}%)")
        print(f"Different cluster:  {results['different_cluster']:>6} ({100*results['different_cluster']/matched:>5.1f}%)")
        print(f"V1 not in F99:      {results['v1_no_cluster']:>6} ({100*results['v1_no_cluster']/matched:>5.1f}%)")
        print(f"V2 not in F99:      {results['v2_no_cluster']:>6} ({100*results['v2_no_cluster']/matched:>5.1f}%)")

        same_or_cluster = results['same_template'] + results['same_cluster']
        print(f"\nEffective agreement (same template OR same cluster): "
              f"{same_or_cluster} ({100*same_or_cluster/matched:.1f}%)")

    print("\n" + "-" * 75)
    print("T-GROUP LABEL AGREEMENT")
    print("-" * 75)

    if matched > 0:
        print(f"T-group agrees (V1=V2): {results['tgroup_agreement']:>6} ({100*results['tgroup_agreement']/matched:>5.1f}%)")
        print(f"T-group disagrees:      {results['tgroup_disagreement']:>6} ({100*results['tgroup_disagreement']/matched:>5.1f}%)")

        v2_with_cluster = results['cluster_tgroup_matches_v2'] + results['cluster_tgroup_differs_v2']
        if v2_with_cluster > 0:
            print(f"\nV2 T-group matches cluster: {results['cluster_tgroup_matches_v2']} ({100*results['cluster_tgroup_matches_v2']/v2_with_cluster:.1f}%)")
            print(f"V2 T-group differs from cluster: {results['cluster_tgroup_differs_v2']} ({100*results['cluster_tgroup_differs_v2']/v2_with_cluster:.1f}%)")

    print("\n" + "-" * 75)
    print("CLUSTER DISAGREEMENT EXAMPLES (first 10)")
    print("-" * 75)

    for i, d in enumerate(results['disagreement_details'][:10]):
        print(f"\n{i+1}. {d['unp']}")
        print(f"   V1: {d['v1_range']} → {d['v1_ref']} (T={d['v1_tgroup']})")
        print(f"   V2: {d['v2_range']} → {d['v2_ref']} (T={d['v2_tgroup']})")
        print(f"   Jaccard: {d['jaccard']:.2f}")


def main():
    parser = argparse.ArgumentParser(description='V1 vs V2 cluster comparison')
    parser.add_argument('--validation-dir', type=Path, required=True,
                        help='Directory containing batch_* subdirectories')
    parser.add_argument('--output', type=Path, default=None,
                        help='Output JSON file for detailed results')
    args = parser.parse_args()

    # Load cluster mappings
    domain_to_cluster, cluster_to_domains, domain_to_tgroup = load_ecod_cluster_mapping()

    # Load validation data
    v1_data, v2_data = load_validation_data(args.validation_dir)

    # Analyze
    results = analyze_template_consistency(v1_data, v2_data, domain_to_cluster, domain_to_tgroup)

    # Print results
    print_results(results)

    # Save detailed results
    if args.output:
        import json
        # Remove large lists for JSON
        results_json = {k: v for k, v in results.items() if k != 'disagreement_details'}
        results_json['disagreement_count'] = len(results['disagreement_details'])
        with open(args.output, 'w') as f:
            json.dump(results_json, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
