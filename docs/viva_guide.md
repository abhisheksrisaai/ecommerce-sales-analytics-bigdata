# Viva Guide

This guide walks a faculty examiner through the codebase. For each major file
it states what it does, why it is needed, how it runs, key functions, where
they are called from, likely viva questions and honest caveats.

---

## Entry point

**File:** `run_project.sh`

- **What it does:** Runs all pipeline stages in dependency order:
  setup → HDFS ingestion → MapReduce → Hive → Spark → MongoDB.
- **Why it is needed:** Provides a single command that reproduces the whole
  project and creates the `logs/` evidence trail.
- **How it runs:** `bash run_project.sh` from the project root.
- **Key point:** Sources `config/settings.sh` for Java/Hadoop/Hive/Spark paths.

---

## Configuration

**Files:** `config/paths.py`, `config/settings.py`, `config/settings.sh`

- **What they do:** Centralise all paths and tunable settings.
- **Why they are needed:** No other file should hard-code a user-specific path.
- **Key values:**
  - `RAW_DIR` → `data/raw/`
  - `OUT_DIR` → `out/`
  - `REPORT_DIR` → `out/report/`
  - `MONGO_URI` → `mongodb://localhost:27017`
  - `POPULARITY_WEIGHT` = 0.6, `SENTIMENT_WEIGHT` = 0.4
- **Caveat:** `settings.sh` assumes Homebrew paths on macOS; edit if your
  installation differs.

---

## Data cleaning

**File:** `src/cleaning/csv_normalize.py`

- **What it does:** Reads a raw CSV, drops the header and re-serialises each
  record onto one line with dangerous characters replaced.
- **Why it is needed:** Hive's OpenCSVSerde cannot handle embedded newlines or
  inconsistent quoting in the reviews file.
- **Key functions:**
  - `sanitize(field)` – replaces newlines, quotes and backslashes.
  - `main()` – CLI driver called by `ingest_hdfs.sh`.
- **Called from:** `src/utils/ingest_hdfs.sh`.
- **Likely question:** Why not just use the raw files in Hive?
- **Answer:** Embedded newlines cause `CsvMalformedLineException` and the
  header is read as data because OpenCSVSerde ignores `skip.header.line.count`.

---

## Ingestion

**File:** `src/utils/ingest_hdfs.sh`

- **What it does:** Copies raw CSVs to `/olist/raw/`, builds `/olist/clean/`
  using `csv_normalize.py`, and reports sizes.
- **Why it is needed:** Creates the immutable bronze layer and the Hive-safe
  clean layer.
- **Key sections:** raw upload loop, clean normalisation loop, fsck quota check.
- **Called from:** `run_project.sh`.
- **Caveat:** Uses `cd "$RAW_DIR"` so Hadoop receives relative paths and avoids
  spaces in the absolute path.

---

## MapReduce

**Files:** `src/mapreduce/java/RevenueByProduct.java`,
`src/mapreduce/java/OrdersByMonth.java`,
`src/mapreduce/streaming/*.py`

- **What they do:** Compute revenue by product, orders by month and payment
  distribution.
- **Why they are needed:** Demonstrate scalable batch aggregation and the
  MapReduce programming model.
- **Key Java classes:**
  - `RevenueMapper`, `RevenueCombiner`, `ProductPartitioner`, `RevenueReducer`.
  - `OrdersByMonthMapper`, `SumCombiner`, `SumReducer`.
- **Key Python scripts:** `payment_mapper.py`, `payment_combiner.py`,
  `payment_reducer.py`.
- **Called from:** `src/utils/run_mapreduce.sh`.
- **Likely question:** What does the combiner do?
- **Answer:** It pre-aggregates map outputs locally before the shuffle, cutting
  network traffic (Job 1 reduces ~113 k map outputs to ~33 k before shuffle).

---

## Hive

**Files:** `src/hive/warehouse.hql`, `src/hive/analytics.hql`,
`src/hive/hive_exec.py`

- **What they do:** Define external/partitioned tables and run ten analytics
  queries.
- **Why they are needed:** Provide SQL analytics over the cleaned data and
  demonstrate Hive warehousing.
- **Key function in `hive_exec.py`:**
  - `split_statements(text)` – parses HQL into individual statements while
    respecting quotes and comments.
  - `run(statement, database)` – executes one statement through Beeline.
- **Called from:** `src/utils/run_hive.sh`.
- **Caveat:** Beeline's `-f` mode corrupts statements in this environment, so
  we use `-e` one statement at a time.

---

## Spark

**Files:** `src/spark/etl_analytics.py`, `src/spark/als_recommender.py`

- **What they do:** Build a curated Parquet fact table and run Spark SQL
  analyses; the ALS file is a reference negative result.
- **Why they are needed:** Cross-validate Hive numbers and demonstrate Spark
  ETL/SQL.
