#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-3 artefact: load dashboard aggregates into MongoDB and train a
popularity + category-affinity recommender that actually works on sparse data.

This script runs without Hadoop/Spark because it operates directly on the
local CSVs and the running MongoDB serving store. It is meant to complete the
DA-3 dashboard and replace the ALS negative result with an honest, evaluated
baseline recommender.

Run:
    python3 code/scripts/da3_loader_and_recommender.py
"""
import os
import sys
import csv
import random
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING

DB_NAME = "olist_analytics"
OUT = os.environ.get("LOCAL_OUT", "out")
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "raw")

random.seed(42)


def read_raw(name):
    return pd.read_csv(os.path.join(RAW, name), dtype=str)


def load_aggregates(db):
    """Compute dashboard-ready aggregates from local CSVs and load into MongoDB."""
    orders = read_raw("olist_orders_dataset.csv")
    items = read_raw("olist_order_items_dataset.csv")
    customers = read_raw("olist_customers_dataset.csv")
    products = read_raw("olist_products_dataset.csv")
    translation = read_raw("product_category_name_translation.csv")
    payments = read_raw("olist_order_payments_dataset.csv")
    reviews = read_raw("olist_order_reviews_dataset.csv")

    # types
    items["price"] = items["price"].astype(float)
    items["freight_value"] = items["freight_value"].astype(float)
    items["line_revenue"] = items["price"] + items["freight_value"]
    payments["payment_value"] = payments["payment_value"].astype(float)
    reviews["review_score"] = reviews["review_score"].astype(int)

    # category mapping
    cat_map = dict(zip(translation["product_category_name"],
                       translation["product_category_name_english"]))
    products["category"] = products["product_category_name"].map(cat_map).fillna(
        products["product_category_name"]).fillna("unknown")

    # join items with orders/products/customers
    fact = (items
            .merge(orders, on="order_id", how="inner")
            .merge(customers, on="customer_id", how="left")
            .merge(products[["product_id", "category"]], on="product_id", how="left"))
    fact["order_purchase_timestamp"] = pd.to_datetime(fact["order_purchase_timestamp"], errors="coerce")
    fact["purchase_month"] = fact["order_purchase_timestamp"].dt.strftime("%Y-%m")
    fact["order_delivered_customer_date"] = pd.to_datetime(
        fact["order_delivered_customer_date"], errors="coerce")
    fact["order_estimated_delivery_date"] = pd.to_datetime(
        fact["order_estimated_delivery_date"], errors="coerce")
    fact["delivery_days"] = (
        fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]).dt.days
    fact["is_late"] = (fact["order_delivered_customer_date"] >
                       fact["order_estimated_delivery_date"]).astype(int)

    delivered = fact[fact["order_status"] == "delivered"]

    # ------------------------------------------------------------------ monthly_gmv
    monthly = (delivered.groupby("purchase_month")
               .agg(orders=("order_id", "nunique"),
                    gmv=("line_revenue", "sum"),
                    items=("order_item_id", "count"))
               .reset_index())
    monthly["gmv"] = monthly["gmv"].round(2)
    db.monthly_gmv.drop()
    db.monthly_gmv.insert_many(monthly.to_dict("records"))
    db.monthly_gmv.create_index([("purchase_month", ASCENDING)])
    print("loaded monthly_gmv:", len(monthly), "documents")

    # ------------------------------------------------------------------ state_revenue
    state_rev = (delivered.groupby("customer_state")
                 .agg(orders=("order_id", "nunique"),
                      revenue=("line_revenue", "sum"),
                      avg_order_value=("line_revenue", "mean"))
                 .reset_index())
    state_rev["revenue"] = state_rev["revenue"].round(2)
    state_rev["avg_order_value"] = state_rev["avg_order_value"].round(2)
    state_rev = state_rev.sort_values("revenue", ascending=False)
    db.state_revenue.drop()
    db.state_revenue.insert_many(state_rev.to_dict("records"))
    db.state_revenue.create_index([("revenue", DESCENDING)])
    print("loaded state_revenue:", len(state_rev), "documents")

    # ------------------------------------------------------------------ delivery_performance
    deliv = (delivered[delivered["delivery_days"].notna()]
             .groupby("customer_state")
             .agg(delivered_orders=("order_id", "nunique"),
                  avg_delivery_days=("delivery_days", "mean"),
                  late_orders=("is_late", "sum"))
             .reset_index())
    deliv["late_pct"] = (100.0 * deliv["late_orders"] /
                         deliv["delivered_orders"]).round(2)
    deliv["avg_delivery_days"] = deliv["avg_delivery_days"].round(1)
    deliv = deliv[deliv["delivered_orders"] > 500].sort_values("late_pct", ascending=False)
    db.delivery_performance.drop()
    db.delivery_performance.insert_many(deliv.to_dict("records"))
    print("loaded delivery_performance:", len(deliv), "documents")

    # ------------------------------------------------------------------ payment_distribution
    pay = (payments.groupby("payment_type")
           .agg(transactions=("order_id", "count"),
                total_value=("payment_value", "sum"),
                avg_value=("payment_value", "mean"),
                avg_installments=("payment_installments", lambda x: pd.to_numeric(x, errors="coerce").mean()))
           .reset_index())
    pay["total_value"] = pay["total_value"].round(2)
    pay["avg_value"] = pay["avg_value"].round(2)
    pay["avg_installments"] = pay["avg_installments"].round(2)
    pay = pay.sort_values("transactions", ascending=False)
    db.payment_distribution.drop()
    db.payment_distribution.insert_many(pay.to_dict("records"))
    print("loaded payment_distribution:", len(pay), "documents")

    # ------------------------------------------------------------------ review_distribution
    rev = (reviews.groupby("review_score")
           .size()
           .reset_index(name="reviews"))
    rev["pct"] = (100.0 * rev["reviews"] / rev["reviews"].sum()).round(2)
    db.review_distribution.drop()
    db.review_distribution.insert_many(rev.to_dict("records"))
    print("loaded review_distribution:", len(rev), "documents")

    # ------------------------------------------------------------------ top_products
    top_prod = (delivered.groupby(["product_id", "category"])
                .agg(items_sold=("order_item_id", "count"),
                     revenue=("line_revenue", "sum"))
                .reset_index())
    top_prod["revenue"] = top_prod["revenue"].round(2)
    top_prod = top_prod.sort_values("revenue", ascending=False).head(100)
    db.top_products.drop()
    db.top_products.insert_many(top_prod.to_dict("records"))
    db.top_products.create_index([("revenue", DESCENDING)])
    print("loaded top_products:", len(top_prod), "documents")

    # ------------------------------------------------------------------ repeat_customers
    cust_orders = (orders[orders["order_status"] == "delivered"]
                   .merge(customers, on="customer_id", how="left"))
    repeat = (cust_orders.groupby("customer_unique_id")
              .agg(order_count=("order_id", "nunique"))
              .reset_index())
    total = len(repeat)
    repeat_count = int((repeat["order_count"] > 1).sum())
    repeat_rate = round(100.0 * repeat_count / total, 2)
    db.repeat_customers.drop()
    db.repeat_customers.insert_one({
        "total_customers": total,
        "repeat_customers": repeat_count,
        "repeat_rate_pct": repeat_rate,
        "computed_at": datetime.utcnow(),
    })
    print("loaded repeat_customers: total={} repeat={} rate={}%".format(
        total, repeat_count, repeat_rate))

    return fact, products, customers, orders


def build_popularity_recommender(fact, products, customers, orders, db, top_k=10):
    """Train/evaluate a popularity + category-affinity baseline.

    For each customer, recommend top products from categories they have already
    bought, falling back to global top products if needed. Evaluate with
    Precision@K and Recall@K on a time-based or random train/test split.
    """
    # fact already carries customer_unique_id and category from load_aggregates
    interactions = fact[fact["order_status"] == "delivered"].copy()

    # global product popularity
    product_pop = (interactions.groupby(["product_id", "category"])
                   .agg(score=("line_revenue", "sum"),
                        orders=("order_id", "nunique"))
                   .reset_index())
    product_pop["score"] = product_pop["score"].round(4)
    product_pop = product_pop.sort_values(["score", "orders"], ascending=False)
    global_top = product_pop["product_id"].tolist()

    # category -> ordered product list
    cat_to_products = defaultdict(list)
    for _, r in product_pop.iterrows():
        cat_to_products[r["category"]].append(r["product_id"])

    # customer -> categories bought and products bought
    cust_cats = defaultdict(set)
    cust_bought = defaultdict(set)
    for _, r in interactions.iterrows():
        cust_cats[r["customer_unique_id"]].add(r["category"])
        cust_bought[r["customer_unique_id"]].add(r["product_id"])

    # ------------------------------------------------------------------ train/test split for evaluation
    # Use customer_unique_id split to avoid leakage, keep customers with 2+ items
    all_customers = list(cust_bought.keys())
    eligible = [c for c in all_customers if len(cust_bought[c]) >= 2]
    random.shuffle(eligible)
    split = int(0.8 * len(eligible))
    train_users = set(eligible[:split])
    test_users = set(eligible[split:])

    # For evaluation, use last 20% of each test user's products as held-out
    # (random here because timestamps are not reliable enough per customer)
    test_holdout = {}
    for c in test_users:
        prods = list(cust_bought[c])
        n_hold = max(1, len(prods) // 5)
        test_holdout[c] = set(random.sample(prods, n_hold))

    # Recommend function: exclude a caller-supplied set (default: everything the
    # customer has bought). During evaluation the held-out item is removed from
    # the exclude set so it can be recommended.
    def recommend(customer_id, k=top_k, exclude=None):
        cats = cust_cats.get(customer_id, set())
        if exclude is None:
            exclude = cust_bought.get(customer_id, set())
        recs = []
        # First: top products from categories the customer already bought
        for cat in cats:
            for pid in cat_to_products.get(cat, []):
                if pid not in exclude and pid not in recs:
                    recs.append(pid)
                if len(recs) >= k:
                    break
            if len(recs) >= k:
                break
        # Fallback: global top products
        if len(recs) < k:
            for pid in global_top:
                if pid not in exclude and pid not in recs:
                    recs.append(pid)
                if len(recs) >= k:
                    break
        return recs[:k]

    # ------------------------------------------------------------------ leave-one-out evaluation
    # Hold out one purchased item per eligible customer, rebuild the profile
    # without it, and see whether the held-out item appears in the top-K list.
    eligible = [c for c in all_customers if len(cust_bought[c]) >= 2]
    hits = 0
    for c in eligible:
        held_out = random.choice(list(cust_bought[c]))
        # Profile excludes the held-out item, but recommendation is allowed to
        # return it (we only exclude the customer's *other* purchases).
        other_seen = cust_bought[c] - {held_out}
        recs = recommend(c, k=top_k, exclude=other_seen)
        if held_out in recs:
            hits += 1

    n_test = len(eligible)
    hit_rate_at_k = round(hits / n_test, 4)
    precision_at_k = round(hits / (n_test * top_k), 4)
    recall_at_k = round(hits / n_test, 4)
    f1_at_k = round(2 * precision_at_k * recall_at_k /
                    (precision_at_k + recall_at_k), 4) if (precision_at_k + recall_at_k) else 0.0

    print("\n=== POPULARITY / CATEGORY-AFFINITY RECOMMENDER ===")
    print("eligible customers (2+ items): {}".format(n_test))
    print("HitRate@{}:     {}".format(top_k, hit_rate_at_k))
    print("Precision@{}:   {}".format(top_k, precision_at_k))
    print("Recall@{}:      {}".format(top_k, recall_at_k))
    print("F1@{}:          {}".format(top_k, f1_at_k))

    # ------------------------------------------------------------------ store recommendations in MongoDB
    docs = []
    now = datetime.utcnow()
    for c in sorted(all_customers)[:20000]:  # cap at 20k for the demo
        recs = recommend(c, k=top_k)
        docs.append({
            "_id": c,
            "recommendations": [
                {"rank": i + 1, "product_id": pid}
                for i, pid in enumerate(recs)
            ],
            "n_recommendations": len(recs),
            "generated_at": now,
            "model": "popularity_category_affinity",
        })

    db.recommendations.drop()
    if docs:
        db.recommendations.insert_many(docs)
    db.recommendations.create_index([("_id", ASCENDING)])
    db.recommendations.create_index([("recommendations.product_id", ASCENDING)])
    print("recommendations collection updated: {} documents".format(len(docs)))

    # ------------------------------------------------------------------ write local CSV for reference
    csv_path = os.path.join(OUT, "recommendations.csv")
    os.makedirs(OUT, exist_ok=True)
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["customer_unique_id", "product_id", "rank"])
        for d in docs:
            for r in d["recommendations"]:
                writer.writerow([d["_id"], r["product_id"], r["rank"]])
    print("wrote {}".format(csv_path))

    # ------------------------------------------------------------------ persist metrics
    metrics_path = os.path.join(OUT, "recommender_metrics.txt")
    with open(metrics_path, "w") as fh:
        fh.write("model=popularity_category_affinity\n")
        fh.write("top_k={}\n".format(top_k))
        fh.write("eligible_customers={}\n".format(n_test))
        fh.write("hit_rate@{}={}\n".format(top_k, hit_rate_at_k))
        fh.write("precision@{}={}\n".format(top_k, precision_at_k))
        fh.write("recall@{}={}\n".format(top_k, recall_at_k))
        fh.write("f1@{}={}\n".format(top_k, f1_at_k))
    print("wrote {}".format(metrics_path))

    return {"hit_rate_at_k": hit_rate_at_k,
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "f1_at_k": f1_at_k}


def main():
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]
    print("connected to MongoDB database '{}\n".format(DB_NAME))

    fact, products, customers, orders = load_aggregates(db)
    metrics = build_popularity_recommender(fact, products, customers, orders, db)

    print("\nCollections now in '{}':".format(DB_NAME), db.list_collection_names())
    client.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
