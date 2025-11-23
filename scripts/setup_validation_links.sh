#!/bin/bash
# Create symlinks for validation structures

mkdir -p validation_1000_run
cd validation_1000_run

for cif in ../validation_1000_structures/*.cif; do
    prefix=$(basename "$cif" .cif)
    ln -sf "$cif" "$prefix.cif"
    json="../validation_1000_structures/$prefix.json"
    ln -sf "$json" "$prefix.json"
done

cd ..
echo "Created $(ls validation_1000_run/*.cif | wc -l) structure symlinks"
