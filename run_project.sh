#!/usr/bin/env bash
# E-Commerce Big Data Analytics project - data pipeline driver.
#
# Runs the data pipeline stages in dependency order. Each stage writes its
# console output into logs/, which is the evidence trail referenced by the
# reports.
#
# NOTE: This script runs the data pipeline only (setup → HDFS → MapReduce →
# Hive → Spark → MongoDB). Report, slide deck and screenshot generation are
# separate manual steps documented in README.md.
#
# Usage: bash run_project.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_DIR/config/settings.sh"
cd "$PROJECT_DIR"

# setup_env.sh is safe to include: it installs configuration, formats the
# NameNode only once, and skips daemons that are already up.
STAGES=(
    "src/utils/setup_env.sh|Cluster bring-up (configs + HDFS + YARN)"
    "src/utils/ingest_hdfs.sh|HDFS ingestion"
    "src/utils/run_mapreduce.sh|MapReduce jobs"
    "src/utils/run_hive.sh|Hive warehouse + HQL"
    "src/utils/run_spark.sh|Spark ETL + ALS reference"
    "src/utils/load_mongodb.sh|MongoDB serving layer"
)

overall=0
for entry in "${STAGES[@]}"; do
    script="${entry%%|*}"
    label="${entry##*|}"
    echo
    echo "###############################################################"
    echo "# STAGE: $label  ($script)"
    echo "###############################################################"
    if bash "$PROJECT_DIR/$script"; then
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
