# Data Dictionary

## Raw datasets (`data/raw/`)

| File | Rows | Key fields | Purpose |
|---|---|---|---|
| `olist_orders_dataset.csv` | 99,441 | `order_id`, `customer_id`, `order_status`, timestamps | Order header and lifecycle. |
| `olist_order_items_dataset.csv` | 112,650 | `order_id`, `product_id`, `price`, `freight_value` | Line-level revenue. |
| `olist_customers_dataset.csv` | 99,441 | `customer_id`, `customer_unique_id`, `customer_state` | Customer location and unique ID. |
| `olist_products_dataset.csv` | 32,951 | `product_id`, `product_category_name` | Product category (Portuguese). |
| `olist_order_payments_dataset.csv` | 103,886 | `order_id`, `payment_type`, `payment_value` | Payment method and amount. |
| `olist_order_reviews_dataset.csv` | 99,224 | `order_id`, `review_score`, `review_comment_message` | Review score and free text. |
| `olist_sellers_dataset.csv` | 3,095 | `seller_id`, `seller_state` | Seller location. |
| `product_category_name_translation.csv` | 71 | Portuguese → English category name | Category translation. |
| `olist_geolocation_dataset.csv` | 1,000,163 | zip, lat, long | Geographic reference (ingested only). |

## Derived fields

| Field | Definition |
|---|---|
| `line_revenue` | `price + freight_value` per order-item row. |
| `gmv` | Sum of `line_revenue` over delivered orders for a period. |
| `purchase_month` | `YYYY-MM` extracted from `order_purchase_timestamp`. |
| `delivery_days` | `order_delivered_customer_date - order_purchase_timestamp` in days. |
| `is_late` | 1 if `order_delivered_customer_date > order_estimated_delivery_date`, else 0. |
| `category` | English category name mapped via translation table; falls back to Portuguese or `unknown`. |
| `sentiment_score` | Product-level weighted-average Portuguese sentiment in [-1, 1]. |
| `confidence` | `min(1, n / n_max)` where `n` is the number of review texts for the product and `n_max` is the largest review count of any product in the split. |
| `nlp_score` | `0.6 * popularity_norm + 0.4 * (confidence * sentiment_norm + (1 - confidence) * 0.5)`. |

## MongoDB collections

| Collection | Source | Key fields |
|---|---|---|
| `monthly_gmv` | Aggregates | `purchase_month`, `orders`, `gmv`, `items` |
| `state_revenue` | Aggregates | `customer_state`, `orders`, `revenue`, `avg_order_value` |
| `delivery_performance` | Aggregates | `customer_state`, `delivered_orders`, `avg_delivery_days`, `late_pct` |
| `payment_distribution` | Aggregates | `payment_type`, `transactions`, `total_value`, `avg_value` |
| `review_distribution` | Aggregates | `review_score`, `reviews`, `pct` |
| `top_products` | Aggregates | `product_id`, `category`, `items_sold`, `revenue` |
| `category_stats` | Aggregates | `_id` = category, `revenue`, `items_sold`, `avg_review` |
| `repeat_customers` | Aggregates | `total_customers`, `repeat_customers`, `repeat_rate_pct` |
| `product_sentiment` | NLP pipeline | `product_id`, `category`, `sentiment_score`, `review_count` |
| `baseline_recommendations` | Recommender | `_id` = customer, `recommendations[]` |
| `recommendations` | Recommender | `_id` = customer, `recommendations[]`, active NLP model |

## Evaluation metrics

| Metric | Formula | Interpretation |
|---|---|---|
| HitRate@10 | `hits / eligible_customers` | Probability the held-out item appears in the top-10. |
| Precision@10 | `hits / (eligible_customers * 10)` | Fraction of top-10 slots that are hits. |
| Recall@10 | Same as HitRate@10 here | Fraction of held-out items retrieved. |
| F1@10 | `2 * precision * recall / (precision + recall)` | Harmonic mean of precision and recall. |

All metrics are computed on customers with at least two delivered items using
leave-one-out.
