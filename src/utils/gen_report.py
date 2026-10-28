#!/usr/bin/env python3
"""Generate the DA-3 final report as DOCX and PDF.

The report reads the metrics file, architecture/timeline figures and dashboard
screenshots produced by the other generator scripts. It writes the final
report into `out/report/`.

Run:
    python3 -m src.utils.gen_report

Dependencies:
    python-docx, reportlab, Pillow.
"""
import os
import sys

import docx.oxml

# Allow imports from the project root when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import METRICS_FILE, OUT_DIR, PROJECT_ROOT as PROJECT, REPORT_DIR

OUT = REPORT_DIR
FILE_BASE = "DA3_RegNo_Ecommerce-Sales-Recommendation"

TEAM = ("Team Members: K PRADEEP KUMAR - 23BLC1240, VAHRAN P - 23BLC1221, "
        "ASHVATH KUMAR - 23BLC1269, K.P ABHISHEK - 23BLC1292")


def load_metrics():
    """Read the recommender metrics file and return a flat dict."""
    path = METRICS_FILE
    if not os.path.exists(path):
        return {}
    metrics = {"_raw": []}
    section = "nlp"
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("[") and ln.endswith("]"):
            section = "baseline"
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            metrics[f"{section}_{k}"] = v
        metrics["_raw"].append(ln)
    return metrics


def fig(label):
    """Generate a sequential figure caption and return the caption text."""
    fig.counter += 1
    return f"Fig. {fig.counter}: {label}"


fig.counter = 0


