# DPAM Version Differences: GitHub v2.0 vs Production Automatic

This document compares the DPAM GitHub implementation (13 steps) with the DPAM Automatic production system (25 steps).

## Overview

**DPAM GitHub v2.0** (13 steps): Domain identification pipeline
- Steps 1-13: Core domain parsing using HHsearch, Foldseek, and DALI
- Output: Predicted domain boundaries with structural evidence

**DPAM Automatic Production** (25 steps): Complete pipeline with ML-based ECOD classification
- Steps 1-13: Domain identification (same as GitHub)
- Steps 14-19: DOMASS machine learning pipeline for ECOD classification
- Steps 20-25: Refinement, filtering, and final output generation

## Phase 1: Domain Identification (Steps 1-13)

**Status**: Implemented in both GitHub and Production versions

These steps are functionally identical between versions, identifying domain boundaries through sequence and structural similarity searches.

### Current Implementation Status (GitHub v2.0)

| Step | Status | Notes |
|------|--------|-------|
| 1 | ✅ Complete | Structure preparation |
| 2 | ✅ Complete | HHsearch sequence search |
| 3 | ✅ Complete | Foldseek structure search |
| 4 | ✅ Complete | Filter Foldseek hits |
| 5 | ✅ Complete | Map to ECOD domains |
| 6 | ✅ Complete | Get DALI candidates |
| 7 | ⚠️ Blocked | **libgfortran.so.3 dependency issue** |
| 8 | ❌ Pending | Analyze DALI results |
| 9 | ❌ Pending | Get support scores |
| 10 | ❌ Pending | Filter domain candidates |
| 11 | ❌ Pending | SSE analysis |
| 12 | ❌ Pending | Disorder prediction |
| 13 | ❌ Pending | Parse final domains |

**Critical Blocker**: Step 7 requires `libgfortran.so.3` for DALI's `puu` binary. This must be resolved before proceeding with Steps 8-13.

## Phase 2: DOMASS ML Classification (Steps 14-19)

**Status**: Production only, not yet implemented in GitHub v2.0

This phase uses a TensorFlow neural network to predict ECOD classifications for identified domains.

### Step 14: Parse Domains

**Purpose**: Identify domain boundaries by integrating structural distance, PAE confidence, HHsearch evidence, and DALI evidence using probabilistic scoring

**Key Concept**: Each residue pair has a probability of being in the same domain, calculated from four independent evidence sources. Domains are regions where residue pairs have high co-occurrence probability.

**Algorithm Overview**:

```python
# 1. Load evidence sources
pdb_distances = load_structure('step2/{species}/{prot}.pdb')
pae_errors = load_json('{species}/AF-{prot}-F1-predicted_aligned_error_{version}.json')
hhsearch_hits = load_domains('step11/{species}/{prot}.goodDomains')
dali_hits = load_domains('step11/{species}/{prot}.goodDomains')
disorder = load_disorder('step13/{species}/{prot}.diso')

# 2. Convert evidence to probabilities
for res1, res2 in all_pairs:
    p_dist = get_PDB_prob(pdb_distances[res1][res2])
    p_pae = get_PAE_prob(pae_errors[res1][res2])
    p_hh = get_HHS_prob(hhsearch_score[res1][res2])
    p_dali = get_DALI_prob(dali_zscore[res1][res2])

    # Geometric mean (assumes independence)
    p_total = (p_dist * p_pae * p_hh * p_dali) ** 0.25

# 3. Initial segmentation (5-residue windows)
segments = []
for chunk in sliding_window(residues, size=5):
    ordered_chunk = [r for r in chunk if r not in disorder]
    if len(ordered_chunk) >= 3:
        segments.append(ordered_chunk)

# 4. Cluster segments by probability
segment_pairs = []
for seg_i, seg_j in combinations(segments, 2):
    mean_prob = mean(p_total[r1][r2] for r1 in seg_i for r2 in seg_j if r1+5 < r2)
    if mean_prob > 0.64:  # threshold
        segment_pairs.append((i, j, mean_prob))

# 5. Build domains via greedy merging
domains = []
for (seg_i, seg_j, prob) in sorted(segment_pairs, key=prob, reverse=True):
    # Find existing domains containing these segments
    merge_candidates = find_domains_containing(seg_i, seg_j)

    if len(merge_candidates) == 2:
        # Decide if two domains should merge
        if should_merge(domain1, domain2, inter_prob, param=1.1):
            merge_domains(domain1, domain2)
    elif len(merge_candidates) == 1:
        # Add new segment to existing domain
        if should_extend(domain, new_seg, inter_prob, param=1.1):
            domain.add(new_seg)
    else:
        # Create new domain
        domains.append(Domain([seg_i, seg_j]))

# 6. Refine boundaries (fill short gaps)
for domain in domains:
    for gap in find_gaps(domain, max_length=20):
        if not overlaps_other_domains(gap) or gap_length <= 10:
            domain.add_residues(gap)

# 7. Final filtering
final_domains = []
for domain in domains:
    # Remove short terminal segments (<10 residues)
    trimmed = trim_short_segments(domain, min_length=10)
    if len(trimmed) >= 25:
        final_domains.append(trimmed)
```

**Probability Lookup Tables**:

```python
# PDB distance (Ångströms) → probability
get_PDB_prob(dist):
    ≤3Å:  0.95  # Very close, likely same domain
    ≤6Å:  0.94
    ≤12Å: 0.91
    ≤24Å: 0.77
    ≤50Å: 0.33
    >200Å: 0.06  # Far apart, likely different domains

# PAE (Predicted Aligned Error) → probability
get_PAE_prob(error):
    ≤1Å:  0.97  # High confidence
    ≤5Å:  0.61
    ≤10Å: 0.48
    ≤20Å: 0.39
    >28Å: 0.11  # Low confidence

# HHsearch probability → probability
get_HHS_prob(hh_prob):
    ≥180: 0.98  # Very strong hit (prob>100 + bonus)
    ≥100: 0.81
    ≥50:  0.76
    <50:  0.50  # Weak or no hit

# DALI z-score → probability
get_DALI_prob(z_score):
    ≥35:  0.95  # Very significant
    ≥20:  0.93
    ≥10:  0.74
    ≥5:   0.57
    <2:   0.50  # Weak or no hit
```

**HHsearch/DALI Score Augmentation**:

To reward residue pairs covered by multiple hits:
```python
# HHsearch: Add bonus for multiple hits
if num_hits > 10:
    score = max_probability + 100
else:
    score = max_probability + (num_hits * 10 - 10)

# DALI: Add bonus for multiple z-scores
if num_hits > 5:
    score = max_zscore + 5
else:
    score = max_zscore + (num_hits - 1)
```

