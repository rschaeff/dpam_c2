#!/usr/bin/env python3
"""
MMseqs2 Clustering Analysis for V1 vs V2 Validation

This script:
1. Extracts ECOD F99 representative domain sequences
2. Extracts V1 SwissProt domain sequences from our validation set
3. Extracts V2 domain sequences from validation results
4. Runs MMseqs2 clustering on the combined set
5. Analyzes T-group homogeneity within clusters

The goal is to determine:
- Whether V1→V2 substitution results in different cluster memberships
- Whether V2 T-group labels are correct (clusters should be T-group homogeneous)

Usage:
    python scripts/mmseqs_clustering_analysis.py \
        --validation-dir validation_10k \
        --output-dir mmseqs_analysis \
        --identity 0.99

Requirements:
    - psycopg2 for database access
    - mmseqs2 in PATH
"""

import argparse
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import tempfile
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 required. Run: pip install psycopg2-binary")
    sys.exit(1)


def get_db_connection():
    """Get connection to ecod_protein database."""
    return psycopg2.connect(
        host='dione',
        port=45000,
        database='ecod_protein',
        user='ecod'
    )


def extract_ecod_f99_representatives(output_fasta: Path, tgroup_file: Path,
                                      limit: int = None) -> int:
    """
    Extract ECOD F99 cluster representative sequences and their T-groups.

    Returns number of sequences extracted.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Get F99 representatives with sequences and T-groups
    query = """
        SELECT
            d.domain_id,
            ds.sequence,
            fga.t_group_id
        FROM ecod_commons.domain_clusters dc
        JOIN ecod_commons.clustering_runs cr ON dc.clustering_run_id = cr.id
        JOIN ecod_commons.clustering_parameters cp ON cr.parameter_set_id = cp.id
        JOIN ecod_commons.domains d ON dc.domain_id = d.id
        JOIN ecod_commons.domain_sequences ds ON d.id = ds.domain_id
        JOIN ecod_commons.f_group_assignments fga ON dc.f_group_assignment_id = fga.id
        WHERE cp.parameter_set_name = 'F99'
        AND dc.is_representative = TRUE
        AND d.is_obsolete = FALSE
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)

    count = 0
    with open(output_fasta, 'w') as fasta_out, open(tgroup_file, 'w') as tg_out:
        tg_out.write("domain_id\tsource\tt_group\n")
        for row in cur.fetchall():
            domain_id, sequence, t_group_id = row
            if sequence:
                fasta_out.write(f">ECOD_{domain_id}\n{sequence}\n")
                tg_out.write(f"ECOD_{domain_id}\tECOD\t{t_group_id}\n")
                count += 1

    conn.close()
    return count


def extract_v1_validation_sequences(validation_dir: Path, output_fasta: Path,
                                     tgroup_file: Path) -> int:
    """
    Extract V1 domain sequences for proteins in our validation set.

    Uses database to get sequences for V1 domains matching our validation UniProts.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Collect UniProt IDs from our validation set
    unp_ids = set()
    for batch_dir in validation_dir.glob('batch_*'):
        v1_file = batch_dir / 'v1_reference.tsv'
        if v1_file.exists():
            with open(v1_file) as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split('\t')
                    if parts:
                        unp_ids.add(parts[0])

    print(f"Found {len(unp_ids)} UniProt IDs in validation set")

    # Get V1 domains with sequences from protein table
    # We need to join to get the actual sequence for the domain range
    count = 0
    with open(output_fasta, 'a') as fasta_out, open(tgroup_file, 'a') as tg_out:
        for batch_dir in sorted(validation_dir.glob('batch_*')):
            v1_file = batch_dir / 'v1_reference.tsv'
            if not v1_file.exists():
                continue

            with open(v1_file) as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 5:
                        unp, domain_id, range_str, t_group, judge = parts[:5]
                        hit_ecod = parts[7] if len(parts) > 7 else None

                        # Get sequence for this domain from ECOD reference
                        if hit_ecod:
                            cur.execute("""
                                SELECT ds.sequence
                                FROM ecod_commons.domains d
                                JOIN ecod_commons.domain_sequences ds ON d.id = ds.domain_id
                                WHERE d.domain_id = %s
                            """, (hit_ecod,))
                            row = cur.fetchone()
                            if row and row[0]:
                                seq = row[0]
                                fasta_out.write(f">V1_{unp}_{domain_id}\n{seq}\n")
                                tg_out.write(f"V1_{unp}_{domain_id}\tV1\t{t_group}\n")
                                count += 1

    conn.close()
    return count


def extract_v2_sequences(validation_dir: Path, output_fasta: Path,
                         tgroup_file: Path) -> int:
    """
    Extract V2 domain sequences from validation results.

    Uses the ECOD template reference in step24 output to get sequences.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    count = 0
    with open(output_fasta, 'a') as fasta_out, open(tgroup_file, 'a') as tg_out:
        for batch_dir in sorted(validation_dir.glob('batch_*')):
            step24_dir = batch_dir / 'step24'
            if not step24_dir.exists():
                continue

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
                            range_str = parts[1]
                            ecod_ref = parts[2]
                            t_group = parts[4]
                            judge = parts[10]

                            # Get sequence from ECOD reference
                            if ecod_ref and ecod_ref != 'na':
                                cur.execute("""
                                    SELECT ds.sequence
                                    FROM ecod_commons.domains d
                                    JOIN ecod_commons.domain_sequences ds ON d.id = ds.domain_id
                                    WHERE d.domain_id = %s
                                """, (ecod_ref,))
                                row = cur.fetchone()
                                if row and row[0]:
                                    seq = row[0]
                                    domain_id = f"V2_{unp}_d{i}"
                                    fasta_out.write(f">{domain_id}\n{seq}\n")
                                    tg_out.write(f"{domain_id}\tV2\t{t_group}\n")
                                    count += 1

    conn.close()
    return count


