# DA-3 Completion & Presentation

**Topic:** E-Commerce Sales Analytics and Product Recommendation using Hadoop, Hive and Spark  
**Team:** K Pradeep Kumar (23BLC1240), Vahran P (23BLC1221), Ashvath Kumar (23BLC1269), K.P Abhishek (23BLC1292)  
**Primary submitter registration:** 23BLC1292  
**Submission:** 20 October 2026

## Deliverables

| File | Description |
|---|---|
| `DA3_23BLC1292_Ecommerce-Sales-Recommendation.pdf` | Final report (10 pages) |
| `DA3_23BLC1292_Ecommerce-Sales-Recommendation.docx` | Editable report source |
| `DA3_23BLC1292_Ecommerce-Sales-Recommendation.pptx` | Presentation slides (12 slides) |
| `dashboard/*.png` | Dashboard screenshots (all six pages, error-free) |

(Previous `DA3_23BLC1240_*` copies are retained in `archive/old_deliverables/`.)

## What was completed for DA-3

1. **Fixed dashboard** — All six Streamlit pages now render without deprecation banners. Fixed `_id` handling, metrics-file parsing so the active NLP model (not the baseline) is displayed, payment category disclosure, monthly-trend default period, state labels, dynamic delivery insight and recommendation display.
2. **Portuguese NLP sentiment pipeline** — Real customer review text is normalised, scored with a curated Portuguese lexicon of 1,260 tokens, and attributed to products weighted by revenue share within each order.
3. **NLP-aware recommender** — Combines product popularity (60%) with confidence-adjusted review sentiment (40%). Compared fairly against the retained popularity/category-affinity baseline on a single precomputed leave-one-out held-out set with popularity, category lists and sentiment computed from the training data only.
4. **Extended MongoDB serving layer** — Added `product_sentiment` and `baseline_recommendations` collections alongside the existing analytics and active `recommendations` collection.
5. **Tests** — 16 unit tests covering sentiment scoring, metrics paths, MongoDB schemas, recommender ranking properties and dashboard metrics format.
6. **Final report and slides** — Rewritten to fix DA-2/DA-3 contradictions, add sequential figure numbering, explain raw vs cleaned row counts, define every metric precisely, add a leakage audit and limitations section, include references, and regenerate all dashboard screenshots from the corrected application.

## How to run the dashboard

Make sure MongoDB is running on `localhost:27017` and the aggregates have been loaded:

```bash
cd "../Ecommerce_BigData_Project"
python3 -m src.recommender.loader_and_recommender
python3 -m streamlit run src/dashboard/app.py --server.port 8501
```

Then open http://localhost:8501 in a browser.

## How to run tests

```bash
cd "../Ecommerce_BigData_Project"
python3 tests/test_da3.py
```

## Key metrics

| Metric | Baseline | NLP sentiment-aware |
|---|---|---|
| Eligible customers | 5,334 | 5,334 |
| HitRate@10 | 0.0621 | 0.0654 (+0.33 pp, +5.3% relative) |
| Precision@10 | 0.0062 | 0.0065 |
| Recall@10 | 0.0621 | 0.0654 |
| F1@10 | 0.0113 | 0.0118 |
| Reviews with text | — | 38,293 / 93,729 (40.9%) |
| Products with sentiment | — | 17,113 |
| Repeat customer rate | 3.00% | 3.00% |
| Peak monthly GMV | R$1,153,364.20 (Nov 2017) | R$1,153,364.20 (Nov 2017) |
| Top category | health_beauty (R$1,412,089.53) | health_beauty (R$1,412,089.53) |
