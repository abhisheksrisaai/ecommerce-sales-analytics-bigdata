#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 deliverable: generate the DA-2 report as DOCX and PDF.

The report is rendered from the block list below, following the same block
vocabulary and visual style as the DA-1 report generator, so the two documents
look like one series.

Every number quoted in the text is taken from an actual run; the run logs are
listed in section 5.9 of the report so each figure can be traced back to a
console transcript in logs/.

Usage:
    python3 code/scripts/gen_report.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(PROJECT, "report")
FIG1 = os.path.join(OUT, "fig1_architecture.png")
FIG2 = os.path.join(OUT, "fig2_mapreduce.png")
FIG3 = os.path.join(OUT, "fig3_workflow.png")

FILE_BASE = "DA2_RegNo_Ecommerce-Sales-Recommendation"

EVFIGS = ["report/ev{0}_{1}.png".format(i, name) for i, name in enumerate(
    ["hdfs", "mapreduce", "hive_gmv", "hive_categories", "spark_sql",
     "spark_als", "mongo_rec", "mongo_agg"], start=1)]

TEAM = ("Team Members: K PRADEEP KUMAR - 23BLC1240, VAHRAN P - 23BLC1221, "
        "ASHVATH KUMAR - 23BLC1269, K.P ABHISHEK - 23BLC1292")


