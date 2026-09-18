# BCSE402L Big Data Analytics — Project Context & Memory

> Read this file first in any new session. It records what has been done and what comes next.

## Course & Assignment Facts
- Course: **BCSE402L – Big Data Analytics (TH)**, 3 credits, VIT.
- Source docs in this folder: `BCSE402L_BIG-DATA-ANALYTICS_TH_1.1_0_BCSE402L.pdf` (syllabus), `Project guidelines.docx`.
- Syllabus modules: (1) Big Data overview, (2) Hadoop/HDFS/YARN/Hive/Pig, (3) MapReduce, (4) NoSQL (MongoDB/Cassandra/HBase), (5) Spark (RDD, SQL, MLlib, ETL), (6) Data streams, (7) Graph/social network analytics, (8) Recent trends.
- Group project, max 4 members. Viva for every DA (schedule TBD).
- Submission filename format: `DA_<Regno>_<Topic>.pdf`
- Deadlines:
  - **DA-1 Topic Selection & Planning — 4 Aug 2026** (3–4 page report + flowchart)
  - **DA-2 Progress & Application — 19 Sep 2026** (5–6 page report: applied technique + code/screenshots, progress, tools justification, team contribution)
  - **DA-3 Completion & Presentation — 20 Oct 2026** (8–10 page report + 10–12 slides, results, dashboard, Q&A)

## ACTIVE PROJECT (continue this one only)
**E-Commerce Sales Analytics and Product Recommendation using Hadoop, Hive and Spark**
- Dataset: Brazilian E-Commerce Public Dataset by Olist (Kaggle) — 9 CSVs, ~100k orders (2016–2018), ≈120 MB.
- Stack: HDFS data lake → Pig/MapReduce cleaning + aggregation jobs → Hive warehouse (partitioned tables, HQL analytics) → Spark SQL joins → ALS recommender (Spark MLlib) → MongoDB serving store → dashboard.
- Syllabus coverage: Module 2 (Hadoop/Hive/Pig), Module 3 (MapReduce), Module 4 (MongoDB), Module 5 (Spark/MLlib).
- Timeline (from DA-1): setup+download 4–10 Aug → ingest/clean 11–24 Aug → MR jobs + Hive 25 Aug–7 Sep → Spark ETL + ALS by 19 Sep (DA-2) → MongoDB + dashboard 20 Sep–12 Oct → final report/slides 13–20 Oct (DA-3).

## DROPPED
- Real-Time Twitter Sentiment Analysis (Spark Streaming + MongoDB) — was prepared for a friend; **user is NOT continuing with it. Do not revive it unless asked.** Files kept in `DA1/` just in case.

## Completed So Far
- **DA-1 done (4 Aug 2026):** Both reports generated as DOCX + PDF (3 pages each, all 5 required sections + flowchart) in `DA1/`.
  - E-commerce: `DA1/DA_RegNo_Ecommerce-Sales-Recommendation.{pdf,docx}`
  - Twitter (dropped): `DA1/DA_RegNo_Twitter-Sentiment-Analysis.{pdf,docx}`
  - Flowchart images: `DA1/flow_p1.png` (Twitter), `DA1/flow_p2.png` (e-commerce)
  - Generator script (edit + rerun to regenerate reports): `DA1/gen_reports.py` (uses python-docx, reportlab, Pillow — all installed under `~/Library/Python/3.9`)
- **TODO before DA-1 submission:** replace `[Name – Reg. No.]` placeholders in the DOCX and rename file to `DA_<Regno>_<Topic>.pdf`.
  - Note: `DA1/gen_reports.py` has a wrong `OUT` path (`/Users/abhishek/Documents/BD PROJECT/DA1` — missing `projects/`), so rerunning it as-is writes to a non-existent directory. Fix before reuse.

## DA-2 done (16 Sep 2026) — all five pipeline stages actually run
Everything lives in `DA2/`. **The DA-1 claim that the environment was already set up was false**: a fresh audit found no Java, Hadoop, Hive, Spark, MongoDB or Docker. The whole stack was installed and run during DA-2. Be ready for this at viva.

- Installed natively via Homebrew: Hadoop 3.5.0, Hive 4.2.1, Spark 4.2.0, MongoDB 8.3.11, OpenJDK 21, python@3.11.
- Dataset: 9 Olist CSVs, 1,550,922 rows, 122 MB in `DA2/data/raw/` (public mirror, `data/raw_sha256.txt`).
- One command replays everything: `bash DA2/code/scripts/run_all.sh` → exit 0, six stages OK.
  - HDFS `/olist/raw` + `/olist/clean`, 120.3 MB HEALTHY.
  - 3 MapReduce jobs (2 Java + 1 Streaming); combiners verified via counters (Job 1: 112,650 → 32,951 before shuffle).
  - Hive: 8 external tables + partitioned Parquet; 24/24 DDL and 11/11 analytics statements, 0 errors.
  - Spark: curated Parquet fact table (112,650 rows, 36 columns); 6 Spark SQL analyses; **Hive and Spark numbers now match exactly** (one shared definition of revenue: `sum(price + freight_value)` over delivered orders).
  - MongoDB `olist_analytics`: 500 recommendation documents + 74 category documents, 5 NoSQL queries.
- **ALS is an honest negative result** (documented in the report, not hidden): RMSE 0.9702 vs 0.9324 global-mean baseline on the usable subset (−4.05%); the matrix has ~1.07 purchases per customer, so collaborative filtering has almost no signal. Recommended DA-3 fix: popularity/category-affinity baseline + top-N ranking metric instead of RMSE.
- Deliverables: `DA2/report/DA2_RegNo_Ecommerce-Sales-Recommendation.{docx,pdf}` (6 pages, all 5 required sections, 10 tables, 3 generated figures). Regenerate with `python3 DA2/code/scripts/make_diagrams.py` then `python3 DA2/code/scripts/gen_report.py`.
- Evidence: `DA2/logs/*` (console transcripts for every stage), `DA2/evidence/data_profile.txt`, `DA2/out/*`.

## Next Up (DA-3, due 20 Oct)
- Dashboard over the MongoDB collections (the one unfinished item from the DA-1 plan).
- Replace ALS with a popularity/category-affinity recommender and evaluate it with Precision@K / Recall@K.
- Optional: Spark Structured Streaming over the review stream to cover the data-streams module (Module 6).
- DA-3 needs an 8–10 page report plus 10–12 slides; results and dashboard must be demoable. Before submission, replace `RegNo` in the DA-2 filenames with the actual registration number.
