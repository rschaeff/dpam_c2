# DOMASS Model Behavior and Small Domain Limitations

## Overview

This document describes the behavior of the DOMASS machine learning model used in steps 15-16 of the DPAM pipeline, particularly regarding small domains that lack structural validation.

## Bug Fixes Applied (December 2025)

### Step 10: Template Range Preservation
- **Issue**: `words[:7]` was dropping the template_range column (column 7) when creating `.goodDomains`
- **Fix**: Changed to `words[:8]` to preserve template_range
- **File**: `dpam/steps/step10_filter_domains.py` line 224

### Step 15: Column Index Correction
- **Issue**: After step10 fix, column indices were off by one
- **Fix**: Updated to read `template_range = parts[9]` and `query_range = parts[10]`
- **File**: `dpam/steps/step15_prepare_domass.py` lines 263, 280-282

### PipelineState: Legacy Format Handling
- **Issue**: `failed_steps` stored as list `[]` in legacy state files but load expected dict
- **Fix**: Added isinstance check to handle both list and dict formats
- **File**: `dpam/core/models.py` lines 281-288

## DOMASS Model Behavior

### Model Architecture
- Input: 13 features (domain properties, HHsearch scores, DALI scores, consensus metrics)
- Hidden layer: 64 neurons, ReLU activation
- Output: 2-class softmax (incorrect=0, correct=1)
- Checkpoint: `domass_epo29`

### Feature Normalization
| Feature | Normalization |
|---------|---------------|
| HH_prob | /100 (percentage to fraction) |
| HH_rank | /10 |
| DALI_zscore | /10 |
| DALI_rank | /10 |
| DALI sentinels | zscore=0, tiles=10, rank=10 (for missing DALI) |
| HH sentinels | prob=0, cov=0, rank=10 (for missing HHsearch) |

### Key Observation: HHsearch-Only Hits Get Low Probability

The DOMASS model was trained to require structural validation. When a domain-ECOD pair has:
- **HHsearch hit only** (no DALI confirmation): Model gives ~0.003 probability
- **DALI hit only** (no HHsearch): Model gives ~0.94 probability
- **Both HHsearch and DALI**: Model gives high probability

Example from A3MRU4 D1 (30 residues):
```
D1→156.1.1 (HHsearch only, HH_prob=0.999): DPAM_prob = 0.003
D1→308.1.1 (DALI only, zscore=0.94):       DPAM_prob = 0.944
```

This is **by design** - the model doesn't trust sequence-only predictions without structural confirmation.

## Small Domain Limitations

### Problem Statement

Small domains (typically <50 residues) often fail to get DALI hits because:
1. Fewer structural features for alignment
2. DALI Z-scores scale with alignment length
3. Iterative DALI may not pick up small domain matches
4. Foldseek may miss small domains

### Consequences

1. Small domains only have HHsearch support
2. DOMASS assigns very low probability (~0.003) to HHsearch-only hits
3. Small domains fail the confidence threshold (step 17 requires prob >= 0.6)
4. Small domains may be incorrectly merged with adjacent domains (step 19-22)

### Case Study: A3MRU4

| Domain | Range | Size | V1 Assignment | V2 Assignment |
|--------|-------|------|---------------|---------------|
| D1 | 6-35 | 30 res | 156.1.1 (dpam=0.969) | Merged with D2 → 308.1.1 |
| D2 | 56-124 | 69 res | 308.1.1 (dpam=0.996) | 308.1.1 (dpam=0.985) |

V1 reference shows dpam_prob=0.969 for D1→156.1.1 despite having no structure hits (scount=0).
This discrepancy suggests V1 may have used different model weights or post-processing.

### Domains Most Affected

- N-terminal oligomerization domains (e.g., ribosomal L7/L12 N-terminal, T-group 156.1.1)
- Small helical bundles (<40 residues)
- Peptide-binding domains
- Disordered region flanking domains

## V1 vs V2 Discrepancy

The V1 reference database shows high dpam_prob values for some HHsearch-only small domains, but our DOMASS model testing shows the model gives ~0.003 for such cases.

Possible explanations:
1. **Different model checkpoint**: V1 may have used a different version of domass_epo29
2. **Manual curation**: V1 reference may have been manually adjusted
3. **Post-processing**: dpam_prob may have been modified after DOMASS computation
4. **Different DALI results**: V1's DALI may have found hits that V2 missed

## Potential Solutions (Future Work)

1. **Lower confidence threshold for small domains**: Reduce step17 threshold from 0.6 to 0.3 for domains <50 residues
2. **HHsearch confidence boost**: If HH_prob >= 0.99 and domain is small, boost confidence
3. **Retrain DOMASS model**: Include training examples with HHsearch-only small domains
4. **Separate classification for small domains**: Use HHsearch probability directly for small domains
5. **Improve DALI sensitivity**: Adjust DALI parameters for small domain detection

## Files Modified

- `dpam/steps/step10_filter_domains.py` - Template range preservation
- `dpam/steps/step15_prepare_domass.py` - Column index correction
- `dpam/core/models.py` - Legacy state file handling

## Testing

Validation run on 10,000 SwissProt proteins (10 batches of 1,000) with fixes applied.
Compare results with V1 reference in `swissprot.domain` table on dione:45000/ecod_protein.
