#!/bin/bash
#
# Fetch v1.0 reference data from production server
#

REMOTE_USER="rschae"
REMOTE_HOST="hgd-aug.swmed.org"
REMOTE_DIR="/path/to/dpam_automatic"  # UPDATE THIS
STRUCTURE="P38326"

LOCAL_REF_DIR="$HOME/dev/dpam_c2/tests/validation/reference/$STRUCTURE"

echo "Fetching v1.0 reference data for $STRUCTURE..."
echo "Remote: $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
echo "Local:  $LOCAL_REF_DIR"
echo ""

# Create local directory
mkdir -p "$LOCAL_REF_DIR"

# Fetch all step outputs for this structure
rsync -avz --progress \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/step*/yeast/$STRUCTURE.*" \
    "$LOCAL_REF_DIR/"

# Also get the input structure if available
rsync -avz --progress \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/step1/yeast/$STRUCTURE.pdb" \
    "$LOCAL_REF_DIR/" 2>/dev/null || echo "Note: PDB not found in step1"

rsync -avz --progress \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/step2/yeast/$STRUCTURE.pdb" \
    "$LOCAL_REF_DIR/" 2>/dev/null || echo "Note: PDB not found in step2"

echo ""
echo "Files fetched:"
ls -lh "$LOCAL_REF_DIR"

echo ""
echo "Done! Reference data saved to:"
echo "  $LOCAL_REF_DIR"
