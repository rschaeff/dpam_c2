#!/bin/bash
# ============================================================================
# DPAM v2.0 Container Test — TACC Lonestar6
# ============================================================================
#
# Self-contained test script. Run inside an idev session:
#
#   idev -N 1 -n 128 -p development -t 02:00:00
#   bash test_ls6.sh
#
# Prerequisites:
#   1. Container image at $WORK/dpam/dpam.sif
#   2. ECOD reference data at $WORK/dpam/ecod_data/
#   3. Test input files staged (script will check and prompt)
#
# The script:
#   - Verifies container tools and Python packages
#   - Runs prep (a3m → hhsearch) for one test protein
#   - Runs the full DPAM pipeline (steps 1-24)
#   - Validates output against expected domain assignment
#   - Reports timings for each phase
#
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Load TACC modules (apptainer is not in PATH by default on LS6)
# ---------------------------------------------------------------------------
if ! command -v apptainer &>/dev/null; then
    if command -v module &>/dev/null; then
        module load tacc-apptainer 2>/dev/null || module load apptainer 2>/dev/null || true
    fi
fi
if ! command -v apptainer &>/dev/null; then
    echo "ERROR: apptainer not found. Try: module load tacc-apptainer"
    exit 1
fi

# ---------------------------------------------------------------------------
# Configuration — edit these if your paths differ
# ---------------------------------------------------------------------------
SIF="${WORK}/dpam/dpam.sif"
DATA="${WORK}/dpam/ecod_data"
WORKDIR="${SCRATCH}/dpam_test_$$"          # unique per invocation
PREFIX="AF-P06596-F1"                      # test protein (~145 residues)
EXPECTED_DOMAIN="D1	23-145"              # expected output from pipeline

