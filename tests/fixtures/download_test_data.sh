#!/bin/bash
#
# Download minimal test data for DPAM tests.
#
# Usage: ./download_test_data.sh [UNIPROT_ID]
#
# Default: P62988 (Ubiquitin, 76 residues)
#

set -e

UNIPROT_ID="${1:-P62988}"
AF_ID="AF-${UNIPROT_ID}-F1"

echo "Downloading test data for ${AF_ID}..."

# Detect download tool (prefer curl over wget for better proxy support)
if command -v curl &> /dev/null; then
    DOWNLOAD_CMD="curl -f -L -o"
    QUIET_FLAG="-s"
elif command -v wget &> /dev/null; then
    DOWNLOAD_CMD="wget -O"
    QUIET_FLAG="-q"
else
    echo "Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Download PDB
echo "Downloading PDB..."
if command -v curl &> /dev/null; then
    if ! curl -f -L -s --max-time 30 --connect-timeout 10 "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.pdb" -o test_structure.pdb; then
        echo "Error: Failed to download PDB file. Check network/proxy settings."
        echo "If behind a proxy, set: export http_proxy=http://your-proxy:port"
        echo "Or download manually from: https://alphafold.ebi.ac.uk/entry/${AF_ID}"
        exit 1
    fi
else
    if ! wget -q --timeout=30 --tries=2 "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.pdb" -O test_structure.pdb; then
        echo "Error: Failed to download PDB file. Check network/proxy settings."
        echo "If behind a proxy, set: export http_proxy=http://your-proxy:port"
        echo "Or download manually from: https://alphafold.ebi.ac.uk/entry/${AF_ID}"
        exit 1
    fi
fi
echo "✓ Downloaded test_structure.pdb"

# Download CIF
echo "Downloading CIF..."
if command -v curl &> /dev/null; then
    curl -f -L -s --max-time 30 --connect-timeout 10 "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.cif" -o test_structure.cif 2>/dev/null || \
      echo "⚠ CIF download failed (optional)"
else
    wget -q --timeout=30 --tries=2 "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.cif" -O test_structure.cif 2>/dev/null || \
      echo "⚠ CIF download failed (optional)"
fi

# Download PAE JSON
echo "Downloading PAE matrix..."
if command -v curl &> /dev/null; then
    if ! curl -f -L -s --max-time 30 --connect-timeout 10 "https://alphafold.ebi.ac.uk/files/${AF_ID}-predicted_aligned_error_v4.json" -o test_structure.json; then
        echo "Error: Failed to download PAE JSON file."
        exit 1
    fi
else
    if ! wget -q --timeout=30 --tries=2 "https://alphafold.ebi.ac.uk/files/${AF_ID}-predicted_aligned_error_v4.json" -O test_structure.json; then
        echo "Error: Failed to download PAE JSON file."
        exit 1
    fi
fi
echo "✓ Downloaded test_structure.json"

# Create FASTA from PDB
echo "Extracting sequence..."
python3 << 'EOF'
import sys
try:
    import gemmi
    st = gemmi.read_structure("test_structure.pdb")
    polymer = st[0][0]

    # Extract sequence
    seq = ""
    for residue in polymer:
        if residue.name in gemmi.find_tabulated_residue(residue.name).one_letter_code:
            seq += gemmi.find_tabulated_residue(residue.name).one_letter_code

    # Write FASTA
    with open("test_structure.fa", "w") as f:
        f.write(">test_structure\n")
        f.write(seq + "\n")

    print(f"✓ Created test_structure.fa ({len(seq)} residues)")
    sys.exit(0)
except ImportError:
    print("⚠ gemmi not available, using simple extraction", file=sys.stderr)
    sys.exit(1)
EOF

# Fallback if gemmi not available
if [ $? -ne 0 ]; then
    # Simple FASTA extraction from SEQRES records
    grep "^SEQRES" test_structure.pdb | \
      awk '{for(i=4;i<=NF;i++) printf "%s", $i} END {print ""}' | \
      sed 's/\(...\)/\1\n/g' | \
      awk 'BEGIN{print ">test_structure"} {printf "%s", substr($1,1,1)} END{print ""}' \
      > test_structure.fa
    echo "✓ Created test_structure.fa (simple extraction)"
fi

# Validation
echo ""
echo "Validation:"
echo "  PDB atoms:  $(grep -c '^ATOM' test_structure.pdb)"
echo "  JSON valid: $(python3 -m json.tool test_structure.json > /dev/null && echo 'yes' || echo 'no')"
echo "  FASTA:      $(grep -v '^>' test_structure.fa | wc -c | tr -d ' ') bp"

echo ""
echo "✓ Test data ready in $(pwd)"
echo ""
echo "Files created:"
ls -lh test_structure.{pdb,fa,json} 2>/dev/null | awk '{print "  " $9 "\t" $5}'
