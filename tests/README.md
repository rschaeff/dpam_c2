## DPAM Test Suite

Comprehensive test suite for DPAM v2.0 pipeline.

## Test Structure

```
tests/
├── conftest.py                 # Pytest fixtures and configuration
├── test_dependencies.py        # External tool and dependency tests
├── unit/                       # Fast unit tests (no external deps)
│   ├── test_utils.py          # Range parsing, amino acids
│   └── test_probability_funcs.py  # Step 13 probability functions
├── integration/                # Integration tests (require tools)
│   ├── test_step01_prepare.py
│   ├── test_step13_parse_domains.py
│   └── ...
└── fixtures/                   # Test data
    ├── README.md
    ├── download_test_data.sh
    └── test_structure.*
```

## Quick Start

### 1. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### 2. Download Test Fixtures

```bash
cd tests/fixtures
./download_test_data.sh
cd ../..
```

### 3. Run Tests

```bash
# Run all tests
pytest

# Run only fast unit tests
pytest -m unit

# Run specific test file
pytest tests/test_dependencies.py

# Run with coverage
pytest --cov=dpam --cov-report=html
```

## Test Categories

### Dependency Tests (`test_dependencies.py`)

**Purpose:** Verify external tools and dependencies are available

**Run separately:**
```bash
pytest tests/test_dependencies.py -v
```

**Expected failures:**
- If external tools not installed (hhsearch, foldseek, dali, mkdssp)
- If ECOD reference data not available

**Fix:** Install missing tools or set `DPAM_TEST_DATA_DIR` environment variable

---

### Unit Tests (`unit/`)

**Purpose:** Test pure Python functions in isolation

**Markers:** `@pytest.mark.unit`

**Run:**
```bash
pytest -m unit
```

**Characteristics:**
- ✅ Fast (<10 seconds total)
- ✅ No external dependencies
- ✅ No external tools required
- ✅ Can run without test fixtures

**Tests:**
- Range parsing (critical - used everywhere)
- Amino acid conversions
- Probability lookup functions (exact thresholds for v1.0 compatibility)

---

### Integration Tests (`integration/`)

**Purpose:** Test pipeline steps end-to-end with real tools

**Markers:** `@pytest.mark.integration`

**Run:**
```bash
pytest -m integration
```

**Requirements:**
- External tools installed
- Test fixtures downloaded
- ECOD reference data (for some tests)

**Characteristics:**
- ⏱️  Slower (5-10 minutes total)
- Requires external tools
- Tests actual tool execution
- Validates output formats

**Tests:**
- Step 1 (Prepare): File preparation and validation
- Step 13 (Parse Domains): Complete domain parsing workflow
- Additional steps: 2-12 (to be added)

---

## Running Selective Tests

### By Marker

```bash
# Only unit tests (fast)
pytest -m unit

# Only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Tests requiring specific tool
pytest -m requires_hhsearch
```

### By Step

```bash
# Test specific step
pytest tests/integration/test_step01_prepare.py

# Test multiple steps
pytest tests/integration/test_step01*.py tests/integration/test_step13*.py
```

### By Test Name

```bash
# Test with specific name pattern
pytest -k "test_probability"

# Multiple patterns
pytest -k "test_prepare or test_parse"
```

## Environment Variables

### `DPAM_TEST_DATA_DIR`

Set to point to ECOD reference data directory:

```bash
export DPAM_TEST_DATA_DIR=/path/to/ecod_data
pytest -m requires_ecod
```

### `PYTEST_ADDOPTS`

Set pytest options globally:

```bash
export PYTEST_ADDOPTS="-v --tb=short"
pytest
```

## Test Fixtures

### Required Files

Integration tests require minimal test structure files:

- `test_structure.pdb` - AlphaFold structure
- `test_structure.fa` - FASTA sequence
- `test_structure.json` - PAE matrix

### Download

```bash
cd tests/fixtures
./download_test_data.sh [UNIPROT_ID]
```

Default: P62988 (Ubiquitin, 76 residues)

### Recommendations

**Good test proteins:**
- **Ubiquitin (P62988)**: 76 residues, single domain
- **Lysozyme (P00698)**: 147 residues, high quality

**Avoid:**
- Large proteins (>500 residues) - too slow
- Multi-domain proteins - complex for minimal tests

## Coverage

