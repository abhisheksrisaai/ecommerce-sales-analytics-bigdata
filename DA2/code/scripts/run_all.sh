#!/usr/bin/env bash
# BCSE402L - Big Data Analytics (TH)
# DA-2 artefact: end-to-end pipeline driver.
#
# Runs every stage in dependency order and tees all output into logs/, which
# is the evidence trail referenced by the DA-2 report.
#
# Usage: bash code/scripts/run_all.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_DIR/code/scripts/env.sh"
cd "$PROJECT_DIR"

# 00 is safe to include: it installs the configuration, formats the NameNode
# only if it is not already formatted, and skips daemons that are already up,
# so a full re-run on a live cluster does not destroy HDFS data.
STAGES=(
    "00_setup_env.sh|Cluster bring-up (configs + HDFS + YARN)"
    "01_ingest_hdfs.sh|HDFS ingestion"
    "02_run_mapreduce.sh|MapReduce jobs"
    "03_run_hive.sh|Hive warehouse + HQL"
    "04_run_spark.sh|Spark ETL + ALS"
    "05_run_mongo.sh|MongoDB serving layer"
)

overall=0
for entry in "${STAGES[@]}"; do
    script="${entry%%|*}"
    label="${entry##*|}"
    echo
    echo "###############################################################"
    echo "# STAGE: $label  ($script)"
    echo "###############################################################"
    if bash "$PROJECT_DIR/code/scripts/$script"; then
        echo "### $label: OK"
    else
        echo "### $label: FAILED (exit $?)"
        overall=1
    fi
done

echo
echo "###############################################################"
echo "# PIPELINE COMPLETE (overall exit $overall)"
echo "###############################################################"
echo "logs: $(ls -1 "$PROJECT_DIR/logs" | tr '\n' ' ')"
exit $overall
