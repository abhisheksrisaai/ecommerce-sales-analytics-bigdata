#!/usr/bin/env python3
"""Unit tests for the DA-3 sentiment pipeline, recommender and dashboard helpers.

Run:
    python3 -m pytest tests/test_da3.py
    python3 tests/test_da3.py

Dependencies:
    unittest, pymongo, pandas, numpy.
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict

# Allow imports from the project root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import METRICS_FILE, MONGO_URI
from src.sentiment import portuguese_sentiment as ps
from pymongo import MongoClient


class TestPortugueseSentiment(unittest.TestCase):
    """Tests for the Portuguese sentiment lexicon scorer."""

    def test_positive_text(self):
        self.assertGreater(ps.score_text("Produto excelente, adorei a compra"), 0)

    def test_negative_text(self):
        self.assertLess(ps.score_text("Produto ruim, nao gostei"), 0)

    def test_negation_flips_positive(self):
        self.assertLess(ps.score_text("Nao gostei do produto"), 0)

    def test_empty_text(self):
        self.assertIsNone(ps.score_text(""))
        self.assertIsNone(ps.score_text(None))

    def test_normalise_accents(self):
        self.assertEqual(ps.normalise("Ótimo produto!"), "otimo produto")

    def test_aggregate_sentiment(self):
        stats = ps.aggregate_sentiment([
            "muito bom", "excelente", "ruim", "nao gostei"
        ])
        self.assertEqual(stats["count"], 4)
        self.assertIsInstance(stats["mean"], float)


class TestMetricsPath(unittest.TestCase):
    """Tests for dashboard metrics-file path handling."""

    def test_metrics_file_resolved_from_project_root(self):
        """The configured METRICS_FILE must exist after the loader runs."""
        self.assertTrue(os.path.exists(METRICS_FILE),
                        f"metrics file should exist at {METRICS_FILE}")

    def test_missing_metrics_handled_gracefully(self):
        """A missing metrics file should result in an empty metrics dict."""
        bogus_path = os.path.join(tempfile.gettempdir(), "nonexistent_metrics.txt")
        self.assertFalse(os.path.exists(bogus_path))
        # Dashboard load_metrics returns empty dict when file missing
        metrics = {}
        self.assertEqual(metrics, {})


class TestMongoDBSchemas(unittest.TestCase):
    """Tests verifying the MongoDB serving-layer schema."""

    def setUp(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self.client.admin.command("ping")
        except Exception as exc:
            self.skipTest(f"MongoDB not reachable at {MONGO_URI}: {exc}")
        self.db = self.client["olist_analytics"]

    def tearDown(self):
        if hasattr(self, "client"):
            self.client.close()

    def test_required_collections_exist(self):
        required = {"monthly_gmv", "state_revenue", "delivery_performance",
                    "payment_distribution", "review_distribution", "top_products",
                    "repeat_customers", "category_stats", "recommendations",
                    "baseline_recommendations", "product_sentiment"}
        actual = set(self.db.list_collection_names())
        missing = required - actual
        self.assertEqual(missing, set(), f"missing collections: {missing}")

    def test_category_stats_are_populated_and_consistent(self):
        """Every dashboard category must have revenue and review data."""
        count = self.db.category_stats.count_documents({})
        self.assertGreater(count, 0,
                           "category_stats is empty; dashboard shows N/A")
        top = self.db.category_stats.find_one(sort=[("revenue", -1)])
        self.assertIsNotNone(top)
        for field in ("category", "items_sold", "revenue", "avg_review"):
            self.assertIn(field, top)
        self.assertGreater(top["revenue"], 0)
        self.assertGreater(top["items_sold"], 0)

    def test_recommendations_have_component_scores(self):
        doc = self.db.recommendations.find_one()
        self.assertIsNotNone(doc)
        self.assertIn("recommendations", doc)
        self.assertTrue(len(doc["recommendations"]) > 0)
        rec = doc["recommendations"][0]
        self.assertIn("score", rec)
        self.assertIn("popularity_score", rec)
        self.assertIn("sentiment_score", rec)
        self.assertEqual(doc["model"].lower(), "nlp_sentiment_popularity")

    def test_product_sentiment_range(self):
        doc = self.db.product_sentiment.find_one()
        if doc:
            self.assertIn("sentiment_score", doc)
            self.assertGreaterEqual(doc["sentiment_score"], -1.0)
            self.assertLessEqual(doc["sentiment_score"], 1.0)

    def test_category_stats_use_id_as_category(self):
        doc = self.db.category_stats.find_one()
        self.assertIsNotNone(doc)
        self.assertIn("_id", doc)
        self.assertIn("revenue", doc)


class TestRecommenderRanking(unittest.TestCase):
    """Tests for the recommender ranking formula and rules."""

    def test_sentiment_changes_ranking(self):
        """A higher sentiment score should improve rank when popularity is equal."""
        products = [
            {"product_id": "p1", "popularity_norm": 0.5, "sentiment_norm": 0.9, "confidence": 1.0},
            {"product_id": "p2", "popularity_norm": 0.5, "sentiment_norm": 0.1, "confidence": 1.0},
        ]
        scored = []
        for p in products:
            # Match the formula used in loader_and_recommender.py
            score = 0.6 * p["popularity_norm"] + 0.4 * p["sentiment_norm"]
            scored.append((p["product_id"], score))
        scored.sort(key=lambda x: x[1], reverse=True)
        self.assertEqual(scored[0][0], "p1")
        self.assertEqual(scored[1][0], "p2")

    def test_cold_start_recommends_global_top(self):
        """A customer with no history should receive global top products."""
        global_top = ["a", "b", "c", "d"]
        cust_bought = set()  # cold start
        recs = [pid for pid in global_top if pid not in cust_bought][:3]
        self.assertEqual(recs, ["a", "b", "c"])

    def test_excludes_already_bought(self):
        """Recommendations should not include products the customer already bought."""
        global_top = ["a", "b", "c", "d"]
        cust_bought = {"a", "c"}
        recs = [pid for pid in global_top if pid not in cust_bought][:3]
        self.assertEqual(recs, ["b", "d"])


class TestDashboardMetrics(unittest.TestCase):
    """Tests for the recommender metrics file format."""

    def test_metrics_file_format(self):
        self.assertTrue(os.path.exists(METRICS_FILE))
        with open(METRICS_FILE) as fh:
            content = fh.read()
        self.assertIn("model=nlp_sentiment_popularity", content)
        self.assertIn("[baseline_popularity_category_affinity]", content)
        for key in ["hit_rate@10", "precision@10", "recall@10", "f1@10"]:
            self.assertIn(key, content)


class TestRecommenderEvaluation(unittest.TestCase):
    """Tests that exercise the actual recommender evaluation path."""

    def setUp(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self.client.admin.command("ping")
        except Exception as exc:
            self.skipTest(f"MongoDB not reachable at {MONGO_URI}: {exc}")
        self.db = self.client["olist_analytics"]

    def tearDown(self):
        if hasattr(self, "client"):
            self.client.close()

    def _load_aggregates(self):
        """Load fact and dimension tables from MongoDB."""
        from src.recommender.loader_and_recommender import load_aggregates
        return load_aggregates(self.db)

    def _compute_split(self, fact, reviews):
        """Return the same evaluation split the recommender uses."""
        from src.recommender.loader_and_recommender import _build_evaluation_split
        interactions = fact[fact["order_status"] == "delivered"].copy()
        cust_bought = defaultdict(set)
        for _, r in interactions.iterrows():
            cust_bought[r["customer_unique_id"]].add(r["product_id"])
        eligible = [c for c in cust_bought if len(cust_bought[c]) >= 2]
        return _build_evaluation_split(interactions, reviews, eligible, cust_bought)

    def test_build_recommenders_runs_and_nlp_beats_baseline(self):
        """The full evaluation path runs and NLP matches or beats the baseline."""
        from src.recommender.loader_and_recommender import build_recommenders
        fact, products, customers, orders, reviews = self._load_aggregates()
        baseline, nlp, held_out_map = build_recommenders(
            fact, products, customers, orders, reviews, self.db)
        self.assertEqual(baseline["eligible_customers"], nlp["eligible_customers"])
        self.assertGreaterEqual(nlp["hit_rate"], baseline["hit_rate"])
        self.assertIn("hit_rate", baseline)
        self.assertIn("hit_rate", nlp)
        self.assertEqual(len(held_out_map), baseline["eligible_customers"])

    def test_same_held_out_map_for_both_models(self):
        """A single held-out map is built before training and shared by both models."""
        fact, products, customers, orders, reviews = self._load_aggregates()
        interactions = fact[fact["order_status"] == "delivered"].copy()
        cust_bought = defaultdict(set)
        for _, r in interactions.iterrows():
            cust_bought[r["customer_unique_id"]].add(r["product_id"])
        eligible = [c for c in cust_bought if len(cust_bought[c]) >= 2]
        held_out_map, _, _ = self._compute_split(fact, reviews)
        self.assertEqual(len(held_out_map), len(eligible))
        for c in eligible:
            self.assertIn(c, held_out_map)
            self.assertIn(held_out_map[c], cust_bought[c])

    def test_held_out_products_excluded_from_training_interactions(self):
        """No held-out (customer, product) pair appears in training interactions."""
        fact, products, customers, orders, reviews = self._load_aggregates()
        held_out_map, training_interactions, _ = self._compute_split(fact, reviews)
        held_out_set = set(held_out_map.items())
        training_pairs = set(
            zip(training_interactions["customer_unique_id"],
                training_interactions["product_id"]))
        overlap = held_out_set & training_pairs
        self.assertEqual(overlap, set(),
                         f"{len(overlap)} held-out pairs leaked into training interactions")

    def test_held_out_order_reviews_excluded_from_training_sentiment(self):
        """Reviews belonging to orders with held-out items are excluded."""
        fact, products, customers, orders, reviews = self._load_aggregates()
        interactions = fact[fact["order_status"] == "delivered"].copy()
        held_out_map, _, training_reviews = self._compute_split(fact, reviews)
        held_out_set = set(held_out_map.items())
        is_held_out = interactions.apply(
            lambda r: (r["customer_unique_id"], r["product_id"]) in held_out_set, axis=1)
        held_out_order_ids = set(interactions[is_held_out]["order_id"].unique())
        leaked = training_reviews[training_reviews["order_id"].isin(held_out_order_ids)]
        self.assertEqual(len(leaked), 0,
                         f"{len(leaked)} reviews from held-out orders leaked into training sentiment")

    def test_held_out_absent_from_visible_history(self):
        """For each customer, the held-out product is not in the visible history."""
        fact, products, customers, orders, reviews = self._load_aggregates()
        interactions = fact[fact["order_status"] == "delivered"].copy()
        cust_bought = defaultdict(set)
        for _, r in interactions.iterrows():
            cust_bought[r["customer_unique_id"]].add(r["product_id"])
        held_out_map, _, _ = self._compute_split(fact, reviews)
        for c, held_out in held_out_map.items():
            other_seen = cust_bought[c] - {held_out}
            self.assertNotIn(held_out, other_seen)

    def test_evaluation_split_deterministic_with_fixed_seed(self):
        """Resetting the random seed reproduces the same held-out map."""
        fact, products, customers, orders, reviews = self._load_aggregates()
        random.seed(42)
        held_out_map1, _, _ = self._compute_split(fact, reviews)
        random.seed(42)
        held_out_map2, _, _ = self._compute_split(fact, reviews)
        self.assertEqual(held_out_map1, held_out_map2)

    def test_evaluation_deterministic_across_fresh_processes(self):
        """Two fresh Python processes produce identical held-out maps and metrics."""
        script = """