**Key Parameters**:
- `param1 = 0.64`: Minimum probability threshold for segment co-occurrence
- `param2 = 1.1`: Merge tolerance (inter-domain prob must be ≥ intra-domain prob / 1.1)
- Minimum domain length: 25 residues (after refinement)
- Minimum segment length for trimming: 10 residues

**Input Files**:
- `step1/{species}/{prot}.fa`: Sequence
- `step2/{species}/{prot}.pdb`: Structure with coordinates
- `step11/{species}/{prot}.goodDomains`: HHsearch/DALI evidence
- `step13/{species}/{prot}.diso`: Disordered regions
- `{species}/AF-{prot}-F1-predicted_aligned_error_{version}.json`: PAE matrix

**Output Format** (`step14/{species}/{prot}.domains`):
```
D1  25-150,160-200
D2  210-350
D3  400-550
```

**Refinement Stages**:

1. **V0**: Initial segments (5-residue windows, ≥3 ordered, ≥20 total)
2. **V1**: Clustered domains (greedy merging by probability)
3. **V2**: Gap-filled domains (add short linkers ≤20 residues)
4. **V3**: Trimmed domains (remove short segments, enforce ≥25 length)

**Merge Decision Logic**:

Two domains merge if:
- Either domain has ≤20 residue pairs (too small), OR
- `inter_prob * 1.1 ≥ intra_prob` (domains are nearly as cohesive as merged unit)

**Purpose**: This probabilistic approach integrates:
- **Local geometry** (PDB distances)
- **Model confidence** (PAE)
- **Sequence homology** (HHsearch)
- **Structural similarity** (DALI)

All sources contribute equally (geometric mean), avoiding bias from any single method.

### Step 15: Prepare DOMASS Features

**Purpose**: Extract and format all features for DOMASS ML model, combining domain properties with HHsearch and DALI evidence

**Key Concept**: For each domain from Step 14, find all overlapping ECOD hits from HHsearch (Step 5) and DALI (Step 9), then extract 17 features per domain-ECOD pair. Only ECOD templates found by BOTH methods are included.

**Algorithm**:

```python
def check_overlap(residsA, residsB):
    """Domains overlap if ≥50% of either set matches."""
    overlap = set(residsA) & set(residsB)
    return (len(overlap) >= len(residsA) * 0.5 or
            len(overlap) >= len(residsB) * 0.5)

# 1. Load ECOD hierarchy (T-group, H-group)
ecod_to_tgroup = load_ecod_hierarchy('ecod.latest.domains')

# 2. Count secondary structure elements per domain
for domain in domains:
    sse_counts = count_sse('step12/{species}/{prot}.sse', domain.resids)
    domain.helix_count = count_helices(sse_counts, min_length=6)
    domain.strand_count = count_strands(sse_counts, min_length=3)

# 3. Load HHsearch hits with rank calculation
hhsearch_hits = []
qres_to_hgroups = {}  # Track which H-groups cover each query residue

for hit in load_hhsearch('step5/{species}/{prot}.result'):
    # Calculate rank: average number of H-groups covering each residue
    for qres in hit.query_resids:
        qres_to_hgroups[qres].add(hit.hgroup)

    ranks = [len(qres_to_hgroups[qres]) for qres in hit.query_resids]
    hit.rank = mean(ranks) / 10  # Normalize

    hhsearch_hits.append(hit)

max_hh_rank = max(hit.rank for hit in hhsearch_hits) or 100

# 4. Load DALI hits with ECOD residue mapping
dali_hits = []
for hit in load_dali('step9/{species}/{prot}_good_hits'):
    # Map PDB residues to ECOD canonical numbering
    ecod_map = load_map(f'ECOD_maps/{hit.ecod_id}.map')
    hit.template_resids = [ecod_map[r] for r in hit.raw_template_resids]
    dali_hits.append(hit)

max_dali_rank = max(hit.rank for hit in dali_hits) or 100

# 5. For each domain, find overlapping hits
for domain in domains:
    # Find HHsearch hits overlapping this domain
    hh_overlaps = {}
    for hit in hhsearch_hits:
        if check_overlap(domain.resids, hit.query_resids):
            # Keep best hit per ECOD (highest probability)
            if hit.ecod not in hh_overlaps or hit.prob > hh_overlaps[hit.ecod].prob:
                hh_overlaps[hit.ecod] = hit

    # Find DALI hits overlapping this domain
    dali_overlaps = {}
    for hit in dali_hits:
        if check_overlap(domain.resids, hit.query_resids):
            # Keep best hit per ECOD (highest z-score)
            if hit.ecod not in dali_overlaps or hit.zscore > dali_overlaps[hit.ecod].zscore:
                dali_overlaps[hit.ecod] = hit

    # 6. Generate features for ECODs found by BOTH methods
    for ecod in set(hh_overlaps.keys()) & set(dali_overlaps.keys()):
        hh = hh_overlaps[ecod]
        dali = dali_overlaps[ecod]

        # Calculate consensus metrics
        common_qres = set(hh.query_resids) & set(dali.query_resids)
        consensus_cov = len(common_qres) / domain.length

        # Build residue mapping
        hh_map = {hh.query_resids[i]: hh.template_resids[i]
                  for i in range(len(hh.query_resids))}
        dali_map = {dali.query_resids[i]: dali.template_resids[i]
                    for i in range(len(dali.query_resids))}

        # Calculate template position differences
        consensus_diffs = []
        for qres in common_qres:
            diff = abs(hh_map[qres] - dali_map[qres])
            consensus_diffs.append(diff)

        consensus_diff = mean(consensus_diffs) if consensus_diffs else -1

        # Output 17 features
        write_features(
            domain_id=domain.name,
            domain_range=domain.range,
            tgroup=ecod_to_tgroup[ecod],
            ecod_id=ecod,
            # Domain properties (3 features)
            domain_length=domain.length,
            helix_count=domain.helix_count,
            strand_count=domain.strand_count,
            # HHsearch features (3 features)
            hh_prob=hh.probability,
            hh_coverage=hh.coverage,
            hh_rank=hh.rank,
            # DALI features (5 features)
            dali_zscore=dali.zscore,
            dali_qscore=dali.qscore,
            dali_ztile=dali.zscore_percentile,
            dali_qtile=dali.qscore_percentile,
            dali_rank=dali.rank,
            # Consensus features (2 features)
            consensus_diff=consensus_diff,
            consensus_cov=consensus_cov,
            # Metadata (not used by model)
            hh_name=hh.hit_name,
            dali_name=dali.hit_name,
            dali_rotation=(dali.rot1, dali.rot2, dali.rot3),
            dali_translation=dali.trans
        )

    # 7. Handle ECODs found by only one method
    # HHsearch-only hits (assign default DALI values)
    for ecod in set(hh_overlaps.keys()) - set(dali_overlaps.keys()):
        write_features(...,
            dali_zscore=0, dali_qscore=0,
            dali_ztile=10, dali_qtile=10,
            dali_rank=max_dali_rank,
            consensus_diff=-1, consensus_cov=0)

    # DALI-only hits (assign default HHsearch values)
    for ecod in set(dali_overlaps.keys()) - set(hh_overlaps.keys()):
        write_features(...,
            hh_prob=0, hh_coverage=0, hh_rank=max_hh_rank,
            consensus_diff=-1, consensus_cov=0)
```