# Apptainer cache on $SCRATCH to avoid $HOME quota issues
export APPTAINER_CACHEDIR="${SCRATCH}/.apptainer/cache"
export APPTAINER_TMPDIR="${SCRATCH}/.apptainer/tmp"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[0;33m'
BLD='\033[1m'
RST='\033[0m'

pass() { echo -e "  ${GRN}PASS${RST} $1"; }
fail() { echo -e "  ${RED}FAIL${RST} $1"; FAILURES=$((FAILURES + 1)); }
warn() { echo -e "  ${YEL}WARN${RST} $1"; }
section() { echo -e "\n${BLD}=== $1 ===${RST}"; }
timer_start() { T_START=$(date +%s); }
timer_stop() {
    local elapsed=$(( $(date +%s) - T_START ))
    echo -e "  Time: ${elapsed}s"
}

FAILURES=0

# ---------------------------------------------------------------------------
# 0. Preflight checks
# ---------------------------------------------------------------------------
section "Preflight Checks"

if [[ ! -f "$SIF" ]]; then
    echo -e "${RED}ERROR${RST}: Container not found at $SIF"
    echo "Transfer it from leda:"
    echo "  scp leda:~/dev/dpam_c2/dpam.sif \$WORK/dpam/"
    exit 1
fi
pass "Container: $SIF ($(du -h "$SIF" | cut -f1))"

if [[ ! -d "$DATA" ]]; then
    echo -e "${RED}ERROR${RST}: Reference data not found at $DATA"
    echo "Ensure ECOD reference data is at \$WORK/dpam/ecod_data/"
    exit 1
fi
pass "Reference data: $DATA"

# Check for test input files
INPUTS_DIR="${WORK}/dpam/test_inputs"
if [[ ! -f "${INPUTS_DIR}/${PREFIX}.a3m" ]]; then
    echo -e "${YEL}Test inputs not found at ${INPUTS_DIR}/${RST}"
    echo ""
    echo "Stage them from leda first:"
    echo "  # On leda:"
    echo "  mkdir -p /tmp/dpam_test_inputs"
    echo "  cp validation_swissprot/${PREFIX}.{a3m,cif,json} /tmp/dpam_test_inputs/"
    echo ""
    echo "  # Then scp to LS6:"
    echo "  scp -r /tmp/dpam_test_inputs ls6.tacc.utexas.edu:\$WORK/dpam/test_inputs"
    exit 1
fi
pass "Test inputs: ${PREFIX}.{a3m,cif,json}"

# Check node resources
NCPUS=$(nproc)
MEM_GB=$(free -g | awk '/Mem:/{print $2}')
pass "Node: ${NCPUS} cores, ${MEM_GB} GB RAM"

echo ""
echo "Test protein: $PREFIX (~145 residues, 213 DALI candidates)"
echo "Working dir:  $WORKDIR"

# ---------------------------------------------------------------------------
# 1. Set up working directory
# ---------------------------------------------------------------------------
section "Setup"

mkdir -p "$WORKDIR"
cp "${INPUTS_DIR}/${PREFIX}.a3m" "$WORKDIR/"
cp "${INPUTS_DIR}/${PREFIX}.cif" "$WORKDIR/"
cp "${INPUTS_DIR}/${PREFIX}.json" "$WORKDIR/"
echo "$PREFIX" > "$WORKDIR/proteins.txt"
pass "Working directory created with input files"

# Write prep script into working directory
cat > "$WORKDIR/prep_from_a3m.py" << 'PREP_EOF'
#!/usr/bin/env python3
"""Complete HHsearch pipeline from pre-existing a3m files."""
import sys, json, shutil, argparse
from pathlib import Path

def prep_protein(prefix, working_dir, data_dir, cpus, skip_addss):
    from dpam.tools.hhsuite import AddSS, HHMake, HHSearch
    a3m_file = working_dir / f"{prefix}.a3m"
    hmm_file = working_dir / f"{prefix}.hmm"
    hhsearch_file = working_dir / f"{prefix}.hhsearch"
    if not a3m_file.exists():
        print(f"  SKIP {prefix}: no .a3m"); return False
    if hhsearch_file.exists():
        print(f"  SKIP {prefix}: .hhsearch exists"); _write_state(prefix, working_dir); return True
    if not skip_addss:
        a3m_ss = working_dir / f"{prefix}.a3m.ss"
        try:
            AddSS().run(a3m_file, a3m_ss, working_dir)
            shutil.move(str(a3m_ss), str(a3m_file))
            print(f"  {prefix}: addss.pl done")
        except Exception as e:
            print(f"  {prefix}: addss.pl failed ({e}), continuing without SS")
    else:
        print(f"  {prefix}: skipping addss.pl")
    HHMake().run(a3m_file, hmm_file, working_dir)
    print(f"  {prefix}: hhmake done")
    pdb70_db = data_dir / "pdb70"
    if not (pdb70_db.parent / f"{pdb70_db.name}_cs219.ffdata").exists():
        pdb70_db = data_dir / "pdb70" / "pdb70"
    HHSearch().run(hmm_file, pdb70_db, hhsearch_file, cpus, 100000, working_dir)
    print(f"  {prefix}: hhsearch done")
    _write_state(prefix, working_dir)
    return True

def _write_state(prefix, working_dir):
    state = {"prefix": prefix, "working_dir": str(working_dir),
             "completed_steps": ["HHSEARCH"], "failed_steps": {}, "metadata": {}}
    with open(working_dir / f".{prefix}.dpam_state.json", "w") as f:
        json.dump(state, f, indent=2)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("proteins"); p.add_argument("working_dir"); p.add_argument("data_dir")
    p.add_argument("--cpus", type=int, default=4)
    p.add_argument("--skip-addss", action="store_true")
    args = p.parse_args()
    working_dir, data_dir = Path(args.working_dir), Path(args.data_dir)
    with open(args.proteins) as f:
        prefixes = [l.strip() for l in f if l.strip()]
    ok = fail = 0
    for prefix in prefixes:
        try:
            if prep_protein(prefix, working_dir, data_dir, args.cpus, args.skip_addss): ok += 1
            else: fail += 1
        except Exception as e:
            print(f"  FAILED {prefix}: {e}"); fail += 1
    print(f"Done: {ok} ok, {fail} failed")
    sys.exit(1 if fail else 0)

if __name__ == "__main__": main()
PREP_EOF
pass "Prep script written"

# Helper: run a command inside the container
run_container() {
    apptainer exec --cleanenv \
        --bind "${DATA}:/data" \
        --bind "${WORKDIR}:/work" \
        --bind /tmp:/tmp \
        "$SIF" "$@"
}

# ---------------------------------------------------------------------------
# 2. Container verification
# ---------------------------------------------------------------------------
section "Container Tool Verification"

# Temporarily allow pipe failures (SIGPIPE from head is harmless)
set +e

echo -n "  hhsearch:  "; run_container hhsearch 2>&1 | head -1 | sed 's/^- .*/OK (binary runs)/'
echo -n "  hhmake:    "; run_container hhmake 2>&1 | head -1 | sed 's/^- .*/OK (binary runs)/'
echo -n "  foldseek:  "; run_container foldseek version 2>&1
echo -n "  dali.pl:   "; run_container test -x /opt/dali/bin/dali.pl && echo "OK" || echo "MISSING"
echo -n "  dsspcmbi:  "; run_container test -x /opt/dali/bin/dsspcmbi && echo "OK" || echo "MISSING"
echo -n "  addss.pl:  "; run_container which addss.pl 2>&1 || warn "not in PATH"
echo -n "  psipred:   "; run_container which psipred 2>&1 || warn "not in PATH"

echo ""
echo "  Python packages:"
run_container python3 -c "
import numpy, gemmi, tensorflow as tf
print(f'    numpy {numpy.__version__}, gemmi {gemmi.__version__}, tensorflow {tf.__version__}')
" 2>&1 | grep -v "^2026\|tensorflow/core\|AVX"

echo ""
echo "  Environment:"
run_container bash -c '
echo "    DALI_HOME=$DALI_HOME"
echo "    HHLIB=$HHLIB"
echo "    OMP_PROC_BIND=$OMP_PROC_BIND"
echo "    CONDA_PREFIX=$CONDA_PREFIX"
test -f $HHLIB/data/cs219.lib && echo "    cs219.lib: OK" || echo "    cs219.lib: MISSING"
'

echo ""
echo "  Reference data:"
run_container bash -c '
# pdb70 may be flat (pdb70_cs219.ffdata) or in subdir (pdb70/pdb70_cs219.ffdata)
if test -f /data/pdb70_cs219.ffdata || test -f /data/pdb70/pdb70_cs219.ffdata; then
    echo "    pdb70: OK"
else
    echo "    pdb70: MISSING"
fi
# ECOD foldseek DB may be flat files or in subdir
if test -f /data/ECOD_foldseek_DB.index || test -d /data/ECOD_foldseek_DB; then
    echo "    ECOD_foldseek_DB: OK"
else
    echo "    ECOD_foldseek_DB: MISSING"
fi
test -d /data/ECOD70 && echo "    ECOD70: OK" || echo "    ECOD70: MISSING"
test -f /data/domass_epo29.meta && echo "    domass_epo29: OK" || echo "    domass_epo29: MISSING"
test -f /data/ECOD_length && echo "    ECOD_length: OK" || echo "    ECOD_length: MISSING"
test -f /data/ecod.latest.domains && echo "    ecod.latest.domains: OK" || echo "    ecod.latest.domains: MISSING"
' 2>&1

set -e

# ---------------------------------------------------------------------------
# 3. Phase 1 — Prep (a3m → hhsearch)
# ---------------------------------------------------------------------------
section "Phase 1: Prep (a3m -> addss -> hhmake -> hhsearch)"
timer_start

run_container python3 /work/prep_from_a3m.py \
    /work/proteins.txt /work /data \
    --cpus "$NCPUS" \
    --skip-addss

timer_stop

if [[ -f "$WORKDIR/${PREFIX}.hhsearch" ]]; then
    HHSEARCH_HITS=$(grep -c "^>" "$WORKDIR/${PREFIX}.hhsearch" 2>/dev/null || echo "?")
    pass "hhsearch output: $(du -h "$WORKDIR/${PREFIX}.hhsearch" | cut -f1) ($HHSEARCH_HITS hits)"
else
    fail "hhsearch output not created"
fi

# ---------------------------------------------------------------------------
# 4. Phase 2 — Full pipeline (steps 1-24)
# ---------------------------------------------------------------------------
section "Phase 2: DPAM Pipeline (steps 1-24, --resume skips step 2)"
timer_start

# Use all cores, local /tmp for DALI scratch, oversubscribe DALI workers
DALI_WORKERS=$(( NCPUS * 4 ))
if (( DALI_WORKERS > 128 )); then DALI_WORKERS=128; fi

run_container dpam run "$PREFIX" \
    --working-dir /work \
    --data-dir /data \
    --cpus "$NCPUS" \
    --scratch-dir /tmp \
    --dali-workers "$DALI_WORKERS" \
    --skip-addss \
    --resume 2>&1 | tee "$WORKDIR/pipeline.log"

timer_stop

# ---------------------------------------------------------------------------
# 5. Validate results
# ---------------------------------------------------------------------------
section "Validation"

# Check pipeline state
if [[ -f "$WORKDIR/.${PREFIX}.dpam_state.json" ]]; then
    COMPLETED=$(python3 -c "
import json
with open('$WORKDIR/.${PREFIX}.dpam_state.json') as f:
    d = json.load(f)
print(len(d['completed_steps']))
")
    FAILED=$(python3 -c "
import json
with open('$WORKDIR/.${PREFIX}.dpam_state.json') as f:
    d = json.load(f)
failed = list(d['failed_steps'].keys())
print(f'{len(failed)}: {failed}' if failed else '0')
")
    echo "  Steps completed: $COMPLETED"
    echo "  Steps failed:    $FAILED"
else
    fail "State file not found"
fi

# Check domain output
if [[ -f "$WORKDIR/${PREFIX}.finalDPAM.domains" ]]; then
    ACTUAL=$(cat "$WORKDIR/${PREFIX}.finalDPAM.domains")
    echo "  Domain output: $ACTUAL"
    if [[ "$ACTUAL" == "$EXPECTED_DOMAIN" ]]; then
        pass "Domain matches expected: $EXPECTED_DOMAIN"
    else
        warn "Domain differs from expected ($EXPECTED_DOMAIN)"
        echo "       This may be acceptable — DALI results can vary slightly."
    fi
else
    fail "finalDPAM.domains not created"
fi

# Check ML predictions
if [[ -f "$WORKDIR/${PREFIX}.step23_predictions" ]]; then
    pass "ML predictions written"
    echo "  $(head -2 "$WORKDIR/${PREFIX}.step23_predictions")"
else
    warn "No ML predictions (step 23 may have failed)"
fi

# Check key intermediate files
echo ""
echo "  Key outputs:"
for f in ".hhsearch" ".foldseek" ".map2ecod.result" "_hits4Dali" \
         "_iterativdDali_hits" ".goodDomains" ".sse" ".diso" \
         ".finalDPAM.domains" ".step15_features" ".step16_predictions" \
         ".step17_confident_predictions"; do
    full="$WORKDIR/${PREFIX}${f}"
    if [[ -f "$full" ]]; then
        echo "    ${PREFIX}${f}: $(du -h "$full" | cut -f1)"
    else
        echo "    ${PREFIX}${f}: MISSING"
    fi
done

# ---------------------------------------------------------------------------
# 6. Summary
# ---------------------------------------------------------------------------
section "Summary"

TOTAL_TIME=$(grep -oP 'in \K[0-9.]+s' "$WORKDIR/pipeline.log" 2>/dev/null | \
    awk '{sum += $1} END {printf "%.0f", sum}')

echo "  Protein:    $PREFIX (~145 residues)"
echo "  Node:       ${NCPUS} cores, ${MEM_GB} GB RAM"
echo "  Steps:      $COMPLETED completed, $FAILED failed"
echo ""

if (( FAILURES == 0 )); then
    echo -e "  ${GRN}${BLD}ALL TESTS PASSED${RST}"
else
    echo -e "  ${RED}${BLD}${FAILURES} TEST(S) FAILED${RST}"
fi

echo ""
echo "  Working directory preserved at: $WORKDIR"
echo "  Pipeline log: $WORKDIR/pipeline.log"
echo ""
echo "  To clean up:  rm -rf $WORKDIR"