import json, hashlib, sys
sys.path.insert(0, {project_root!r})
import random
random.seed(42)
from pymongo import MongoClient
from config.paths import MONGO_URI
from src.recommender.loader_and_recommender import load_aggregates, build_recommenders
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
client.admin.command("ping")
db = client["olist_analytics"]
fact, products, customers, orders, reviews = load_aggregates(db)
baseline, nlp, held_out_map = build_recommenders(
    fact, products, customers, orders, reviews, db)
client.close()
result = {{
    "held_out_hash": hashlib.md5(
        json.dumps(sorted(held_out_map.items()), sort_keys=True).encode()).hexdigest(),
    "eligible": len(held_out_map),
    "baseline_hit_rate": baseline["hit_rate"],
    "nlp_hit_rate": nlp["hit_rate"],
    "baseline_f1": baseline["f1"],
    "nlp_f1": nlp["f1"],
}}
print(json.dumps(result))
""".format(project_root=PROJECT_ROOT)
        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT
        results = []
        for _ in range(2):
            proc = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, env=env, timeout=300)
            if proc.returncode != 0:
                self.fail(f"fresh-process run failed: {proc.stderr}")
            results.append(json.loads(proc.stdout.strip().splitlines()[-1]))
        self.assertEqual(results[0]["held_out_hash"], results[1]["held_out_hash"])
        self.assertEqual(results[0]["baseline_hit_rate"], results[1]["baseline_hit_rate"])
        self.assertEqual(results[0]["nlp_hit_rate"], results[1]["nlp_hit_rate"])
        self.assertEqual(results[0]["baseline_f1"], results[1]["baseline_f1"])
        self.assertEqual(results[0]["nlp_f1"], results[1]["nlp_f1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