**Feature Definitions** (17 total):

| # | Feature | Description | Source |
|---|---------|-------------|--------|
| 1 | domain_length | Number of residues in domain | Step 14 |
| 2 | helix_count | Number of α-helices (≥6 residues) | Step 12 (SSE) |
| 3 | strand_count | Number of β-strands (≥3 residues) | Step 12 (SSE) |
| 4 | hh_prob | HHsearch probability (0-1) | Step 5 |
| 5 | hh_coverage | HHsearch coverage (0-1) | Step 5 |
| 6 | hh_rank | Average H-group redundancy / 10 | Step 5 |
| 7 | dali_zscore | DALI z-score | Step 9 |
| 8 | dali_qscore | DALI q-score | Step 9 |
| 9 | dali_ztile | DALI z-score percentile (0-10) | Step 9 |
| 10 | dali_qtile | DALI q-score percentile (0-10) | Step 9 |
| 11 | dali_rank | DALI hit rank / 10 | Step 9 |
| 12 | consensus_diff | Mean template position difference | Calculated |
| 13 | consensus_cov | Fraction of domain in both alignments | Calculated |
| 14-17 | metadata | Hit names, rotation, translation | Not used by model |

**Rank Calculation Details**:

HHsearch rank measures alignment ambiguity:
```python
# For each query residue, count how many H-groups cover it
qres_to_hgroups[residue] = {hgroup1, hgroup2, ...}

# Rank = average number of competing H-groups
rank = mean(len(qres_to_hgroups[r]) for r in query_resids) / 10
```

Higher rank = more ambiguous (multiple fold families match).

**Overlap Threshold**: 50% - more permissive than Step 18's 33% threshold because we want to capture all potential ECOD assignments for ML model evaluation.

**Input Files**:
- `step14/{species}/{prot}.domains`: Parsed domains
- `step5/{species}/{prot}.result`: HHsearch hits with alignments
- `step9/{species}/{prot}_good_hits`: DALI hits with alignments
- `step12/{species}/{prot}.sse`: Secondary structure elements
- `ECOD_maps/{ecod_id}.map`: PDB→ECOD residue numbering
- `ecod.latest.domains`: ECOD hierarchy (T-groups, H-groups)

**Output Format** (`step15/{species}/{prot}.data`):
```
domID  domRange  tgroup  ecodid  domLen  Helix_num  Strand_num  HHprob  HHcov  HHrank  Dzscore  Dqscore  Dztile  Dqtile  Drank  Cdiff  Ccov  HHname  Dname  Drot1  Drot2  Drot3  Dtrans
D1     25-150    1.10.8  e00123  126     5          6           0.987   0.843  1.20    23.4     0.765    2.1     3.4     0.50   2.34   0.753  hit1    hit2   ...
```

**Note**: Only 13 of 17 features are used by the Step 16 neural network (columns 5-17, excluding metadata).

### Step 16: Run DOMASS Neural Network

**Purpose**: Predict probability that each domain-ECOD pair is correct

**Implementation Details**:

```python
# TensorFlow model architecture
Input: 13 features (float32)
Hidden Layer: 64 neurons, ReLU activation
Output: 2-class softmax (incorrect=0, correct=1)

# Model checkpoint
checkpoint = "domass_epo29.ckpt"

# Feature normalization (from Step 15)
features_normalized = (features - mean) / std

# Inference
predictions = model.predict(features_normalized)
dpam_probability = predictions[:, 1]  # Probability of correct assignment
```

**Input Format** (from Step 15):
```
domain_name  domain_range  ecod_id  ecod_tgroup  [13 features...]
```

**Output Format**:
```
domain_name  domain_range  ecod_tgroup  ecod_ref  DPAM_prob  [input_features...]
```

**Key Characteristics**:
- Batch processing of all domain-ECOD pairs
- Uses pre-trained model (epoch 29)
- Binary classification: correct vs incorrect ECOD assignment
- Output probability (0.0-1.0) used for confidence filtering in Step 17

### Step 17: Filter Confident Predictions

**Purpose**: Select high-confidence ECOD classifications with quality labels

**Algorithm**:

```python
# Filter by probability threshold
THRESHOLD = 0.6

for domain in domains:
    # Get all predictions for this domain
    predictions = get_predictions(domain)

    # Group by T-group (finest ECOD level)
    tgroup_to_best = {}
    for pred in predictions:
        if pred.prob >= THRESHOLD:
            if pred.tgroup not in tgroup_to_best:
                tgroup_to_best[pred.tgroup] = pred.prob
            else:
                tgroup_to_best[pred.tgroup] = max(
                    tgroup_to_best[pred.tgroup],
                    pred.prob
                )

    # Find similar T-groups (within 0.05 of best)
    similar_tgroups = set()
    for tgroup, prob in tgroup_to_best.items():
        if prob >= max(tgroup_to_best.values()) - 0.05:
            similar_tgroups.add(tgroup)

    # Extract H-groups (X.Y from X.Y.Z)
    similar_hgroups = set()
    for tgroup in similar_tgroups:
        parts = tgroup.split('.')
        hgroup = f"{parts[0]}.{parts[1]}"
        similar_hgroups.add(hgroup)

    # Quality classification
    if len(similar_tgroups) == 1:
        quality = 'good'      # Unambiguous T-group
    elif len(similar_hgroups) == 1:
        quality = 'ok'        # Same H-group (family consensus)
    else:
        quality = 'bad'       # Conflicting families
```

**Quality Labels**:
- **good**: Single T-group above threshold (unambiguous classification)
- **ok**: Multiple T-groups but same H-group (family-level consensus)
- **bad**: Multiple conflicting H-groups (ambiguous)

**Output Format**:
```
domain_name  domain_range  tgroup  ecod_ref  DPAM_prob  quality  [features...]
```

**Filtering Rules**:
1. Minimum probability: 0.6
2. T-group similarity window: 0.05 (if prob ≥ best_prob - 0.05)
3. Quality based on hierarchical agreement

### Step 18: Get Alignment Mappings

**Purpose**: Map domain residues to template ECOD structure residues using original alignments

**Key Concept**: For each confident domain-ECOD prediction from Step 17, extract the actual residue-to-residue mappings from the original HHsearch (Step 5) and DALI (Step 9) alignments.

**Algorithm**:

