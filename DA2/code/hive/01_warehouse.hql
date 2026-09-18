-- BCSE402L - Big Data Analytics (TH)
-- DA-2 artefact: Hive warehouse definition (Module 2: Hive / HQL)
--
-- The nine Olist CSVs are stored in HDFS in two layers by
-- code/scripts/01_ingest_hdfs.sh:
--   /olist/raw/<entity>    the files exactly as downloaded (immutable)
--   /olist/clean/<entity>  the same data with the single header line removed
--
-- Hive reads the clean layer, for a concrete reason: Hive 4.2.1's
-- OpenCSVSerde does not honour TBLPROPERTIES ("skip.header.line.count" = "1"),
-- so an external table pointed at the raw file silently admits the header row
-- as data. That was observable directly:
--     SELECT MIN(length(customer_id)), COUNT(DISTINCT customer_id) FROM customers;
--     -> minimum id length 11, i.e. the literal string 'customer_id', and a
--        row count one greater than the source file's data-row count.
-- Removing the header during ingestion fixes this at the source.
--
-- OpenCSVSerde exposes every column as STRING. That is deliberate: it keeps
-- ingestion lossless and pushes type casting into the queries, which is the
-- usual Hive pattern for a raw landing zone.

CREATE DATABASE IF NOT EXISTS olist
COMMENT 'Olist Brazilian e-commerce warehouse (HDFS backed)'
LOCATION '/user/hive/warehouse/olist.db';

USE olist;

-- ---------------------------------------------------------------------
-- External tables over the HDFS landing zone
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS customers;
CREATE EXTERNAL TABLE customers (
    customer_id              STRING,
    customer_unique_id       STRING,
    customer_zip_code_prefix STRING,
    customer_city            STRING,
    customer_state           STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/customers';

DROP TABLE IF EXISTS orders;
CREATE EXTERNAL TABLE orders (
    order_id                      STRING,
    customer_id                   STRING,
    order_status                  STRING,
    order_purchase_timestamp      STRING,
    order_approved_at             STRING,
    order_delivered_carrier_date  STRING,
    order_delivered_customer_date STRING,
    order_estimated_delivery_date STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/orders';

DROP TABLE IF EXISTS order_items;
CREATE EXTERNAL TABLE order_items (
    order_id            STRING,
    order_item_id       INT,
    product_id          STRING,
    seller_id           STRING,
    shipping_limit_date STRING,
    price               DOUBLE,
    freight_value       DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/order_items';

DROP TABLE IF EXISTS payments;
CREATE EXTERNAL TABLE payments (
    order_id             STRING,
    payment_sequential   INT,
    payment_type         STRING,
    payment_installments INT,
    payment_value        DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/payments';

DROP TABLE IF EXISTS reviews;
CREATE EXTERNAL TABLE reviews (
    review_id               STRING,
    order_id                STRING,
    review_score            INT,
    review_comment_title    STRING,
    review_comment_message  STRING,
    review_creation_date    STRING,
    review_answer_timestamp STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/reviews';

DROP TABLE IF EXISTS products;
CREATE EXTERNAL TABLE products (
    product_id                 STRING,
    product_category_name      STRING,
    product_name_lenght        INT,
    product_description_lenght INT,
    product_photos_qty         INT,
    product_weight_g           INT,
    product_length_cm          INT,
    product_height_cm          INT,
    product_width_cm           INT
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/products';

DROP TABLE IF EXISTS sellers;
CREATE EXTERNAL TABLE sellers (
    seller_id              STRING,
    seller_zip_code_prefix STRING,
    seller_city            STRING,
    seller_state           STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/sellers';

DROP TABLE IF EXISTS category_translation;
CREATE EXTERNAL TABLE category_translation (
    product_category_name         STRING,
    product_category_name_english STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar" = ",", "quoteChar" = "\"", "escapeChar" = "\\")
STORED AS TEXTFILE
LOCATION '/olist/clean/category_translation';

-- ---------------------------------------------------------------------
-- Managed, partitioned warehouse table
--
-- The raw orders file is one flat file. Re-writing it as a table partitioned
-- by purchase month means later queries "WHERE year_month = '2018-01'" read
-- only that month's directory instead of scanning all 99,441 rows.
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS orders_partitioned;
CREATE TABLE orders_partitioned (
    order_id                      STRING,
    customer_id                   STRING,
    order_status                  STRING,
    order_purchase_timestamp      STRING,
    order_delivered_customer_date STRING,
    order_estimated_delivery_date STRING
)
PARTITIONED BY (purchase_year_month STRING)
STORED AS PARQUET;

SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

INSERT OVERWRITE TABLE orders_partitioned PARTITION (purchase_year_month)
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    substr(order_purchase_timestamp, 1, 7) AS purchase_year_month
FROM orders
WHERE order_status = 'delivered'
  AND order_purchase_timestamp IS NOT NULL
  AND order_purchase_timestamp != '';

SELECT 'partitions created' AS check_name, count(*) AS partition_count
FROM (SELECT DISTINCT purchase_year_month FROM orders_partitioned) t;