### Generate Coverage Report

```bash
pytest --cov=dpam --cov-report=html
open htmlcov/index.html
```

### Current Coverage Targets

- **Unit tests:** >90% coverage of utils, core models
- **Integration tests:** >80% coverage of step functions
- **Overall:** >75% total coverage

## Continuous Integration

### GitHub Actions

Tests run automatically on push/PR:

```yaml
# .github/workflows/test.yml
- Unit tests (always run)
- Integration tests (if tools available)
- Coverage reporting
```

### Local Pre-commit

Run before committing:

```bash
# Fast check
pytest -m unit

# Full check (slower)
pytest -m "not slow"
```

## Troubleshooting

### Tests Skipped

**Issue:** Many tests skipped with "tool not available"

**Solution:** Install required tools:
```bash
# Example for Ubuntu/Debian
sudo apt-get install dssp
# Install hhsuite, foldseek, dali separately
```

### Fixtures Not Found

**Issue:** `FileNotFoundError` for test fixtures

**Solution:** Download test data:
```bash
cd tests/fixtures
./download_test_data.sh
```

### ECOD Data Not Found

**Issue:** Tests marked `requires_ecod` are skipped

**Solution:** Set data directory:
```bash
export DPAM_TEST_DATA_DIR=/path/to/ecod_data
```

Or tests will automatically skip (this is expected).

### Import Errors

**Issue:** `ModuleNotFoundError: No module named 'dpam'`

**Solution:** Install package in development mode:
```bash
pip install -e .
```

### Test Failures

**Issue:** Tests fail with unexpected errors

**Debug:**
```bash
# Run with verbose output
pytest -vv tests/test_file.py

# Run single test with full traceback
pytest tests/test_file.py::test_name -vv --tb=long

# Drop into debugger on failure
pytest --pdb
```

## Adding New Tests

### Unit Test Template

```python
# tests/unit/test_mymodule.py
import pytest
from dpam.mymodule import my_function

@pytest.mark.unit
def test_my_function():
    result = my_function(input_data)
    assert result == expected_output
```

### Integration Test Template

```python
# tests/integration/test_step99_mystep.py
import pytest
from dpam.steps.step99_mystep import run_step99

@pytest.mark.integration
@pytest.mark.requires_mytool
def test_step99_basic(test_prefix, working_dir, mytool_available):
    success = run_step99(test_prefix, working_dir)
    assert success

    # Check outputs
    output_file = working_dir / f"{test_prefix}.output"
    assert output_file.exists()
```

## Test Metrics

### Current Status

| Category | Files | Tests | Runtime | Coverage |
|----------|-------|-------|---------|----------|
| Dependencies | 1 | ~30 | <5s | N/A |
| Unit | 2 | ~60 | <10s | >90% |
| Integration | 2 | ~20 | ~2min | >70% |
| **Total** | **5** | **~110** | **~2min** | **~80%** |

### Goals

- [ ] Add integration tests for steps 2-12
- [ ] Add full pipeline test
- [ ] Achieve >85% total coverage
- [ ] Add performance benchmarks
- [ ] Add backward compatibility tests (v1.0 output comparison)

## Resources

- **Pytest Docs:** https://docs.pytest.org/
- **Coverage.py:** https://coverage.readthedocs.io/
- **DPAM Docs:** `docs/` directory
- **AlphaFold DB:** https://alphafold.ebi.ac.uk/

## Contributing

When adding new code:

1. Write unit tests for new functions
2. Write integration tests for new steps
3. Run tests locally before committing:
   ```bash
   pytest -m unit  # Quick check
   pytest          # Full check
   ```
4. Ensure coverage doesn't decrease:
   ```bash
   pytest --cov=dpam --cov-report=term-missing
   ```

## Summary

**Minimal test suite is ready!** ✅

- ✅ Directory structure created
- ✅ Pytest configuration complete
- ✅ Dependency tests implemented
- ✅ Unit tests for critical utilities
- ✅ Integration tests for steps 1 and 13
- ✅ Test fixture download scripts
- ✅ Documentation complete

**Next steps:**
1. Download test fixtures: `cd tests/fixtures && ./download_test_data.sh`
2. Run unit tests: `pytest -m unit`
3. Run dependency check: `pytest tests/test_dependencies.py`
4. Add remaining integration tests as needed
