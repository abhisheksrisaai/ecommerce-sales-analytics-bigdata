#!/usr/bin/env bash
# BCSE402L - Big Data Analytics (TH)
# DA-2 artefact: HDFS ingestion step
#
# Loads the nine Olist CSVs from the local filesystem into the HDFS landing
# zone, one directory per entity. Each directory holds a single CSV so Hive
# external tables and Spark readers can treat it as a table.
#
# The raw layer is deliberately kept as received (no transformation): it is
# the immutable "bronze" copy that every later stage can be rebuilt from.
#
# NOTE ON THE WORKING DIRECTORY
#   The project path contains a space ("BD PROJECT"). Hadoop's Path parser
#   treats that space as a URI separator, so `hdfs dfs -put` fails with
#   "No such file or directory" when handed the absolute local path:
#       put: '/Users/.../BD PROJECT/DA2/data/raw/x.csv': No such file or directory
#   Running the transfer from inside the data directory and passing a plain
#   file name avoids the issue entirely, which is what this script does.
#
# Usage: bash code/scripts/01_ingest_hdfs.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RAW_DIR="$PROJECT_DIR/data/raw"
HDFS_BASE="${HDFS_BASE:-/olist}"

# entity directory in HDFS  <-  source CSV file name
PAIRS="
customers:olist_customers_dataset.csv
orders:olist_orders_dataset.csv
order_items:olist_order_items_dataset.csv
payments:olist_order_payments_dataset.csv
reviews:olist_order_reviews_dataset.csv
products:olist_products_dataset.csv
sellers:olist_sellers_dataset.csv
geolocation:olist_geolocation_dataset.csv
category_translation:product_category_name_translation.csv
"

echo "=== HDFS INGESTION: $RAW_DIR -> $HDFS_BASE/raw ==="
hdfs dfs -mkdir -p "$HDFS_BASE/raw"

# Staged out of the way first so the relative-path transfer below has a clean
# parent directory. Everything under $HDFS_BASE is rebuilt by this step.
cd "$RAW_DIR"

echo
printf "%-22s %-45s %12s  %s\n" ENTITY SOURCE BYTES STATUS
printf -- "------------------------------------------------------------------------------\n"

while IFS=: read -r entity file; do
    [ -z "${entity:-}" ] && continue
    dst="$HDFS_BASE/raw/$entity"

    if [ ! -f "$file" ]; then
        printf "%-22s %-45s %12s  %s\n" "$entity" "$file" "-" "MISSING"
        continue
    fi

    hdfs dfs -mkdir -p "$dst"
    # -f overwrites a previous copy so the step is idempotent and re-runnable.
    if hdfs dfs -put -f "$file" "$dst/" 2>/dev/null; then
        printf "%-22s %-45s %12s  %s\n" "$entity" "$file" "$(wc -c < "$file" | tr -d ' ')" "stored"
    else
        printf "%-22s %-45s %12s  %s\n" "$entity" "$file" "-" "FAILED"
        exit 1
    fi
done <<< "$PAIRS"

echo
echo "=== LANDING ZONE CONTENTS ==="
hdfs dfs -ls -R "$HDFS_BASE/raw" 2>/dev/null | grep -v "^Found"

echo
echo "=== BUILDING THE CLEAN LAYER (header removed, records normalised) ==="
echo "The clean layer fixes two concrete problems that break Hive reads:"
echo "  1. Hive 4.2.1's OpenCSVSerde does not honour skip.header.line.count, so a"
echo "     header left in place is read as a data row and inflates every count."
echo "  2. olist_order_reviews_dataset.csv embeds newlines inside quoted comment"
echo "     fields. Hive reads one line per record, so those rows fail with"
echo "     CsvMalformedLineException: Unterminated quoted field at end of CSV line."
echo "/olist/raw keeps the files exactly as downloaded; /olist/clean holds the"
echo "same records, re-serialised by a real CSV parser onto one line each."
echo
printf "%-22s %12s %12s %s\n" ENTITY RAW_LINES CLEAN_LINES STATUS
printf -- "------------------------------------------------------------------------------\n"

while IFS=: read -r entity file; do
    [ -z "${entity:-}" ] && continue
    dst="$HDFS_BASE/clean/$entity"

    raw_lines=$(wc -l < "$file" | tr -d ' ')
    # Normalisation goes through csv_normalize.py (see that file for why), and
    # piping to `hdfs dfs -put -` also avoids the space-in-path URI problem
    # described above.
    if python3 "$PROJECT_DIR/code/scripts/csv_normalize.py" "$file" \
            | hdfs dfs -put -f - "$dst/$file" 2>/dev/null; then
        clean_lines=$(hdfs dfs -cat "$dst/$file" 2>/dev/null | wc -l | tr -d ' ')
        printf "%-22s %12s %12s %s\n" "$entity" "$raw_lines" "$clean_lines" "stored"
    else
        printf "%-22s %12s %12s %s\n" "$entity" "$raw_lines" "-" "FAILED"
        exit 1
    fi
done <<< "$PAIRS"

echo
echo "=== TOTAL SIZE IN HDFS ==="
echo -n "raw   : "; hdfs dfs -du -s -h "$HDFS_BASE/raw" 2>/dev/null
echo -n "clean : "; hdfs dfs -du -s -h "$HDFS_BASE/clean" 2>/dev/null

echo
echo "=== BLOCK LAYOUT (splits and replication) ==="
hdfs fsck "$HDFS_BASE/raw" -files -blocks 2>/dev/null | grep -E "^/olist|Total blocks|Average block|Status:" | head -30

echo
echo "=== NAMESPACE QUOTA / COUNTS ==="
hdfs dfs -count -q "$HDFS_BASE/raw" 2>/dev/null
