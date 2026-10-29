#!/usr/bin/env python3
"""Streamlit dashboard over the MongoDB serving layer.

This application provides six interactive views over the Olist e-commerce
aggregates and recommendations stored in MongoDB. It is intended for the DA-3
viva demonstration.

The MongoDB collections are populated by `src.recommender.loader_and_recommender`.

Inputs:
    - MongoDB database `olist_analytics` (configurable in `config/paths.py`).
    - `deploy/snapshot/*.json.gz` (fallback for deployments without MongoDB).
    - `out/recommender_metrics.txt` (written by the recommender loader).

When MongoDB is unreachable, the dashboard automatically falls back to the
bundled snapshot in `deploy/snapshot/`. This keeps the public Streamlit
deployment self-contained while the local/viva version continues to use the
real MongoDB serving layer.

Run:
    python3 -m streamlit run src/dashboard/app.py --server.port 8501

Dependencies:
    streamlit, pandas, plotly, pymongo, mongomock.
"""
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo import MongoClient

# Allow imports from the project root when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import METRICS_FILE, MONGO_DB_NAME, MONGO_URI
from config.settings import DASHBOARD_TITLE

BUNDLED_SNAPSHOT_DIR = os.path.join(PROJECT_ROOT, "deploy", "snapshot")

st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Brazilian state name mapping
# ---------------------------------------------------------------------------
STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


# ---------------------------------------------------------------------------
# Data backend: MongoDB with a bundled-snapshot fallback
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading bundled data snapshot...")
def _get_bundled_db():
    """Load `deploy/snapshot/*.json.gz` into an in-memory Mongo-compatible store.

    The public Streamlit deployment has no MongoDB server. The snapshot is
    exported from the local serving database by `deploy/export_snapshot.py` and
    uses the same collection names and document shapes as the real database.
    """
    import gzip
    import json

    import mongomock

    if not os.path.isdir(BUNDLED_SNAPSHOT_DIR):
        raise FileNotFoundError(
            f"Bundled snapshot directory not found: {BUNDLED_SNAPSHOT_DIR}"
        )

    client = mongomock.MongoClient()
    db = client[MONGO_DB_NAME]
    for filename in sorted(os.listdir(BUNDLED_SNAPSHOT_DIR)):
        if not filename.endswith(".json.gz"):
            continue
        collection_name = filename[: -len(".json.gz")]
        path = os.path.join(BUNDLED_SNAPSHOT_DIR, filename)
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            docs = json.load(handle)
        if docs:
            db[collection_name].insert_many(docs)
    return db


