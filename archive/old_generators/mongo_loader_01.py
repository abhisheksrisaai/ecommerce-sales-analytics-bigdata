#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: MongoDB serving layer + NoSQL queries (Module 4)

Why MongoDB here?
    The recommender output is a per-customer variable-length list of product
    ids. In a relational schema that becomes either a child table scanned on
    every read (slow, many rows) or a denormalised string column (awkward to
    query). A document store models the natural access pattern directly:
    one document per customer, the recommendation list embedded in it, so a
    dashboard lookup is a single primary-key document read.

Collections written
    recommendations   { _id: customer_unique_id, recommendations: [ {product_id, rank, score} ], generated_at }
    category_stats    { _id: category, items_sold, revenue }

Run:
    python3 code/mongo/01_load_and_query.py
"""
import os
import sys
import csv
from datetime import datetime

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
except ImportError:
    print("pymongo is required: python3 -m pip install pymongo")
    sys.exit(1)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "olist_analytics"
OUT = os.environ.get("LOCAL_OUT", "out")
REC_CSV = os.path.join(OUT, "recommendations.csv")
CAT_CSV = os.path.join(OUT, "top_categories.csv")


def build_recommendation_documents(path, limit_users=None):
    """Group the flat (customer, product, score) rows into one document each."""
    docs = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            cust = row["customer_unique_id"]
            documents = docs.setdefault(cust, {"recommendations": []})
            documents["recommendations"].append({
                "product_id": row["product_id"],
                "score": float(row["score"]),
            })
            if limit_users and len(docs) >= limit_users:
                break

    now = datetime.utcnow()
    out = []
    for cust, payload in docs.items():
        recs = sorted(payload["recommendations"],
                      key=lambda r: r["score"], reverse=True)
        for rank, rec in enumerate(recs, 1):
            rec["rank"] = rank
        out.append({
            "_id": cust,
            "recommendations": recs,
            "n_recommendations": len(recs),
            "generated_at": now,
            "model": "ALS rank=10 regParam=0.1",
        })
    return out


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")               # fail fast if mongod is down
    db = client[DB_NAME]

    print("connected to MongoDB at {0}, database '{1}'".format(MONGO_URI, DB_NAME))

    # ------------------------------------------------------------- load stage
    recs = build_recommendation_documents(REC_CSV, limit_users=20000)
    db.recommendations.drop()
    if recs:
        db.recommendations.insert_many(recs)
    print("recommendations collection: {0:,} documents inserted".format(len(recs)))

    # Index supporting the most common read: does this customer have recs?
    db.recommendations.create_index([("_id", ASCENDING)])
    # Multikey index for the reverse question: who should be shown this product?
    db.recommendations.create_index([("recommendations.product_id", ASCENDING)])

    if os.path.exists(CAT_CSV):
        cat_docs = []
        with open(CAT_CSV, newline="") as fh:
            for row in csv.DictReader(fh):
                cat_docs.append({
                    "_id": row["category"],
                    "items_sold": int(row["items_sold"]),
                    "revenue": float(row["revenue"]),
                    "avg_review": float(row["avg_review"]) if row.get("avg_review") not in (None, "", "nan") else None,
                })
        db.category_stats.drop()
        if cat_docs:
            db.category_stats.insert_many(cat_docs)
        db.category_stats.create_index([("revenue", DESCENDING)])
        print("category_stats collection: {0:,} documents inserted".format(len(cat_docs)))

    # ------------------------------------------------------------ query stage
    print("\n" + "=" * 78)
    print("Q1. One document read: recommendations for a single customer")
    print("=" * 78)
    sample = db.recommendations.find_one()
    if sample:
        print("customer: {0}".format(sample["_id"]))
        for rec in sample["recommendations"][:5]:
            print("  rank {0:>2}  {1}  score={2}".format(
                rec["rank"], rec["product_id"], rec["score"]))

    print("\n" + "=" * 78)
    print("Q2. Aggregation pipeline: how many customers, average list length")
    print("=" * 78)
    for doc in db.recommendations.aggregate([
        {"$group": {"_id": None,
                    "customers": {"$sum": 1},
                    "avg_recommendations": {"$avg": "$n_recommendations"},
                    "total_recommendations": {"$sum": "$n_recommendations"}}},
        {"$project": {"_id": 0, "customers": 1,
                      "avg_recommendations": {"$round": ["$avg_recommendations", 2]},
                      "total_recommendations": 1}},
    ]):
        print(doc)

    print("\n" + "=" * 78)
    print("Q3. Aggregation pipeline: top categories by revenue")
    print("=" * 78)
    for doc in db.category_stats.aggregate([
        {"$sort": {"revenue": -1}},
        {"$limit": 5},
        {"$project": {"_id": 1, "revenue": 1, "items_sold": 1, "avg_review": 1}},
    ]):
        print("  {0:<28} revenue={1:>12,.2f}  items={2:>7,}  review={3}".format(
            doc["_id"], doc["revenue"], doc["items_sold"], doc.get("avg_review")))

    print("\n" + "=" * 78)
    print("Q4. Multikey index query: which customers are recommended a product?")
    print("=" * 78)
    target = None
    if sample:
        target = sample["recommendations"][0]["product_id"]
    if target:
        n = db.recommendations.count_documents({"recommendations.product_id": target})
        print("product {0} appears in {1:,} customer recommendation lists".format(target, n))
        for doc in db.recommendations.find(
                {"recommendations.product_id": target},
                {"_id": 1, "recommendations.$": 1}).limit(3):
            match = doc["recommendations"][0]
            print("  customer {0}: rank={1} score={2}".format(
                doc["_id"], match["rank"], match["score"]))

    print("\n" + "=" * 78)
    print("Q5. High-confidence recommendations (score filter)")
    print("=" * 78)
    for doc in db.recommendations.aggregate([
        {"$unwind": "$recommendations"},
        {"$match": {"recommendations.score": {"$gt": 4.0}}},
        {"$group": {"_id": "$recommendations.product_id",
                    "customers": {"$sum": 1},
                    "avg_score": {"$avg": "$recommendations.score"}}},
        {"$sort": {"customers": -1}},
        {"$limit": 5},
        {"$project": {"customers": 1, "avg_score": {"$round": ["$avg_score", 3]}}},
    ]):
        print("  product {0}  customers={1:>5}  avg_score={2}".format(
            doc["_id"], doc["customers"], doc["avg_score"]))

    print("\n" + "=" * 78)
    print("Collections in '{0}': {1}".format(DB_NAME, db.list_collection_names()))
    print("Indexes on recommendations:")
    for name, spec in db.recommendations.index_information().items():
        print("  {0}: {1}".format(name, spec["key"]))
    print("=" * 78)

    client.close()


if __name__ == "__main__":
    main()