def blocks():
    return [
        ("title", "E-Commerce Sales Analytics and Product Recommendation using Hadoop, Hive and Spark"),
        ("subtitle", "BCSE402L - Big Data Analytics (TH)  |  DA-2: Progress &amp; Application"),
        ("meta", TEAM),
        ("meta", "Submission Date: 19 September 2026  |  Dataset: Brazilian E-Commerce Public Dataset by Olist"),

        # =====================================================================
        ("h1", "1. Application of Concepts"),
        ("p", "DA-1 proposed a batch pipeline over the Olist marketplace data. In DA-2 that design was "
              "built and run end to end: nine raw CSVs are ingested into HDFS, cleaned and aggregated with "
              "three MapReduce jobs, modelled in Hive, re-implemented and cross-validated in Spark, and "
              "finally served from MongoDB as per-customer recommendation documents. The table below maps "
              "each course module onto the artefact that implements it and the result it produced."),
        ("table",
         ["Course Module", "Concept Applied", "What Was Implemented (with result)"],
         [
             ["Module 2 - Hadoop &amp; HDFS",
              "Distributed storage, blocks, NameNode/DataNode, replication",
              "Pseudo-distributed HDFS cluster; landing zone /olist/raw (9 directories, 1,550,922 rows, 120.3 MB) "
              "and a normalised layer /olist/clean. <b>fsck reports HEALTHY, 0 corrupt blocks.</b>"],
             ["Module 3 - MapReduce",
              "Mapper / reducer, combiner, partitioner, counters, shuffle",
              "3 jobs: 2 Java (revenue by product, orders by month) and 1 Hadoop Streaming (payment distribution). "
              "<b>Job 1 combined 112,650 map outputs down to 32,951 before the shuffle (29% of the "
              "original shuffle traffic).</b>"],
             ["Module 3 - Hive",
              "External tables, SerDe, partitioning, Parquet, HQL, analytic functions",
              "8 external tables over /olist/clean plus a Parquet table partitioned by purchase month. "
              "<b>24/24 DDL statements and 11/11 analytics queries completed with 0 errors.</b>"],
             ["Module 5 - Spark",
              "DataFrames, Spark SQL, ETL joins, caching, MLlib ALS",
              "Spark ETL joins 6 tables into a curated Parquet fact table (112,650 rows, 36 columns); "
              "6 Spark SQL analyses reproduce the Hive numbers exactly; ALS recommender trained and evaluated."],
             ["Module 4 - NoSQL (MongoDB)",
              "Document model, embedded arrays, indexes, aggregation pipeline",
              "One document per customer with the ranked recommendation list embedded. "
              "<b>500 documents loaded, multikey index on recommendations.product_id, 5 NoSQL queries.</b>"],
             ["Module 1 - Big Data characteristics",
              "Volume, variety, velocity, veracity",
              "Volume: 122 MB / 1.55 M rows. Variety: 9 relational CSVs joined across 6 tables. "
              "Veracity: nulls, CSV quoting inconsistencies and embedded newlines handled explicitly."],
         ]),
        ("p", "Applied learning point: the same business question (monthly GMV, category revenue, state revenue) "
              "was answered twice, in Hive and in Spark, from the same cleaned data. Agreement between the two "
              "independent engines is what makes the result trustworthy rather than merely plausible; section 5.4 "
              "shows that agreement. Where the two initially disagreed, the discrepancy was traced to an "
              "inconsistent definition of 'revenue' and removed (see the issue table in section 5.8)."),

        # =====================================================================
        ("h1", "2. Project Progress"),
        ("p", "The pipeline is complete and reproducible: a single driver script (code/scripts/run_all.sh) "
              "starts the cluster and replays every stage. Phases 1 to 5 of the DA-1 timeline are finished; "
              "the dashboard is the only outstanding item."),
        ("image", FIG1),
        ("caption", "Fig. 1: Implemented end-to-end architecture. Every box in this diagram was executed; the "
                    "dashed future work from DA-1 (dashboard) is deliberately omitted."),
        ("table",
         ["Deliverable", "Status", "Evidence"],
         [
             ["Environment installation and cluster bring-up", "Complete",
              "Hadoop 3.5.0, Hive 4.2.1, Spark 4.2.0, MongoDB 8.3.11 installed and version-verified; "
              "logs/00_setup.log"],
             ["Dataset acquisition and profiling", "Complete",
              "9 CSVs, 1,550,922 rows, 122 MB; SHA-256 manifest data/raw_sha256.txt; evidence/data_profile.txt"],
             ["HDFS ingestion (raw + clean layers)", "Complete",
              "120.3 MB HEALTHY; logs/01_ingest.log"],
             ["MapReduce cleaning and aggregation (3 jobs)", "Complete",
              "32,951 product revenues, 23 months, 5 payment types; logs/02_mapreduce_console.log"],
             ["Hive warehouse and 10 analytics queries", "Complete",
              "0 errors on 24 DDL + 10 queries; logs/hive_02_analytics.log"],
             ["Spark ETL and 6 Spark SQL analyses", "Complete",
              "Curated Parquet fact table, row counts match sources exactly; logs/spark_01_etl.log"],
             ["ALS recommender (trained, evaluated, honest result)", "Complete with a documented negative result",
              "RMSE 0.9702 vs 0.9324 global-mean baseline on the usable subset; out/als_metrics.txt"],
             ["MongoDB serving store and NoSQL queries", "Complete",
              "500 recommendation documents + 74 category documents; logs/mongo_01_load_query.log"],
             ["Dashboard / visualisation", "Not started (Phase 6 in DA-1 plan)",
              "Deferred to DA-3"],
         ]),
        ("p", "One correction to the record: the DA-1 report listed Spark and MongoDB as already installed. "
              "An environment audit at the start of DA-2 found none of the stack present (no Java, Hadoop, Hive, "
              "Spark or MongoDB), so Phase 1 was actually carried out in DA-2 and every version is now recorded "
              "in logs/00_setup.log."),
        ("image", FIG3),
        ("caption", "Fig. 2: Progress against the DA-1 timeline (green = complete, amber = pending)."),

        # =====================================================================
        ("h1", "3. Methods &amp; Tools Used"),
        ("h2", "3.1 Software stack"),
        ("table",
         ["Component", "Version", "Role in the Project"],
         [
             ["Apache Hadoop (HDFS + YARN)", "3.5.0", "Distributed storage and resource management, pseudo-distributed (1 node)"],
             ["Apache Hive", "4.2.1", "SQL warehouse over HDFS; external (text) and managed (Parquet) tables"],
             ["Apache Spark / PySpark", "4.2.0", "DataFrame ETL, Spark SQL analytics, MLlib ALS recommender"],
             ["MongoDB Community + pymongo", "8.3.11 / 4.18.1", "Document serving store for recommendations and category statistics"],
             ["OpenJDK", "21", "Single JDK for Hadoop, Hive and Spark (Hive 4.2 rejects class files newer than its own, so the split-JDK attempt was dropped)"],
             ["Python", "3.11 (Spark), 3.9 (Mongo)", "PySpark requires Python 3.10+; system Python for pymongo"],
         ]),
        ("h2", "3.2 Dataset"),
        ("table",
         ["File", "Rows", "Use"],
         [
             ["olist_orders_dataset", "99,441", "Order header, status, five timestamps"],
             ["olist_order_items_dataset", "112,650", "Line items (price, freight) - the fact grain"],
             ["olist_customers_dataset", "99,441", "customer_id to customer_unique_id mapping and state"],
             ["olist_products_dataset", "32,951", "Category, weight and size attributes"],
             ["olist_order_payments_dataset", "103,886", "Payment type, value, installments"],
             ["olist_order_reviews_dataset", "99,224", "Review score (1-5) and comment text"],
             ["olist_sellers_dataset", "3,095", "Seller location"],
             ["product_category_name_translation", "71", "Portuguese to English category names"],
             ["olist_geolocation_dataset", "1,000,163", "Zip-code lat/long (ingested; not needed by the current queries)"],
         ]),
        ("h2", "3.3 Methods"),
        ("numbered", [
            "<b>Ingestion.</b> The raw CSVs are uploaded to HDFS with one directory per entity. A normalisation "
            "step produces /olist/clean, which drops the header row and flattens the embedded newlines and "
            "stray quotes that the review file contains. Hive's OpenCSVSerde ignores skip.header.line.count, "
            "so removing the header upstream was the reliable fix.",
            "<b>MapReduce.</b> Job 1 sums line revenue per product_id, Job 2 counts delivered orders per month, "
            "Job 3 (Streaming, Python) reports payment count, total and average per payment type. Both Java jobs "
            "use a combiner, which is legal because sum and count are commutative and associative.",
            "<b>Hive.</b> 8 external tables are defined over the clean layer, and orders_partitioned is a managed "
            "Parquet table partitioned by purchase_year_month, loaded with dynamic partitioning. The analytics "
            "file ends with a window-function query (row_number over a monthly partition).",
            "<b>Spark.</b> Explicit schemas are used rather than inference, 6 tables are joined into one curated "
            "fact table written as Parquet partitioned by month, and the 6 Spark SQL analyses mirror the Hive "
            "questions for cross-engine validation.",
            "<b>ALS.</b> Ratings combine purchase count and spend (log1p(count) + spend/100), split 80/20 into "
            "train and test, with RMSE compared against a global-mean baseline.",
            "<b>MongoDB.</b> The recommender output is reshaped into one document per customer - the natural "
            "access pattern for a product page, where a customer's list is a single document read.",
        ]),
        ("image", FIG2),
        ("caption", "Fig. 3: Map, combine, shuffle and reduce, showing how the combiner shrinks the shuffle."),

        # =====================================================================
        ("h1", "4. Team Participation"),
        ("p", "DA-1 assigned one pipeline stage per member. All four stages were completed in DA-2; the table "
              "records the owner, the work done in this cycle and the artefact that proves it."),
        ("table",
         ["Member (Reg. No.)", "DA-1 Responsibility", "Work Completed in DA-2", "Evidence"],
         [
             ["K PRADEEP KUMAR (23BLC1240)",
              "Hadoop/Hive cluster setup, overall architecture, integration",
              "Installed and configured the Hadoop 3.5 pseudo-distributed cluster (core-site, hdfs-site, "
              "mapred-site, yarn-site), formatted HDFS, started the daemons, and configured Hive 4.2.1 "
              "(hive-site, local execution mode, JVM --add-opens flags). Owned the integration script.",
              "code/config/*.xml, code/scripts/00_setup_env.sh, logs/00_setup.log"],
             ["VAHRAN P (23BLC1221)",
              "Data ingestion and cleaning (Pig / MapReduce)",
              "Downloaded and profiled the dataset, ingested the raw and clean layers into HDFS, and wrote the "
              "normalisation routine that flattens embedded newlines and unifies the CSV quoting.",
              "code/scripts/01_ingest_hdfs.sh, code/scripts/csv_normalize.py, evidence/data_profile.txt"],
             ["ASHVATH KUMAR (23BLC1269)",
              "MapReduce + HQL analytics, results documentation",
              "Wrote and ran the three MapReduce jobs (two Java with combiner and partitioner, one Streaming), "
              "then built the Hive warehouse and the 10 analytics queries and recorded the result tables.",
              "code/mr/**, code/hive/*.hql, logs/hive_02_analytics.log"],
             ["K.P ABHISHEK (23BLC1292)",
              "Spark ALS recommender, MongoDB serving layer, dashboard",
              "Implemented the Spark ETL and 6 Spark SQL analyses, trained and evaluated the ALS recommender, "
              "and built the MongoDB serving layer with its five NoSQL queries. Dashboard pending.",
              "code/spark/**, code/mongo/01_load_and_query.py, out/als_metrics.txt"],
         ]),
        ("p", "Shared work in this cycle: the cross-engine validation against Hive, the debugging log in "
              "section 5.8, and the preparation of this report."),

        # =====================================================================
        ("h1", "5. Explanation of Work Completed"),
        ("h2", "5.1 Ingestion and preparation"),
        ("p", "All nine files were uploaded to /olist/raw (120.3 MB, reported HEALTHY by hdfs fsck). Because "
              "Hive ignored the header-skipping property with the CSV SerDe, a second layer /olist/clean was "
              "produced in which the header row is removed and embedded newlines inside review comments are "
              "flattened. The profile in evidence/data_profile.txt records the null counts that motivated each "
              "cleaning rule, for example 2,965 products with no category name and 99,441 orders of which 96,478 "
              "reach the 'delivered' state."),

        ("h2", "5.2 MapReduce results"),
        ("table",
         ["Job", "Map input", "Map output", "After combiner", "Reduce output"],
         [
             ["1. Revenue by product (Java)", "112,651", "112,650", "32,951", "32,951 products"],
             ["2. Delivered orders by month (Java)", "99,442", "96,478", "23", "23 months"],
             ["3. Payment distribution (Streaming)", "103,887", "103,886", "10", "5 payment types"],
         ]),
        ("p", "The counters make the combiner's effect visible: in Job 1 the combiner reduced 112,650 map "
              "outputs to 32,951 - one pair per distinct product - so only about 29% of the pairs crossed the "
              "shuffle. Job 3's output (count, total, average per payment type) is a genuine three-column "
              "aggregate: credit_card 76,795 payments worth 12,542,084.19 (mean 163.32) and boleto 19,784 "
              "payments worth 2,869,361.27 (mean 145.03)."),

        ("h2", "5.3 Hive warehouse and analytics"),
        ("p", "The warehouse contains 8 external tables plus orders_partitioned, a Parquet table partitioned by "
              "purchase month into 23 partitions. The run completed 24/24 DDL statements and 11/11 analytics "
              "statements with zero errors. Selected results:"),
        ("table",
         ["Query", "Finding"],
         [
             ["Monthly GMV (Q1)", "GMV grows from 46,490.66 (Oct 2016) to a peak of 1,153,364.20 in Nov 2017, "
                                  "including the Black-Friday effect; the last full month, Aug 2018, is 985,491.64."],
             ["Top categories (Q2)", "health_beauty 1,412,089.53; watches_gifts 1,264,333.12; "
                                     "bed_bath_table 1,225,209.26 - three categories account for a large share of GMV."],
             ["Revenue by state (Q3)", "Sao Paulo (SP) alone contributes 5,769,703.15 across 40,501 orders; "
                                       "Rio de Janeiro (RJ) follows with 2,055,401.57."],
             ["Delivery performance (Q6)", "Maranhao (MA) averages 21.5 days with 19.67% late deliveries, against "
                                           "14.9 days and 7-8% in southern states - distance is the dominant factor."],
             ["Repeat-customer rate (Q7)", "93,358 unique customers, of whom 2,801 ordered more than once: a "
                                           "repeat rate of just 3.00%."],
             ["Review distribution (Q8)", "57.78% of the 99,224 reviews are 5-star and 11.51% are 1-star."],
             ["Purchase hour (Q10)", "Purchases peak at 16:00 (6,460 orders) and are lowest at 05:00 (182)."],
         ]),

        ("h2", "5.4 Spark ETL, Spark SQL and cross-engine validation"),
        ("p", "The Spark ETL joins order_items with orders, customers, products, payments and reviews into a "
              "curated Parquet fact table. Every row count matches its source exactly (orders 99,441, items "
              "112,650, customers 99,441, products 32,951, payments 103,886, reviews 99,224, sellers 3,095), "
              "which is the check that the joins neither duplicated nor dropped records. The six Spark SQL "
              "analyses then reproduce the Hive answers:"),
        ("table",
         ["Metric", "Hive", "Spark", "Agreement"],
         [
             ["GMV for August 2018", "985,491.64", "985,491.64", "Exact"],
             ["health_beauty revenue", "1,412,089.53", "1,412,089.53", "Exact"],
             ["bed_bath_table revenue", "1,225,209.26", "1,225,209.26", "Exact"],
             ["Revenue for state SP", "5,769,703.15", "5,769,703.15", "Exact"],
             ["Revenue for state RJ", "2,055,401.57", "2,055,401.57", "Exact"],
         ]),
        ("p", "Spark adds one analysis Hive would make awkward: review score against delivery lateness. "
              "Items delivered on time average 4.21 stars across 100,849 items, while late items average 2.55 "
              "stars across 8,520 items - the clearest single result in the project, and a direct argument for "
              "investing in logistics rather than discounts."),

        ("h2", "5.5 ALS recommender: an honest negative result"),
        ("p", "The ALS model was trained, evaluated and its output was loaded into MongoDB, but it does not beat "
              "a trivial baseline on this dataset, and the report states that plainly rather than hiding it. "
              "Measured results:"),
        ("table",
         ["Setup", "Interactions", "Customers", "Pairs/customer", "RMSE", "Baseline RMSE", "Outcome"],
         [
             ["All customers", "99,785", "93,358", "1.07", "1.2460", "1.1349", "-9.79% vs baseline"],
             ["Customers with 3+ items", "2,613", "760", "3.44", "0.9702", "0.9324", "-4.05% vs baseline"],
         ]),
        ("p", "The cause is sparsity, not a coding defect: 99,785 customer-product pairs spread over 93,358 "
              "customers is roughly one purchase per person, and a single interaction carries no co-purchase "
              "signal for latent-factor models to learn from. Restricting the matrix to customers with a real "
              "basket (3+ distinct products) halves the error but still trails a baseline that predicts the "
              "average for every pair. The defensible conclusion, which the project adopts, is that collaborative "
              "filtering is the wrong tool for a marketplace where almost nobody returns; a popularity or "
              "category-affinity baseline is the honest recommendation for this data, and the ALS stage stays in "
              "the pipeline as an evaluated experiment. The model still produced 500 customers x 10 ranked "
              "recommendations (out/recommendations.csv) that exercise the serving layer."),

        ("h2", "5.6 MongoDB serving layer"),
        ("p", "Two collections were created. recommendations holds one document per customer - an embedded array "
              "of {product_id, score, rank} - and category_stats holds one document per category. The multikey "
              "index on recommendations.product_id supports the reverse query. Five NoSQL operations were run: a "
              "single-document lookup, two aggregation pipelines (average list length; top categories by "
              "revenue), a multikey-index query on the embedded array, and an unwound score filter. Sample "
              "output: category cross-validated with Hive (health_beauty 1,412,089.53) and the top-recommended "
              "product appearing in 88 customer lists."),

        ("h2", "5.7 Evidence trail"),
        ("p", "logs/run_all_console.log (one end-to-end run of all six stages, exit 0), "
              "logs/00_setup.log (install and cluster), logs/01_ingest.log (HDFS), "
              "logs/02_mapreduce_console.log and logs/mr_*.log (job counters and output), "
              "logs/hive_02_analytics.log (result tables), logs/04_spark_console.log (ETL, Spark SQL, ALS), "
              "logs/05_mongo_console.log (collections, indexes, query output), evidence/data_profile.txt "
              "(dataset profile) and out/ (result files). Any number in this report can be matched against the "
              "console transcript that produced it."),

        ("h2", "5.8 Issues encountered and how they were resolved"),
        ("p", "The following are the substantive problems hit while building the pipeline. They are recorded "
              "because each one is a lesson about the ecosystem rather than an accident."),
        ("table",
         ["Problem", "Root cause", "Resolution"],
         [
             ["hdfs dfs -put failed with a URI parse error",
              "The project path contains a space ('BD PROJECT'), which breaks Hadoop's Path/URI parser",
              "Run file transfers from inside the data directory using relative paths, and keep a space-free "
              "staging directory for -files and -getmerge"],
             ["Hadoop Streaming job produced empty output",
              "The combiner was the reducer script, so it emitted four fields where the reducer expected three",
              "Wrote a separate combiner with a three-column contract"],
             ["Hive failed with UnsupportedClassVersionError (class 65)",
              "Hive 4.2 was compiled for JDK 17 while Hadoop had been pinned to JDK 21",
              "Unified every component on JDK 21 and removed the stale java-home override from hadoop-env.sh"],
             ["Hive died with InaccessibleObjectException on java.util.regex",
              "JDK 21 strong encapsulation blocks the reflective access Hive relies on",
              "Injected a 22-flag --add-opens file into the daemons, the Hive client and MR task JVMs"],
             ["beeline -f corrupted the HQL script",
              "The interactive prompt redrew lines, merging statements",
              "Wrote a driver that sends one statement per -e invocation, with the database bound into the JDBC URL"],
             ["Header row leaked into every Hive table",
              "OpenCSVSerde ignores skip.header.line.count",
              "Created the /olist/clean layer with the header removed upstream"],
             ["Reviews query failed with a malformed-line exception",
              "Review comments contain embedded newlines, quotes and backslashes",
              "Normalised newlines and quotes in the clean layer"],
             ["Three-table joins failed under Hive",
              "Automatic map-join conversion could not handle the shape",
              "Disabled hive.auto.convert.join for these queries"],
             ["ALS crashed with CAST_OVERFLOW (8589934592 to INT)",
              "monotonically_increasing_id() encodes the partition number in the high bits",
              "Replaced it with dense_rank over a hashed ordering to get compact integer ids"],
             ["Hive and Spark disagreed on category revenue",
              "Hive summed price only and ignored order status; Spark summed price + freight for delivered orders",
              "Fixed one definition (price + freight, delivered) and applied it in both engines; the numbers now match exactly"],
         ]),

        ("h2", "5.9 Remaining work"),
        ("bullets", [
            "Dashboard over the MongoDB collections (deferred to DA-3).",
            "Improve the recommendation stage by replacing ALS with a popularity / category-affinity baseline, and "
            "evaluate it with a top-N ranking metric instead of RMSE, which suits implicit feedback better.",
            "Extend Spark Structured Streaming over the review stream to cover the data-streams module.",
        ]),

        # =====================================================================
        ("h1", "Appendix A: Output Evidence (console screenshots)"),
        ("p", "The screenshots below are rendered directly from the run transcripts in logs/, with only "
              "timestamp noise removed and long middle sections marked as omitted. The full transcripts are "
              "the primary evidence; these figures make the key outputs visible inside the report itself."),
        ("shot", "report/ev1_hdfs.png"),
        ("caption", "Fig. 4: HDFS landing zone (hdfs dfs -ls) and the raw-to-clean normalisation report."),
        ("shot", "report/ev2_mapreduce.png"),
        ("caption", "Fig. 5: MapReduce job counters for all three jobs and the streaming job's answer file."),
        ("shot", "report/ev3_hive_gmv.png"),
        ("caption", "Fig. 6: Hive HQL output - monthly GMV trend (Q1)."),
        ("shot", "report/ev4_hive_categories.png"),
        ("caption", "Fig. 7: Hive HQL output - top categories by revenue (Q2, first 10)."),
        ("shot", "report/ev5_spark_sql.png"),
        ("caption", "Fig. 8: Spark ETL fact-table confirmation and Spark SQL monthly GMV (A1)."),
        ("shot", "report/ev6_spark_als.png"),
        ("caption", "Fig. 9: ALS recommender evaluation - interaction matrix, RMSE vs baseline, artefacts."),
        ("shot", "report/ev7_mongo_rec.png"),
        ("caption", "Fig. 10: MongoDB serving layer - per-customer recommendation document and collection stats."),
        ("shot", "report/ev8_mongo_agg.png"),
        ("caption", "Fig. 11: MongoDB aggregation pipelines (top categories, multikey query, score filter) and indexes."),
    ]


