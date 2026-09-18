#!/usr/bin/env bash
# BCSE402L - Big Data Analytics (TH)
# DA-2 artefact: start MongoDB and run the serving-layer stage.
#
# Usage: bash code/scripts/05_run_mongo.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_DIR/code/scripts/env.sh"
cd "$PROJECT_DIR"

LOGDIR="$PROJECT_DIR/logs"
DATA_ROOT="/Users/abhishek/bd-hadoop-data"
MONGO_DB_PATH="$DATA_ROOT/mongodb"
mkdir -p "$LOGDIR" "$MONGO_DB_PATH"

echo "=== MONGODB VERSION ==="
mongod --version 2>&1 | head -3

started_here=0
if ! pgrep -f "mongod .*--dbpath $MONGO_DB_PATH" >/dev/null 2>&1; then
    echo
    echo "=== STARTING MONGOD (dbpath $MONGO_DB_PATH) ==="
    # mongod is started with nohup rather than with its own --fork flag:
    # MongoDB 8.x refuses that option on macOS with
    #   BadValue: Server fork+exec via `--fork` or `processManagement.fork`
    #   is incompatible with macOS
    # so the daemonising is left to the shell instead.
    # A stale unix socket from a previous unclean shutdown would also block the
    # bind, so it is removed first.
    rm -f /tmp/mongodb-27017.sock 2>/dev/null
    nohup mongod --dbpath "$MONGO_DB_PATH" \
           --logpath "$LOGDIR/mongod.log" \
           --logappend \
           --port 27017 \
           --bind_ip 127.0.0.1 >/dev/null 2>&1 &
    disown 2>/dev/null || true
    started_here=1
fi

for i in $(seq 1 20); do
    if mongosh --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1; then break; fi
    sleep 1
done
echo "mongod: $(mongosh --quiet --eval 'db.runCommand({ping:1}).ok' 2>/dev/null || echo 'not responding')"

echo
echo "=== LOADING RECOMMENDATIONS AND RUNNING NOSQL QUERIES ==="
python3 code/mongo/01_load_and_query.py 2>&1 | tee "$LOGDIR/mongo_01_load_query.log"

echo
echo "=== SERVER-SIDE VIEW (mongosh) ==="
mongosh --quiet olist_analytics --eval '
  print("collections: " + db.getCollectionNames());
  print("recommendation docs: " + db.recommendations.countDocuments({}));
  print("sample document:");
  printjson(db.recommendations.findOne());
' 2>&1 | head -60

echo
echo "=== MONGODB DATA SIZE ON DISK ==="
du -sh "$MONGO_DB_PATH" 2>/dev/null
echo "started_here=$started_here"
