#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-3 artefact: Streamlit dashboard over the MongoDB serving layer.

Reads from the olist_analytics database populated by:
  - code/mongo/01_load_and_query.py (recommendations, category_stats)
  - code/scripts/da3_loader_and_recommender.py (all other collections)

Run:
    streamlit run code/dashboard/app.py
"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "olist_analytics"

st.set_page_config(
    page_title="Olist E-Commerce Analytics",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[DB_NAME]


def coll(name):
    return get_db()[name]


def find_all(name, limit=None):
    cur = coll(name).find({}, {"_id": 0})
    if limit:
        cur = cur.limit(limit)
    return list(cur)


st.title("📊 Olist E-Commerce Analytics & Recommendations")
st.markdown("""
Dashboard for the **E-Commerce Sales Analytics and Product Recommendation** project.
Data lives in MongoDB and was produced by the Hadoop, Hive, Spark and MapReduce pipeline.
""")

# --------------------------------------------------------------------- sidebar
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["🏠 Overview", "📈 Sales Trends", "🏷️ Categories & Products",
     "🗺️ Geography", "🚚 Delivery", "🎯 Recommendations"]
)

# --------------------------------------------------------------------- overview
if page == "🏠 Overview":
    st.header("Executive Summary")

    monthly = pd.DataFrame(find_all("monthly_gmv"))
    cat = pd.DataFrame(find_all("category_stats"))
    repeat = coll("repeat_customers").find_one({}, {"_id": 0})
    pay = pd.DataFrame(find_all("payment_distribution"))

    total_gmv = monthly["gmv"].sum() if not monthly.empty else 0
    total_orders = int(monthly["orders"].sum()) if not monthly.empty else 0
    top_category = cat.iloc[0]["_id"] if not cat.empty else "N/A"
    top_cat_revenue = cat.iloc[0]["revenue"] if not cat.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", f"{total_orders:,}")
    col2.metric("Total GMV", f"R${total_gmv:,.2f}")
    col3.metric("Top Category", top_category,
                f"R${top_cat_revenue:,.2f}")
    col4.metric("Repeat Customer Rate", f"{repeat['repeat_rate_pct']}%",
                f"{repeat['repeat_customers']:,} of {repeat['total_customers']:,}")

    st.subheader("Revenue by Category (Top 10)")
    fig = px.bar(
        cat.head(10).sort_values("revenue"),
        x="revenue",
        y="_id",
        orientation="h",
        labels={"_id": "Category", "revenue": "Revenue (R$)"},
        color="revenue",
        color_continuous_scale="Blues",
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Payment Method Distribution")
    fig2 = px.pie(
        pay,
        names="payment_type",
        values="transactions",
        hole=0.35,
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------- sales trends
elif page == "📈 Sales Trends":
    st.header("Sales Trends")
    monthly = pd.DataFrame(find_all("monthly_gmv"))
    monthly = monthly.sort_values("purchase_month")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Monthly GMV")
        fig = px.line(
            monthly,
            x="purchase_month",
            y="gmv",
            markers=True,
            labels={"purchase_month": "Month", "gmv": "GMV (R$)"},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Monthly Order Volume")
        fig = px.bar(
            monthly,
            x="purchase_month",
            y="orders",
            labels={"purchase_month": "Month", "orders": "Orders"},
            color="orders",
            color_continuous_scale="Greens",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Data")
    st.dataframe(monthly, use_container_width=True)

# --------------------------------------------------------------------- categories & products
elif page == "🏷️ Categories & Products":
    st.header("Categories & Products")

    cat = pd.DataFrame(find_all("category_stats")).sort_values("revenue", ascending=False)
    top_products = pd.DataFrame(find_all("top_products")).sort_values("revenue", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 Categories by Revenue")
        fig = px.bar(
            cat.head(10),
            x="_id",
            y="revenue",
            labels={"_id": "Category", "revenue": "Revenue (R$)"},
            color="revenue",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Review Score vs. Revenue")
        fig = px.scatter(
            cat,
            x="avg_review",
            y="revenue",
            size="items_sold",
            hover_name="_id",
            labels={"avg_review": "Average Review", "revenue": "Revenue (R$)"},
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Products by Revenue")
    st.dataframe(top_products.head(10), use_container_width=True)

# --------------------------------------------------------------------- geography
elif page == "🗺️ Geography":
    st.header("Geographic Distribution")

    state = pd.DataFrame(find_all("state_revenue")).sort_values("revenue", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by State (Top 15)")
        fig = px.bar(
            state.head(15),
            x="_id",
            y="revenue",
            labels={"_id": "State", "revenue": "Revenue (R$)"},
            color="revenue",
            color_continuous_scale="Purples",
        )
        fig.update_layout(height=450, xaxis_tickangle=0)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Orders by State")
        fig = px.bar(
            state.head(15),
            x="_id",
            y="orders",
            labels={"_id": "State", "orders": "Orders"},
            color="orders",
            color_continuous_scale="Oranges",
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("State Revenue Table")
    st.dataframe(state, use_container_width=True)

# --------------------------------------------------------------------- delivery
elif page == "🚚 Delivery":
    st.header("Delivery Performance")

    deliv = pd.DataFrame(find_all("delivery_performance")).sort_values("late_pct", ascending=False)
    rev = pd.DataFrame(find_all("review_distribution")).sort_values("review_score")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Average Delivery Days by State")
        fig = px.bar(
            deliv.sort_values("avg_delivery_days", ascending=True),
            x="_id",
            y="avg_delivery_days",
            labels={"_id": "State", "avg_delivery_days": "Avg Delivery Days"},
            color="avg_delivery_days",
            color_continuous_scale="RdYlGn_r",
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Late Delivery % by State")
        fig = px.bar(
            deliv,
            x="_id",
            y="late_pct",
            labels={"_id": "State", "late_pct": "Late %"},
            color="late_pct",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Review Score Distribution")
    fig2 = px.bar(
        rev,
        x="review_score",
        y="reviews",
        labels={"review_score": "Review Score", "reviews": "Reviews"},
        color="reviews",
        color_continuous_scale="Teal",
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.info(
        "Key insight: on-time deliveries average **4.21★** while late deliveries "
        "average **2.55★** — logistics performance is the strongest driver of customer satisfaction."
    )

# --------------------------------------------------------------------- recommendations
elif page == "🎯 Recommendations":
    st.header("Product Recommendations")

    metrics_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "out", "recommender_metrics.txt")
    metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path) as fh:
            for ln in fh:
                if "=" in ln:
                    k, v = ln.strip().split("=", 1)
                    metrics[k] = v

    st.markdown("""
    The recommendation model is a **popularity + category-affinity baseline**.
    It recommends top-selling products from categories the customer has already purchased,
    falling back to global bestsellers for cold-start users.
    """)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model", metrics.get("model", "N/A"))
    col2.metric("HitRate@10", metrics.get("hit_rate@10", "N/A"))
    col3.metric("Precision@10", metrics.get("precision@10", "N/A"))
    col4.metric("Recall@10", metrics.get("recall@10", "N/A"))

    st.subheader("Look up recommendations for a customer")
    sample = coll("recommendations").find_one()
    default_cust = sample["_id"] if sample else ""
    cust_id = st.text_input("Customer unique ID", value=default_cust)

    if cust_id:
        doc = coll("recommendations").find_one({"_id": cust_id})
        if doc:
            recs = doc.get("recommendations", [])
            df = pd.DataFrame(recs)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Customer not found. Try copying an ID from recommendations.csv.")

    st.subheader("Most Frequently Recommended Products")
    pipeline = [
        {"$unwind": "$recommendations"},
        {"$group": {"_id": "$recommendations.product_id",
                    "customers": {"$sum": 1}}},
        {"$sort": {"customers": -1}},
        {"$limit": 10},
    ]
    top_rec = pd.DataFrame(list(coll("recommendations").aggregate(pipeline)))
    if not top_rec.empty:
        fig = px.bar(
            top_rec,
            x="_id",
            y="customers",
            labels={"_id": "Product ID", "customers": "Customers"},
            color="customers",
            color_continuous_scale="Cividis",
        )
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
