"""Runtime settings for the E-Commerce Big Data Analytics project.

All tunable parameters live here instead of being scattered through scripts.
Values can be overridden with environment variables where noted.
"""
import os

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "8501"))
DASHBOARD_TITLE = "Olist E-Commerce Analytics & Recommendations"

# ---------------------------------------------------------------------------
# Recommender
# ---------------------------------------------------------------------------
RECOMMENDER_TOP_K = int(os.environ.get("RECOMMENDER_TOP_K", "10"))
RECOMMENDER_ELIGIBLE_MIN_ITEMS = int(os.environ.get("RECOMMENDER_ELIGIBLE_MIN_ITEMS", "2"))
POPULARITY_WEIGHT = float(os.environ.get("POPULARITY_WEIGHT", "0.6"))
SENTIMENT_WEIGHT = float(os.environ.get("SENTIMENT_WEIGHT", "0.4"))

# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------
# Confidence approaches 1.0 as the number of reviews grows.
SENTIMENT_DEFAULT_NEUTRAL = 0.0
SENTIMENT_NEGATION_WINDOW = int(os.environ.get("SENTIMENT_NEGATION_WINDOW", "2"))

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
# Set to a non-empty value to skip long-running Hadoop/Spark stages during
# development or testing.
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