def run_mmseqs_clustering(fasta_file: Path, output_dir: Path,
                          identity: float = 0.99, coverage: float = 0.9) -> Path:
    """
    Run MMseqs2 clustering on the combined FASTA file.

    Returns path to cluster TSV file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / 'seqdb'
    cluster_db = output_dir / 'clusterdb'
    cluster_tsv = output_dir / 'clusters.tsv'
    tmp_dir = output_dir / 'tmp'

    # Create sequence database
    print("Creating MMseqs2 database...")
    subprocess.run([
        'mmseqs', 'createdb', str(fasta_file), str(db_path)
    ], check=True)

    # Run clustering
    print(f"Running clustering (identity={identity}, coverage={coverage})...")
    subprocess.run([
        'mmseqs', 'cluster', str(db_path), str(cluster_db), str(tmp_dir),
        '--min-seq-id', str(identity),
        '-c', str(coverage),
        '--cov-mode', '0',  # bidirectional coverage
        '--cluster-mode', '0',  # Greedy set cover
    ], check=True)

    # Convert to TSV
    print("Converting clusters to TSV...")
    subprocess.run([
        'mmseqs', 'createtsv', str(db_path), str(db_path), str(cluster_db), str(cluster_tsv)
    ], check=True)

    return cluster_tsv


def analyze_clusters(cluster_tsv: Path, tgroup_file: Path) -> dict:
    """
    Analyze T-group homogeneity within clusters.

    Returns dictionary with analysis results.
    """
    # Load T-group assignments
    tgroups = {}
    sources = {}
    with open(tgroup_file) as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                domain_id, source, t_group = parts[:3]
                tgroups[domain_id] = t_group
                sources[domain_id] = source

    # Load clusters
    clusters = defaultdict(list)
    with open(cluster_tsv) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                rep, member = parts[:2]
                clusters[rep].append(member)

    # Analyze each cluster
    results = {
        'total_clusters': len(clusters),
        'homogeneous_clusters': 0,
        'heterogeneous_clusters': 0,
        'mixed_source_clusters': 0,
        'v1_v2_same_cluster': 0,
        'tgroup_disagreements': [],
        'cluster_sizes': [],
    }

    for rep, members in clusters.items():
        results['cluster_sizes'].append(len(members))

        # Get T-groups and sources for this cluster
        cluster_tgroups = set()
        cluster_sources = set()
        for m in members:
            if m in tgroups:
                cluster_tgroups.add(tgroups[m])
                cluster_sources.add(sources[m])

        if len(cluster_tgroups) <= 1:
            results['homogeneous_clusters'] += 1
        else:
            results['heterogeneous_clusters'] += 1
            results['tgroup_disagreements'].append({
                'representative': rep,
                'members': len(members),
                'tgroups': list(cluster_tgroups),
                'sources': list(cluster_sources),
            })

        if len(cluster_sources) > 1:
            results['mixed_source_clusters'] += 1

        if 'V1' in cluster_sources and 'V2' in cluster_sources:
            results['v1_v2_same_cluster'] += 1

    return results


def print_analysis(results: dict):
    """Print analysis results."""
    print("\n" + "=" * 75)
    print("MMSEQS2 CLUSTERING ANALYSIS")
    print("=" * 75)

    print(f"\nTotal clusters: {results['total_clusters']}")
    print(f"Homogeneous (single T-group): {results['homogeneous_clusters']} "
          f"({100*results['homogeneous_clusters']/results['total_clusters']:.1f}%)")
    print(f"Heterogeneous (multiple T-groups): {results['heterogeneous_clusters']} "
          f"({100*results['heterogeneous_clusters']/results['total_clusters']:.1f}%)")

    print(f"\nMixed-source clusters: {results['mixed_source_clusters']}")
    print(f"Clusters containing both V1 and V2: {results['v1_v2_same_cluster']}")

    if results['cluster_sizes']:
        sizes = results['cluster_sizes']
        print(f"\nCluster size statistics:")
        print(f"  Min: {min(sizes)}, Max: {max(sizes)}, Mean: {sum(sizes)/len(sizes):.1f}")

        # Size distribution
        singles = sum(1 for s in sizes if s == 1)
        small = sum(1 for s in sizes if 2 <= s <= 5)
        medium = sum(1 for s in sizes if 6 <= s <= 20)
        large = sum(1 for s in sizes if s > 20)
        print(f"  Singletons: {singles}, Small (2-5): {small}, Medium (6-20): {medium}, Large (>20): {large}")

    print("\n" + "-" * 75)
    print("TOP 10 HETEROGENEOUS CLUSTERS")
    print("-" * 75)

    # Sort by number of T-groups
    disagreements = sorted(results['tgroup_disagreements'],
                          key=lambda x: len(x['tgroups']), reverse=True)

    for i, d in enumerate(disagreements[:10]):
        print(f"\n{i+1}. Cluster rep: {d['representative']}")
        print(f"   Members: {d['members']}")
        print(f"   Sources: {', '.join(d['sources'])}")
        print(f"   T-groups: {', '.join(d['tgroups'][:5])}" +
              ("..." if len(d['tgroups']) > 5 else ""))


def main():
    parser = argparse.ArgumentParser(description='MMseqs2 clustering analysis for V1 vs V2')
    parser.add_argument('--validation-dir', type=Path, required=True,
                        help='Directory containing batch_* subdirectories')
    parser.add_argument('--output-dir', type=Path, default=Path('mmseqs_analysis'),
                        help='Output directory for analysis files')
    parser.add_argument('--identity', type=float, default=0.99,
                        help='Sequence identity threshold (default: 0.99)')
    parser.add_argument('--coverage', type=float, default=0.9,
                        help='Coverage threshold (default: 0.9)')
    parser.add_argument('--ecod-limit', type=int, default=None,
                        help='Limit number of ECOD sequences (for testing)')
    parser.add_argument('--skip-extraction', action='store_true',
                        help='Skip extraction, use existing FASTA files')
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    combined_fasta = args.output_dir / 'combined_domains.fasta'
    tgroup_file = args.output_dir / 'tgroup_assignments.tsv'

    if not args.skip_extraction:
        # Clear output files
        if combined_fasta.exists():
            combined_fasta.unlink()
        if tgroup_file.exists():
            tgroup_file.unlink()

        # Extract sequences
        print("Extracting ECOD F99 representative sequences...")
        ecod_count = extract_ecod_f99_representatives(
            combined_fasta, tgroup_file, limit=args.ecod_limit
        )
        print(f"  Extracted {ecod_count} ECOD sequences")

        print("\nExtracting V1 SwissProt domain sequences...")
        v1_count = extract_v1_validation_sequences(
            args.validation_dir, combined_fasta, tgroup_file
        )
        print(f"  Extracted {v1_count} V1 sequences")

        print("\nExtracting V2 domain sequences...")
        v2_count = extract_v2_sequences(
            args.validation_dir, combined_fasta, tgroup_file
        )
        print(f"  Extracted {v2_count} V2 sequences")

        print(f"\nTotal sequences: {ecod_count + v1_count + v2_count}")

    # Run clustering
    cluster_tsv = run_mmseqs_clustering(
        combined_fasta, args.output_dir,
        identity=args.identity, coverage=args.coverage
    )

    # Analyze results
    print("\nAnalyzing clusters...")
    results = analyze_clusters(cluster_tsv, tgroup_file)
    print_analysis(results)

    # Save detailed results
    import json
    results_file = args.output_dir / 'analysis_results.json'
    # Remove large list for JSON serialization
    results_for_json = {k: v for k, v in results.items() if k != 'cluster_sizes'}
    results_for_json['cluster_size_distribution'] = {
        'min': min(results['cluster_sizes']),
        'max': max(results['cluster_sizes']),
        'mean': sum(results['cluster_sizes']) / len(results['cluster_sizes']),
        'singletons': sum(1 for s in results['cluster_sizes'] if s == 1),
    }
    with open(results_file, 'w') as f:
        json.dump(results_for_json, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")


if __name__ == '__main__':
    main()
