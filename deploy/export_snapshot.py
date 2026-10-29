#!/usr/bin/env python3
"""Export the dashboard's MongoDB collections to `deploy/snapshot/*.json.gz`.

The public Streamlit deployment cannot reach the local MongoDB, so it loads
this snapshot into an in-memory `mongomock` database (see
`src/dashboard/app.py`). Run this script after the recommender loader has
populated MongoDB:

    python3 deploy/export_snapshot.py

The snapshot is deterministic: documents are sorted by `_id` before writing,
and `_id` is dropped from every collection except `recommendations`, where it
is the customer key used by the lookup.
"""
import gzip
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import MONGO_DB_NAME, MONGO_URI
from pymongo import MongoClient

SNAPSHOT_DIR = os.path.join(PROJECT_ROOT, "deploy", "snapshot")

# Collections read by src/dashboard/app.py.
COLLECTIONS = [
    "monthly_gmv",
    "category_stats",
    "state_revenue",
    "delivery_performance",
    "payment_distribution",
    "review_distribution",
    "top_products",
    "repeat_customers",
    "recommendations",
]

# `recommendations._id` is the customer_unique_id used by the customer lookup.
KEEP_ID = {"recommendations"}


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[MONGO_DB_NAME]

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    for name in COLLECTIONS:
        docs = list(db[name].find({}).sort("_id", 1))
        if name not in KEEP_ID:
            for doc in docs:
                doc.pop("_id", None)
        path = os.path.join(SNAPSHOT_DIR, f"{name}.json.gz")
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(docs, handle, ensure_ascii=False, separators=(",", ":"),
                      default=str)
        size_kb = os.path.getsize(path) / 1024
        print(f"{name:24s} {len(docs):6d} docs  {size_kb:8.1f} KB")

    client.close()

    # Verify the snapshot loads and the dashboard's key queries work.
    import mongomock

    mem = mongomock.MongoClient()[MONGO_DB_NAME]
    for name in COLLECTIONS:
        path = os.path.join(SNAPSHOT_DIR, f"{name}.json.gz")
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            docs = json.load(handle)
        if docs:
            mem[name].insert_many(docs)

    assert mem.category_stats.count_documents({}) > 0
    assert mem.monthly_gmv.count_documents({}) > 0
    assert mem.recommendations.find_one() is not None
    pipeline = [
        {"$unwind": "$recommendations"},
        {"$group": {"_id": "$recommendations.product_id", "customers": {"$sum": 1}}},
        {"$sort": {"customers": -1}},
        {"$limit": 10},
    ]
    assert len(list(mem.recommendations.aggregate(pipeline))) == 10
    print("snapshot verified with mongomock")


if __name__ == "__main__":
    main()
