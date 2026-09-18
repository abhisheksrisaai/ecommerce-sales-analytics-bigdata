#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: ALS collaborative-filtering recommender (Module 5, MLlib)

Method
    1. Implicit feedback is derived from purchase history: a customer buying
       an item more often (or paying more for it) is treated as a stronger
       signal. Counts are logged so that a single repeat purchase does not
       dominate the factorisation.
    2. Spark MLlib ALS factorises the sparse user x item matrix into latent
       factors, solving a regularised least-squares problem per user and per
       item alternately - each step is independent, which is why ALS scales
       out across a cluster.
    3. Quality is measured with RMSE on a held-out split.
    4. Top-N items are generated per customer, excluding items already bought.

Run:
    spark-submit --master 'local[*]' code/spark/02_als_recommender.py
"""
import os
import math

from pyspark.sql import SparkSession, functions as F, Window
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

RAW = os.environ.get("RAW", "hdfs:///olist/clean")
MODEL_PATH = os.environ.get("MODEL_PATH", "hdfs:///olist/models/als_recommender")
LOCAL_OUT = os.environ.get("LOCAL_OUT", "out")

# See 01_etl_analytics.py: the clean layer has no header row, so columns are
# declared explicitly and cast where needed.
SCHEMAS = {
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id",
                    "shipping_limit_date", "price", "freight_value"],
    "orders": ["order_id", "customer_id", "order_status",
               "order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date",
               "order_estimated_delivery_date"],
    "customers": ["customer_id", "customer_unique_id",
                  "customer_zip_code_prefix", "customer_city",
                  "customer_state"],
}

RANK = 10              # latent factors
MAX_ITER = 10
REG_PARAM = 0.1
TOP_N = 10

# Minimum number of distinct products a customer must have bought to take part
# in the factorisation.
#
# This threshold is not cosmetic. The Olist data yields roughly 99,800
# customer-product pairs across about 93,400 customers, i.e. barely one
# interaction each, and a single-interaction row carries no co-purchase signal
# for ALS to learn from. Trained on the full matrix, the model scored RMSE
# 1.2460 against a global-mean baseline of 1.1349: worse than predicting the
# average for every pair. Restricting to customers with a real basket makes the
# evaluation say something about the algorithm instead of about the sparsity.
MIN_ITEMS_PER_USER = 3


def build_spark():
    return (SparkSession.builder
            .appName("Olist ALS product recommender")
            .config("spark.sql.shuffle.partitions", "8")
            .getOrCreate())


def read_csv(spark, name):
    # The directory is passed rather than a "*.csv" glob; see the note in
    # 01_etl_analytics.py, where the globbing behaviour is explained.
    return (spark.read
            .option("header", False)
            .option("quote", '"')
            .option("escape", "\\")
            .schema(", ".join("{0} STRING".format(c) for c in SCHEMAS[name]))
            .csv("{0}/{1}".format(RAW, name)))


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    items = (read_csv(spark, "order_items")
             .select("order_id", "product_id", "price")
             .withColumn("price", F.col("price").cast("double"))
             .filter(F.col("price").isNotNull()))

    orders = (read_csv(spark, "orders")
              .select("order_id", "customer_id", "order_status")
              .filter(F.col("order_status") == "delivered"))

    customers = (read_csv(spark, "customers")
                 .select("customer_id", "customer_unique_id"))

    # ---------------------------------------------------------- build ratings
    # customer_unique_id is the real person; customer_id is per order.
    interactions = (items
                    .join(orders, "order_id", "inner")
                    .join(customers, "customer_id", "inner")
                    .groupBy("customer_unique_id", "product_id")
                    .agg(F.count("*").alias("purchases"),
                         F.sum("price").alias("total_spend")))

    # Implicit-feedback confidence: more purchases and higher spend both push
    # the rating up, but the log dampens very large values.
    interactions = interactions.withColumn(
        "rating",
        F.round(F.log1p(F.col("purchases") * 1.0), 4) +
        F.round(F.least(F.col("total_spend") / 100.0, F.lit(5.0)), 4))

    print("\n=== INTERACTION MATRIX ===")
    total_pairs = interactions.count()
    total_users = interactions.select("customer_unique_id").distinct().count()
    total_items = interactions.select("product_id").distinct().count()
    print("interactions      : {0:,}".format(total_pairs))
    print("distinct customers: {0:,}".format(total_users))
    print("distinct products : {0:,}".format(total_items))
    print("pairs per customer: {0:.2f}".format(total_pairs / max(total_users, 1)))

    # Keep only customers whose basket is large enough to give ALS something to
    # learn from; see MIN_ITEMS_PER_USER for the measured reason.
    basket_size = (interactions.groupBy("customer_unique_id")
                   .agg(F.count("product_id").alias("items")))
    eligible = (basket_size.filter(F.col("items") >= MIN_ITEMS_PER_USER)
                .select("customer_unique_id"))

    interactions = interactions.join(eligible, "customer_unique_id", "inner")

    eligible_pairs = interactions.count()
    eligible_users = interactions.select("customer_unique_id").distinct().count()
    print("\n=== MODEL SUBSET (customers with >= {0} distinct products) ===".format(
        MIN_ITEMS_PER_USER))
    print("interactions      : {0:,}".format(eligible_pairs))
    print("distinct customers: {0:,}".format(eligible_users))
    print("pairs per customer: {0:.2f}".format(
        eligible_pairs / max(eligible_users, 1)))

    # ALS needs dense integer user and item ids.
    #
    # monotonically_increasing_id() is not usable for this: it puts the
    # partition number in the high bits, so its values exceed the 32-bit range
    # and the cast to int fails with
    #   SparkArithmeticException: [CAST_OVERFLOW] The value 8589934592L ... 
    #   cannot be cast to "INT"
    # (8589934592 is 2^33, i.e. partition 1 shifted into the top bits).
    # A dense rank over a deterministic ordering gives compact consecutive ids.
    # Ordering by the hashed id keeps the mapping stable across runs.
    user_index = (interactions.select("customer_unique_id").distinct()
                  .withColumn("user_id",
                              F.dense_rank()
                               .over(Window.orderBy(F.xxhash64("customer_unique_id")))
                               .cast("int")))
    item_index = (interactions.select("product_id").distinct()
                  .withColumn("item_id",
                              F.dense_rank()
                               .over(Window.orderBy(F.xxhash64("product_id")))
                               .cast("int")))

    ratings = (interactions
               .join(user_index, "customer_unique_id")
               .join(item_index, "product_id")
               .select(F.col("user_id").cast("int"),
                       F.col("item_id").cast("int"),
                       F.col("rating").cast("float")))

    # ------------------------------------------------------------- train/test
    train, test = ratings.randomSplit([0.8, 0.2], seed=42)
    print("\ntrain rows: {0:,}   test rows: {1:,}".format(train.count(), test.count()))

    als = ALS(
        rank=RANK,
        maxIter=MAX_ITER,
        regParam=REG_PARAM,
        userCol="user_id",
        itemCol="item_id",
        ratingCol="rating",
        coldStartStrategy="drop",     # do not emit NaN predictions
        nonnegative=True,
        implicitPrefs=False,
        seed=42)

    print("\n=== TRAINING ALS (rank={0}, maxIter={1}, regParam={2}) ===".format(
        RANK, MAX_ITER, REG_PARAM))
    model = als.fit(train)

    predictions = model.transform(test)
    rmse = RegressionEvaluator(metricName="rmse", labelCol="rating",
                               predictionCol="prediction").evaluate(predictions)
    print("RMSE on held-out interactions: {0:.4f}".format(rmse))

    # --- baseline: predict the global mean for every pair -------------------
    global_mean = train.agg(F.avg("rating")).first()[0]
    baseline_rmse = RegressionEvaluator(
        metricName="rmse", labelCol="rating", predictionCol="prediction"
    ).evaluate(test.withColumn("prediction", F.lit(float(global_mean))))
    print("RMSE of global-mean baseline  : {0:.4f}".format(baseline_rmse))
    print("improvement over baseline     : {0:.2f}%".format(
        100.0 * (baseline_rmse - rmse) / baseline_rmse))

    # ------------------------------------------------------------- top-N list
    user_recs = model.recommendForAllUsers(TOP_N)

    exploded = (user_recs
                .select("user_id",
                        F.explode("recommendations").alias("rec"))
                .select("user_id", F.col("rec.item_id").alias("item_id"),
                        F.col("rec.rating").alias("score")))

    final = (exploded
             .join(item_index, "item_id")
             .join(user_index, "user_id")
             .select("customer_unique_id", "product_id",
                     F.round("score", 4).alias("score"))
             .orderBy("customer_unique_id", F.desc("score")))

    os.makedirs(LOCAL_OUT, exist_ok=True)
    pdf = final.limit(5000).toPandas()
    pdf.to_csv(os.path.join(LOCAL_OUT, "recommendations.csv"), index=False)
    print("\nwrote {0}/recommendations.csv  ({1:,} rows sampled)".format(
        LOCAL_OUT, len(pdf)))

    print("\n=== SAMPLE RECOMMENDATIONS (first 3 customers) ===")
    sample_users = [r[0] for r in final.select("customer_unique_id").distinct().limit(3).collect()]
    final.filter(F.col("customer_unique_id").isin(sample_users)) \
         .orderBy("customer_unique_id", F.desc("score")).show(30, truncate=False)

    # ------------------------------------------------------------ persistence
    model.write().overwrite().save(MODEL_PATH)
    print("model saved to {0}".format(MODEL_PATH))

    # metrics for the report
    with open(os.path.join(LOCAL_OUT, "als_metrics.txt"), "w") as fh:
        fh.write("rank={0}\nmaxIter={1}\nregParam={2}\n".format(RANK, MAX_ITER, REG_PARAM))
        fh.write("min_items_per_user={0}\n".format(MIN_ITEMS_PER_USER))
        fh.write("total_pairs_all_customers={0}\n".format(total_pairs))
        fh.write("total_customers_all={0}\n".format(total_users))
        fh.write("total_products={0}\n".format(total_items))
        fh.write("model_pairs={0}\n".format(eligible_pairs))
        fh.write("model_customers={0}\n".format(eligible_users))
        fh.write("train_rows={0}\n".format(train.count()))
        fh.write("test_rows={0}\n".format(test.count()))
        fh.write("rmse={0:.4f}\n".format(rmse))
        fh.write("baseline_rmse={0:.4f}\n".format(baseline_rmse))
        fh.write("improvement_pct={0:.2f}\n".format(
            100.0 * (baseline_rmse - rmse) / baseline_rmse))

    spark.stop()


if __name__ == "__main__":
    main()
