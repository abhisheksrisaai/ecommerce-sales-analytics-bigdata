# Deploying the dashboard

The public dashboard is a Streamlit Community Cloud app. It has no MongoDB
server, so `src/dashboard/app.py` tries the real MongoDB first and falls back to
the snapshot in `deploy/snapshot/` when the connection fails. The local/viva
version still uses MongoDB; only the public deployment runs from the snapshot.

## What is in the snapshot

`deploy/snapshot/*.json.gz` contains the nine collections the dashboard reads:

| Collection | Purpose |
|---|---|
| `monthly_gmv` | Sales Trends page |
| `category_stats` | Overview and Categories pages |
| `state_revenue` | Geography page |
| `delivery_performance` | Delivery page |
| `payment_distribution` | Overview payment chart |
| `review_distribution` | Delivery page review chart |
| `top_products` | Categories page top products |
| `repeat_customers` | Overview repeat-customer metric |
| `recommendations` | Recommendations page |

The snapshot is about 3.4 MB compressed. `baseline_recommendations` and
`product_sentiment` are not exported because the dashboard does not read them;
the baseline metrics come from `out/recommender_metrics.txt`.

## Regenerate the snapshot

Run this after the recommender loader has populated MongoDB:

```bash
python3 deploy/export_snapshot.py
```

The script writes `deploy/snapshot/*.json.gz`, then loads the files into
`mongomock` and checks the dashboard's key queries before finishing. Commit the
updated snapshot and push; Streamlit Cloud redeploys on the next push.

## Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `abhisheksrisaai/ecommerce-sales-analytics-bigdata`
   - **Branch:** `main`
   - **Main file path:** `src/dashboard/app.py`
   - **App URL:** choose a subdomain, for example `olist-ecommerce-analytics`.
4. Open **Advanced settings** and select Python 3.11 or 3.12. No secrets are
   required for the snapshot mode.
5. Click **Deploy**. The first build takes a few minutes.
6. When the app opens, the sidebar should show:

   > Demo mode: MongoDB is unavailable, so this dashboard is reading a bundled
   > snapshot of the serving collections.

## Update the live app

```bash
python3 deploy/export_snapshot.py
git add deploy/snapshot
git commit -m "Refresh dashboard deployment snapshot"
git push origin main
```

Streamlit Cloud watches the connected branch and redeploys automatically. If it
does not, open the app menu and choose **Reboot app**.

## Troubleshooting

- **“could not connect to MongoDB and no bundled snapshot was found”** — check
  that `deploy/snapshot/` is present on the deployed branch and that
  `mongomock` is in `requirements.txt`.
- **Charts show old values** — the loaders cache for 5 minutes. Reboot the app
  from the Streamlit Cloud menu, or push a commit to trigger a redeploy.
- **The app takes a few seconds to start** — this is the 3-second MongoDB
  connection attempt before the fallback. It only happens on a cold start.
- **Local dashboard still uses MongoDB** — intended. The fallback only runs when
  `mongodb://localhost:27017` (or `MONGO_URI`) is unreachable.
