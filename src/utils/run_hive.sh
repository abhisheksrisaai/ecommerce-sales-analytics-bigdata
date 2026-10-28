#!/usr/bin/env bash
# Run the Hive warehouse build and the analytics queries.
#
# Statements are executed through src.hive.hive_exec, which passes each one to
# Beeline with `-e`. See that file's header for why Beeline's own script mode
# (`-f`) cannot be used here.
#
# Usage: bash src/utils/run_hive.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_DIR/config/settings.sh"
cd "$PROJECT_DIR"

LOGDIR="$PROJECT_DIR/logs"
mkdir -p "$LOGDIR"

echo "=== HIVE / BEELINE VERSION ==="
beeline --version 2>&1 | head -2

echo
echo "=== STAGE 1: WAREHOUSE DEFINITION (external + partitioned tables) ==="
python3 -m src.hive.hive_exec src/hive/warehouse.hql "$LOGDIR/hive_01_warehouse.log"

echo
echo "=== STAGE 2: ANALYTICS QUERIES (10 HQL queries) ==="
python3 -m src.hive.hive_exec src/hive/analytics.hql "$LOGDIR/hive_02_analytics.log"

echo
echo "=== HDFS LAYOUT OF THE PARTITIONED TABLE ==="
hdfs dfs -ls /user/hive/warehouse/olist.db/orders_partitioned 2>/dev/null | head -25

echo
echo "=== STORAGE FOOTPRINT OF THE WAREHOUSE ==="
hdfs dfs -du -s -h /user/hive/warehouse/olist.db 2>/dev/null
