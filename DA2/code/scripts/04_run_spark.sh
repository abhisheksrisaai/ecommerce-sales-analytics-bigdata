#!/usr/bin/env bash
# BCSE402L - Big Data Analytics (TH)
# DA-2 artefact: run the Spark stages (ETL + Spark SQL, then ALS).
#
# Usage: bash code/scripts/04_run_spark.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_DIR/code/scripts/env.sh"
cd "$PROJECT_DIR"

LOGDIR="$PROJECT_DIR/logs"
mkdir -p "$LOGDIR"

# Point Spark at the same YARN/HDFS configuration the cluster uses.
export HADOOP_CONF_DIR="$HADOOP_CONF_DIR"
export YARN_CONF_DIR="$HADOOP_CONF_DIR"

# PySpark 4.2 uses PEP 604 union syntax (X | Y) at import time, which needs
# Python 3.10 or newer. The system interpreter is 3.9, so the Homebrew 3.11
# install is used for both the driver and the workers; otherwise PySpark fails
# during import with
#   TypeError: unsupported operand type(s) for |: 'type' and 'type'
SPARK_PYTHON="/opt/homebrew/opt/python@3.11/bin/python3.11"
if [ ! -x "$SPARK_PYTHON" ]; then
    echo "ERROR: $SPARK_PYTHON not found; install with: brew install python@3.11"
    exit 1
fi
export PYSPARK_PYTHON="${PYSPARK_PYTHON:-$SPARK_PYTHON}"
export PYSPARK_DRIVER_PYTHON="${PYSPARK_DRIVER_PYTHON:-$SPARK_PYTHON}"
echo "pyspark interpreter: $PYSPARK_PYTHON ($("$PYSPARK_PYTHON" --version 2>&1))"

echo "=== SPARK VERSION ==="
"$SPARK_HOME/bin/spark-submit" --version 2>&1 | head -8

echo
echo "=== STAGE 1: SPARK ETL + SPARK SQL ANALYTICS ==="
"$SPARK_HOME/bin/spark-submit" \
    --master 'local[*]' \
    --driver-memory 3g \
    --conf spark.sql.shuffle.partitions=8 \
    --conf spark.ui.showConsoleProgress=false \
    code/spark/01_etl_analytics.py 2>&1 | tee "$LOGDIR/spark_01_etl.log" \
    | grep -Ev "^(2[0-9]{3}-|WARN|INFO)" 

echo
echo "=== STAGE 2: ALS COLLABORATIVE-FILTERING RECOMMENDER ==="
"$SPARK_HOME/bin/spark-submit" \
    --master 'local[*]' \
    --driver-memory 3g \
    --conf spark.sql.shuffle.partitions=8 \
    --conf spark.ui.showConsoleProgress=false \
    code/spark/02_als_recommender.py 2>&1 | tee "$LOGDIR/spark_02_als.log" \
    | grep -Ev "^(2[0-9]{3}-|WARN|INFO)"

echo
echo "=== ARTEFACTS ==="
ls -la out/
echo
echo "=== ETL PARQUET OUTPUT IN HDFS ==="
hdfs dfs -ls /olist/warehouse/olist_curated 2>/dev/null | head -12
echo
echo "=== TRAINED MODEL IN HDFS ==="
hdfs dfs -ls /olist/models/als_recommender 2>/dev/null | head
