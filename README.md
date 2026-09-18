# E-Commerce Sales Analytics and Product Recommendation

Course project for **BCSE402L – Big Data Analytics (VIT)**: a batch analytics
pipeline over the Brazilian Olist marketplace data (~100k orders, 2016–2018)
built on the Hadoop ecosystem. Raw CSVs are ingested into HDFS, cleaned and
aggregated with MapReduce, modelled in Hive, cross-validated in Spark, and
served from MongoDB as per-customer recommendations.

## Stack

| Component | Version | Role |
|---|---|---|
| Apache Hadoop (HDFS + YARN) | 3.5.0 | Distributed storage, pseudo-distributed |
| Apache Hive | 4.2.1 | SQL warehouse, external + partitioned Parquet tables |
| Apache Spark / PySpark | 4.2.0 | DataFrame ETL, Spark SQL, MLlib ALS |
| MongoDB Community | 8.3.11 | Document serving store |
| OpenJDK | 21 | Single JDK for the whole stack |

## Layout

- `DA2/code/` – pipeline source: `scripts/` (stage drivers incl. `run_all.sh`),
  `mr/` (2 Java + 1 Streaming job), `hive/` (warehouse DDL + 10 analytics
  queries), `spark/` (ETL, Spark SQL, ALS recommender), `mongo/` (serving
  layer), `config/` (cluster XML configs)
- `DA2/data/raw/` – the 9 Olist CSVs (122 MB) + `raw_sha256.txt` manifest
- `DA2/report/` – DA-2 report (DOCX + PDF, with console-output appendix) and
  the generated figures
- `DA2/logs/` – console transcripts of every stage (the evidence trail)
- `DA2/out/` – job outputs, `top_categories.csv`, `recommendations.csv`,
  `als_metrics.txt`
- `DA2/evidence/` – dataset profile
- `DA1/` – earlier topic-selection reports (one active, one dropped)
- `PROJECT_CONTEXT.md` – running project memory (course facts, status, next steps)

## Reproduce

macOS + Homebrew. Install the stack (`brew install hadoop hive apache-spark`),
then:

```bash
bash DA2/code/scripts/run_all.sh   # six stages, exits 0 when all pass
```

Regenerate the figures and the report:

```bash
python3 DA2/code/scripts/make_diagrams.py
python3 DA2/code/scripts/make_evidence_figs.py
python3 DA2/code/scripts/gen_report.py
```

## Results (all verified, Hive and Spark agree exactly)

- Monthly GMV, top categories (`health_beauty` ₹14.1L), state revenue (SP ₹57.7L)
- On-time delivery averages 4.21★ vs 2.55★ late — the clearest finding
- Only 3.00% of customers ever order twice
- ALS recommender is a documented negative result: with ~1.07 purchases per
  customer the matrix is too sparse for latent-factor models (RMSE 0.9702 vs
  0.9324 global-mean baseline). A popularity baseline is the honest
  recommendation for this data.

## Team

K Pradeep Kumar (23BLC1240) · Vahran P (23BLC1221) · Ashvath Kumar (23BLC1269) ·
K.P Abhishek (23BLC1292)
