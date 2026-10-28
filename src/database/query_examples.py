#!/usr/bin/env python3
"""Example MongoDB queries against the Olist serving layer.

This file demonstrates common NoSQL read patterns on the collections produced
by `src.recommender.loader_and_recommender`. It is useful for viva
explanations and quick sanity checks.

Run:
    python3 -m src.database.query_examples

Dependencies:
    pymongo.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import MONGO_DB_NAME, MONGO_URI
from pymongo import MongoClient


def main():
    """Run example queries and print concise results."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        print(f"ERROR: cannot reach MongoDB at {MONGO_URI}: {exc}")
        return 1

    db = client[MONGO_DB_NAME]
    print("Collections:", db.list_collection_names())

    # Q1: one customer's recommendations
    sample = db.recommendations.find_one()
    if sample:
        print("\nQ1: sample recommendation document")
        print("customer:", sample["_id"])
        for rec in sample["recommendations"][:5]:
            print(f"  rank {rec['rank']:>2}  {rec['product_id']}  score={rec['score']}")

    # Q2: top 5 recommended products
    print("\nQ2: top 5 most frequently recommended products")
    pipeline = [
        {"$unwind": "$recommendations"},
        {"$group": {"_id": "$recommendations.product_id", "customers": {"$sum": 1}}},
        {"$sort": {"customers": -1}},
        {"$limit": 5},
    ]
    for doc in db.recommendations.aggregate(pipeline):
        print(f"  {doc['_id']}  customers={doc['customers']}")

    # Q3: top 5 categories by revenue
    print("\nQ3: top 5 categories by revenue")
    for doc in db.category_stats.find().sort("revenue", -1).limit(5):
        print(f"  {doc['_id']:<28} revenue={doc['revenue']:>12,.2f}")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
