#!/usr/bin/env python3
"""
Modern, blast-free replacement for addss.pl's a3m secondary-structure step.

Background
----------
DPAM's HHSEARCH step calls addss.pl to add PSIPRED secondary structure to the
hhblits a3m (improves hhsearch sensitivity). addss.pl's a3m mode builds the
PSIPRED profile via the legacy NCBI `blastpgp -B <msa> -C <chk>` path, which
SEGFAULTS (exit 139) on this system -- the legacy toolkit is dead and its
`-B` alignment-restore code is broken.

addss.pl, however, ALSO contains a blast-free MSA path (its HMMER mode,
`AddSSToHMMER`): it derives the PSIPRED `.mtx` directly from HMM profile
log-odds (empirically calibrated, scale=0.3 for HMMER3) and runs
psipred/psipass2 -- no blastpgp, no makemat. This module routes through that
path:

    a3m  -> match-column MSA  -> hmmbuild --hand (LENG == query length)
         -> addss.pl <hmm> (blast-free HMMER mode)  -> SSPRD/SSCON
         -> inject >ss_pred / >ss_conf into the a3m (hhsearch-readable)

The MSA-derived profile is preserved (not single-sequence), and we reuse
addss.pl's calibrated mtx math rather than reinventing PSSM scaling.
"""
from __future__ import annotations
import argparse, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HMMBUILD = os.environ.get("HMMBUILD", "/sw/apps/hmmer-3.4/bin/hmmbuild")
PSIPRED_BIN = os.environ.get("PSIPRED_BIN",
    str(Path(os.environ.get("CONDA_PREFIX", "/home/rschaeff/.conda/envs/dpam")) / "bin" / "psipred"))
PSIPASS2_BIN = os.environ.get("PSIPASS2_BIN",
    str(Path(os.environ.get("CONDA_PREFIX", "/home/rschaeff/.conda/envs/dpam")) / "bin" / "psipass2"))
PSIPRED_DATA = os.environ.get("PSIPRED_DATA",
    str(Path(os.environ.get("CONDA_PREFIX", "/home/rschaeff/.conda/envs/dpam")) / "share" / "psipred" / "data"))
DPAM_TOOLS = Path(__file__).resolve().parent

# PSIPRED .mtx fixed header block (12 values), verbatim from addss.pl
MTX_HEADER = ("2.670000e-03\n4.100000e-02\n-3.194183e+00\n1.400000e-01\n2.670000e-03\n"
              "4.420198e-02\n-3.118986e+00\n1.400000e-01\n3.176060e-03\n1.339561e-01\n"
              "-2.010243e+00\n4.012145e-01\n")
LOG2 = math.log(2.0)
HMM_SCALE = 0.3  # empirical HMMER3 bit-score -> PSI-BLAST score scale (from addss.pl)


def parse_a3m(path: Path):
    """Return (headers, seqs) preserving order. First record is the query."""
    headers, seqs, cur = [], [], []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if cur:
                    seqs.append("".join(cur)); cur = []
                headers.append(line)
            elif line:
                cur.append(line)
    if cur:
        seqs.append("".join(cur))
    return headers, seqs


def match_columns(seq: str) -> str:
    """a3m -> match-column string: keep uppercase + '-' (match states),
    drop lowercase (insertions). Length == number of query match columns."""
    return "".join(c for c in seq if c.isupper() or c == "-")


def build_match_msa(headers, seqs):
    """Build a match-column alignment (all rows == query length)."""
    qlen = len(match_columns(seqs[0]))
    rows = []
    for h, s in zip(headers, seqs):
        mc = match_columns(s)
        if len(mc) != qlen:
            # malformed row; pad/truncate defensively
            mc = (mc + "-" * qlen)[:qlen]
        rows.append((h[1:].split()[0] or "seq", mc))
    return qlen, rows


def write_stockholm(qlen, rows, out: Path):
    """Stockholm with #=GC RF marking ALL columns as match (for hmmbuild --hand)."""
    with open(out, "w") as fh:
        fh.write("# STOCKHOLM 1.0\n")
        # unique, whitespace-free names
        seen = {}
        for i, (name, seq) in enumerate(rows):
            nm = re.sub(r"\s+", "_", name)
            if nm in seen:
                seen[nm] += 1; nm = f"{nm}_{seen[nm]}"
            else:
                seen[nm] = 0
            fh.write(f"{nm:<40} {seq}\n")
        fh.write(f"{'#=GC RF':<40} {'x'*qlen}\n")
        fh.write("//\n")


def parse_hmm(hmm_path: Path):
    """Parse a HMMER3 hmm -> (length, query_consensus, null_probs[20], emis_probs[L][20]).
    Robust to HMMER 3.4's extra trailing match-line columns (MAP CONS RF MM CS)."""
    def neg_ln_to_p(tok):
        return 0.0 if tok == "*" else math.exp(-float(tok))
    length = None; null = None; emis = []; cons = []
    with open(hmm_path) as fh:
        lines = fh.readlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("LENG"):
            length = int(ln.split()[1])
        elif ln.lstrip().startswith("COMPO"):
            null = [neg_ln_to_p(t) for t in ln.split()[1:21]]
            i += 3  # skip COMPO insert-emission + begin-transition lines
            # then match states begin
            while i < len(lines):
                m = lines[i].split()
                if m and m[0].isdigit() and len(m) >= 22:
                    emis.append([neg_ln_to_p(t) for t in m[1:21]])
                    cons.append(m[22] if len(m) > 22 else "X")  # consensus residue
                    i += 3  # match-emit + insert-emit + transition
                    continue
                if lines[i].strip() == "//":
                    break
                i += 1
            break
        i += 1
    if length is None or null is None or not emis:
        raise RuntimeError(f"failed to parse hmm {hmm_path}")
    return length, "".join(c.upper() for c in cons), null, emis


