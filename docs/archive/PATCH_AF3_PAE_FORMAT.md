# Patch: AlphaFold 3 PAE Format Support

**Date:** 2026-01-29
**Author:** Claude (via archaea project)
**Issue:** DPAM fails to parse AlphaFold 3 confidence files

## Problem

DPAM's PAE (Predicted Aligned Error) parsing code only recognized two formats:
1. AlphaFold 2 format: `{"predicted_aligned_error": [[...], [...], ...]}`
2. Legacy sparse format: `{"residue1": [...], "residue2": [...], "distance": [...]}`

AlphaFold 3 uses a different key name for the PAE matrix:
- AF3 format: `{"pae": [[...], [...], ...], "atom_plddts": [...], ...}`

This caused all AF3 structures to fail at the PARSE_DOMAINS and DISORDER steps with:
```
ValueError: Unrecognized PAE format
```

## Solution

Added support for the AlphaFold 3 `pae` key in three files:

### 1. `dpam/core/models.py` (line ~73)

```python
# Before:
if 'predicted_aligned_error' in json_data:
    pae_list = json_data['predicted_aligned_error']
    ...
elif 'distance' in json_data:
    ...

# After:
if 'predicted_aligned_error' in json_data:
    # AlphaFold 2 format
    pae_list = json_data['predicted_aligned_error']
    ...
elif 'pae' in json_data:
    # AlphaFold 3 format
    pae_list = json_data['pae']
    ...
elif 'distance' in json_data:
    ...
```

### 2. `dpam/steps/step12_disorder.py` (line ~117)

Same pattern - added `elif 'pae' in json_dict:` branch with identical processing logic.

### 3. `dpam/steps/step13_parse_domains.py` (line ~231)

Same pattern - added `elif 'pae' in json_dict:` branch with identical processing logic.

## Files Modified

- `dpam/core/models.py`
- `dpam/steps/step12_disorder.py`
- `dpam/steps/step13_parse_domains.py`

## Testing

To verify the fix works:

```bash
# Test on a single AF3 structure
cd /data/ecod/archaea/dpam_tier1_batched/batch_01
dpam run A0A2H9QRQ9 --working-dir . --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data --steps PARSE_DOMAINS
```

## Context

This fix was needed for the archaeal proteome project which uses AlphaFold 3 predictions
for 38,263 tier1 proteins. The AF3 confidence JSON files have a different structure than
AF2, but the PAE matrix itself is in the same format (NxN array of floats).

## Commit Command

```bash
git add dpam/core/models.py dpam/steps/step12_disorder.py dpam/steps/step13_parse_domains.py
git commit -m "Add AlphaFold 3 PAE format support

DPAM now recognizes the 'pae' key used in AlphaFold 3 confidence JSON files,
in addition to the 'predicted_aligned_error' key used by AlphaFold 2.

Files modified:
- dpam/core/models.py: PAEMatrix.from_json()
- dpam/steps/step12_disorder.py: load_pae()
- dpam/steps/step13_parse_domains.py: load_pae()
"
```