@st.cache_resource(show_spinner=False)
def _connect():
    """Connect to MongoDB, or load the bundled snapshot if it is unreachable.

    Returns
    -------
    tuple
        `(database, backend_name)` where `backend_name` is `"mongodb"` or
        `"bundled"`.

    Raises
    ------
    pymongo.errors.ServerSelectionTimeoutError
        If MongoDB is unreachable and no bundled snapshot is available.
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        return client[MONGO_DB_NAME], "mongodb"
    except Exception as exc:
        if os.path.isdir(BUNDLED_SNAPSHOT_DIR):
            print(f"MongoDB unavailable ({exc}); using bundled snapshot")
            return _get_bundled_db(), "bundled"
        raise


def get_db():
    """Return the serving database (MongoDB or the bundled snapshot)."""
    return _connect()[0]


def data_backend():
    """Return `"mongodb"` or `"bundled"` for the active data backend."""
    return _connect()[1]


def coll(name):
    """Return a MongoDB collection by name.

    Parameters
    ----------
    name : str
        Collection name.

    Returns
    -------
    pymongo.collection.Collection or mongomock.collection.Collection
    """
    return get_db()[name]


# Resolve the backend once so the sidebar can report it and the app fails fast
# when neither MongoDB nor a bundled snapshot is available.
try:
    get_db()
except Exception as exc:
    st.error(
        "The dashboard could not connect to MongoDB and no bundled snapshot "
        f"was found at `{BUNDLED_SNAPSHOT_DIR}`."
    )
    st.exception(exc)
    st.stop()


# ---------------------------------------------------------------------------
# Collection loaders with explicit, meaningful column names
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_monthly_gmv():
    """Load monthly GMV and order counts from MongoDB."""
    df = pd.DataFrame(list(coll("monthly_gmv").find({}, {"_id": 0})))
    if df.empty:
        return df
    df = df.sort_values("purchase_month").reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_category_stats():
    """Load category-level revenue and review statistics.

    Supports both historical and current `category_stats` schemas:
    the current loader stores the category in a `category` field, while older
    versions used `_id` as the category name.
    """
    df = pd.DataFrame(list(coll("category_stats").find()))
    if df.empty:
        return df
    if "category" not in df.columns:
        df = df.rename(columns={"_id": "category"})
    else:
        df = df.drop(columns=["_id"], errors="ignore")
    df = df.sort_values("revenue", ascending=False).reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_state_revenue():
    """Load state-level revenue and enrich with full state names."""
    df = pd.DataFrame(list(coll("state_revenue").find({}, {"_id": 0})))
    if df.empty:
        return df
    df["state_name"] = df["customer_state"].map(STATE_NAMES).fillna(df["customer_state"])
    df["label"] = df["customer_state"] + " - " + df["state_name"]
    df = df.sort_values("revenue", ascending=False).reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_delivery_performance():
    """Load delivery performance by state with full state names."""
    df = pd.DataFrame(list(coll("delivery_performance").find({}, {"_id": 0})))
    if df.empty:
        return df
    df["state_name"] = df["customer_state"].map(STATE_NAMES).fillna(df["customer_state"])
    df["label"] = df["customer_state"] + " - " + df["state_name"]
    df = df.sort_values("late_pct", ascending=False).reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_payment_distribution():
    """Load payment-type distribution from MongoDB."""
    df = pd.DataFrame(list(coll("payment_distribution").find({}, {"_id": 0})))
    if df.empty:
        return df
    df = df.sort_values("transactions", ascending=False).reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_review_distribution():
    """Load review-score distribution from MongoDB."""
    df = pd.DataFrame(list(coll("review_distribution").find({}, {"_id": 0})))
    if df.empty:
        return df
    df = df.sort_values("review_score").reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_top_products():
    """Load top products by revenue from MongoDB."""
    df = pd.DataFrame(list(coll("top_products").find({}, {"_id": 0})))
    if df.empty:
        return df
    df = df.sort_values("revenue", ascending=False).reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_repeat_customers():
    """Load the repeat-customer summary document."""
    doc = coll("repeat_customers").find_one({}, {"_id": 0})
    if doc is None:
        return {"total_customers": 0, "repeat_customers": 0, "repeat_rate_pct": 0}
    return doc


@st.cache_data(ttl=300, show_spinner=False)
def load_recommendations_sample():
    """Return one recommendation document to seed the customer lookup."""
    doc = coll("recommendations").find_one()
    return doc


# ---------------------------------------------------------------------------
# Metrics loader
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def load_metrics(path=None):
    """Read the recommender metrics file and return a flat dict.

    The metrics file contains an active NLP section followed by a
    `[baseline_popularity_category_affinity]` section. Keys are prefixed with
    `nlp_` or `baseline_` so the dashboard can display both models.

    Parameters
    ----------
    path : str, optional
        Path to the metrics file. Defaults to `out/recommender_metrics.txt`.

    Returns
    -------
    dict
        Flattened key-value pairs from the metrics file.
    """
    if path is None:
        path = METRICS_FILE
    metrics = {}
    if not os.path.exists(path):
        return metrics
    try:
        section = "nlp"
        with open(path) as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                if ln.startswith("[") and ln.endswith("]"):
                    section = "baseline"
                    continue
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    metrics[f"{section}_{k}"] = v
    except Exception as e:
        st.sidebar.warning(f"Could not read metrics file: {e}")
    return metrics


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------
st.title("📊 Olist E-Commerce Analytics & Recommendations")
st.markdown("""
Dashboard for the **E-Commerce Sales Analytics and Product Recommendation** project.
Data lives in MongoDB and was produced by the Hadoop, Hive, Spark and MapReduce pipeline.
""")

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["🏠 Overview", "📈 Sales Trends", "🏷️ Categories & Products",
     "🗺️ Geography", "🚚 Delivery", "🎯 Recommendations"]
)

# ---------------------------------------------------------------------------
# Overview page
# ---------------------------------------------------------------------------
if page == "🏠 Overview":
    st.header("Executive Summary")

    monthly = load_monthly_gmv()
    cat = load_category_stats()
    repeat = load_repeat_customers()
    pay = load_payment_distribution()

    total_gmv = float(monthly["gmv"].sum()) if not monthly.empty else 0.0
    total_orders = int(monthly["orders"].sum()) if not monthly.empty else 0
    top_category = cat.iloc[0]["category"] if not cat.empty else "N/A"
    top_cat_revenue = float(cat.iloc[0]["revenue"]) if not cat.empty else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", f"{total_orders:,}")
    col2.metric("Total GMV", f"R${total_gmv:,.2f}")
    col3.metric("Top Category", top_category, f"R${top_cat_revenue:,.2f}")
    col4.metric(
        "Repeat Customer Rate",
        f"{repeat.get('repeat_rate_pct', 0)}%",
        f"{repeat.get('repeat_customers', 0):,} of {repeat.get('total_customers', 0):,}"
    )

    st.subheader("Revenue by Category (Top 10)")
    if not cat.empty:
        fig = px.bar(
            cat.head(10).sort_values("revenue"),
            x="revenue",
            y="category",
            orientation="h",
            labels={"category": "Category", "revenue": "Revenue (R$)"},
            color="revenue",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, config={'displayModeBar': False})
    else:
        st.info("No category data available. Run the recommender loader first.")

    st.subheader("Payment Method Distribution")
    if not pay.empty:
        main_pay = pay[pay["payment_type"] != "not_defined"].copy()
        undefined = pay[pay["payment_type"] == "not_defined"]
        fig2 = px.pie(
            main_pay,
            names="payment_type",
            values="transactions",
            hole=0.35,
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, config={'displayModeBar': False})
        if not undefined.empty:
            row = undefined.iloc[0]
            st.caption(
                f"Note: {row['transactions']} transactions with payment_type='not_defined' "
                f"(R${row['total_value']:,.2f}) are excluded from the chart above."
            )
    else:
        st.info("No payment data available.")

    st.subheader("Active Recommender")
    metrics = load_metrics()
    rec1, rec2, rec3 = st.columns(3)
    rec1.metric("Model", metrics.get("nlp_model", "N/A"))
    rec2.metric("NLP HitRate@10", metrics.get("nlp_hit_rate@10", "N/A"))
    rec3.metric("Baseline HitRate@10", metrics.get("baseline_hit_rate@10", "N/A"))
    st.caption(
        "Open the Recommendations page in the sidebar to look up a customer "
        "and see the top recommended products."
    )


# ---------------------------------------------------------------------------
# Sales Trends page
# ---------------------------------------------------------------------------
elif page == "📈 Sales Trends":
    st.header("Sales Trends")
    monthly = load_monthly_gmv()

    if monthly.empty:
        st.info("No monthly GMV data available.")
    else:
        min_month = monthly["purchase_month"].min()
        default_start = "2017-01" if min_month <= "2017-01" else min_month
        start_month = st.selectbox(
            "Start month",
            options=monthly["purchase_month"].tolist(),
            index=monthly["purchase_month"].tolist().index(default_start)
            if default_start in monthly["purchase_month"].values else 0,
        )
        filtered = monthly[monthly["purchase_month"] >= start_month].copy()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Monthly GMV")
            fig = px.line(
                filtered,
                x="purchase_month",
                y="gmv",
                markers=True,
                labels={"purchase_month": "Month", "gmv": "GMV (R$)"},
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, config={'displayModeBar': False})

        with col2:
            st.subheader("Monthly Order Volume")
            fig = px.bar(
                filtered,
                x="purchase_month",
                y="orders",
                labels={"purchase_month": "Month", "orders": "Orders"},
                color="orders",
                color_continuous_scale="Greens",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, config={'displayModeBar': False})

        st.subheader("Monthly Data")
        st.dataframe(filtered, width='stretch')


# ---------------------------------------------------------------------------
# Categories & Products page
# ---------------------------------------------------------------------------
elif page == "🏷️ Categories & Products":
    st.header("Categories & Products")

    cat = load_category_stats()
    top_products = load_top_products()

    if cat.empty:
        st.info("No category data available.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 10 Categories by Revenue")
            fig = px.bar(
                cat.head(10),
                x="category",
                y="revenue",
                labels={"category": "Category", "revenue": "Revenue (R$)"},
                color="revenue",
                color_continuous_scale="Blues",
            )
            fig.update_layout(height=450, xaxis_tickangle=-45)
            st.plotly_chart(fig, config={'displayModeBar': False})

        with col2:
            st.subheader("Review Score vs. Revenue")
            fig = px.scatter(
                cat,
                x="avg_review",
                y="revenue",
                size="items_sold",
                hover_name="category",
                labels={"avg_review": "Average Review", "revenue": "Revenue (R$)"},
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, config={'displayModeBar': False})

    st.subheader("Top 10 Products by Revenue")
    if not top_products.empty:
        display = top_products.head(10).copy()
        display["label"] = display["product_id"].str[:16] + "... (" + display["category"] + ")"
        st.dataframe(display[["product_id", "category", "items_sold", "revenue"]], width='stretch')
        fig = px.bar(
            display,
            x="label",
            y="revenue",
            labels={"label": "Product (category)", "revenue": "Revenue (R$)"},
            color="revenue",
            color_continuous_scale="Cividis",
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, config={'displayModeBar': False})
    else:
        st.info("No product data available.")


# ---------------------------------------------------------------------------
# Geography page
# ---------------------------------------------------------------------------
elif page == "🗺️ Geography":
    st.header("Geographic Distribution")

    state = load_state_revenue()

    if state.empty:
        st.info("No state revenue data available.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Revenue by State (Top 15)")
            fig = px.bar(
                state.head(15),
                x="label",
                y="revenue",
                labels={"label": "State", "revenue": "Revenue (R$)"},
                color="revenue",
                color_continuous_scale="Purples",
            )
            fig.update_layout(height=450, xaxis_tickangle=0)
            st.plotly_chart(fig, config={'displayModeBar': False})

        with col2:
            st.subheader("Orders by State")
            fig = px.bar(
                state.head(15),
                x="label",
                y="orders",
                labels={"label": "State", "orders": "Orders"},
                color="orders",
                color_continuous_scale="Oranges",
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, config={'displayModeBar': False})

        st.subheader("State Revenue Table")
        st.dataframe(state[["customer_state", "state_name", "orders", "revenue", "avg_order_value"]],
                     width='stretch')


# ---------------------------------------------------------------------------
# Delivery page
# ---------------------------------------------------------------------------
elif page == "🚚 Delivery":
    st.header("Delivery Performance")

    deliv = load_delivery_performance()
    rev = load_review_distribution()

    if deliv.empty:
        st.info("No delivery performance data available.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Average Delivery Days by State")
            fig = px.bar(
                deliv.sort_values("avg_delivery_days", ascending=True),
                x="label",
                y="avg_delivery_days",
                labels={"label": "State", "avg_delivery_days": "Avg Delivery Days"},
                color="avg_delivery_days",
                color_continuous_scale="RdYlGn_r",
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, config={'displayModeBar': False})

        with col2:
            st.subheader("Late Delivery % by State")
            fig = px.bar(
                deliv,
                x="label",
                y="late_pct",
                labels={"label": "State", "late_pct": "Late %"},
                color="late_pct",
                color_continuous_scale="Reds",
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, config={'displayModeBar': False})

    st.subheader("Review Score Distribution")
    if not rev.empty:
        fig2 = px.bar(
            rev,
            x="review_score",
            y="reviews",
            labels={"review_score": "Review Score", "reviews": "Reviews"},
            color="reviews",
            color_continuous_scale="Teal",
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, config={'displayModeBar': False})
    else:
        st.info("No review distribution data available.")

    if not deliv.empty:
        avg_days = deliv["avg_delivery_days"].mean()
        worst_state = deliv.iloc[0]
        st.info(
            f"Across the {len(deliv)} states with more than 500 delivered orders, the average delivery "
            f"time is **{avg_days:.1f} days**. **{worst_state['state_name']} ({worst_state['customer_state']})** "
            f"has the highest late rate at **{worst_state['late_pct']}%**, averaging "
            f"**{worst_state['avg_delivery_days']:.1f} days**."
        )


# ---------------------------------------------------------------------------
# Recommendations page
# ---------------------------------------------------------------------------
elif page == "🎯 Recommendations":
    st.header("Product Recommendations")

    metrics = load_metrics()

    active_model = metrics.get("nlp_model", "N/A")
    active_hit = metrics.get("nlp_hit_rate@10", "N/A")
    active_prec = metrics.get("nlp_precision@10", "N/A")
    active_rec = metrics.get("nlp_recall@10", "N/A")
    base_hit = metrics.get("baseline_hit_rate@10", "N/A")

    st.markdown(f"""
    The active recommendation model is **{active_model}**. It combines product popularity,
    customer category affinity and Portuguese review-text sentiment to rank recommendations.
    Cold-start users receive global bestsellers. The retained popularity baseline achieves
    HitRate@10 = **{base_hit}** on the same evaluation split.
    """)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model", "NLP + popularity")
    col2.metric("HitRate@10", active_hit)
    col3.metric("Precision@10", active_prec)
    col4.metric("Recall@10", active_rec)

    top_products = load_top_products()
    product_cat = {}
    if not top_products.empty:
        product_cat = dict(zip(top_products["product_id"], top_products["category"]))

    st.subheader("Look up recommendations for a customer")
    sample = load_recommendations_sample()
    default_cust = sample.get("_id", "") if sample else ""
    cust_id = st.text_input("Customer unique ID", value=default_cust)

    if cust_id:
        doc = coll("recommendations").find_one({"_id": cust_id})
        if doc:
            recs = doc.get("recommendations", [])
            if recs:
                df = pd.DataFrame(recs)
                df["category"] = df["product_id"].map(product_cat).fillna("unknown")
                display_cols = ["rank", "product_id", "category"]
                if "score" in df.columns:
                    display_cols.append("score")
                if "sentiment_score" in df.columns:
                    display_cols.append("sentiment_score")
                if "popularity_score" in df.columns:
                    display_cols.append("popularity_score")
                st.dataframe(df[display_cols], width='stretch')
            else:
                st.info("No recommendations available for this customer.")
        else:
            st.warning("Customer not found. Try another customer ID.")

    st.subheader("Most Frequently Recommended Products")
    pipeline = [
        {"$unwind": "$recommendations"},
        {"$group": {"_id": "$recommendations.product_id", "customers": {"$sum": 1}}},
        {"$sort": {"customers": -1}},
        {"$limit": 10},
    ]
    top_rec = pd.DataFrame(list(coll("recommendations").aggregate(pipeline)))
    if not top_rec.empty:
        top_rec["category"] = top_rec["_id"].map(product_cat).fillna("unknown")
        top_rec["label"] = top_rec["_id"].str[:16] + "... (" + top_rec["category"] + ")"
        fig = px.bar(
            top_rec,
            x="label",
            y="customers",
            labels={"label": "Product (category)", "customers": "Customers"},
            color="customers",
            color_continuous_scale="Cividis",
        )
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, config={'displayModeBar': False})
    else:
        st.info("No recommendation data available.")
