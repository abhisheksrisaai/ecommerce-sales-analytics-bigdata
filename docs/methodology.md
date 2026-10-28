# Methodology

## 1. Data cleaning

The raw CSVs are copied to HDFS `/olist/raw/` unchanged. A clean layer
`/olist/clean/` is built by `src/cleaning/csv_normalize.py`:

- Header row is dropped.
- Embedded newlines become spaces.
- Double quotes become single quotes.
- Backslashes become forward slashes.

This fixes Hive `CsvMalformedLineException` errors in the reviews table and
ensures row counts match the source data minus the header.

## 2. MapReduce

Three jobs demonstrate core MapReduce concepts:

- **RevenueByProduct** emits `(product_id, line_revenue)`, aggregates with a
  combiner, shuffles with a custom partitioner, and sums in reducers.
- **OrdersByMonth** filters for delivered orders, parses timestamps and counts
  orders per month.
- **PaymentDistribution** is a Python streaming job with separate mapper,
  combiner and reducer scripts.

## 3. Hive warehouse

Eight external tables point at `/olist/clean/` and one managed Parquet table is
partitioned by `purchase_year_month`. Ten HQL analytics queries answer the
business questions. Hive runs in local mode to avoid a log4j2 bridge conflict
with YARN containers.

## 4. Spark ETL

Spark reads the clean CSVs with explicit schemas, joins six tables into a
112,650-row fact table, and persists it as Parquet. Six Spark SQL analyses
reproduce the Hive numbers exactly after aligning the revenue definition. Spark
also runs an ALS recommender, which is reported as a negative result due to the
sparse interaction matrix (~1.07 purchases per customer).

## 5. Portuguese NLP sentiment

A lexicon-based scorer processes `review_comment_message`:

- Lexicon: 1,260 tokens (720 positive, 540 negative), curated from common
  Portuguese sentiment words.
- Normalisation: lower-case, NFKD accent removal, punctuation → spaces.
- Negation: a two-word window after `nao`, `nem`, `nunca`, `jamais`, `sem`
  flips polarity; explicit negative bigrams such as `nao gostei` are scored
  strongly negative.
- Score range: [-1, 1].

Because reviews are order-level, sentiment is attributed to products using
revenue-share weighting within each order.

## 6. Recommender

### Baseline

For each customer, recommend bestselling products from categories they have
already purchased, falling back to global bestsellers for cold-start users.

### NLP-aware model

Score per product:

```text
popularity_norm = (popularity - min) / (max - min)
sentiment_norm  = (sentiment_score - min) / (max - min)
confidence      = min(1, review_count / max_review_count)
nlp_score       = 0.6 * popularity_norm
                  + 0.4 * (confidence * sentiment_norm
                           + (1 - confidence) * 0.5)
```

Products without reviews default to neutral sentiment (0.5 in the rescaled
[0, 1] space).

## 7. Evaluation

Leave-one-out on customers with two or more delivered items. A single held-out
item per eligible customer is sampled once before any model is trained, and the
same held-out set is used for both the baseline and the NLP recommender so the
two HitRate@10 values are directly comparable.

To prevent leakage, product popularity, category bestseller lists and product
sentiment are recomputed from the training portion of the data only: every
(customer, held-out product) line-item is removed from the interaction table,
and every review belonging to an order that contains a held-out item is removed
from the sentiment calculation. The final deployed recommendation collections
are built from the full dataset after evaluation, so they use all available
signal in production while the benchmark metrics remain leakage-free.

Because both models are still evaluated on the same Olist dataset (rather than
on a later time period), the reported HitRate@10 values are a same-dataset
ranking benchmark, not a true future-prediction estimate.

## 8. Limitations and assumptions

- The sentiment lexicon is hand-curated and does not handle sarcasm or domain
  slang.
- Reviews are order-level, so product sentiment is a proxy, not ground truth.
- The evaluation uses a same-dataset leave-one-out split, not a time-based
  train/test split.
- Hive ran in local mode due to a log4j2/YARN conflict in this environment.
- The dataset is sparse; absolute HitRate@10 values are modest for any model.
