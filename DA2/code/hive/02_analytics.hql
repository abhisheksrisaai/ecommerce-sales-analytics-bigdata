-- BCSE402L - Big Data Analytics (TH)
-- DA-2 artefact: Hive analytics queries (HQL)
--
-- Run after 01_warehouse.hql:
--   hive --hiveconf hive.cli.print.header=true -f 02_analytics.hql
--
-- Every query below is an aggregation or join that Hive compiles into
-- MapReduce / Tez stages over the HDFS-resident tables.

USE olist;

-- =====================================================================
-- Q1. Monthly order volume and gross merchandise value
--     Answers: how is the marketplace growing month over month?
-- =====================================================================
SELECT
    substr(o.order_purchase_timestamp, 1, 7)              AS year_month,
    count(DISTINCT o.order_id)                            AS orders,
    round(sum(oi.price + oi.freight_value), 2)            AS gmv
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY substr(o.order_purchase_timestamp, 1, 7)
ORDER BY year_month;

-- =====================================================================
-- Q2. Top 15 product categories by revenue
--     Joins items -> products -> translation, i.e. a three-way join that a
--     single-machine spreadsheet cannot do comfortably at this row count.
--
--     "revenue" is defined the same way everywhere in this project, in Hive
--     and in Spark alike: sum(price + freight_value) over delivered orders.
--     Q1 uses that definition for the monthly GMV, so Q2 must too, otherwise
--     the two queries would report different totals for the same orders and
--     the cross-engine comparison would be meaningless.
-- =====================================================================
SELECT
    coalesce(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
    count(*)                                            AS items_sold,
    round(sum(oi.price + oi.freight_value), 2)          AS revenue,
    round(avg(oi.price), 2)                             AS avg_item_price
FROM orders o
JOIN order_items oi            ON o.order_id = oi.order_id
JOIN products p                ON oi.product_id = p.product_id
LEFT JOIN category_translation t ON p.product_category_name = t.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY coalesce(t.product_category_name_english, p.product_category_name, 'unknown')
ORDER BY revenue DESC
LIMIT 15;

-- =====================================================================
-- Q3. Orders and revenue by customer state (geographic distribution)
--     Uses the same item-level revenue definition as Q1 and Q2. The earlier
--     version summed payments.payment_value instead, which answers a subtly
--     different question (cash collected, not goods sold) and made the Hive
--     and Spark numbers for the same state disagree.
-- =====================================================================
SELECT
    c.customer_state,
    count(DISTINCT o.order_id)                          AS orders,
    round(sum(oi.price + oi.freight_value), 2)          AS revenue,
    round(sum(oi.price + oi.freight_value)
          / count(DISTINCT o.order_id), 2)              AS avg_order_value
FROM orders o
JOIN customers c   ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC
LIMIT 12;

-- =====================================================================
-- Q4. Payment method distribution
-- =====================================================================
SELECT
    payment_type,
    count(*)                                            AS transactions,
    round(sum(payment_value), 2)                        AS total_value,
    round(avg(payment_value), 2)                        AS avg_value,
    round(avg(payment_installments), 2)                 AS avg_installments
FROM payments
GROUP BY payment_type
ORDER BY transactions DESC;

-- =====================================================================
-- Q5. Delivery performance: actual vs promised, and late-delivery rate
--     Shows date arithmetic and conditional aggregation in HQL.
-- =====================================================================
SELECT
    c.customer_state,
    count(*)                                                          AS delivered_orders,
    round(avg(datediff(o.order_delivered_customer_date,
                       o.order_purchase_timestamp)), 1)               AS avg_delivery_days,
    sum(CASE WHEN o.order_delivered_customer_date >
                  o.order_estimated_delivery_date THEN 1 ELSE 0 END)  AS late_orders,
    round(100.0 * sum(CASE WHEN o.order_delivered_customer_date >
                                o.order_estimated_delivery_date
                           THEN 1 ELSE 0 END) / count(*), 2)          AS late_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_delivered_customer_date != ''
GROUP BY c.customer_state
HAVING count(*) > 500
ORDER BY late_pct DESC
LIMIT 12;

-- =====================================================================
-- Q6. Repeat-customer rate
--     customer_id is per-order; customer_unique_id identifies the person.
-- =====================================================================
SELECT
    count(*)                                                       AS total_customers,
    sum(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)               AS repeat_customers,
    round(100.0 * sum(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)
          / count(*), 2)                                           AS repeat_rate_pct
FROM (
    SELECT c.customer_unique_id, count(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
) t;

-- =====================================================================
-- Q7. Review score distribution
-- =====================================================================
SELECT
    review_score,
    count(*)                                            AS reviews,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2)  AS pct
FROM reviews
GROUP BY review_score
ORDER BY review_score;

-- =====================================================================
-- Q8. Revenue by category and review sentiment
--     Combines the revenue join with the review table.
-- =====================================================================
SELECT
    coalesce(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
    round(avg(r.review_score), 2)                       AS avg_review_score,
    count(*)                                            AS items_reviewed
FROM order_items oi
JOIN products p             ON oi.product_id = p.product_id
LEFT JOIN category_translation t ON p.product_category_name = t.product_category_name
JOIN reviews r              ON oi.order_id = r.order_id
GROUP BY coalesce(t.product_category_name_english, p.product_category_name, 'unknown')
HAVING count(*) > 300
ORDER BY avg_review_score DESC
LIMIT 15;

-- =====================================================================
-- Q9. Window function: top 5 categories per month by revenue
--     Demonstrates Hive analytic functions (PARTITION BY ... ORDER BY).
-- =====================================================================
SELECT year_month, category, revenue, rn FROM (
    SELECT
        substr(o.order_purchase_timestamp, 1, 7)                          AS year_month,
        coalesce(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
        round(sum(oi.price + oi.freight_value), 2)                        AS revenue,
        row_number() OVER (
            PARTITION BY substr(o.order_purchase_timestamp, 1, 7)
            ORDER BY sum(oi.price + oi.freight_value) DESC
        )                                                                 AS rn
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p     ON oi.product_id = p.product_id
    LEFT JOIN category_translation t ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY substr(o.order_purchase_timestamp, 1, 7),
             coalesce(t.product_category_name_english, p.product_category_name, 'unknown')
) ranked
WHERE rn <= 5
ORDER BY year_month, rn
LIMIT 60;

-- =====================================================================
-- Q10. Purchase-hour heat map (when do customers buy?)
--      Reads the partitioned table, so it demonstrates partition pruning
--      when a year_month predicate is supplied.
-- =====================================================================
SELECT
    hour(order_purchase_timestamp)                      AS purchase_hour,
    count(*)                                            AS orders
FROM orders_partitioned
WHERE purchase_year_month BETWEEN '2017-01' AND '2018-08'
GROUP BY hour(order_purchase_timestamp)
ORDER BY purchase_hour;
