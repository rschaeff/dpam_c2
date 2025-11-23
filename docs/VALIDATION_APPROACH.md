# DPAM v2.0 Validation Approach

**Date**: 2025-11-22
**Decision**: Use modern tools, validate end-to-end quality

## Philosophy

**Goal**: Validate that dpam_c2 produces **equivalent quality results**, not bit-for-bit identical intermediate files.

**Rationale**: If minor tool version changes (Foldseek `c460257dd` → `10.941cd33`) cause dramatic pipeline differences, the issue is pipeline fragility, not the tools themselves.

## What We Validate

### ✅ Primary Validation Targets

**End-to-end quality metrics**:
- Domain detection accuracy (precision/recall on annotated proteins)
- ECOD classification correctness
- Domain boundary accuracy
- Coverage of known domains

**Pipeline correctness**:
- All steps execute without errors
- Data flows correctly through pipeline
- Output formats are valid
- Edge cases handled properly

**Code quality**:
- Type safety (mypy passes)
- Test coverage (unit + integration tests)
- Error handling
- Documentation completeness

### ❌ Not Primary Validation Targets

**Exact intermediate file matching**:
- Foldseek hit counts (tool-dependent)
- Floating-point precision differences
- File ordering differences
- Whitespace/formatting

**Tool version lock-in**:
- Should work with modern tool versions
- Should benefit from algorithm improvements
- Should not require 2022-era binaries

## Validation Strategy

### Phase 1: Tool Version Documentation ✅ COMPLETE