```python
def get_resids(domain_range):
    """Convert range string '10-50,60-100' to list of residue IDs"""
    resids = []
    for seg in domain_range.split(','):
        start, end = map(int, seg.split('-'))
        resids.extend(range(start, end + 1))
    return resids

def check_overlap(residsA, residsB):
    """
    Check if two residue sets overlap significantly.

    Rules:
    - Must have ≥33% overlap relative to A
    - If yes, must have either:
      - ≥50% overlap relative to A, OR
      - ≥50% overlap relative to B
    """
    overlap = set(residsA) & set(residsB)
    if len(overlap) >= len(residsA) * 0.33:
        if len(overlap) >= len(residsA) * 0.5 or \
           len(overlap) >= len(residsB) * 0.5:
            return True
    return False

def get_range(resids):
    """Convert residue list back to range string with no gaps"""
    resids.sort()
    segs = []
    for resid in resids:
        if not segs or resid > segs[-1][-1] + 1:
            segs.append([resid])
        else:
            segs[-1].append(resid)
    return ','.join(f"{seg[0]}-{seg[-1]}" for seg in segs)

# Main mapping logic
for domain in confident_domains:
    domain_resids = get_resids(domain.range)

    # Find overlapping HHsearch hits
    for hh_hit in hhsearch_results:
        if check_overlap(domain_resids, hh_hit.query_resids):
            # Map using ECOD residue numbering
            ecod_map = load_ecod_map(hh_hit.ecod_id)  # .map file

            mapped_template_resids = []
            for i, qres in enumerate(hh_hit.query_resids):
                if qres in domain_resids:
                    tres = hh_hit.template_resids[i]
                    if tres in ecod_map:
                        # Convert to ECOD canonical numbering
                        mapped_tres = ecod_map[tres]
                        mapped_template_resids.append(mapped_tres)

            hh_template_range = get_range(mapped_template_resids)

    # Find overlapping DALI hits (similar process)
    for dali_hit in dali_results:
        if check_overlap(domain_resids, dali_hit.query_resids):
            mapped_template_resids = []
            for i, qres in enumerate(dali_hit.query_resids):
                if qres in domain_resids:
                    tres = dali_hit.template_resids[i]
                    mapped_template_resids.append(tres)

            dali_template_range = get_range(mapped_template_resids)
```

**Input Files**:
- `step5/{prefix}.result`: HHsearch alignments with query/template ranges
- `step9/{prefix}_good_hits`: DALI alignments with residue mappings
- `step17/{prefix}.result`: Confident domain predictions
- `ECOD_maps/{ecod_id}.map`: ECOD residue numbering maps

**Output Format** (`step18/{prefix}.data`):
```
domain_name  domain_range  ecod_id  tgroup  DPAM_prob  quality  HH_template_range  DALI_template_range
```

**Example**:
```
d1  25-150,160-200  e001822778  1.10.150.10  0.85  good  31-156,166-206  33-154,168-204
d2  210-350         e001148094  2.60.40.10   0.72  ok   215-355         na
```

**Special Cases**:
- `na` if no overlapping alignment found
- ECOD map converts PDB residue numbering to canonical ECOD numbering
- Handles insertions/deletions in alignments

**Purpose**: This mapping enables:
1. Validation that domain boundaries match template structure
2. Structure-based refinement in later steps
3. Confidence assessment based on alignment agreement

### Step 19: Get Merge Candidates

**Purpose**: Identify domain pairs that should potentially be merged based on shared ECOD template coverage

**Key Concept**: When two predicted domains both match different regions of the same ECOD template with high confidence, they may actually be parts of a single domain that was incorrectly split. This step identifies such merge candidates.

**Algorithm**:

```python
# 1. Load position-specific weights for each ECOD template
for ecod in needed_ecods:
    if has_weight_file(ecod):
        # Load empirical weights (from structural/evolutionary analysis)
        ecod_weights[ecod] = load_weights(f'posi_weights/{ecod}.weight')
        total_weight[ecod] = sum(ecod_weights[ecod].values())
    else:
        # Uniform weights if no data available
        ecod_weights[ecod] = {i: 1.0 for i in range(1, ecod_length[ecod]+1)}
        total_weight[ecod] = ecod_length[ecod]

# 2. Calculate weighted coverage for each domain-ECOD hit
for domain in domains:
    for hit in domain_hits:
        # Get aligned template residues (prefer DALI > HHsearch)
        if len(dali_resids) > len(hhsearch_resids) * 0.5:
            template_resids = dali_resids
        else:
            template_resids = hhsearch_resids

        # Calculate weighted coverage
        covered_weight = sum(ecod_weights[ecod][res]
                           for res in template_resids)
        coverage_ratio = covered_weight / total_weight[ecod]

        domain_hits[domain].append({
            'ecod': ecod,
            'tgroup': tgroup,
            'prob': prob,
            'coverage': coverage_ratio
        })

# 3. Find domain pairs that share ECOD templates
for ecod in ecods:
    hits = ecod_to_hits[ecod]
    if len(hits) > 1:
        # Check all pairs of domains hitting this ECOD
        for domain1, domain2 in combinations(hits, 2):
            # Both domains must have high confidence
            if (domain1.prob + 0.1 >= best_prob[domain1.name] and
                domain2.prob + 0.1 >= best_prob[domain2.name]):

                # Check template residue overlap
                common = domain1.template_resids & domain2.template_resids

                # Domains must cover different regions (< 25% overlap)
                if (len(common) < 0.25 * len(domain1.template_resids) and
                    len(common) < 0.25 * len(domain2.template_resids)):

                    # Record as potential merge candidate
                    merge_candidates.add((domain1.name, domain2.name))
                    supporting_ecods[pair].append(ecod)

# 4. Filter merge candidates by support vs opposition
for (domain1, domain2) in merge_candidates:
    support_ecods = supporting_ecods[(domain1, domain2)]

    # Count ECODs that oppose merging domain1
    against_ecods1 = set()
    for hit in domain1_hits:
        if (hit.prob + 0.1 >= best_prob[domain1] and
            hit.coverage > 0.5 and
            hit.ecod not in support_ecods):
            against_ecods1.add(hit.ecod)

    # Count ECODs that oppose merging domain2
    against_ecods2 = set()
    for hit in domain2_hits:
        if (hit.prob + 0.1 >= best_prob[domain2] and
            hit.coverage > 0.5 and
            hit.ecod not in support_ecods):
            against_ecods2.add(hit.ecod)

    # Merge if support exceeds opposition for at least one domain
    if (len(support_ecods) > len(against_ecods1) or
        len(support_ecods) > len(against_ecods2)):
        final_merge_pairs.append((domain1, domain2))
```

**Input Files**:
- `step18/{prefix}.data`: Domain-ECOD mappings with template ranges
- `ECOD_length`: Template lengths
- `posi_weights/{ecod}.weight`: Position-specific weights (optional)