- **Key sections in `etl_analytics.py`:** schema declarations, cleaning,
  joins, Parquet write, six analytics queries.
- **Called from:** `src/utils/run_spark.sh`.
- **Likely question:** Why does ALS fail?
- **Answer:** Only ~1.07 purchases per customer; the matrix is too sparse for
  latent-factor models to beat a simple baseline.

---

## Sentiment

**File:** `src/sentiment/portuguese_sentiment.py`

- **What it does:** Scores Portuguese review text with a lexicon.
- **Why it is needed:** Provide a ranking signal for the NLP-aware recommender
  without depending on pretrained models or downloads.
- **Key functions:**
  - `normalise(text)` – lower-case, remove accents, clean punctuation.
  - `score_text(text)` – return sentiment in [-1, 1].
  - `review_stats(df)` – add sentiment columns to a reviews DataFrame.
- **Called from:** `src/recommender/loader_and_recommender.py`.
- **Caveat:** Lexicon-based; cannot handle sarcasm, slang or domain-specific
  negation beyond the coded window.

---

## Recommender and serving layer

**File:** `src/recommender/loader_and_recommender.py`

- **What it does:** Loads dashboard aggregates, computes product sentiment,
  trains/evaluates baseline and NLP recommenders, writes results to MongoDB
  and local files.
- **Why it is needed:** It is the DA-3 core: the active recommender and all
  dashboard aggregates come from this script.
- **Key functions:**
  - `load_aggregates(db)` – reads CSVs, computes aggregates, loads MongoDB.
  - `compute_product_sentiment(reviews, items, products)` – revenue-share
    sentiment attribution.
  - `build_recommenders(...)` – builds baseline and NLP models using a single
    precomputed held-out set, evaluates both on training-data-only features,
    then stores final recommendations from the full dataset.
- **Called from:** `src/utils/load_mongodb.sh` and directly via
  `python3 -m src.recommender.loader_and_recommender`.
- **Likely question:** How is review-to-product attribution handled?
- **Answer:** Order-level review sentiment is multiplied by each product's
  revenue-share within the order, then aggregated per product.
- **Likely question:** What is the confidence formula?
- **Answer:** `c = min(1, n / n_max)` where `n` is the number of reviews for
  the product and `n_max` is the maximum review count across all products.

---

## Dashboard

**File:** `src/dashboard/app.py`

- **What it does:** Streamlit application with six pages over MongoDB.
- **Why it is needed:** Interactive demonstration of the serving layer.
- **Key functions:**
  - `get_db()` – cached MongoDB connection.
  - `load_*()` – cached collection loaders.
  - `load_metrics()` – reads `out/recommender_metrics.txt`.
- **Called from:** `streamlit run src/dashboard/app.py`.
- **Caveat:** The metrics parser must handle the `[baseline_...]` section in
  the metrics file; otherwise the dashboard would show baseline metrics as the
  active model.

---

## Tests

**File:** `tests/test_da3.py`

- **What it does:** Unit tests for sentiment, metrics paths, MongoDB schemas
  and recommender ranking properties.
- **Why it is needed:** Verifies that code changes do not break documented
  behaviour.
- **Run:** `python3 tests/test_da3.py`.
- **Caveat:** MongoDB schema tests require `mongod` to be running.

---

## Report generators

**Files:** `src/utils/gen_report.py`, `src/utils/gen_slides.py`,
`src/utils/gen_figures.py`, `src/utils/capture_dashboard.py`

- **What they do:** Produce the final PDF/DOCX report, PPTX slides,
  architecture/timeline figures and dashboard screenshots.
- **Why they are needed:** Generate all submission deliverables from the same
  code and data.
- **Called from:** Manual commands listed in `README.md`.

---

## Likely viva questions and answers

**Q: Why MongoDB and not a relational database?**
A: Recommendations are variable-length lists per customer. A document store
models this naturally; a relational schema would need a child table or
 denormalised strings.

**Q: Why does Hive disagree with Spark initially?**
A: Hive was summing `price` only while Spark summed `price + freight_value`.
After unifying the definition the numbers match exactly.

**Q: What is the active recommender?**
A: `nlp_sentiment_popularity` in `src/recommender/loader_and_recommender.py`.

**Q: How much did NLP improve recommendations?**
A: On the corrected same-dataset leave-one-out benchmark, HitRate@10 is 0.0621
for the popularity/category baseline and 0.0654 for the NLP model, an absolute
gain of 0.33 percentage points (5.3% relative). The earlier higher numbers
(0.0966 vs 0.1065) came from an evaluation that used a different random
held-out item for each model and leaked full-dataset popularity and sentiment
into the training phase; both issues have been fixed.

**Q: What are the main limitations?**
A: Lexicon-based sentiment, order-level review proxy, same-dataset evaluation
split, sparse data, Hive local-mode constraint.