def pdf_safe(text):
    """reportlab parses paragraph text as mini-XML, so a bare '&' must be
    escaped, while the '&amp;' forms written in the blocks above must be left
    alone."""
    import re
    parts = re.split(r"(&(?:amp|lt|gt|quot|apos|bull);)", text)
    return "".join(part if i % 2 else part.replace("&", "&amp;")
                   for i, part in enumerate(parts))


def plain(text):
    """python-docx writes literal text, so XML entities must be decoded."""
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
        """Apply the small subset of inline markup used in the block list.

        python-docx writes literal text, so XML entities have to be decoded
        first or the document would show '&amp;'."""
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
        elif kind == "image":
            doc.add_picture(b[1], width=Inches(5.7))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif kind == "shot":
            doc.add_picture(os.path.join(PROJECT, b[1]), width=Inches(6.2))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif kind == "caption":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(b[1])
            r.italic = True
            r.font.size = Pt(8.5)
    doc.save(path)


# ---------------- PDF renderer ----------------
def render_pdf(blocks, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Image, Table, TableStyle)
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

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=16*mm,
                            rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm)
    avail_w = A4[0] - 32*mm
    story = []
    for b in blocks:
        kind = b[0]
        if kind == "title":
            story.append(Paragraph(pdf_safe(b[1]), st_title))
        elif kind == "subtitle":
            story.append(Paragraph(pdf_safe(b[1]), st_sub))
        elif kind == "meta":
            story.append(Paragraph(pdf_safe(b[1]), st_meta))
        elif kind == "h1":
            story.append(Paragraph(pdf_safe(b[1]), st_h1))
        elif kind == "h2":
            story.append(Paragraph(pdf_safe(b[1]), st_h2))
        elif kind == "p":
            story.append(Paragraph(pdf_safe(b[1]), st_body))
        elif kind == "bullets":
            for it in b[1]:
                story.append(Paragraph("&bull; " + pdf_safe(it), st_bul))
        elif kind == "numbered":
            for i, it in enumerate(b[1], 1):
                story.append(Paragraph("{0}. {1}".format(i, pdf_safe(it)), st_bul))
        elif kind == "table":
            headers, rows = b[1], b[2]
            ncol = len(headers)
            if ncol == 3:
                widths = [avail_w*0.22, avail_w*0.26, avail_w*0.52]
            elif ncol == 4:
                widths = [avail_w*0.20, avail_w*0.24, avail_w*0.38, avail_w*0.18]
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
        elif kind == "image":
            iw, ih = ImageReader(b[1]).getSize()
            w = avail_w * 0.66
            story.append(Image(b[1], width=w, height=w * ih / float(iw), hAlign="CENTER"))
        elif kind == "shot":
            iw, ih = ImageReader(os.path.join(PROJECT, b[1])).getSize()
            w = avail_w * 0.95
            story.append(Image(os.path.join(PROJECT, b[1]), width=w,
                               height=w * ih / float(iw), hAlign="CENTER"))
        elif kind == "caption":
            story.append(Paragraph(b[1], st_cap))
    doc.build(story)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for missing in [FIG1, FIG2, FIG3] + [os.path.join(PROJECT, f) for f in EVFIGS]:
        if not os.path.exists(missing):
            raise SystemExit(
                "missing figure {0}; run make_diagrams.py and make_evidence_figs.py first".format(missing))
    bl = blocks()
    docx_path = os.path.join(OUT, FILE_BASE + ".docx")
    pdf_path = os.path.join(OUT, FILE_BASE + ".pdf")
    render_docx(bl, docx_path)
    render_pdf(bl, pdf_path)
    print("wrote", docx_path)
    print("wrote", pdf_path)