**Weight File Format** (`posi_weights/{ecod}.weight`):
```
resid  aa  dssp  weight
1      M   C     0.85
2      K   H     1.23
3      L   H     1.45
...
```

Weights represent structural/evolutionary importance of each position. Higher weights = more functionally/structurally critical.

**Output Format** (`step19/{prefix}.result`):
```
domain1  domain1_range  domain2  domain2_range
d1       25-150         d2       160-250
d3       300-400        d5       420-500
```

**Output Format** (`step19/{prefix}.info` - debug info):
```
d1,d2    e001822778,e001148094
d3,d5    e000976739
```

**Merge Criteria Summary**:

1. **Shared Template**: Both domains must hit the same ECOD template
2. **High Confidence**: Both predictions within 0.1 of their respective best scores
3. **Non-overlapping**: Template regions must overlap < 25%
4. **Support > Opposition**: Supporting ECODs must outnumber opposing ECODs

**Rationale**: Initial domain parsing (Steps 1-13) may over-split domains due to:
- Low-confidence regions between structured segments
- Flexible linkers in AlphaFold models
- Conservative boundary definitions

This step identifies cases where multiple predicted domains collectively match a single ECOD template better than they match separate templates, suggesting they should be merged into one domain.

## Phase 3: Refinement and Output (Steps 20-24)

**Status**: Production only, not yet implemented in GitHub v2.0

These steps perform final refinement, conflict resolution, and output formatting.

### Step 20: Extract Domains

**Purpose**: Extract PDB files for domains that are candidates for merging (from Step 19)

**Key Concept**: For each domain involved in a potential merge, create a separate PDB file containing only that domain's residues. These files are needed for structural comparison in subsequent steps.

**Algorithm**:

```python
# 1. Collect all domains from merge candidates
domains_to_extract = []
merge_pairs = load_merge_pairs('step19/{species}/{prot}.result')

for (domain1, domain1_range, domain2, domain2_range) in merge_pairs:
    # Parse range to residue list
    domain1_resids = parse_range(domain1_range)
    domain2_resids = parse_range(domain2_range)

    domains_to_extract.append((prot, domain1, domain1_resids))
    domains_to_extract.append((prot, domain2, domain2_resids))

# Remove duplicates (same domain may appear in multiple pairs)
domains_to_extract = unique(domains_to_extract)

# 2. Extract PDB for each domain
for (prot, domain_name, resids) in domains_to_extract:
    input_pdb = f'step2/{species}/{prot}.pdb'
    output_pdb = f'step20/{species}/{prot}_{domain_name}.pdb'

    with open(input_pdb, 'r') as fin:
        with open(output_pdb, 'w') as fout:
            for line in fin:
                if line.startswith('ATOM'):
                    resid = int(line[22:26])  # PDB format columns
                    if resid in resids:
                        fout.write(line)
```

**Input Files**:
- `step19/{species}/{prot}.result`: Merge candidate pairs
- `step2/{species}/{prot}.pdb`: Original structure with secondary structure

**Output Format**:
- `step20/{species}/{prot}_{domain_name}.pdb`: One PDB per domain involved in merging

**Example**:

Given merge candidates in `step19/human/P12345.result`:
```
d1  25-150,160-200  d2  210-350
d3  400-500         d4  510-600
```

Produces:
```
step20/human/P12345_d1.pdb  (residues 25-150, 160-200)
step20/human/P12345_d2.pdb  (residues 210-350)
step20/human/P12345_d3.pdb  (residues 400-500)
step20/human/P12345_d4.pdb  (residues 510-600)
```

**Purpose**: These extracted domain PDBs are used in Step 21 for structural comparison to determine if merging is geometrically favorable.

**Note**: Only extracts ATOM records, preserving original PDB formatting and residue numbering.

### Step 21: Compare Domains

**Purpose**: Determine if merge candidate domain pairs are structurally connected or spatially adjacent

**Key Concept**: Two domains should only be merged if they are either:
1. **Sequence-connected**: Close in linear sequence (≤5 residues apart in structured regions), OR
2. **Structure-connected**: Form a stable interface with sufficient atomic contacts (≥9 close contacts at ≤8Å)

**Algorithm**:

```python
def get_seq_dist(residsA, residsB, good_resids):
    """
    Check if two domains are connected in sequence space.

    Args:
        residsA: Residue set for domain A
        residsB: Residue set for domain B
        good_resids: Ordered list of all structured residues

    Returns:
        1 if connected (≤5 residues apart), 0 otherwise
    """
    # Map residues to indices in structured region
    indsA = [i for i, res in enumerate(good_resids) if res in residsA]
    indsB = [i for i, res in enumerate(good_resids) if res in residsB]

    # Check if any pair is within 5 positions
    for indA in indsA:
        for indB in indsB:
            if abs(indA - indB) <= 5:
                return 1  # Connected
    return 0

def get_structure_dist(pdb1, pdb2, residsA, residsB):
    """
    Check if two domains form a structural interface.

    Returns:
        Number of residue pairs with inter-atomic distance ≤ 8Å
    """
    # Load all atom coordinates from both domains
    resid_to_coords = {}
    for pdb_file in [pdb1, pdb2]:
        for line in pdb_file:
            if line.startswith('ATOM'):
                resid = int(line[22:26])
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                resid_to_coords.setdefault(resid, []).append([x, y, z])

    # Count interface contacts
    interface_count = 0
    for residA in residsA:
        for residB in residsB:
            # Find minimum distance between any atoms
            min_dist = float('inf')
            for coordA in resid_to_coords[residA]:
                for coordB in resid_to_coords[residB]:
                    dist = sqrt(
                        (coordA[0] - coordB[0])**2 +
                        (coordA[1] - coordB[1])**2 +
                        (coordA[2] - coordB[2])**2
                    )
                    min_dist = min(min_dist, dist)

            if min_dist <= 8.0:
                interface_count += 1

    return interface_count

# Main comparison logic
for (prot, domain1, range1, domain2, range2) in merge_candidates:
    # Load structured regions (from Step 14 domain parsing)
    good_resids = load_structured_residues(
        f'step14/{species}/{prot}.domains'
    )

    residsA = parse_range(range1)
    residsB = parse_range(range2)

    # Test 1: Sequence proximity
    if get_seq_dist(residsA, residsB, good_resids):
        judgment = 1  # Sequence-connected
    else:
        # Test 2: Structural interface
        pdb1 = f'step20/{species}/{prot}_{domain1}.pdb'
        pdb2 = f'step20/{species}/{prot}_{domain2}.pdb'
        interface_count = get_structure_dist(pdb1, pdb2, residsA, residsB)

        if interface_count >= 9:
            judgment = 2  # Structure-connected
        else:
            judgment = 0  # Not connected (reject merge)
```

