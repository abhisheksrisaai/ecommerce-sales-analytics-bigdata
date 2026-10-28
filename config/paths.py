"""Project path configuration.

This module defines all project-relative paths in one place so that no other
file needs to hard-code absolute paths. Import it wherever the project needs to
locate data, source code, outputs, logs or deliverables.

Example:
    from config.paths import RAW_DIR, OUT_DIR, REPORT_DIR
    csv_path = os.path.join(RAW_DIR, "olist_orders_dataset.csv")
"""
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Local directories
data = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(data, "raw")
SAMPLE_DIR = os.path.join(data, "sample")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
OUT_DIR = os.path.join(PROJECT_ROOT, "out")
REPORT_DIR = os.path.join(OUT_DIR, "report")
MAPREDUCE_BUILD_DIR = os.path.join(OUT_DIR, "mapreduce", "build")
DELIVERABLES_DIR = os.path.join(PROJECT_ROOT, "deliverables")
ARCHIVE_DIR = os.path.join(PROJECT_ROOT, "archive")

# HDFS paths used by the ingestion and MapReduce stages.
# These are independent of the local filesystem layout.
HDFS_BASE = "/olist"
HDFS_RAW_DIR = f"{HDFS_BASE}/raw"
HDFS_CLEAN_DIR = f"{HDFS_BASE}/clean"
HDFS_OUT_DIR = f"{HDFS_BASE}/out"

# MongoDB connection
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "olist_analytics")

# Common file paths
METRICS_FILE = os.path.join(OUT_DIR, "recommender_metrics.txt")


def ensure_dirs():
    """Create local output, log and report directories if they do not exist."""
    for d in (OUT_DIR, LOGS_DIR, REPORT_DIR):
        os.makedirs(d, exist_ok=True)