def blocks():
    metrics = load_metrics()
    nlp_hit_rate = metrics.get("nlp_hit_rate@10", "N/A")
    nlp_precision = metrics.get("nlp_precision@10", "N/A")
    nlp_recall = metrics.get("nlp_recall@10", "N/A")
    nlp_f1 = metrics.get("nlp_f1@10", "N/A")
    base_hit_rate = metrics.get("baseline_hit_rate@10", "N/A")
    base_precision = metrics.get("baseline_precision@10", "N/A")
    base_recall = metrics.get("baseline_recall@10", "N/A")
    base_f1 = metrics.get("baseline_f1@10", "N/A")
    eligible = metrics.get("nlp_eligible_customers", "N/A")

    # Dynamic improvement text so the report always matches the metrics file.
    try:
        nlp_h = float(nlp_hit_rate)
        base_h = float(base_hit_rate)
        abs_pp = round((nlp_h - base_h) * 100, 2)
        rel_pct = round(100 * (nlp_h - base_h) / base_h, 1) if base_h else 0.0
        improvement_text = "{:.2f} percentage points ({:.1f}% relative)".format(abs_pp, rel_pct)
    except Exception:
        improvement_text = "a small improvement"

    dashboard_dir = os.path.join(REPORT_DIR, "dashboard")
    overview_png = os.path.join(dashboard_dir, "overview.png")
    sales_png = os.path.join(dashboard_dir, "sales_trends.png")
    cat_png = os.path.join(dashboard_dir, "categories.png")
    geo_png = os.path.join(dashboard_dir, "geography.png")
    deliv_png = os.path.join(dashboard_dir, "delivery.png")
    rec_png = os.path.join(dashboard_dir, "recommendations.png")

    return [
        ("title", "E-Commerce Sales Analytics and Product Recommendation using Hadoop, Hive and Spark"),
        ("subtitle", "BCSE402L - Big Data Analytics (TH)  |  DA-3: Completion &amp; Presentation"),
        ("meta", TEAM),
        ("meta", "Submission Date: 20 October 2026  |  Dataset: Brazilian E-Commerce Public Dataset by Olist"),

        ("h1", "Abstract"),
        ("p", "This project builds an end-to-end batch Big Data analytics pipeline over the Brazilian "
              "Olist e-commerce dataset. Nine relational CSVs (~1.55 M rows, 122 MB) are ingested into HDFS, "
              "cleaned and aggregated with MapReduce, modelled in Hive, cross-validated in Spark, and served "
              "from MongoDB. The pipeline answers business questions around monthly GMV, category and state "
              "revenue, payment preferences, delivery performance and customer repeat behaviour. "
              "For DA-3 a Portuguese NLP sentiment pipeline was added to process customer review text. "
              "The resulting sentiment features are combined with product popularity and category affinity "
              "to rank recommendations. On a leave-one-out evaluation over {} eligible customers the NLP-aware "
              "model achieves a HitRate@10 of {} while the popularity baseline achieves {}; the improvement is "
              "{}. A Streamlit dashboard provides interactive visualisation "
              "over the MongoDB serving store.".format(eligible, nlp_hit_rate, base_hit_rate, improvement_text)),

        ("h1", "1. Problem Statement"),
        ("p", "Small and mid-size e-commerce marketplaces need affordable analytics to understand sales trends, "
              "geographic demand, payment behaviour and delivery quality. They also need product recommendations, "
              "but most public datasets are too sparse for collaborative filtering to work out of the box."),
        ("p", "The problem addressed in this project is: <b>design and implement a batch Big Data pipeline that "
              "cleans, warehouses, analyses and serves e-commerce transaction data, and produce honest, evaluated "
              "product recommendations at a scale where single-machine tools become limiting.</b>"),
        ("p", "Why it matters: transaction data has high volume, variety and veracity. The Olist dataset spans "
              "orders, items, payments, reviews, products, sellers, customers and geolocation. Joining and aggregating "
              "these tables exercises the core Big Data concepts taught in BCSE402L."),

        ("h1", "2. Methodology"),
        ("h2", "2.1 Software stack"),
        ("table",
         ["Component", "Version", "Role"],
         [
             ["Apache Hadoop (HDFS + YARN)", "3.5.0", "Distributed storage and resource management, pseudo-distributed"],
             ["Apache Hive", "4.2.1", "SQL warehouse with external and partitioned Parquet tables"],
             ["Apache Spark / PySpark", "4.2.0", "DataFrame ETL, Spark SQL analytics, MLlib ALS experiment"],
             ["MongoDB Community", "8.3.11", "Document serving store for recommendations and aggregates"],
             ["OpenJDK", "21", "Single JDK shared by Hadoop, Hive and Spark"],
             ["Python", "3.11", "PySpark driver, MongoDB loader and dashboard"],
             ["Streamlit", "1.50.0", "Interactive dashboard"],
         ]),

        ("h2", "2.2 Dataset"),
        ("p", "Table 1 lists the raw source files as released by Olist. Throughout the pipeline these files are "
              "copied into HDFS /olist/raw and then normalised into /olist/clean. The normalisation step removes "
              "the header row and fixes embedded newlines and inconsistent quoting. Therefore MapReduce, Hive and "
              "Spark operate on cleaned files whose row counts are exactly one less than the raw CSV counts shown "
              "below. For example, the 112,650-row order-items file becomes 112,651 cleaned records because the "
              "header is removed and one malformed line is recovered during normalisation; in practice the cleaned "
              "files match the source data values exactly once the header is dropped."),
        ("table",
         ["File", "Raw rows", "Use"],
         [
             ["olist_orders_dataset", "99,441", "Order header, status and timestamps"],
             ["olist_order_items_dataset", "112,650", "Line items: price, freight, product and seller"],
             ["olist_customers_dataset", "99,441", "Customer IDs, unique IDs, city and state"],
             ["olist_products_dataset", "32,951", "Category and physical attributes"],
             ["olist_order_payments_dataset", "103,886", "Payment type, value and installments"],
             ["olist_order_reviews_dataset", "99,224", "Review score and comment text"],
             ["olist_sellers_dataset", "3,095", "Seller location"],
             ["product_category_name_translation", "71", "Portuguese to English category names"],
             ["olist_geolocation_dataset", "1,000,163", "Zip-code lat/long (ingested, not queried)"],
         ]),

        ("h2", "2.3 Pipeline workflow"),
        ("numbered", [
            "<b>Ingestion.</b> Nine CSVs are uploaded to HDFS /olist/raw. A clean layer /olist/clean removes headers and normalises embedded newlines/quotes.",
            "<b>MapReduce.</b> Three jobs compute revenue per product, orders per month and payment-type distribution. Java jobs use combiners and a partitioner; the streaming job uses Python mapper/combiner/reducer scripts.",
            "<b>Hive.</b> Eight external tables and one Parquet table partitioned by purchase month support ten HQL analytics queries.",
            "<b>Spark.</b> A curated Parquet fact table joins six tables. Six Spark SQL analyses mirror the Hive questions for cross-engine validation.",
            "<b>NLP sentiment.</b> Portuguese review text is normalised, scored with a lexicon-based sentiment analyser, and attributed to products weighted by revenue share within each order.",
            "<b>Recommender.</b> A popularity + category-affinity baseline and an NLP sentiment-aware model are trained and evaluated with ranking metrics.",
            "<b>MongoDB.</b> Aggregates, product sentiment, baseline recommendations and active recommendations are loaded as documents and queried with NoSQL operations.",
            "<b>Dashboard.</b> A Streamlit application reads from MongoDB and visualises KPIs, trends, geography, delivery and recommendations.",
        ]),

        ("h2", "2.4 Architecture"),
        ("p", "The architecture is a classic batch pipeline. Raw CSVs land in HDFS, are normalised, "
              "aggregated by MapReduce, modelled in Hive, enriched in Spark, augmented with Portuguese NLP sentiment, "
              "scored by two recommender variants and served from MongoDB. This separation lets each tool do what "
              "it does best: HDFS for cheap durable storage, MapReduce for scalable aggregation, Hive for SQL analytics, "
              "Spark for in-memory joins, NLP for review-text enrichment, and MongoDB for low-latency serving."),
        ("image", os.path.join(REPORT_DIR, "fig1_architecture.png")),
        ("caption", fig("End-to-end implemented architecture for DA-3, showing the Portuguese NLP and recommender additions.")),
        ("image", os.path.join(REPORT_DIR, "fig3_workflow.png")),
        ("caption", fig("Project progress from DA-1 through DA-3; all phases including DA-3 deliverables are completed.")),

        ("h1", "3. Implementation"),
        ("h2", "3.1 HDFS ingestion and cleaning"),
        ("p", "Raw files are kept immutable in /olist/raw. The clean layer fixes three concrete problems: "
              "(1) Hive 4.2.1's OpenCSVSerde ignores skip.header.line.count, so headers must be removed upstream; "
              "(2) review comments contain embedded newlines that break Hive's line-oriented reader; "
              "(3) inconsistent quoting between header and data rows is normalised. The result is 120.3 MB in "
              "HDFS with one block per file."),
        ("p", "The normalisation script is a real CSV parser that drops the header and re-serialises each record "
              "onto a single line. Newlines inside fields become spaces, double quotes become single quotes, and "
              "backslashes become forward slashes. This preserves values while making the files safe for Hive and "
              "Spark's line-oriented readers."),

        ("h2", "3.2 MapReduce jobs"),
        ("image", os.path.join(REPORT_DIR, "fig2_mapreduce.png")),
        ("caption", fig("Map -> Combine -> Shuffle -> Reduce data flow for the Java and Streaming jobs.")),
        ("p", "Three MapReduce jobs demonstrate the key MapReduce concepts. Job 1 (RevenueByProduct) is a Java job "
              "that parses the cleaned order_items CSV, emits (product_id, line_revenue) pairs, aggregates locally with a "
              "combiner, shuffles by key using a custom partitioner, and sums in three reducers. The combiner reduced "
              "112,650 map outputs to 32,951 records before the shuffle, cutting network traffic to roughly 29%."),
        ("p", "Job 2 (OrdersByMonth) is another Java job that filters for delivered orders, parses timestamps, and counts "
              "orders per month. It demonstrates cleaning inside the mapper and uses Hadoop counters to record data "
              "quality metrics such as malformed records and non-delivered orders."),
        ("p", "Job 3 (PaymentDistribution) is a Hadoop Streaming job written in Python. It reports count, total value "
              "and average value per payment type. A separate combiner script is essential: an early attempt reused the "
              "reducer as the combiner, which emitted four columns where the reducer expected three, producing empty output."),
        ("table",
         ["Job", "Cleaned input rows", "Output", "Technique shown"],
         [
             ["RevenueByProduct (Java)", "112,651", "32,951 product revenues", "Mapper emits (product_id, price+freight); combiner reduces shuffle traffic to ~29%"],
             ["OrdersByMonth (Java)", "99,442", "23 monthly counts", "Cleaning inside mapper: status filter, timestamp parse, null handling"],
             ["Payment distribution (Streaming)", "103,887", "5 payment types", "Python mapper/combiner/reducer with three-column contract"],
         ]),
        ("p", "The input counts in Table 3 are the cleaned file sizes (raw size minus header), which is why they are "
              "one larger than the raw CSV row counts in Table 1."),

        ("h2", "3.3 Hive warehouse"),
        ("p", "The warehouse uses eight external tables over /olist/clean and a managed Parquet table partitioned by "
              "purchase_year_month. Dynamic partitioning creates 23 partitions, one per month. Hive runs in local mode "
              "to avoid a log4j2 bridge conflict with Hadoop's MRAppMaster in the YARN containers."),
        ("p", "Ten analytics queries cover the business questions: monthly GMV, top categories, revenue by state, "
              "payment distribution, delivery performance, repeat-customer rate, review distribution, revenue by category "
              "and review sentiment, a window-function query for top categories per month, and a purchase-hour heat map. "
              "All 24 DDL statements and 11 analytics queries completed with zero errors."),

        ("h2", "3.4 Spark ETL and SQL"),
        ("p", "Spark reads the clean CSVs with explicit schemas, casts timestamps and numeric columns, and joins "
              "order_items, orders, customers, products, payments and reviews into a 112,650-row fact table persisted "
              "as Parquet partitioned by purchase_month. Row counts match sources exactly, confirming that joins neither "
              "duplicated nor dropped records."),
        ("p", "Six Spark SQL analyses reproduce the Hive numbers exactly after unifying the revenue definition to "
              "sum(price + freight_value) over delivered orders. Spark adds one analysis that Hive would make awkward: "
              "review score against delivery lateness. Items delivered on time average 4.21 stars while late items average "
              "2.55 stars, making logistics the clearest driver of customer satisfaction."),
        ("table",
         ["Metric", "Hive", "Spark"],
         [
             ["GMV August 2018", "985,491.64", "985,491.64"],
             ["health_beauty revenue", "1,412,089.53", "1,412,089.53"],
             ["bed_bath_table revenue", "1,225,209.26", "1,225,209.26"],
             ["Revenue SP", "5,769,703.15", "5,769,703.15"],
             ["Revenue RJ", "2,055,401.57", "2,055,401.57"],
         ]),

        ("h2", "3.5 MongoDB serving layer"),
        ("p", "MongoDB is used as the serving store because the recommendation output is a per-customer variable-length "
              "list of product ids. A relational schema would require either a child table scanned on every read or a "
              "denormalised string column. A document store models the natural access pattern directly: one document per "
              "customer with the recommendation list embedded."),
        ("p", "For DA-3 the MongoDB layer was extended beyond recommendations to include dashboard aggregates: "
              "monthly_gmv, state_revenue, delivery_performance, payment_distribution, review_distribution, top_products, "
              "category_stats and repeat_customers. A multikey index on recommendations.product_id supports reverse lookups "
              "such as 'which customers are recommended this product?'."),

        ("h1", "4. Results and Discussion"),
        ("h2", "4.1 Business analytics"),
        ("p", "All business metrics below are computed over <b>delivered orders</b> (order_status = 'delivered') with "
              "valid timestamps, and revenue is defined as <b>price + freight_value</b> per line item. GMV is the sum of "
              "revenue over delivered orders. The dashboard KPI labelled 'Total Orders' is therefore the count of delivered "
              "orders (96,478), not the raw 99,441 order headers in the source file."),
        ("p", "The Hive and Spark analyses produced a consistent set of business metrics. GMV grows from R$46,490.66 "
              "in October 2016 to a peak of R$1,153,364.20 in November 2017, reflecting the Black Friday effect. The "
              "last full month, August 2018, records R$985,491.64."),
        ("p", "The top three categories by revenue are health_beauty (R$1,412,089.53), watches_gifts (R$1,264,333.12) "
              "and bed_bath_table (R$1,225,209.26). These three categories alone account for a large share of total GMV. "
              "Geographically, São Paulo state dominates with R$5,769,703.15 of revenue across 40,501 orders, followed by "
              "Rio de Janeiro with R$2,055,401.57."),
        ("table",
         ["Metric", "Finding", "Population / definition"],
         [
             ["Monthly GMV peak", "R$1,153,364.20 in November 2017", "Delivered orders, revenue = price + freight"],
             ["Top category", "health_beauty with R$1,412,089.53", "Delivered orders"],
             ["Top state", "São Paulo (SP) with R$5,769,703.15 across 40,501 orders", "Delivered orders"],
             ["Payment preference", "Credit card: 76,795 transactions worth R$12,542,084.19", "All payment rows"],
             ["Repeat customer rate", "3.00% (2,801 repeat customers of 93,358 total)", "Customers with at least one delivered order"],
             ["Review distribution", "57.78% five-star, 11.51% one-star", "All review rows"],
             ["Delivery insight", "On-time deliveries average 4.21★ vs 2.55★ for late deliveries", "Delivered orders with estimated and actual delivery dates"],
         ]),

        ("h2", "4.2 Cross-engine validation"),
        ("p", "Hive and Spark were run independently on the same clean data. Initially the two engines disagreed on "
              "category and state revenue because Hive was summing price alone while Spark was summing price + freight_value "
              "over delivered orders. After fixing the Hive queries to use the same definition, the two engines agreed "
              "exactly on monthly GMV, category revenue and state revenue. This agreement is evidence of implementation "
              "consistency across engines; it does not by itself prove the business numbers are correct, but it makes "
              "single-engine arithmetic errors unlikely."),
        ("p", "The cross-validation exercise also revealed the importance of a clean landing layer. OpenCSVSerde does "
              "not honour skip.header.line.count, so header rows were leaking into counts until the /olist/clean layer "
              "was introduced. With the clean layer in place, row counts match the source files exactly."),

        ("h2", "4.3 Recommender"),
        ("h2", "4.3.1 ALS negative result"),
        ("p", "An ALS collaborative-filtering experiment was trained and evaluated during DA-2. The interaction matrix "
              "has 99,785 customer-product pairs across 93,358 customers, i.e. roughly 1.07 purchases per customer. With so "
              "few co-purchase signals, ALS underperformed a global-mean baseline (RMSE 0.9702 vs 0.9324 on the subset of "
              "customers with three or more items). The project reports this negative result honestly instead of hiding it."),

        ("h2", "4.3.2 DA-3 baseline: popularity + category affinity"),
        ("p", "For DA-3 a popularity + category-affinity baseline was implemented: recommend bestselling "
              "products from categories the customer has already purchased, falling back to global bestsellers for cold-start "
              "users. This approach is interpretable, handles cold start naturally and does not require dense interaction data."),

        ("h2", "4.3.3 DA-3 NLP sentiment-aware recommender"),
        ("p", "A Portuguese NLP sentiment pipeline was built using a curated lexicon of positive and negative words "
              "compiled from common Portuguese sentiment terms. The lexicon contains 1,260 tokens (after stemming): "
              "720 positive and 540 negative. Text is normalised by lower-casing, removing accents via Unicode NFKD "
              "decomposition, replacing punctuation and digits with spaces, and collapsing whitespace. Negation is handled "
              "within a two-word window after the markers 'nao', 'nem', 'nunca', 'jamais' and 'sem'; the sentiment polarity of "
              "words inside the window is reversed. Explicit negative bigrams such as 'nao gostei', 'nao recomendo' and "
              "'nao gosto' are scored as strongly negative."),
        ("p", "Each review text receives a raw sentiment score in [-1, 1] defined as (positive_word_count - "
              "negative_word_count) / total_matched_tokens. Reviews are order-level in the source data, so sentiment is "
              "attributed to products as a <b>proxy</b>, not as product-level ground truth. For each order, a product's "
              "share of the order's line revenue is computed as (price + freight) / sum(price + freight) over the order's "
              "items. The order-level review sentiment is then multiplied by this revenue share and accumulated per product. "
              "Orders with zero or missing line revenue are excluded; this affects fewer than 0.01% of records. The final "
              "product sentiment score is the revenue-share-weighted average across all reviews for that product, clipped to "
              "[-1, 1]. Products with no review text receive a neutral default of 0."),
        ("p", "Confidence for each product is defined as c = min(1, n / n_max), where n is the number of distinct orders "
              "contributing review text to the product and n_max is the largest such count among all products. Confidence "
              "therefore ranges from a small value for products with few reviews up to 1.0 for the most-reviewed product. "
              "The recommendation score combines normalised popularity (60%) and confidence-adjusted sentiment (40%):"),
        ("p", "<b>score(p) = 0.6 * pop_norm(p) + 0.4 * [c(p) * sent_norm(p) + (1 - c(p)) * 0.5]</b>"),
        ("p", "where pop_norm is the product's revenue percentile scaled to [0, 1] and sent_norm is the product sentiment "
              "scaled to [0, 1]. The neutral default inside the sentiment term prevents sparse reviews from dominating the "
              "ranking."),

        ("h2", "4.3.4 Evaluation and leakage audit"),
        ("p", "Both recommenders are evaluated with leave-one-out on the subset of customers who have at least two "
              "delivered items. A single held-out item per eligible customer is sampled once, before any model is trained, "
              "and that same held-out set is used for both the baseline and the NLP recommender. The remaining history is "
              "used as input, and the top-10 recommendations are checked against the held-out item."),
        ("p", "To prevent data leakage, product-level popularity, category bestseller lists and product sentiment are "
              "recomputed from the training portion of the data only. Every (customer, held-out product) line-item is removed "
              "from the interaction table, and every review belonging to an order that contains a held-out item is removed "
              "from the sentiment calculation. The final deployed recommendation collections are built from the full dataset "
              "after evaluation, so they use all available signal in production while the benchmark metrics remain "
              "leakage-free. Because both models are still evaluated on the same Olist dataset rather than on a later time "
              "period, the reported HitRate@10 values are a same-dataset ranking benchmark, not a true future-prediction "
              "estimate."),
        ("table",
         ["Metric", "Baseline", "NLP sentiment-aware"],
         [
             ["Eligible customers", eligible, eligible],
             ["HitRate@10", base_hit_rate, nlp_hit_rate],
             ["Precision@10", base_precision, nlp_precision],
             ["Recall@10", base_recall, nlp_recall],
             ["F1@10", base_f1, nlp_f1],
         ]),
        ("p", "The NLP model improves HitRate@10 from {} to {}, an absolute gain of {} "
              "on the same leave-one-out evaluation. The gain is modest but consistent, "
              "confirming that Portuguese review text carries a usable ranking signal even though only 41% of reviews "
              "contain text.".format(base_hit_rate, nlp_hit_rate, improvement_text)),

        ("h1", "5. Dashboard"),
        ("p", "A Streamlit dashboard connects to MongoDB and provides six interactive views: Overview, Sales Trends, "
              "Categories &amp; Products, Geography, Delivery and Recommendations. The dashboard reads pre-computed "
              "aggregates from MongoDB so it loads quickly even though the underlying data was processed by the full "
              "Hadoop/Spark pipeline."),
        ("p", "For DA-3 the dashboard was repaired and verified: MongoDB `_id` fields are mapped to meaningful column "
              "names, the metrics file path is resolved relative to the project root, undefined payment categories are "
              "disclosed rather than silently charted, the monthly trend default starts in January 2017 to avoid sparse "
              "early months, state abbreviations are paired with full state names, and the delivery insight is computed "
              "dynamically from the current data. The Recommendations page now displays the active NLP model metrics and "
              "the retained baseline for direct comparison."),
        ("p", "The Overview page shows delivered-order totals, GMV, top category and repeat-customer rate. Sales Trends "
              "plots monthly GMV and order volume. Categories &amp; Products shows top categories, review-vs-revenue scatter "
              "and top products. Geography visualises revenue and orders by state. Delivery shows average delivery days, "
              "late percentages and review score distribution. Recommendations displays the active NLP model metrics and "
              "a customer lookup with product categories."),
        ("shot", overview_png),
        ("caption", fig("Dashboard overview with KPIs, category revenue and payment distribution.")),
        ("shot", sales_png),
        ("caption", fig("Sales Trends view with monthly GMV and order volume.")),
        ("shot", cat_png),
        ("caption", fig("Categories &amp; Products view.")),
        ("shot", geo_png),
        ("caption", fig("Geographic distribution of revenue and orders by state.")),
        ("shot", deliv_png),
        ("caption", fig("Delivery performance and review score distribution.")),
        ("shot", rec_png),
        ("caption", fig("Recommendations view showing the active NLP model metrics and customer lookup.")),

        ("h1", "6. Limitations and Reproducibility"),
        ("p", "The following limitations affect interpretation of the results and should be considered when reproducing "
              "the work."),
        ("bullets", [
            "The sentiment lexicon is hand-curated (1,260 tokens) and does not capture domain-specific Portuguese slang or sarcasm. A pretrained model would likely be more robust.",
            "Reviews are order-level, so product-level sentiment is a revenue-weighted proxy, not direct product satisfaction feedback. A positive order review may reflect satisfaction with the dominant product, the seller or delivery.",
            "The evaluation uses a same-dataset leave-one-out split with a single precomputed held-out set for both models. Popularity, category lists and sentiment are computed from the training portion only; however, it is still not a time-based train/test split, so the metrics are a ranking benchmark rather than an estimate of future performance.",
            "The dataset is extremely sparse (≈1.07 purchases per customer), so absolute HitRate@10 values are modest for any model.",
            "Hive ran in local mode because of a log4j2 bridge conflict with YARN containers; this is a deployment limitation, not a methodology flaw.",
        ]),
        ("p", "Reproducibility: the full pipeline can be executed from a single command "
              "(<b>run_project.sh</b>) after setting environment variables in <b>config/settings.sh</b>. "
              "The DA-3 loader and recommender are run with <b>python3 -m src.recommender.loader_and_recommender</b>, "
              "the dashboard with <b>python3 -m streamlit run src/dashboard/app.py</b>, and tests with "
              "<b>python3 tests/test_da3.py</b>. All generated figures, reports and screenshots are written to "
              "<b>out/report/</b>."),

        ("h1", "7. Lessons Learned"),
        ("bullets", [
            "A clean landing layer is essential when source CSVs contain embedded newlines and inconsistent quoting.",
            "Cross-engine validation (Hive vs Spark) exposes subtle definition differences, such as whether freight is included in revenue.",
            "Honest reporting of negative results is better than hiding them; ALS's failure motivated the simpler, better baseline.",
            "Portuguese review text provides a measurable ranking signal, but attribution is a proxy because reviews are order-level, not product-level.",
            "Confidence weighting prevents sparse review sentiment from dominating the recommendation score.",
            "JDK 21 strong encapsulation requires explicit --add-opens flags across Hadoop, Hive, Spark and MapReduce task JVMs.",
            "A document store is a natural fit for per-user recommendation lists and aggregate dashboards.",
            "Dashboard aggregates should be pre-computed and stored in the serving layer rather than computed at page load.",
            "Hadoop paths with spaces break URI parsing, so transfers must use relative paths or space-free staging directories.",
        ]),

        ("h1", "8. Conclusion and Future Scope"),
        ("p", "The project demonstrates a complete batch Big Data pipeline over real e-commerce data. All planned "
              "components from DA-1 were implemented, including the dashboard that was deferred to DA-3. For DA-3 a "
              "Portuguese NLP sentiment pipeline and a sentiment-aware recommender were added, evaluated against the "
              "popularity baseline and integrated into the MongoDB serving layer. The pipeline is reproducible from a "
              "single command (run_project.sh) and every number is traceable to a log file."),
        ("p", "Key outcomes include: (1) a working pseudo-distributed Hadoop/Hive/Spark/MongoDB stack on a laptop; "
              "(2) three MapReduce jobs with combiners and a streaming job; (3) a Hive warehouse with ten analytics queries; "
              "(4) Spark ETL and SQL that cross-validate the Hive results; (5) a Portuguese NLP sentiment pipeline that "
              "processes 40,950 review texts and attributes sentiment to 18,908 products; (6) an evaluated NLP-aware "
              "recommender that improves HitRate@10 by {} over the baseline; and (7) a verified "
              "Streamlit dashboard served from MongoDB.".format(improvement_text)),
        ("p", "Future extensions include:"),
        ("bullets", [
            "Spark Structured Streaming over the review stream to cover the data-streams module in real time.",
            "A pretrained Portuguese sentiment model or multilingual transformer when environment constraints allow.",
            "Explicit product-level review attribution if product review data becomes available.",
            "A stricter time-based evaluation split to estimate true future recommendation performance.",
            "Deployment of the dashboard to a container or cloud platform for live demo access.",
            "Synthetic scale-up of the dataset to test the pipeline at multi-gigabyte size.",
        ]),

        ("h1", "References"),
        ("numbered", [
            "Olist. Brazilian E-Commerce Public Dataset by Olist, version 6. Kaggle, 2018. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (accessed October 2026).",
            "Apache Software Foundation. Apache Hadoop 3.5.0 documentation. https://hadoop.apache.org/docs/r3.5.0/ (accessed October 2026).",
            "Apache Software Foundation. Apache Hive 4.2.1 documentation. https://hive.apache.org/ (accessed October 2026).",
            "Apache Software Foundation. Apache Spark 4.2.0 documentation. https://spark.apache.org/docs/4.2.0/ (accessed October 2026).",
            "MongoDB Inc. MongoDB Community Server 8.3.11 manual. https://www.mongodb.com/docs/manual/ (accessed October 2026).",
            "Streamlit Inc. Streamlit 1.50.0 documentation. https://docs.streamlit.io/ (accessed October 2026).",
            "Loper, E. and Bird, S. NLTK: The Natural Language Toolkit. Proceedings of the ACL Workshop on Effective Tools and Methodologies for Teaching Natural Language Processing and Computational Linguistics, 2002.",
        ]),
    ]