**Input Files**:
- `step21_{species}_{part}.list`: List of domain pairs to compare (from Step 19/20)
- `step14/{species}/{prot}.domains`: Structured regions (all domains)
- `step20/{species}/{prot}_{domain}.pdb`: Domain PDB files

**Input Format** (`step21_{species}_{part}.list`):
```
prot  domain1  range1           domain2  range2
P1    d1       25-150,160-200   d2       210-350
P2    d3       400-500          d4       510-600
```

**Output Format** (`step21_{species}_{part}.result`):
```
prot  domain1  domain2  judgment  range1           range2
P1    d1       d2       1         25-150,160-200   210-350
P2    d3       d4       2         400-500          510-600
P3    d5       d6       0         100-200          300-400
```

**Judgment Values**:
- **0**: Not connected - domains are isolated, should NOT merge
- **1**: Sequence-connected - domains are close in linear sequence (≤5 structured residues apart)
- **2**: Structure-connected - domains form interface with ≥9 residue pairs at ≤8Å distance

**Thresholds Explained**:

1. **Sequence distance ≤5**: Allows for short flexible linkers or disordered regions between domains
2. **Contact distance ≤8Å**: Standard protein interface cutoff (slightly longer than typical hydrogen bonds at ~3-4Å to capture van der Waals contacts)
3. **Minimum 9 contacts**: Ensures genuine interface, not just transient or crystal packing contacts

**Parallel Processing**: Uses job list files (`step21_{species}_{part}.list`) to distribute comparisons across multiple workers, as structural distance calculations are computationally expensive.

**Purpose**: This step prevents merging of domains that are:
- Structurally independent (separate globular units)
- Connected only by long flexible linkers (>5 residues unstructured)
- Potentially artificial splits from AlphaFold model artifacts

Only judgment=1 or judgment=2 pairs proceed to final merging in Step 22+.

### Step 22: Merge Domains

**Purpose**: Perform actual domain merging using transitive closure to handle multi-domain merge groups

**Key Concept**: If domain A should merge with B, and B should merge with C, then all three (A, B, C) should be merged into a single domain. This requires graph clustering, not just pairwise merging.

**Algorithm**:

```python
def get_range(resids):
    """Convert residue set to compact range string."""
    if not resids:
        return 'na'

    resids = sorted(resids)
    segs = []
    for resid in resids:
        if not segs or resid > segs[-1][-1] + 1:
            segs.append([resid])
        else:
            segs[-1].append(resid)

    return ','.join(f"{seg[0]}-{seg[-1]}" for seg in segs)

# 1. Load validated merge pairs (judgment > 0)
merge_pairs = []
for line in step21_results:
    if judgment > 0:  # Only connected pairs
        merge_pairs.append({domain1, domain2})

# 2. Build merge groups via transitive closure
groups = []
for pair in merge_pairs:
    groups.append(pair)

# Iteratively merge intersecting groups
while True:
    new_groups = []
    for group in groups:
        # Check if this group intersects any existing new_group
        merged = False
        for new_group in new_groups:
            if group & new_group:  # Intersection
                new_group.update(group)  # Merge
                merged = True
                break

        if not merged:
            new_groups.append(group)

    # Stop when no more merging occurs
    if len(groups) == len(new_groups):
        break

    groups = new_groups

# 3. For each merge group, combine residues
for group in groups:
    merged_resids = set()
    domain_names = []

    for domain in group:
        domain_names.append(domain)
        merged_resids.update(domain_resids[domain])

    merged_range = get_range(merged_resids)
    output(prot, domain_names, merged_range)
```

**Example of Transitive Closure**:

Given validated pairs from Step 21:
```
# judgment > 0 (connected)
P1: d1-d2 (judgment=1)
P1: d2-d3 (judgment=2)
P2: d5-d6 (judgment=1)
P2: d7-d8 (judgment=2)

# judgment = 0 (not connected)
P1: d3-d4 (judgment=0) - rejected
```

Clustering process:
```
Initial groups: [{d1,d2}, {d2,d3}, {d5,d6}, {d7,d8}]

Iteration 1:
  - {d1,d2} + {d2,d3} → {d1,d2,d3}  (share d2)
  - {d5,d6} (no intersection)
  - {d7,d8} (no intersection)
Groups: [{d1,d2,d3}, {d5,d6}, {d7,d8}]

Iteration 2: No more intersections
Final groups: [{d1,d2,d3}, {d5,d6}, {d7,d8}]
```

**Input Files**:
- `step21/{dataset}.result`: Validation results with judgment values

**Input Format**:
```
prot  domain1  domain2  judgment  range1      range2
P1    d1       d2       1         10-50       55-100
P1    d2       d3       2         55-100      105-150
P1    d3       d4       0         105-150     200-250
P2    d5       d6       1         20-80       85-120
```

**Output Format** (`step22/{dataset}.result`):
```
prot  merged_domain_list  merged_range
P1    d1,d2,d3            10-150
P2    d5,d6               20-120
```

**Note**: Domain d4 is NOT included in P1's merge group because its connection to d3 was rejected (judgment=0).

**Transitive Closure Algorithm Details**:

The algorithm repeatedly merges groups that share any domain:
1. Start with each pair as a separate group
2. For each group, check if it intersects any previously processed group
3. If intersection found, merge the groups (union operation)
4. Repeat until no more merges occur (convergence)

**Complexity**: O(n²) in worst case where n = number of domains, but typically converges quickly for protein domain structures.

**Purpose**: This step handles complex merge scenarios like:
- Chain merges: A→B→C→D
- Star patterns: A connects to B, C, D separately
- Cycles: A→B→C→A (rare but possible with spatial interfaces)

### Step 23: Get Predictions

**Purpose**: Classify merged domains as "full", "part", or "miss" based on final probability and template coverage

**Key Concept**: After merging domains in Step 22, evaluate each domain's ECOD assignments using both ML probability and weighted template coverage. Domains with high confidence and good coverage are "full" predictions, partial coverage indicates "part" predictions, and low confidence domains are "miss".

**Algorithm**:

```python
# 1. Load merged domain groups from Step 22
merged_groups = load_merged_domains('step22/{dataset}.result')

# 2. Load position-specific weights for coverage calculation
for ecod in needed_ecods:
    if has_weight_file(ecod):
        ecod_weights[ecod] = load_weights(f'posi_weights/{ecod}.weight')
        total_weight[ecod] = sum(ecod_weights[ecod].values())
    else:
        ecod_weights[ecod] = {i: 1.0 for i in range(1, ecod_length[ecod]+1)}
        total_weight[ecod] = ecod_length[ecod]

# 3. Process each merged domain group
for (prot, domain_list, merged_range) in merged_groups:
    merged_resids = parse_range(merged_range)

    # Find all ECOD predictions for domains in this group
    predictions = []
    for domain in domain_list.split(','):
        for pred in domain_predictions[prot][domain]:
            predictions.append(pred)

    # Keep only best prediction per ECOD
    ecod_to_best = {}
    for pred in predictions:
        if pred.ecod not in ecod_to_best:
            ecod_to_best[pred.ecod] = pred
        elif pred.prob > ecod_to_best[pred.ecod].prob:
            ecod_to_best[pred.ecod] = pred

    # 4. Calculate coverage ratios for each ECOD
    for ecod, pred in ecod_to_best.items():
        # Get template residues (prefer DALI > HHsearch)
        dali_tres = parse_range(pred.dali_template_range)
        hh_tres = parse_range(pred.hh_template_range)

        if len(dali_tres) > len(hh_tres) * 0.5:
            template_resids = dali_tres
        else:
            template_resids = hh_tres

        # Weighted coverage (using position-specific weights)
        covered_weight = sum(ecod_weights[ecod].get(res, 0)
                           for res in template_resids)
        weighted_ratio = covered_weight / total_weight[ecod]

        # Length-based coverage (simple ratio)
        length_ratio = len(template_resids) / ecod_length[ecod]

        # 5. Classify prediction quality
        if pred.prob >= 0.85:
            # High confidence - check coverage
            if weighted_ratio >= 0.66 and length_ratio >= 0.33:
                classification = 'full'
            elif weighted_ratio >= 0.33 or length_ratio >= 0.33:
                classification = 'part'
            else:
                classification = 'miss'
        else:
            # Low confidence
            classification = 'miss'

        # Output prediction with classification
        output(
            prot=prot,
            merged_domains=domain_list,
            merged_range=merged_range,
            ecod=ecod,
            tgroup=pred.tgroup,
            prob=pred.prob,
            quality=pred.quality,
            classification=classification,
            weighted_ratio=weighted_ratio,
            length_ratio=length_ratio
        )
```

**Classification Logic**:

| Probability | Weighted Coverage | Length Coverage | Classification |
|-------------|-------------------|-----------------|----------------|
| ≥0.85 | ≥0.66 | ≥0.33 | **full** (high confidence, good coverage) |
| ≥0.85 | ≥0.33 or ≥0.33 | — | **part** (high confidence, partial coverage) |
| ≥0.85 | <0.33 | <0.33 | **miss** (high confidence, poor coverage) |
| <0.85 | — | — | **miss** (low confidence) |

**Coverage Calculation**:

Two complementary metrics:

1. **Weighted Coverage**: Uses position-specific importance weights
   ```python
   weighted_ratio = sum(weight[res] for res in aligned) / sum(all weights)
   ```
   - Emphasizes functionally/structurally critical positions
   - More robust to alignment quality issues

2. **Length Coverage**: Simple residue count ratio
   ```python
   length_ratio = len(aligned_residues) / ecod_total_length
   ```
   - Direct measure of structural completeness
   - Independent of position importance

**Thresholds Explained**:

