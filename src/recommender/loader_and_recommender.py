#!/usr/bin/env python3
"""Build dashboard aggregates, product sentiment and recommendations in MongoDB.

This module is the DA-3 entry point for the serving layer. It reads the local
Olist CSVs, computes business aggregates, scores Portuguese review text,
trains two recommenders (a popularity/category-affinity baseline and an
NLP-sentiment-aware model), evaluates them with leave-one-out ranking metrics,
and stores everything in MongoDB.

Inputs:
    - `data/raw/olist_*.csv` (orders, items, customers, products, payments,
      reviews, translations, sellers, geolocation).

Outputs (MongoDB collections in `olist_analytics`):
    - `monthly_gmv`, `state_revenue`, `delivery_performance`,
      `payment_distribution`, `review_distribution`, `top_products`,
      `category_stats`, `repeat_customers` (dashboard aggregates)
    - `product_sentiment` (per-product sentiment metadata)
    - `baseline_recommendations` (popularity baseline)
    - `recommendations` (active NLP-aware model)

Local outputs:
    - `out/recommendations.csv`
    - `out/recommender_metrics.txt`

Run:
    python3 -m src.recommender.loader_and_recommender

Dependencies:
    pandas, numpy, pymongo, and the local `src.sentiment.portuguese_sentiment`
    module. MongoDB must be reachable at the URI configured in `config/paths.py`.
"""
import csv
import os
import random
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd
from pymongo import ASCENDING, DESCENDING, MongoClient

# Allow imports from the project root when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import METRICS_FILE, MONGO_DB_NAME, MONGO_URI, OUT_DIR, RAW_DIR, ensure_dirs
from config.settings import (
    POPULARITY_WEIGHT,
    RECOMMENDER_ELIGIBLE_MIN_ITEMS,
    RECOMMENDER_TOP_K,
    SENTIMENT_WEIGHT,
)
from src.sentiment.portuguese_sentiment import review_stats

random.seed(42)
np.random.seed(42)