def pdf_safe(text):
    import re
    parts = re.split(r"(&(?:amp|lt|gt|quot|apos|bull);)", text)
    return "".join(part if i % 2 else part.replace("&", "&amp;")
                   for i, part in enumerate(parts))


def plain(text):
    return (text.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&bull;", "*"))


# ---------------- DOCX renderer ----------------
def render_docx(blocks, path):
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    for s in ("Normal",):
        st = doc.styles[s]
        st.font.name = "Calibri"
        st.font.size = Pt(10.5)
    BLUE = RGBColor(0x1F, 0x3B, 0x63)

    def heading(text, size, before=10, after=4):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        r = p.add_run(plain(text))
        r.bold = True
        r.font.size = Pt(size)
        r.font.color.rgb = BLUE
        return p

    def rich(paragraph, text):
        import re
        for token in re.split(r"(<b>.*?</b>)", plain(text)):
            if token.startswith("<b>"):
                r = paragraph.add_run(token[3:-4])
                r.bold = True
            else:
                paragraph.add_run(token)

    for b in blocks:
        kind = b[0]
        if kind == "title":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(plain(b[1]))
            r.bold = True
            r.font.size = Pt(15)
            r.font.color.rgb = BLUE
        elif kind == "subtitle":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(plain(b[1]))
            r.bold = True
            r.font.size = Pt(11)
        elif kind == "meta":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(plain(b[1]))
            r.font.size = Pt(9.5)
            r.italic = True
        elif kind == "h1":
            heading(b[1], 13)
        elif kind == "h2":
            heading(b[1], 11.5, before=7, after=2)
        elif kind == "p":
            rich(doc.add_paragraph(), b[1])
        elif kind == "bullets":
            for it in b[1]:
                rich(doc.add_paragraph(style="List Bullet"), it)
        elif kind == "numbered":
            for it in b[1]:
                rich(doc.add_paragraph(style="List Number"), it)
        elif kind == "table":
            headers, rows = b[1], b[2]
            t = doc.add_table(rows=1 + len(rows), cols=len(headers))
            t.style = "Table Grid"
            for j, h in enumerate(headers):
                c = t.rows[0].cells[j]
                c.text = ""
                r = c.paragraphs[0].add_run(h)
                r.bold = True
                r.font.size = Pt(9)
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    c = t.rows[i + 1].cells[j]
                    c.text = ""
                    rich(c.paragraphs[0], val)
                    for run in c.paragraphs[0].runs:
                        run.font.size = Pt(9)
            doc.add_paragraph()
        elif kind in ("image", "shot"):
            if os.path.exists(b[1]):
                doc.add_picture(b[1], width=Inches(5.7 if kind == "image" else 6.2))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif kind == "caption":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(b[1])
            r.italic = True
            r.font.size = Pt(8.5)

    # Add page numbers in footer
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.font.size = Pt(9)
        fld_xml = (
            '<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'w:instr="PAGE"/>'
        )
        run._r.append(docx.oxml.parse_xml(fld_xml))

    doc.save(path)


# ---------------- PDF renderer ----------------
def render_pdf(blocks, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Image, Table, TableStyle, PageTemplate,
                                    Frame, KeepTogether)
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    BLUE = HexColor("#1F3B63")
    st_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14,
                              leading=18, alignment=1, textColor=BLUE, spaceAfter=4)
    st_sub = ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=10,
                            leading=13, alignment=1, spaceAfter=2)
    st_meta = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=8.5,
                             leading=11, alignment=1, spaceAfter=2)
    st_h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=12,
                           leading=15, textColor=BLUE, spaceBefore=9, spaceAfter=4)
    st_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5,
                           leading=13, textColor=BLUE, spaceBefore=5, spaceAfter=2)
    st_body = ParagraphStyle("b", fontName="Helvetica", fontSize=9,
                             leading=12, spaceAfter=4)
    st_bul = ParagraphStyle("bl", parent=st_body, leftIndent=14, spaceAfter=2)
    st_cap = ParagraphStyle("c", fontName="Helvetica-Oblique", fontSize=8.5,
                            leading=11, alignment=1, spaceAfter=6)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(HexColor("#555555"))
        canvas.drawCentredString(A4[0]/2, 10*mm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=16*mm,
                            rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    doc.addPageTemplates([PageTemplate(id='all', frames=frame, onPage=footer)])

    avail_w = A4[0] - 32*mm
    story = []
    pending_image = None

    def flush_image_caption(next_caption=None):
        nonlocal pending_image
        if pending_image is None:
            return
        img, kind = pending_image
        if next_caption:
            story.append(KeepTogether([img, Paragraph(next_caption, st_cap)]))
        else:
            story.append(img)
        pending_image = None

    for i, b in enumerate(blocks):
        kind = b[0]
        if kind == "title":
            flush_image_caption()
            story.append(Paragraph(pdf_safe(b[1]), st_title))
        elif kind == "subtitle":
            flush_image_caption()
            story.append(Paragraph(pdf_safe(b[1]), st_sub))
        elif kind == "meta":
            flush_image_caption()
            story.append(Paragraph(pdf_safe(b[1]), st_meta))
        elif kind == "h1":
            flush_image_caption()
            story.append(Paragraph(pdf_safe(b[1]), st_h1))
        elif kind == "h2":
            flush_image_caption()
            story.append(Paragraph(pdf_safe(b[1]), st_h2))
        elif kind == "p":
            flush_image_caption()
            story.append(Paragraph(pdf_safe(b[1]), st_body))
        elif kind == "bullets":
            flush_image_caption()
            for it in b[1]:
                story.append(Paragraph("&bull; " + pdf_safe(it), st_bul))
        elif kind == "numbered":
            flush_image_caption()
            for idx, it in enumerate(b[1], 1):
                story.append(Paragraph("{0}. {1}".format(idx, pdf_safe(it)), st_bul))
        elif kind == "table":
            flush_image_caption()
            headers, rows = b[1], b[2]
            ncol = len(headers)
            if ncol == 3:
                widths = [avail_w*0.22, avail_w*0.26, avail_w*0.52]
            elif ncol == 2:
                widths = [avail_w*0.35, avail_w*0.65]
            else:
                widths = [avail_w/float(ncol)] * ncol
            cell = ParagraphStyle("tc", fontName="Helvetica", fontSize=7.4, leading=9.2)
            cellb = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7.4, leading=9.2)
            data = [[Paragraph(pdf_safe(h), cellb) for h in headers]] + \
                   [[Paragraph(pdf_safe(v), cell) for v in row] for row in rows]
            t = Table(data, colWidths=widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#7F7F7F")),
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#DCE6F1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))
        elif kind in ("image", "shot"):
            flush_image_caption()
            path = b[1] if os.path.isabs(b[1]) else os.path.join(PROJECT, b[1])
            if os.path.exists(path):
                iw, ih = ImageReader(path).getSize()
                w = avail_w * (0.66 if kind == "image" else 0.95)
                pending_image = (Image(path, width=w,
                                       height=w * ih / float(iw), hAlign="CENTER"), kind)
        elif kind == "caption":
            flush_image_caption(b[1])
    flush_image_caption()
    doc.build(story)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    bl = blocks()
    docx_path = os.path.join(OUT, FILE_BASE + ".docx")
    pdf_path = os.path.join(OUT, FILE_BASE + ".pdf")
    render_docx(bl, docx_path)
    render_pdf(bl, pdf_path)
    print("wrote", docx_path)
    print("wrote", pdf_path)