def write_mtx(length, query, null, emis, out: Path):
    """Write PSIPRED .mtx from HMM profile, replicating addss.pl's calibrated math.
    Column order (23): A B C D E F G H I K L M N P Q R S T V W X Y Z ;
    B,Z = -32768, X = -100; framed by leading -32768 and trailing -32768 -400."""
    with open(out, "w") as fh:
        fh.write(f"{length}\n{query}\n{MTX_HEADER}")
        for row in emis:  # row = 20 emission probs in HMMER order (A C D E F G H I K L M N P Q R S T V W Y)
            lo = []
            for a in range(20):
                p = row[a]; n = null[a]
                if p <= 0.0 or n <= 0.0:
                    val = -32768
                else:
                    val = round(HMM_SCALE * (math.log(p / n) / LOG2) * 1000.0)
                lo.append(val)
            # splice B(idx1), X(idx20), Z(end) -> 23 values
            lo.insert(1, -32768)
            lo.insert(20, -100)
            lo.append(-32768)
            fh.write("-32768 " + " ".join(f"{v:.0f}" for v in lo) + " -32768 -400\n")


def run_psipred(mtx: Path, tmp: Path):
    """psipred + psipass2 -> (ss_pred, ss_conf) strings."""
    ss = tmp / "q.ss"; ss2 = tmp / "q.ss2"
    with open(ss, "w") as out:
        subprocess.run([PSIPRED_BIN, str(mtx),
                        f"{PSIPRED_DATA}/weights.dat", f"{PSIPRED_DATA}/weights.dat2",
                        f"{PSIPRED_DATA}/weights.dat3"], check=True, stdout=out,
                       stderr=subprocess.PIPE, text=True)
    horiz = subprocess.run([PSIPASS2_BIN, f"{PSIPRED_DATA}/weights_p2.dat",
                            "1", "0.98", "1.09", str(ss2), str(ss)],
                           check=True, capture_output=True, text=True).stdout
    ss_pred, ss_conf = [], []
    for line in horiz.splitlines():
        m = re.match(r"^Pred:\s+(\S+)", line)
        c = re.match(r"^Conf:\s+(\d+)", line)
        if m: ss_pred.append(m.group(1))
        if c: ss_conf.append(c.group(1))
    return "".join(ss_pred), "".join(ss_conf)


def run(input_a3m: Path, output_a3m: Path, workdir: Path | None = None):
    input_a3m = Path(input_a3m); output_a3m = Path(output_a3m)
    headers, seqs = parse_a3m(input_a3m)
    if not seqs:
        raise RuntimeError(f"empty a3m: {input_a3m}")
    qlen, rows = build_match_msa(headers, seqs)

    tmp = Path(tempfile.mkdtemp(prefix="addss_modern_", dir=str(workdir or input_a3m.parent)))
    try:
        sto = tmp / "msa.sto"; hmm = tmp / "q.hmm"; mtx = tmp / "q.mtx"
        write_stockholm(qlen, rows, sto)
        # build query-anchored HMM (every column a match state -> LENG == qlen)
        subprocess.run([HMMBUILD, "--hand", "--amino", str(hmm), str(sto)],
                       check=True, capture_output=True, text=True)
        # parse HMM profile -> PSIPRED .mtx (blast-free, calibrated like addss.pl) -> psipred
        length, query, null, emis = parse_hmm(hmm)
        if length != qlen:
            raise RuntimeError(f"hmm LENG {length} != query match columns {qlen}")
        write_mtx(length, query, null, emis, mtx)
        ss_pred, ss_conf = run_psipred(mtx, tmp)
        if len(ss_pred) != qlen:
            raise RuntimeError(f"SS length {len(ss_pred)} != query length {qlen}")
        # inject hhsearch-readable SS at top of a3m (>ss_pred / >ss_conf), keep original
        with open(output_a3m, "w") as out:
            out.write(">ss_pred PSIPRED predicted secondary structure\n")
            out.write(ss_pred + "\n")
            out.write(">ss_conf PSIPRED confidence values\n")
            out.write(ss_conf + "\n")
            with open(input_a3m) as src:
                shutil.copyfileobj(src, out)
        return ss_pred, ss_conf
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Blast-free addss replacement (a3m SS via HMM+PSIPRED)")
    ap.add_argument("input_a3m")
    ap.add_argument("output_a3m")
    a = ap.parse_args()
    sp, sc = run(Path(a.input_a3m), Path(a.output_a3m))
    print(f"ss_pred {len(sp)} residues -> {a.output_a3m}")


if __name__ == "__main__":
    main()
