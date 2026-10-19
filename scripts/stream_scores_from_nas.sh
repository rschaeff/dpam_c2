#!/bin/bash
# Stream domain scores from NAS local disk into PostgreSQL via SSH pipe.
# Reads info files locally on NAS (fast), outputs CSV, pipes to psql COPY.
#
# Usage: bash stream_scores_from_nas.sh

set -e

NAS_HOST="20.3.0.109"
NAS_SSH="ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa rschaeff@${NAS_HOST}"
INFO_DIR="/export/home0/rschaeff_1/data/dpam_reference/ecod_data/ecod_internal"
DB_HOST="dione"
DB_PORT="45000"
DB_NAME="ecod_protein"
DB_USER="ecod"

echo "Truncating dpam_domain_scores..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "TRUNCATE ecod_commons.dpam_domain_scores;"

echo "Streaming scores from NAS -> PostgreSQL..."
# Read info files on NAS, output tab-separated: ecod_num \t hit_ecod_num \t zscore \t qscore
# Then pipe into psql COPY
$NAS_SSH "python3 -c \"
import os, sys
info_dir = '$INFO_DIR'
count = 0
for shard in sorted(os.listdir(info_dir)):
    shard_path = os.path.join(info_dir, shard)
    if not os.path.isdir(shard_path):
        continue
    for fname in os.listdir(shard_path):
        if not fname.endswith('.info'):
            continue
        ecod_num = fname[:-5]
        with open(os.path.join(shard_path, fname)) as f:
            for line in f:
                words = line.split()
                if len(words) >= 3:
                    sys.stdout.write(ecod_num + '\t' + words[0] + '\t' + words[1] + '\t' + words[2] + '\n')
        count += 1
        if count % 5000 == 0:
            print(str(count) + ' files processed', file=sys.stderr)
print('Total: ' + str(count) + ' files', file=sys.stderr)
\"" | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "\COPY ecod_commons.dpam_domain_scores(ecod_num, hit_ecod_num, zscore, qscore) FROM STDIN"

echo "Creating index..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "CREATE INDEX IF NOT EXISTS idx_dpam_domain_scores_ecod_num ON ecod_commons.dpam_domain_scores(ecod_num);"

echo "Verifying..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -c "SELECT count(DISTINCT ecod_num) as ecod_nums, count(*) as total_rows FROM ecod_commons.dpam_domain_scores;"

echo "DONE"
