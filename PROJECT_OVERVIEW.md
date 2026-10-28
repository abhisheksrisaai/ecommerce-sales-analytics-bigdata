# Project Overview: Olist E-Commerce Big Data Analytics

This document explains the complete end-to-end flow, from the raw CSV files to
the final dashboard and recommendations, in plain language.

---

## What the project does

We take a real Brazilian e-commerce dataset released by Olist and build a
complete batch Big Data pipeline. The pipeline answers business questions such
as:

- What are the monthly sales trends?
- Which product categories and states generate the most revenue?
- How do customers pay, and how reliable is delivery?
- Which products should we recommend to a customer?

The project also evaluates whether Portuguese customer review text can improve
product recommendations.

---

## The datasets

Nine CSV files (~120 MB, ~1.55 M rows):

- `olist_orders_dataset.csv` – order headers, status, timestamps.
- `olist_order_items_dataset.csv` – line items with price and freight.
- `olist_customers_dataset.csv` – customer IDs, cities and states.
- `olist_products_dataset.csv` – product category and physical attributes.
- `olist_order_payments_dataset.csv` – payment type and value.
- `olist_order_reviews_dataset.csv` – review score and free-text comment.
- `olist_sellers_dataset.csv` – seller location.
- `product_category_name_translation.csv` – Portuguese to English categories.
- `olist_geolocation_dataset.csv` – zip-code lat/long (ingested, not queried).

These live in `data/raw/`.

---

## Stage 1: ingestion and cleaning

`src/utils/ingest_hdfs.sh` copies the CSVs into HDFS at `/olist/raw/`. It then
builds `/olist/clean/` by running every file through `src/cleaning/csv_normalize.py`.

Why clean?
- Hive's OpenCSVSerde ignores `skip.header.line.count`, so headers must be
  removed.
- Review comments contain embedded newlines that break Hive's line-oriented
  reader.
- Some fields contain inconsistent quoting and backslashes.

The clean layer keeps the same values but makes the files safe for Hive and
Spark.

---

## Stage 2: MapReduce aggregation

`src/utils/run_mapreduce.sh` runs three jobs:

1. **RevenueByProduct** (Java) – sums price + freight per product. Uses a
   combiner and a custom partitioner.
2. **OrdersByMonth** (Java) – counts delivered orders per month. Cleans and
   filters inside the mapper.
3. **PaymentDistribution** (Hadoop Streaming / Python) – count, total and
   average value per payment type.

Results are pulled from HDFS into `out/`.

---

## Stage 3: Hive data warehouse

`src/utils/run_hive.sh` creates external tables over `/olist/clean/` and a
managed Parquet table partitioned by purchase month. It then runs ten analytics
queries covering GMV, categories, states, payments, delivery, repeat customers
and reviews.

---

## Stage 4: Spark ETL and validation

`src/utils/run_spark.sh` joins six clean CSVs into a curated Parquet fact table
and runs six Spark SQL analyses that mirror the Hive queries. Hive and Spark
numbers agree exactly once revenue is defined consistently as
`price + freight_value` over delivered orders.

The same script also runs a Spark MLlib ALS recommender as a **reference
negative result**.

---

## Stage 5: Portuguese NLP sentiment

`src/recommender/loader_and_recommender.py` scores Portuguese review text with
a curated lexicon. Because reviews are order-level, sentiment is attributed to
each product in the order weighted by that product's share of the order's line
revenue.

---

## Stage 6: recommendations

The loader builds two recommenders on the same leave-one-out split:

1. **Baseline** – popularity + category affinity.
2. **NLP-aware** – 60% normalised popularity + 40% confidence-adjusted
   sentiment.

Both are evaluated with HitRate@10, Precision@10, Recall@10 and F1@10. The
NLP-aware model is stored as the active `recommendations` collection; the
baseline is stored as `baseline_recommendations`.

---

## Stage 7: serving and dashboard

Everything is loaded into MongoDB:

- Dashboard aggregates: `monthly_gmv`, `state_revenue`, `delivery_performance`,
  `payment_distribution`, `review_distribution`, `top_products`,
  `category_stats`, `repeat_customers`.
- Recommendation data: `recommendations`, `baseline_recommendations`,
  `product_sentiment`.

`src/dashboard/app.py` reads these collections and renders six interactive
pages with Streamlit and Plotly.

---

## Output files

- `out/recommender_metrics.txt` – both models' metrics.
- `out/recommendations.csv` – active NLP recommendations.
- `out/report/DA3_RegNo_Ecommerce-Sales-Recommendation.{pdf,docx,pptx}` – final
  deliverables.
- `out/report/dashboard/*.png` – dashboard screenshots.