**Identified differences**:
- Foldseek: v1.0 uses `c460257dd` (2022), v2.0 uses `10.941cd33` (modern)
- ECOD database: Identical (Oct 7, 2022)
- Parameters: Identical (except v2 more permissive E-value, which doesn't matter)

**Result**: 77 hits (v2) vs 161 hits (v1) due to improved prefilter in modern Foldseek

**Decision**: Accept modern Foldseek, document as known difference

### Phase 2: Functional Validation (CURRENT)

**Test proteins with known annotations**:
1. Select proteins with well-characterized domains
2. Run dpam_c2 pipeline
3. Compare domain assignments to ground truth
4. Measure precision/recall

**Acceptance criteria**:
- Precision ≥ 90% (domains identified are correct)
- Recall ≥ 80% (most known domains are found)
- No critical errors in pipeline execution
- Performance within 2x of v1.0

### Phase 3: Comparative Validation

**Compare v1.0 and v2.0 on same proteins**:
1. Run both pipelines on test set
2. Compare final domain assignments (not intermediate hits)
3. Analyze differences:
   - Where do they agree? (good)
   - Where do they differ? (investigate)
   - Which is more accurate? (use annotations)

**Acceptance criteria**:
- Agreement ≥ 80% on domain assignments
- Where they differ, v2.0 should be ≥ as accurate as v1.0
- Differences should be explainable (tool improvements)

### Phase 4: Regression Testing

**Prevent future breakage**:
1. Create test suite with annotated proteins
2. Establish baseline quality metrics
3. Run tests on code changes
4. Alert if quality degrades

**Continuous validation**:
- Unit tests for all steps
- Integration tests for full pipeline
- Performance benchmarks
- Quality metrics tracking

## Known Differences from v1.0

### Documented Differences (Acceptable)

| Component | v1.0 | v2.0 | Impact | Status |
|-----------|------|------|--------|--------|
| **Foldseek version** | `c460257dd` | `10.941cd33` | 52% fewer hits (161→77) | ✅ Accepted |
| **Foldseek E-value** | 1000 | 1000000 | None (prefilter is bottleneck) | ✅ Accepted |
| **PSIPRED (addss.pl)** | Used | Skipped | 6% fewer HHsearch lines | ⚠️ Optional |
| **DISORDER algorithm** | Unknown | Modern | Different line counts | ✅ Accepted |

### To Be Investigated

| Component | Observation | Action |
|-----------|-------------|--------|
| **PDB formatting** | 994 line differences | Verify functional equivalence |
| **DALI hit counts** | Cascade from Foldseek | Test end-to-end quality |
| **ML pipeline outputs** | Empty (no domains in test protein) | Test with protein that has domains |

## Test Proteins Selection

### Tier 1: Known Annotations (Ground Truth)

Select proteins with:
- Well-documented ECOD domain structure
- Published domain boundaries
- Multiple domains (to test merging)
- Range of sizes (small, medium, large)

**Candidates**:
- Proteins from ECOD database with high-quality annotations
- Published case studies from DPAM v1.0 papers
- Community benchmark datasets

### Tier 2: v1.0 Reference Set

The 5 proteins we already have:
- AF-A0A024R1R8-F1 (current test - no domains)
- AF-A0A024RBG1-F1 (has ML outputs)
- AF-A0A024RCN7-F1
- AF-A0A075B6H5-F1 (has ML outputs)
- AF-A0A075B6H7-F1 (has ML outputs)

**Use for**: Regression testing, comparative analysis

### Tier 3: Edge Cases

Test robustness:
- Very small proteins (<100 residues)
- Very large proteins (>1000 residues)
- All alpha-helical
- All beta-sheet
- Intrinsically disordered regions
- Multi-domain proteins

## Success Criteria

### Must Have (Required for Release)

✅ **Functional correctness**:
- All 24 steps execute without errors
- Pipeline handles edge cases gracefully
- Output formats are valid

✅ **Code quality**:
- Type checking passes (mypy)
- Unit test coverage >80%
- Integration tests for all steps
- Documentation complete

✅ **Performance**:
- Pipeline completes in reasonable time (<4 hours for typical protein)
- Resource usage within acceptable limits

### Should Have (For Production Confidence)

⚠️ **Quality metrics** (in progress):
- Domain detection precision ≥90%
- Domain detection recall ≥80%
- ECOD classification accuracy ≥85%

⚠️ **Comparative analysis** (pending):
- Agreement with v1.0 ≥80% on domain assignments
- Known differences documented and justified

### Nice to Have (Future Work)

🔄 **Extended validation**:
- Validation on large protein sets (100s-1000s)
- Comparison with other domain parsers
- Benchmarking against published datasets

🔄 **Continuous improvement**:
- Regular tool updates (Foldseek, HHsuite, etc.)
- Algorithm improvements tracked
- Performance optimizations

## Current Status

**Phase 1**: ✅ COMPLETE
- Foldseek version difference identified and documented
- Database verified identical
- Parameters compared

**Phase 2**: ✅ COMPLETE (2025-11-22)
- Tested 3 proteins with known domain annotations
- Measured precision/recall: **100% / 100%**
- ECOD classification accuracy: **100%**
- Quality field bug identified and fixed

**Phase 3**: ✅ COMPLETE (2025-11-22)
- Compared v1.0 and v2.0 on 3 test proteins
- Domain ECOD t-group agreement: **100%**
- Minor boundary differences (≤5 residues): acceptable
- Foldseek hit differences don't affect final quality

**Phase 4**: ⏸️ PENDING
- Regression test suite exists (integration tests)
- Need to expand to larger protein set

## Next Steps

### Completed (This Session)

1. ✅ Document Foldseek version decision
2. ✅ Update validation approach documentation
3. ✅ Test with proteins that have domains (3 proteins)
4. ✅ Generate comparative validation report
5. ✅ Fix quality field bug in step23
6. ✅ Establish quality metrics baseline (100% precision/recall)
7. ✅ Compare v1.0 vs v2.0 on test set
8. ✅ Document quality comparison results

### Short Term (Next Session)

1. Expand validation to 10-20 proteins with multi-domain structures
2. Investigate boundary differences with structural evidence
3. Validate on proteins with different ECOD families (not just 11.1.1 and 221.4.1)
4. Test edge cases (very large proteins, all-alpha, all-beta)

### Medium Term (This Week)

1. Implement regression test suite
2. Add quality metrics to CI/CD
3. Complete integration test coverage
4. Write user documentation

### Long Term (Production Ready)

1. Validate on large protein set
2. Publish validation results
3. Create release candidate
4. Deploy to production

## Validation Reports

### Completed Reports

- `VALIDATION_SETUP_COMPLETE.md` - Framework setup and v1.0 data collection
- `VALIDATION_FIRST_RUN_RESULTS.md` - Initial run with missing tools
- `VALIDATION_RESULTS_FIXED.md` - After fixing HH-suite PATH and file mapping
- `FOLDSEEK_COMPARISON.md` - Detailed Foldseek parameter analysis
- `FOLDSEEK_VERSION_ANALYSIS.md` - Version identification and recommendations
- `VALIDATION_APPROACH.md` - Overall validation philosophy (this document)
- **`VALIDATION_RESULTS.md`** - **Comprehensive validation results on 3 test proteins** ✅ NEW

### Pending Reports

- `LARGE_SCALE_VALIDATION.md` - Validation on 100s-1000s of proteins (future work)

## References

- DPAM v1.0 code: `v1_scripts/`
- DPAM v1.0 outputs: `v1_outputs/`
- dpam_c2 implementation: `dpam/`
- Test proteins: `validation_proteins.txt`
- Validation framework: `scripts/validate_against_v1.py`

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-22 | Use modern Foldseek version | Pipeline should be robust to tool updates; focus on quality, not exact reproduction |
| 2025-11-22 | Accept PSIPRED skip | Optional dependency; HHsearch works without it |
| 2025-11-22 | Focus on end-to-end quality | Intermediate file differences are acceptable if final quality is maintained |
| 2025-11-22 | Document known differences | Transparency about v1.0 vs v2.0 differences |