- **0.85 probability**: High-confidence ML prediction threshold (above Step 17's 0.6 minimum)
- **0.66 weighted ratio**: At least 2/3 of important positions covered (very good match)
- **0.33 coverage**: At least 1/3 covered (partial but significant match)

**Input Files**:
- `step22/{dataset}.result`: Merged domain groups
- `step17/{species}/{prot}.result`: Original predictions with probabilities
- `step18/{species}/{prot}.data`: Template alignments
- `posi_weights/{ecod}.weight`: Position-specific weights
- `ECOD_length`: Template lengths

**Output Format** (`step23/{dataset}.result`):
```
prot  merged_domains  merged_range     ecod        tgroup      prob   quality  class  w_ratio  l_ratio
P1    d1,d2,d3       10-150           e001822778  1.10.150.10 0.92   good     full   0.85     0.78
P1    d1,d2,d3       10-150           e001148094  1.10.150.20 0.87   good     part   0.45     0.56
P2    d5,d6          20-120           e000976739  2.60.40.10  0.76   ok       miss   0.25     0.28
P3    d7             200-350          e003456789  3.40.50.10  0.55   bad      miss   0.50     0.45
```

**Example Classifications**:

1. **Full Domain Match**:
   - Probability: 0.92 (high confidence)
   - Weighted: 0.85 (85% of important positions)
   - Length: 0.78 (78% of structure)
   - → Classification: **full**

2. **Partial Domain Match**:
   - Probability: 0.87 (high confidence)
   - Weighted: 0.45 (45% of important positions)
   - Length: 0.56 (56% of structure)
   - → Classification: **part** (good confidence but incomplete coverage)

3. **Missed Prediction**:
   - Probability: 0.76 (below 0.85 threshold)
   - → Classification: **miss** (low confidence)

**Purpose**: This final classification enables downstream users to:
- **full**: Use confidently for structural analysis
- **part**: Investigate potential missing regions or alternative assignments
- **miss**: Treat as uncertain or novel domains requiring manual inspection

**Integration with Previous Steps**:
- Uses merged domains from Step 22 (handles multi-domain merges)
- Leverages ML probabilities from Step 16 (neural network confidence)
- Incorporates quality labels from Step 17 (hierarchical agreement)
- Applies alignment mappings from Step 18 (template coverage)

### Step 24: Integrate Results

**Purpose**: Add secondary structure analysis and refine classification labels for all domain predictions

**Key Concept**: Analyze secondary structure content (helices and strands) to distinguish between "simple_topology" domains (< 3 SSEs) and truly complex domains. Refine "full", "part", and "miss" classifications into final labels: "good_domain", "partial_domain", "low_confidence", or "simple_topology".

**Algorithm**:

```python
# 1. Load SSE assignments for all proteins
for prot in proteins:
    sse_data = load_sse(f'step12/{dataset}/{prot}.sse')

    # Track which SSEs are helices vs strands
    for resid, sse_id, sse_type in sse_data:
        if sse_type == 'H':
            helix_sses.add(sse_id)
        elif sse_type == 'E':
            strand_sses.add(sse_id)

        resid_to_sse[resid] = sse_id

# 2. Count SSEs for each domain
def count_sses(domain_resids):
    """Count helices and strands in domain."""
    sse_to_count = {}  # SSE ID -> residue count

    for resid in domain_resids:
        if resid in structured_residues:
            sse = resid_to_sse[resid]
            sse_to_count[sse] = sse_to_count.get(sse, 0) + 1

    # Helices: ≥6 residues in helix SSE
    helix_count = sum(1 for sse, count in sse_to_count.items()
                      if sse in helix_sses and count >= 6)

    # Strands: ≥3 residues in strand SSE
    strand_count = sum(1 for sse, count in sse_to_count.items()
                       if sse in strand_sses and count >= 3)

    return helix_count, strand_count

# 3. Refine classifications based on SSE content and original class
for domain in all_domains:
    helix_count, strand_count = count_sses(domain.resids)
    total_sses = helix_count + strand_count

    if domain.classification == 'miss':
        # Miss domains
        if total_sses < 3:
            final_label = 'simple_topology'
        else:
            final_label = 'low_confidence'

    elif domain.classification == 'part':
        # Partial domains - check if really simple topology
        if total_sses < 3:
            # High quality evidence for small domain?
            if (domain.hh_prob >= 0.95 and
                domain.weighted_ratio >= 0.8 and
                domain.length_ratio >= 0.8):
                final_label = 'partial_domain'
            else:
                final_label = 'simple_topology'
        else:
            final_label = 'partial_domain'

    elif domain.classification == 'full':
        # Full domains - check if really simple topology
        if total_sses < 3:
            # High quality evidence for small domain?
            if (domain.hh_prob >= 0.95 and
                domain.weighted_ratio >= 0.8 and
                domain.length_ratio >= 0.8):
                final_label = 'good_domain'
            else:
                final_label = 'simple_topology'
        else:
            final_label = 'good_domain'

    output(domain, final_label, helix_count, strand_count)

# 4. Sort domains by sequence position (mean residue ID)
for prot in proteins:
    prot_domains = get_domains(prot)
    prot_domains.sort(key=lambda d: mean(d.resids))

    # Renumber as nD1, nD2, nD3, ...
    for i, domain in enumerate(prot_domains, 1):
        domain.name = f'nD{i}'
```

**Classification Logic**:

| Original Class | SSE Count | HH Prob | Weighted Cov | Length Cov | Final Label |
|----------------|-----------|---------|--------------|------------|-------------|
| miss | < 3 | — | — | — | **simple_topology** |
| miss | ≥ 3 | — | — | — | **low_confidence** |
| part | < 3 | ≥0.95 | ≥0.8 | ≥0.8 | **partial_domain** |
| part | < 3 | other | other | other | **simple_topology** |
| part | ≥ 3 | — | — | — | **partial_domain** |
| full | < 3 | ≥0.95 | ≥0.8 | ≥0.8 | **good_domain** |
| full | < 3 | other | other | other | **simple_topology** |
| full | ≥ 3 | — | — | — | **good_domain** |

**Final Label Definitions**:

- **good_domain**: High-confidence full match with ≥3 SSEs (complex topology)
- **partial_domain**: High-confidence partial match with ≥3 SSEs, or very high quality small domain
- **low_confidence**: Uncertain prediction with complex topology (≥3 SSEs)
- **simple_topology**: Domains with < 3 SSEs (peptides, simple repeats, disordered regions with some structure)

**SSE Counting Rules**:

- **Helix**: SSE labeled 'H' (from DSSP) with ≥6 consecutive residues
- **Strand**: SSE labeled 'E' (from DSSP) with ≥3 consecutive residues
- **Threshold**: Total helices + strands must be ≥3 for "complex topology"

**Input Files**:
- `step23/{dataset}/{prot}.assign`: Predictions from Step 23 (full/part/miss)
- `step12/{dataset}/{prot}.sse`: Secondary structure elements
- `ecod.latest.domains`: ECOD keywords

**Output Format** (`step24/{dataset}/{prot}_domains`):
```
Domain  Range          ECOD_num    ECOD_key  T-group      DPAM_prob  HH_prob  DALI_z  Hit_cov  Tgroup_cov  Judge           Hcount  Scount
nD1     25-150,160-200 e001822778  TIM_barrel 1.10.150.10  0.920      9.5      23.4    0.850    0.780       good_domain     5       6
nD2     210-350        e001148094  Rossmann  1.10.150.20  0.870      8.7      18.5    0.450    0.560       partial_domain  3       4
nD3     400-450        na          na        na           0.550      6.2      8.3     na       na          simple_topology 1       1
```

**Summary File** (`{dataset}_domains`):
```
Protein  Domain  Range      ECOD_num    ECOD_key  T-group  DPAM_prob  HH_prob  DALI_z  Hit_cov  Tgroup_cov  Judge           Hcount  Scount
P12345   nD1     25-200     e001822778  TIM_barrel ...      0.920      9.5      23.4    0.850    0.780       good_domain     5       6
P12345   nD2     210-350    e001148094  Rossmann  ...      0.870      8.7      18.5    0.450    0.560       partial_domain  3       4
P67890   nD1     10-150     e003456789  Immunoglob ...     0.910      9.2      21.1    0.920    0.850       good_domain     2       8
```

**Note**: HH_prob is scaled by 10 in output (9.5 displayed = 0.95 actual probability).

**Purpose**: This step provides final quality assessment combining:
- ML confidence (DPAM probability)
- Sequence homology (HHsearch)
- Structural similarity (DALI)
- Template coverage (weighted and length-based)
- Structural complexity (SSE count)

The "simple_topology" label is particularly important for filtering out:
- Short peptides (< 25 residues with minimal structure)
- Simple repeats (2-3 helices or strands)
- Flexible/disordered regions with sparse structure
- Linker regions incorrectly parsed as domains

### Step 25: (Not Present in Code)

The production pipeline appears to end at Step 24. Step 25 may be reserved for:
- Additional validation or filtering
- Final output formatting
- Database submission
- Quality control reports

*No Step 25 code was provided - the pipeline concludes at Step 24.*

## Key Differences Summary

| Aspect | GitHub v2.0 (13 steps) | Production (24 steps) |
|--------|------------------------|----------------------|
| **Goal** | Domain boundary prediction | Domain + ECOD classification + quality labels |
| **Methods** | Rule-based (HHsearch, Foldseek, DALI) | Rule-based + ML (DOMASS) |
| **Output** | Domain ranges only | Domain ranges + ECOD assignments + confidence labels |
| **ML Component** | None | TensorFlow neural network (Step 16) |
| **Quality Control** | Structural agreement | Probability-based + hierarchical consensus + SSE analysis |
| **Template Mapping** | Implicit in alignments | Explicit mapping to ECOD residues (Step 18) |
| **Domain Merging** | None | Structural validation + transitive closure (Steps 19-22) |
| **Final Classification** | None | 4-level system: good/partial/low_confidence/simple_topology |

## Implementation Priority for GitHub v2.0

1. **CRITICAL**: Fix Step 7 libgfortran.so.3 dependency
2. **Phase 1 completion**: Implement Steps 8-13
3. **Phase 2 consideration**: Decide if DOMASS ML pipeline should be added
4. **Phase 3 consideration**: Decide if production refinements are needed

## Notes

- The DOMASS model (Steps 16-17) requires training data not included in GitHub v2.0
- Step 18 mapping requires ECOD residue map files (`ECOD_maps/*.map`)
- Production system uses species-based directory structure (`step*/{species}/{protein}`)
- GitHub v2.0 uses flat directory structure
