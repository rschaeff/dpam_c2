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

# Download PDB
echo "Downloading PDB..."
wget -q "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.pdb" -O test_structure.pdb
echo "✓ Downloaded test_structure.pdb"

# Download CIF
echo "Downloading CIF..."
wget -q "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.cif" -O test_structure.cif 2>/dev/null || \
  echo "⚠ CIF download failed (optional)"

# Download PAE JSON
echo "Downloading PAE matrix..."
wget -q "https://alphafold.ebi.ac.uk/files/${AF_ID}-predicted_aligned_error_v4.json" -O test_structure.json
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
