#!/usr/bin/env bash
# BCSE402L - Big Data Analytics (TH)
# DA-2 artefact: run the Hive warehouse build and the analytics queries.
#
# Statements are executed through code/scripts/hive_exec.py, which passes each
# one to Beeline with `-e`. See that file's header for why Beeline's own script
# mode (`-f`) cannot be used here.
#
# Usage: bash code/scripts/03_run_hive.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_DIR/code/scripts/env.sh"
cd "$PROJECT_DIR"

LOGDIR="$PROJECT_DIR/logs"
mkdir -p "$LOGDIR"

echo "=== HIVE / BEELINE VERSION ==="
beeline --version 2>&1 | head -2

echo
echo "=== STAGE 1: WAREHOUSE DEFINITION (external + partitioned tables) ==="
python3 code/scripts/hive_exec.py code/hive/01_warehouse.hql "$LOGDIR/hive_01_warehouse.log"

echo
echo "=== STAGE 2: ANALYTICS QUERIES (10 HQL queries) ==="
python3 code/scripts/hive_exec.py code/hive/02_analytics.hql "$LOGDIR/hive_02_analytics.log"

echo
echo "=== HDFS LAYOUT OF THE PARTITIONED TABLE ==="
hdfs dfs -ls /user/hive/warehouse/olist.db/orders_partitioned 2>/dev/null | head -25

echo
echo "=== STORAGE FOOTPRINT OF THE WAREHOUSE ==="
hdfs dfs -du -s -h /user/hive/warehouse/olist.db 2>/dev/null
