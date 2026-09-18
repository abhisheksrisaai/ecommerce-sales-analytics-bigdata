#!/usr/bin/env bash
# BCSE402L - Big Data Analytics (TH)
# DA-2 artefact: compile and run the three MapReduce jobs.
#
#   Job 1  RevenueByProduct   - custom Java MR, uses a Combiner + Partitioner
#   Job 2  OrdersByMonth      - custom Java MR, cleaning inside the mapper
#   Job 3  payment_distribution - Hadoop Streaming (Python mapper/reducer)
#
# Usage: bash code/scripts/02_run_mapreduce.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_DIR/code/scripts/env.sh"
cd "$PROJECT_DIR"

HDFS_BASE="${HDFS_BASE:-/olist}"
BUILD="$PROJECT_DIR/code/mr/java/build"
OUTDIR="$PROJECT_DIR/out"
LOGDIR="$PROJECT_DIR/logs"
mkdir -p "$BUILD" "$OUTDIR" "$LOGDIR"

# Hadoop parses local paths as URIs, and this project's path contains a space
# ("BD PROJECT"), which is not a legal URI character. Every transfer that
# Hadoop performs therefore goes through a space-free staging directory, and
# the result is copied into the project afterwards. This applies to -files
# (job 3) and to -getmerge (result collection).
STAGE="/Users/abhishek/bd-hadoop-data/stage"
mkdir -p "$STAGE/jobfiles"

echo "=== BUILDING JAVA MAPREDUCE JOBS ==="
CP="$(hadoop classpath)"
javac -nowarn -cp "$CP" -d "$BUILD" \
    code/mr/java/RevenueByProduct.java \
    code/mr/java/OrdersByMonth.java 2>&1 | tail -20

# Package into a job JAR; hadoop jar needs a real archive, not a class dir.
( cd "$BUILD" && jar cf "$BUILD/olist-mr.jar" . )
echo "built $BUILD/olist-mr.jar"
ls -la "$BUILD/olist-mr.jar"

run_job() {
    local name="$1"; shift
    local log="$LOGDIR/mr_${name}.log"
    echo
    echo "###################################################################"
    echo "# $name"
    echo "###################################################################"
    "$@" 2>&1 | tee "$log"
    echo "[exit ${PIPESTATUS[0]}] log: $log"
}

# ------------------------------------------------------------------ JOB 1
hdfs dfs -rm -r -f "$HDFS_BASE/out/revenue_by_product" >/dev/null 2>&1
run_job revenue_by_product hadoop jar "$BUILD/olist-mr.jar" RevenueByProduct \
    "$HDFS_BASE/raw/order_items" "$HDFS_BASE/out/revenue_by_product"

# ------------------------------------------------------------------ JOB 2
hdfs dfs -rm -r -f "$HDFS_BASE/out/orders_by_month" >/dev/null 2>&1
run_job orders_by_month hadoop jar "$BUILD/olist-mr.jar" OrdersByMonth \
    "$HDFS_BASE/raw/orders" "$HDFS_BASE/out/orders_by_month"

# ------------------------------------------------------------------ JOB 3
# Locate the streaming JAR rather than hard-coding a version number.
STREAMING_JAR="$(ls "$HADOOP_HOME"/share/hadoop/tools/lib/hadoop-streaming-*.jar 2>/dev/null | head -1)"
echo
echo "streaming jar: $STREAMING_JAR"

# Copy the mapper and reducer into the space-free staging directory; -files
# turns each path into a URI, and the space in the project path would make
# that URI invalid.
cp "$PROJECT_DIR/code/mr/streaming/payment_mapper.py" "$STAGE/jobfiles/"
cp "$PROJECT_DIR/code/mr/streaming/payment_combiner.py" "$STAGE/jobfiles/"
cp "$PROJECT_DIR/code/mr/streaming/payment_reducer.py" "$STAGE/jobfiles/"
chmod +x "$STAGE/jobfiles/"*.py

hdfs dfs -rm -r -f "$HDFS_BASE/out/payment_distribution" >/dev/null 2>&1
run_job payment_distribution hadoop jar "$STREAMING_JAR" \
    -D mapreduce.job.name="Olist: payment type distribution (streaming)" \
    -D mapreduce.job.reduces=2 \
    -files "$STAGE/jobfiles/payment_mapper.py,$STAGE/jobfiles/payment_combiner.py,$STAGE/jobfiles/payment_reducer.py" \
    -mapper "python3 payment_mapper.py" \
    -combiner "python3 payment_combiner.py" \
    -reducer "python3 payment_reducer.py" \
    -input "$HDFS_BASE/raw/payments" \
    -output "$HDFS_BASE/out/payment_distribution"

# ------------------------------------------------------- collect results
echo
echo "=== RESULTS PULLED TO $OUTDIR ==="
for job in revenue_by_product orders_by_month payment_distribution; do
    rm -rf "$OUTDIR/$job"; mkdir -p "$OUTDIR/$job"
    # Extract to the space-free stage first, then copy into the project.
    if hdfs dfs -getmerge "$HDFS_BASE/out/$job" "$STAGE/$job.txt" 2>/dev/null; then
        cp "$STAGE/$job.txt" "$OUTDIR/$job/part-merged.txt"
        printf "%-24s %s lines\n" "$job" "$(wc -l < "$OUTDIR/$job/part-merged.txt" | tr -d ' ')"
    else
        printf "%-24s MISSING (job did not produce output)\n" "$job"
    fi
done

echo
echo "=== JOB 1: TOP 15 PRODUCTS BY REVENUE ==="
sort -k2,2gr "$OUTDIR/revenue_by_product/part-merged.txt" | head -15 | \
    awk -F'\t' 'BEGIN{printf "%-36s %12s\n","product_id","revenue"} {printf "%-36s %12.2f\n",$1,$2}'

echo
echo "=== JOB 1: REDUCER PARTITION FILES (partitioning evidence) ==="
hdfs dfs -ls "$HDFS_BASE/out/revenue_by_product" | grep part-

echo
echo "=== JOB 2: MONTHLY ORDER VOLUME ==="
cat "$OUTDIR/orders_by_month/part-merged.txt"

echo
echo "=== JOB 3: PAYMENT-TYPE DISTRIBUTION ==="
awk -F'\t' 'BEGIN{printf "%-16s %10s %14s %12s\n","payment_type","count","total","average"} {printf "%-16s %10s %14s %12s\n",$1,$2,$3,$4}' \
    "$OUTDIR/payment_distribution/part-merged.txt"
