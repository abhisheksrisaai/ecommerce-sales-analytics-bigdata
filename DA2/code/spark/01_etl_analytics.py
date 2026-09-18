#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: Spark ETL + Spark SQL analytics (Module 5)

Pipeline
    1. Read the nine Olist CSVs from HDFS as Spark DataFrames.
    2. Clean them: cast timestamps, drop rows that cannot be analysed,
       derive purchase month and delivery duration.
    3. Join the fact and dimension tables into one denormalised DataFrame.
    4. Persist it to HDFS as partitioned Parquet (an "ETL to a columnar
       serving layer" step that both Hive and Spark can read back quickly).
    5. Run the analytical questions with Spark SQL.

Run:
    spark-submit --master 'local[*]' code/spark/01_etl_analytics.py

Override the input location (defaults to the HDFS landing zone):
    RAW=hdfs:///olist/raw spark-submit ... 01_etl_analytics.py
"""
import os
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import IntegerType

# Default to the HDFS landing zone populated by the ingestion step; the
# environment variable makes the same script runnable on local files too.
RAW = os.environ.get("RAW", "hdfs:///olist/clean")
OUT = os.environ.get("OUT", "hdfs:///olist/warehouse/olist_curated")
LOCAL_OUT = os.environ.get("LOCAL_OUT", "out")

# Schema-on-read: the clean landing layer has no header row (it is stripped
# during ingestion), so column names are declared here rather than inferred.
# Everything is typed STRING on purpose and cast in the cleaning step, which
# keeps a malformed value from silently shifting the columns.
SCHEMAS = {
    "orders": ["order_id", "customer_id", "order_status",
               "order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date",
               "order_estimated_delivery_date"],
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id",
                    "shipping_limit_date", "price", "freight_value"],
    "customers": ["customer_id", "customer_unique_id",
                  "customer_zip_code_prefix", "customer_city",
                  "customer_state"],
    "products": ["product_id", "product_category_name", "product_name_lenght",
                 "product_description_lenght", "product_photos_qty",
                 "product_weight_g", "product_length_cm", "product_height_cm",
                 "product_width_cm"],
    "payments": ["order_id", "payment_sequential", "payment_type",
                 "payment_installments", "payment_value"],
    "reviews": ["review_id", "order_id", "review_score",
                "review_comment_title", "review_comment_message",
                "review_creation_date", "review_answer_timestamp"],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city",
                "seller_state"],
    "category_translation": ["product_category_name",
                             "product_category_name_english"],
}


def build_spark():
    return (SparkSession.builder
            .appName("Olist ETL and Spark SQL analytics")
            .config("spark.sql.shuffle.partitions", "8")   # laptop scale
            .getOrCreate())


def read_csv(spark, name):
    """Read one clean-layer directory as a DataFrame with declared columns.

    The directory itself is passed rather than a "*.csv" glob: the Hadoop
    FileSystem client treats a wildcard in the path as a literal file name in
    this configuration and fails with
      FileNotFoundException: File does not exist: hdfs:/olist/clean/orders/*.csv
    Each landing directory holds exactly one CSV, so the directory is enough.
    """
    return (spark.read
            .option("header", False)
            .option("quote", '"')
            .option("escape", "\\")
            .schema(", ".join("{0} STRING".format(c) for c in SCHEMAS[name]))
            .csv("{0}/{1}".format(RAW, name)))


def clean_orders(orders):
    """Cast the timestamp columns and drop rows without a purchase time."""
    ts_cols = ["order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date",
               "order_estimated_delivery_date"]
    for c in ts_cols:
        orders = orders.withColumn(c, F.to_timestamp(F.col(c)))
    return (orders
            .filter(F.col("order_purchase_timestamp").isNotNull())
            .withColumn("purchase_year", F.year("order_purchase_timestamp"))
            .withColumn("purchase_month", F.date_format("order_purchase_timestamp", "yyyy-MM"))
            .withColumn("delivery_days",
                        F.datediff("order_delivered_customer_date",
                                   "order_purchase_timestamp"))
            .withColumn("is_late",
                        F.when(F.col("order_delivered_customer_date") >
                               F.col("order_estimated_delivery_date"), 1).otherwise(0))
            .withColumn("order_status", F.trim(F.col("order_status"))))


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    # ---------------------------------------------------------------- extract
    orders = read_csv(spark, "orders")
    items = read_csv(spark, "order_items")
    customers = read_csv(spark, "customers")
    products = read_csv(spark, "products")
    payments = read_csv(spark, "payments")
    reviews = read_csv(spark, "reviews")
    sellers = read_csv(spark, "sellers")
    translation = read_csv(spark, "category_translation")

    print("\n=== RAW ROW COUNTS (extract) ===")
    for name, df in [("orders", orders), ("order_items", items),
                     ("customers", customers), ("products", products),
                     ("payments", payments), ("reviews", reviews),
                     ("sellers", sellers), ("category_translation", translation)]:
        print("{0:<22} {1:>10,}".format(name, df.count()))

    # ---------------------------------------------------------------- clean
    orders = clean_orders(orders)

    items = (items
             .withColumn("price", F.col("price").cast("double"))
             .withColumn("freight_value", F.col("freight_value").cast("double"))
             .withColumn("order_item_id", F.col("order_item_id").cast(IntegerType()))
             .filter(F.col("price").isNotNull() & (F.col("price") > 0)))
    items = items.withColumn("line_revenue", F.col("price") + F.col("freight_value"))

    review_agg = (reviews
                  .withColumn("review_score", F.col("review_score").cast(IntegerType()))
                  .groupBy("order_id")
                  .agg(F.round(F.avg("review_score"), 2).alias("avg_review_score"),
                       F.count("*").alias("review_count")))

    payment_agg = (payments
                   .withColumn("payment_value", F.col("payment_value").cast("double"))
                   .groupBy("order_id")
                   .agg(F.round(F.sum("payment_value"), 2).alias("order_value"),
                        F.first("payment_type").alias("payment_type"),
                        F.max("payment_installments").alias("installments")))

    products = (products
                .withColumn("product_category_name", F.trim("product_category_name"))
                .withColumn("product_weight_g", F.col("product_weight_g").cast(IntegerType())))
    translation = translation.withColumn(
        "product_category_name", F.trim("product_category_name"))

    # ----------------------------------------------------------------- join
    fact = (items
            .join(orders, "order_id", "inner")
            .join(customers, "customer_id", "left")
            .join(products, "product_id", "left")
            .join(translation, "product_category_name", "left")
            .join(review_agg, "order_id", "left")
            .join(payment_agg, "order_id", "left")
            .withColumn("category",
                        F.coalesce("product_category_name_english",
                                   "product_category_name",
                                   F.lit("unknown"))))

    print("\n=== CURATED FACT TABLE ===")
    print("rows after cleaning and joins: {0:,}".format(fact.count()))
    print("columns: {0}".format(", ".join(fact.columns)))

    # ---------------------------------------------------------------- load
    (fact.select("order_id", "customer_unique_id", "customer_state", "product_id",
                 "category", "seller_id", "price", "freight_value", "line_revenue",
                 "order_value", "payment_type", "avg_review_score", "purchase_month",
                 "delivery_days", "is_late")
         .write.mode("overwrite")
         .partitionBy("purchase_month")
         .parquet(OUT))
    print("\ncurated Parquet written to {0} (partitioned by purchase_month)".format(OUT))

    fact.createOrReplaceTempView("fact")
    fact.createOrReplaceTempView("olist_fact")

    # ------------------------------------------------- Spark SQL analytics
    def show(title, sql):
        print("\n" + "=" * 78)
        print(title)
        print("=" * 78)
        spark.sql(sql).show(20, truncate=False)

    show("A1. Monthly GMV trend", """
        SELECT purchase_month,
               COUNT(DISTINCT order_id)                  AS orders,
               ROUND(SUM(line_revenue), 2)               AS gmv,
               ROUND(AVG(order_value), 2)                AS avg_order_value
        FROM   fact
        WHERE  order_status = 'delivered'
        GROUP  BY purchase_month
        ORDER  BY purchase_month
    """)

    show("A2. Top 10 categories by revenue", """
        SELECT category,
               COUNT(*)                                   AS items_sold,
               ROUND(SUM(line_revenue), 2)                AS revenue,
               ROUND(AVG(avg_review_score), 2)            AS avg_review
        FROM   fact
        WHERE  order_status = 'delivered'
        GROUP  BY category
        ORDER  BY revenue DESC
        LIMIT  10
    """)

    show("A3. Revenue by customer state (top 10)", """
        SELECT customer_state,
               COUNT(DISTINCT order_id)                   AS orders,
               ROUND(SUM(line_revenue), 2)                AS revenue
        FROM   fact
        WHERE  order_status = 'delivered'
        GROUP  BY customer_state
        ORDER  BY revenue DESC
        LIMIT  10
    """)

    show("A4. Delivery performance by state", """
        SELECT customer_state,
               COUNT(DISTINCT order_id)                        AS orders,
               ROUND(AVG(delivery_days), 1)                    AS avg_delivery_days,
               ROUND(100.0 * SUM(is_late) / COUNT(DISTINCT order_id), 2) AS late_pct
        FROM   fact
        WHERE  order_status = 'delivered' AND delivery_days IS NOT NULL
        GROUP  BY customer_state
        HAVING COUNT(DISTINCT order_id) > 500
        ORDER  BY late_pct DESC
        LIMIT  10
    """)

    show("A5. Payment type distribution", """
        SELECT payment_type,
               COUNT(DISTINCT order_id)                   AS orders,
               ROUND(SUM(line_revenue), 2)                AS revenue,
               ROUND(AVG(order_value), 2)                 AS avg_order_value
        FROM   fact
        GROUP  BY payment_type
        ORDER  BY orders DESC
    """)

    show("A6. Review score vs delivery lateness", """
        SELECT CASE WHEN is_late = 1 THEN 'late' ELSE 'on_time' END AS delivery,
               COUNT(*)                                       AS items,
               ROUND(AVG(avg_review_score), 2)                AS avg_review_score
        FROM   fact
        WHERE  avg_review_score IS NOT NULL AND delivery_days IS NOT NULL
        GROUP  BY CASE WHEN is_late = 1 THEN 'late' ELSE 'on_time' END
    """)

    # -------------------------------------------------- save results for report
    os.makedirs(LOCAL_OUT, exist_ok=True)
    (spark.sql("""
        SELECT category, COUNT(*) AS items_sold,
               ROUND(SUM(line_revenue), 2) AS revenue,
               ROUND(AVG(avg_review_score), 2) AS avg_review
        FROM   fact WHERE order_status = 'delivered'
        GROUP  BY category ORDER BY revenue DESC
    """).toPandas().to_csv(os.path.join(LOCAL_OUT, "top_categories.csv"), index=False))
    print("\nwrote {0}/top_categories.csv".format(LOCAL_OUT))

    spark.stop()


if __name__ == "__main__":
    main()