def read_raw(name):
    """Read a CSV file from the local raw data directory.

    Parameters
    ----------
    name : str
        Filename inside `data/raw/` (e.g. "olist_orders_dataset.csv").

    Returns
    -------
    pandas.DataFrame
        The CSV contents read as strings to preserve leading zeros and ids.

    Raises
    ------
    FileNotFoundError
        If the requested CSV does not exist.
    """
    path = os.path.join(RAW_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required dataset not found: {path}")
    return pd.read_csv(path, dtype=str)


def load_aggregates(db):
    """Compute dashboard-ready aggregates from local CSVs and load into MongoDB.

    Parameters
    ----------
    db : pymongo.database.Database
        MongoDB database object (typically `olist_analytics`).

    Returns
    -------
    tuple of pandas.DataFrame
        `(fact, products, customers, orders, reviews)` where `fact` is the
        delivered-order line-item fact table joined with orders, customers and
        product categories.
    """
    orders = read_raw("olist_orders_dataset.csv")
    items = read_raw("olist_order_items_dataset.csv")
    customers = read_raw("olist_customers_dataset.csv")
    products = read_raw("olist_products_dataset.csv")
    translation = read_raw("product_category_name_translation.csv")
    payments = read_raw("olist_order_payments_dataset.csv")
    reviews = read_raw("olist_order_reviews_dataset.csv")

    # Convert numeric columns
    items["price"] = items["price"].astype(float)
    items["freight_value"] = items["freight_value"].astype(float)
    items["line_revenue"] = items["price"] + items["freight_value"]
    payments["payment_value"] = payments["payment_value"].astype(float)
    reviews["review_score"] = reviews["review_score"].astype(int)

    # Map Portuguese category names to English
    cat_map = dict(zip(translation["product_category_name"],
                       translation["product_category_name_english"]))
    products["category"] = products["product_category_name"].map(cat_map).fillna(
        products["product_category_name"]).fillna("unknown")

    # Build the line-item fact table
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

    # ------------------------------------------------------------------ category_stats
    # The dashboard's Overview and Categories pages read this collection. It is
    # computed directly from the fact table so the dashboard does not depend on
    # the Spark `out/top_categories.csv` artefact being present.
    cat_stats = (delivered.groupby("category")
                 .agg(items_sold=("order_item_id", "count"),
                      revenue=("line_revenue", "sum"))
                 .reset_index())
    cat_stats["revenue"] = cat_stats["revenue"].round(2)

    # Average review score per category, matching the Spark ETL: reviews are
    # first averaged per order, then averaged across the category's line items.
    review_agg = (reviews.groupby("order_id")["review_score"]
                  .mean().round(2).rename("avg_review_score"))
    cat_reviews = delivered[["order_id", "category"]].merge(
        review_agg, on="order_id", how="left")
    cat_avg = (cat_reviews.groupby("category")["avg_review_score"]
               .mean().round(2).reset_index(name="avg_review"))
    cat_stats = cat_stats.merge(cat_avg, on="category", how="left")
    cat_stats["avg_review"] = cat_stats["avg_review"].fillna(0.0)
    cat_stats = cat_stats.sort_values("revenue", ascending=False)
    db.category_stats.drop()
    db.category_stats.insert_many(cat_stats.to_dict("records"))
    db.category_stats.create_index([("revenue", DESCENDING)])
    print("loaded category_stats:", len(cat_stats), "documents")

    # ------------------------------------------------------------------ repeat_customers
    cust_orders = (orders[orders["order_status"] == "delivered"]
                   .merge(customers, on="customer_id", how="left"))
    repeat = (cust_orders.groupby("customer_unique_id")
              .agg(order_count=("order_id", "nunique"))
              .reset_index())
    total = len(repeat)
    repeat_count = int((repeat["order_count"] > 1).sum())
    repeat_rate = round(100.0 * repeat_count / total, 2) if total else 0.0
    db.repeat_customers.drop()
    db.repeat_customers.insert_one({
        "total_customers": total,
        "repeat_customers": repeat_count,
        "repeat_rate_pct": repeat_rate,
        "computed_at": datetime.utcnow(),
    })
    print("loaded repeat_customers: total={} repeat={} rate={}%".format(
        total, repeat_count, repeat_rate))

    return fact, products, customers, orders, reviews


def compute_product_sentiment(reviews, items, products):
    """Compute order-level sentiment and derive product-level sentiment.

    Reviews in the Olist dataset are order-level. This function first scores
    the review text with the Portuguese lexicon. Then it attributes that
    sentiment to the products in the order, weighted by each product's share
    of the order's line revenue. This avoids blindly assigning the same
    sentiment to every product while still using all available review text.

    Parameters
    ----------
    reviews : pandas.DataFrame
        Reviews DataFrame, including `review_comment_message`.
    items : pandas.DataFrame
        Order-items DataFrame, including `order_id`, `product_id`, `price`
        and `freight_value`.
    products : pandas.DataFrame
        Products DataFrame, including `product_id` and `category`.

    Returns
    -------
    pandas.DataFrame
        One row per product with columns:
        - `product_id`
        - `category`
        - `sentiment_score`: revenue-share-weighted average sentiment in [-1, 1]
        - `review_count`: number of distinct orders with review text
    """
    print("\n=== NLP SENTIMENT PIPELINE ===")
    scored = review_stats(reviews)
    scored["order_sentiment"] = scored["sentiment_score"].fillna(0.0)
    scored["has_text"] = scored["has_text"].astype(bool)
    print("reviews with text: {} / {} ({:.1f}%)".format(
        scored["has_text"].sum(), len(scored),
        100.0 * scored["has_text"].sum() / len(scored)))

    # Merge reviews with items to attribute sentiment to products
    rev_items = (scored[scored["has_text"]][["order_id", "order_sentiment"]]
                 .merge(items[["order_id", "product_id", "price", "freight_value"]],
                        on="order_id", how="inner"))
    rev_items["line_revenue"] = rev_items["price"].astype(float) + rev_items["freight_value"].astype(float)

    # Revenue share of each product within its order
    order_totals = rev_items.groupby("order_id")["line_revenue"].sum().reset_index(name="order_total")
    rev_items = rev_items.merge(order_totals, on="order_id", how="left")
    rev_items["weight"] = rev_items["line_revenue"] / rev_items["order_total"].replace(0, np.nan)
    # If an order has zero total revenue, split weight equally across its items
    rev_items["weight"] = rev_items["weight"].fillna(
        1.0 / rev_items.groupby("order_id")["product_id"].transform("count"))
    rev_items["weighted_sentiment"] = rev_items["order_sentiment"] * rev_items["weight"]

    # Aggregate to product level
    prod_sent = (rev_items.groupby("product_id")
                 .agg(sentiment_sum=("weighted_sentiment", "sum"),
                      sentiment_weight=("weight", "sum"),
                      review_count=("order_id", "nunique"))
                 .reset_index())
    prod_sent["sentiment_score"] = (prod_sent["sentiment_sum"] /
                                    prod_sent["sentiment_weight"].replace(0, np.nan))
    prod_sent["sentiment_score"] = prod_sent["sentiment_score"].fillna(0.0).round(4)
    prod_sent = prod_sent.merge(products[["product_id", "category"]], on="product_id", how="left")

    print("products with review-text sentiment: {}".format(len(prod_sent)))
    print("mean product sentiment: {:.4f}".format(prod_sent["sentiment_score"].mean()))
    print("sentiment range: [{:.4f}, {:.4f}]".format(
        prod_sent["sentiment_score"].min(), prod_sent["sentiment_score"].max()))

    return prod_sent


def _build_feature_structures(interactions, reviews, items, products, top_k):
    """Build popularity, sentiment and ranking structures from a given data split.

    This helper is called twice: once on the training split (with held-out items
    and their orders excluded) for evaluation, and once on the full data for the
    deployed recommendations.

    Parameters
    ----------
    interactions : pandas.DataFrame
        Line-item interactions to use (already filtered to delivered orders).
    reviews : pandas.DataFrame
        Reviews to use for sentiment.
    items : pandas.DataFrame
        Raw order-items DataFrame.
    products : pandas.DataFrame
        Products DataFrame with category.
    top_k : int
        Number of recommendations per customer.

    Returns
    -------
    dict
        Feature-derived structures needed by the recommenders and evaluator.
    """
    # ------------------------------------------------------------------ product popularity
    product_pop = (interactions.groupby(["product_id", "category"])
                   .agg(popularity=("line_revenue", "sum"),
                        orders=("order_id", "nunique"))
                   .reset_index())
    product_pop["popularity"] = product_pop["popularity"].round(4)
    product_pop = product_pop.sort_values(["popularity", "orders"], ascending=False)

    cat_to_products_pop = defaultdict(list)
    for _, r in product_pop.iterrows():
        cat_to_products_pop[r["category"]].append(r["product_id"])

    # ------------------------------------------------------------------ customer category profile from this split
    cust_cats = defaultdict(set)
    for _, r in interactions.iterrows():
        cust_cats[r["customer_unique_id"]].add(r["category"])

    # ------------------------------------------------------------------ product sentiment
    prod_sent = compute_product_sentiment(reviews, items, products)
    review_count_map = dict(zip(prod_sent["product_id"], prod_sent["review_count"]))

    # Min-max normalise popularity
    pop_min = product_pop["popularity"].min()
    pop_max = product_pop["popularity"].max()
    product_pop["popularity_norm"] = ((product_pop["popularity"] - pop_min) /
                                      (pop_max - pop_min + 1e-9)).round(4)

    # Min-max normalise sentiment to [0, 1] for combination
    sent_min = prod_sent["sentiment_score"].min()
    sent_max = prod_sent["sentiment_score"].max()
    prod_sent["sentiment_norm"] = ((prod_sent["sentiment_score"] - sent_min) /
                                   (sent_max - sent_min + 1e-9)).round(4)

    # Confidence scales with review count relative to the most-reviewed product
    max_reviews = prod_sent["review_count"].max() if len(prod_sent) else 1
    prod_sent["confidence"] = prod_sent["review_count"].apply(
        lambda rc: min(1.0, rc / max_reviews))

    # Combine popularity and sentiment
    product_scores = product_pop[["product_id", "category", "popularity", "popularity_norm"]].copy()
    product_scores = product_scores.merge(
        prod_sent[["product_id", "sentiment_score", "sentiment_norm", "review_count", "confidence"]],
        on="product_id", how="left")
    product_scores["sentiment_norm"] = product_scores["sentiment_norm"].fillna(0.5)
    product_scores["review_count"] = product_scores["review_count"].fillna(0)
    product_scores["confidence"] = product_scores["confidence"].fillna(0.0)
    product_scores["nlp_score"] = (
        POPULARITY_WEIGHT * product_scores["popularity_norm"] +
        SENTIMENT_WEIGHT * (product_scores["confidence"] * product_scores["sentiment_norm"] +
                            (1 - product_scores["confidence"]) * 0.5)
    ).round(4)

    global_pop_rank = list(product_pop.sort_values("popularity", ascending=False)["product_id"])
    global_nlp_rank = list(product_scores.sort_values("nlp_score", ascending=False)["product_id"])

    cat_to_products_nlp = defaultdict(list)
    for _, r in product_scores.sort_values("nlp_score", ascending=False).iterrows():
        cat_to_products_nlp[r["category"]].append(r["product_id"])

    return {
        "product_pop": product_pop,
        "cat_to_products_pop": cat_to_products_pop,
        "cust_cats": cust_cats,
        "prod_sent": prod_sent,
        "product_scores": product_scores,
        "global_pop_rank": global_pop_rank,
        "global_nlp_rank": global_nlp_rank,
        "cat_to_products_nlp": cat_to_products_nlp,
    }


def _make_recommend_funcs(features, cust_bought, top_k):
    """Return baseline and NLP recommend functions bound to a feature set.

    Parameters
    ----------
    features : dict
        Output of `_build_feature_structures`.
    cust_bought : dict
        Full customer -> bought-products mapping (used for exclusion).
    top_k : int
        Number of recommendations.

    Returns
    -------
    tuple
        `(baseline_recommend, nlp_recommend)` functions.
    """
    cat_to_products_pop = features["cat_to_products_pop"]
    cust_cats = features["cust_cats"]
    global_pop_rank = features["global_pop_rank"]
    cat_to_products_nlp = features["cat_to_products_nlp"]
    global_nlp_rank = features["global_nlp_rank"]

    product_scores = features["product_scores"]
    nlp_score_map = dict(zip(product_scores["product_id"], product_scores["nlp_score"]))
    pop_score_map = dict(zip(product_scores["product_id"], product_scores["popularity_norm"]))
    sent_score_map = dict(zip(
        product_scores["product_id"],
        product_scores["confidence"] * product_scores["sentiment_norm"] +
        (1 - product_scores["confidence"]) * 0.5))

    def baseline_recommend(customer_id, k=top_k, exclude=None):
        """Recommend bestselling products from categories the customer bought."""
        cats = cust_cats.get(customer_id, set())
        if exclude is None:
            exclude = cust_bought.get(customer_id, set())
        recs = []
        for cat in sorted(cats):
            for pid in cat_to_products_pop.get(cat, []):
                if pid not in exclude and pid not in recs:
                    recs.append(pid)
                if len(recs) >= k:
                    break
            if len(recs) >= k:
                break
        if len(recs) < k:
            for pid in global_pop_rank:
                if pid not in exclude and pid not in recs:
                    recs.append(pid)
                if len(recs) >= k:
                    break
        return recs[:k]

    def nlp_recommend(customer_id, k=top_k, exclude=None):
        """Combine popularity, category affinity, and review sentiment."""
        cats = cust_cats.get(customer_id, set())
        if exclude is None:
            exclude = cust_bought.get(customer_id, set())

        candidate_pool = []
        for cat in sorted(cats):
            for pid in cat_to_products_nlp.get(cat, []):
                if pid not in exclude and pid not in candidate_pool:
                    candidate_pool.append(pid)
                if len(candidate_pool) >= k * 3:
                    break
            if len(candidate_pool) >= k * 3:
                break
        if len(candidate_pool) < k * 3:
            for pid in global_nlp_rank:
                if pid not in exclude and pid not in candidate_pool:
                    candidate_pool.append(pid)
                if len(candidate_pool) >= k * 3:
                    break

        scored = []
        for pid in candidate_pool:
            score = nlp_score_map.get(pid, 0.0)
            pop_score = pop_score_map.get(pid, 0.0)
            sent_score = sent_score_map.get(pid, 0.5)
            scored.append((pid, score, pop_score, sent_score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    return baseline_recommend, nlp_recommend


def _build_evaluation_split(interactions, reviews, eligible, cust_bought):
    """Precompute one held-out item per eligible customer and build training split.

    This helper exists so the exact same split logic can be exercised by tests
    without reimplementing it.

    Parameters
    ----------
    interactions : pandas.DataFrame
        Delivered line-item interactions.
    reviews : pandas.DataFrame
        Reviews DataFrame.
    eligible : list
        Customers who participate in leave-one-out evaluation.
    cust_bought : dict
        Customer -> set of bought product IDs.

    Returns
    -------
    tuple
        `(held_out_map, training_interactions, training_reviews)`.
    """
    held_out_map = {c: random.choice(sorted(cust_bought[c])) for c in eligible}

    # Exclude every held-out (customer, product) pair from interactions.
    held_out_set = set(held_out_map.items())
    is_held_out = interactions.apply(
        lambda r: (r["customer_unique_id"], r["product_id"]) in held_out_set, axis=1)
    training_interactions = interactions[~is_held_out].copy()

    # Exclude reviews from any order that contains a held-out item, because those
    # reviews are partly about the held-out product.
    held_out_order_ids = set(
        interactions[is_held_out]["order_id"].unique())
    training_reviews = reviews[~reviews["order_id"].isin(held_out_order_ids)].copy()

    return held_out_map, training_interactions, training_reviews


def build_recommenders(fact, products, customers, orders, reviews, db, top_k=RECOMMENDER_TOP_K):
    """Build baseline and NLP recommenders and evaluate both.

    The evaluation precomputes a single held-out item per eligible customer and
    builds all ranking features (popularity, category lists, sentiment) from the
    training data with those held-out items and their order reviews excluded.
    Both models are evaluated on exactly the same held-out set, so their
    HitRate@10 values are directly comparable. After evaluation, the final
    deployed recommendations are produced from the full dataset.

    Parameters
    ----------
    fact : pandas.DataFrame
        Line-item fact table produced by `load_aggregates`.
    products : pandas.DataFrame
        Products with categories.
    customers : pandas.DataFrame
        Customers DataFrame.
    orders : pandas.DataFrame
        Orders DataFrame.
    reviews : pandas.DataFrame
        Reviews DataFrame.
    db : pymongo.database.Database
        MongoDB database for storing recommendations and sentiment.
    top_k : int, optional
        Number of recommendations per customer. Default from settings.

    Returns
    -------
    tuple
        `(baseline_metrics, nlp_metrics, held_out_map)`. The two metrics dicts
        contain `eligible_customers`, `hit_rate`, `precision`, `recall`, `f1`.
        `held_out_map` is the precomputed customer -> held-out product mapping
        used for the evaluation.
    """
    interactions = fact[fact["order_status"] == "delivered"].copy()
    items = read_raw("olist_order_items_dataset.csv")

    # ------------------------------------------------------------------ customer profiles
    cust_bought = defaultdict(set)
    cust_revenue = defaultdict(float)
    for _, r in interactions.iterrows():
        cust_bought[r["customer_unique_id"]].add(r["product_id"])
        cust_revenue[r["customer_unique_id"]] += r["line_revenue"]

    all_customers = list(cust_bought.keys())
    eligible = [c for c in all_customers if len(cust_bought[c]) >= RECOMMENDER_ELIGIBLE_MIN_ITEMS]

    # ------------------------------------------------------------------ precompute held-out set and training split
    held_out_map, training_interactions, training_reviews = _build_evaluation_split(
        interactions, reviews, eligible, cust_bought)

    print("\n=== EVALUATION SPLIT ===")
    print("eligible customers ({}+ items): {}".format(RECOMMENDER_ELIGIBLE_MIN_ITEMS, len(eligible)))
    print("training interactions: {} (excluded {} held-out items)".format(
        len(training_interactions), len(interactions) - len(training_interactions)))
    print("training reviews: {} (excluded {} reviews from held-out orders)".format(
        len(training_reviews), len(reviews) - len(training_reviews)))

    # ------------------------------------------------------------------ build training features and recommenders
    train_features = _build_feature_structures(
        training_interactions, training_reviews, items, products, top_k)
    train_baseline_rec, train_nlp_rec = _make_recommend_funcs(
        train_features, cust_bought, top_k)

    # ------------------------------------------------------------------ evaluate both models on the same held-out set
    def evaluate(recommend_fn, name):
        """Evaluate a recommender with the precomputed held-out set."""
        hits = 0
        for c in eligible:
            held_out = held_out_map[c]
            other_seen = cust_bought[c] - {held_out}
            recs = recommend_fn(c, k=top_k, exclude=other_seen)
            if recs and isinstance(recs[0], tuple):
                rec_ids = [r[0] for r in recs]
            else:
                rec_ids = recs
            if held_out in rec_ids:
                hits += 1
        n_test = len(eligible)
        hit_rate = round(hits / n_test, 4)
        precision = round(hits / (n_test * top_k), 4)
        recall = round(hits / n_test, 4)
        f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) else 0.0
        print("\n=== {} RECOMMENDER ===".format(name))
        print("eligible customers ({}+ items): {}".format(RECOMMENDER_ELIGIBLE_MIN_ITEMS, n_test))
        print("HitRate@{}:     {}".format(top_k, hit_rate))
        print("Precision@{}:   {}".format(top_k, precision))
        print("Recall@{}:      {}".format(top_k, recall))
        print("F1@{}:          {}".format(top_k, f1))
        return {
            "eligible_customers": n_test,
            "hit_rate": hit_rate,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    baseline_metrics = evaluate(train_baseline_rec, "POPULARITY / CATEGORY-AFFINITY BASELINE")
    nlp_metrics = evaluate(train_nlp_rec, "NLP SENTIMENT-AWARE")

    # ------------------------------------------------------------------ build full-data features for deployment
    full_features = _build_feature_structures(interactions, reviews, items, products, top_k)
    full_baseline_rec, full_nlp_rec = _make_recommend_funcs(full_features, cust_bought, top_k)

    # ------------------------------------------------------------------ store baseline recommendations (deployed from full data)
    now = datetime.utcnow()
    baseline_docs = []
    for c in sorted(all_customers)[:20000]:
        recs = full_baseline_rec(c, k=top_k)
        baseline_docs.append({
            "_id": c,
            "recommendations": [{"rank": i + 1, "product_id": pid} for i, pid in enumerate(recs)],
            "n_recommendations": len(recs),
            "generated_at": now,
            "model": "popularity_category_affinity",
        })
    db.baseline_recommendations.drop()
    if baseline_docs:
        db.baseline_recommendations.insert_many(baseline_docs)
    db.baseline_recommendations.create_index([("_id", ASCENDING)])
    print("\nbaseline_recommendations collection: {} documents".format(len(baseline_docs)))

    # ------------------------------------------------------------------ store NLP recommendations (active, deployed from full data)
    nlp_docs = []
    for c in sorted(all_customers)[:20000]:
        recs = full_nlp_rec(c, k=top_k)
        nlp_docs.append({
            "_id": c,
            "recommendations": [
                {
                    "rank": i + 1,
                    "product_id": pid,
                    "score": round(score, 4),
                    "popularity_score": round(pop_score, 4),
                    "sentiment_score": round(sent_score, 4),
                }
                for i, (pid, score, pop_score, sent_score) in enumerate(recs)
            ],
            "n_recommendations": len(recs),
            "generated_at": now,
            "model": "nlp_sentiment_popularity",
        })
    db.recommendations.drop()
    if nlp_docs:
        db.recommendations.insert_many(nlp_docs)
    db.recommendations.create_index([("_id", ASCENDING)])
    db.recommendations.create_index([("recommendations.product_id", ASCENDING)])
    print("recommendations collection (active NLP model): {} documents".format(len(nlp_docs)))

    # ------------------------------------------------------------------ store product sentiment metadata
    prod_sent = full_features["prod_sent"]
    sentiment_docs = prod_sent[["product_id", "category", "sentiment_score",
                                "review_count"]].to_dict("records")
    db.product_sentiment.drop()
    if sentiment_docs:
        db.product_sentiment.insert_many(sentiment_docs)
    db.product_sentiment.create_index([("product_id", ASCENDING)])
    print("product_sentiment collection: {} documents".format(len(sentiment_docs)))

    # ------------------------------------------------------------------ write local CSVs and metrics
    ensure_dirs()
    csv_path = os.path.join(OUT_DIR, "recommendations.csv")
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["customer_unique_id", "product_id", "rank", "score"])
        for d in nlp_docs:
            for r in d["recommendations"]:
                writer.writerow([d["_id"], r["product_id"], r["rank"], r["score"]])
    print("wrote {}".format(csv_path))

    with open(METRICS_FILE, "w") as fh:
        fh.write("model=nlp_sentiment_popularity\n")
        fh.write("top_k={}\n".format(top_k))
        fh.write("eligible_customers={}\n".format(nlp_metrics["eligible_customers"]))
        fh.write("hit_rate@10={}\n".format(nlp_metrics["hit_rate"]))
        fh.write("precision@10={}\n".format(nlp_metrics["precision"]))
        fh.write("recall@10={}\n".format(nlp_metrics["recall"]))
        fh.write("f1@10={}\n".format(nlp_metrics["f1"]))
        fh.write("\n")
        fh.write("[baseline_popularity_category_affinity]\n")
        fh.write("model=popularity_category_affinity\n")
        fh.write("top_k={}\n".format(top_k))
        fh.write("eligible_customers={}\n".format(baseline_metrics["eligible_customers"]))
        fh.write("hit_rate@10={}\n".format(baseline_metrics["hit_rate"]))
        fh.write("precision@10={}\n".format(baseline_metrics["precision"]))
        fh.write("recall@10={}\n".format(baseline_metrics["recall"]))
        fh.write("f1@10={}\n".format(baseline_metrics["f1"]))
    print("wrote {}".format(METRICS_FILE))

    return baseline_metrics, nlp_metrics, held_out_map


def main():
    """Connect to MongoDB, load aggregates and build recommenders."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception as exc:
        print("ERROR: cannot reach MongoDB at {}: {}".format(MONGO_URI, exc))
        print("Make sure MongoDB is running (e.g. `mongod --dbpath /path/to/db`).")
        return 1

    db = client[MONGO_DB_NAME]
    print("connected to MongoDB database '{}\n".format(MONGO_DB_NAME))

    try:
        fact, products, customers, orders, reviews = load_aggregates(db)
        baseline_metrics, nlp_metrics, _held_out_map = build_recommenders(
            fact, products, customers, orders, reviews, db)
    except FileNotFoundError as exc:
        print("ERROR: missing dataset: {}".format(exc))
        return 1
    finally:
        client.close()

    print("\nSummary:")
    print("  Baseline HitRate@10: {}".format(baseline_metrics["hit_rate"]))
    print("  NLP      HitRate@10: {}".format(nlp_metrics["hit_rate"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
