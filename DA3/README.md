# DA-3 Completion & Presentation

**Topic:** E-Commerce Sales Analytics and Product Recommendation using Hadoop, Hive and Spark  
**Team:** K Pradeep Kumar (23BLC1240), Vahran P (23BLC1221), Ashvath Kumar (23BLC1269), K.P Abhishek (23BLC1292)  
**Submission:** 20 October 2026

## Deliverables

| File | Description |
|---|---|
| `DA3_23BLC1240_Ecommerce-Sales-Recommendation.pdf` | Final report (8 pages) |
| `DA3_23BLC1240_Ecommerce-Sales-Recommendation.docx` | Editable report source |
| `DA3_23BLC1240_Ecommerce-Sales-Recommendation.pptx` | Presentation slides (12 slides) |
| `dashboard/*.png` | Dashboard screenshots |

## What was completed for DA-3

1. **Dashboard** — Streamlit app reading from MongoDB, with six views: Overview, Sales Trends, Categories & Products, Geography, Delivery and Recommendations.
2. **Improved recommender** — Replaced the ALS negative result with a popularity + category-affinity baseline and evaluated it with HitRate@10, Precision@10 and Recall@10.
3. **Extended MongoDB serving layer** — Loaded additional aggregate collections for the dashboard: `monthly_gmv`, `state_revenue`, `delivery_performance`, `payment_distribution`, `review_distribution`, `top_products`, `repeat_customers`.
4. **Final report and slides** — 8-page report and 12-slide presentation covering abstract, problem statement, methodology, results, dashboard, lessons learned and future scope.

## How to run the dashboard

Make sure MongoDB is running on `localhost:27017` and the aggregates have been loaded:

```bash
cd "../DA2"
python3 code/scripts/da3_loader_and_recommender.py
python3 -m streamlit run code/dashboard/app.py --server.port 8501
```

Then open http://localhost:8501 in a browser.

## Key metrics

| Metric | Value |
|---|---|
| HitRate@10 | 0.0952 |
| Precision@10 | 0.0095 |
| Recall@10 | 0.0952 |
| F1@10 | 0.0173 |
| Repeat customer rate | 3.00% |
| Peak monthly GMV | R$1,153,364.20 (Nov 2017) |
| Top category | health_beauty (R$1,412,089.53) |
