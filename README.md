# E-Commerce Sales Analytics and Product Recommendation

End-to-end Big Data Analytics project for **BCSE402L – Big Data Analytics**.

The pipeline ingests the Brazilian Olist e-commerce dataset (~100 k orders,
~120 MB), cleans it, aggregates it with MapReduce, warehouses it in Hive,
cross-validates it in Spark, enriches it with Portuguese NLP sentiment, builds
and evaluates two recommenders, and serves everything through MongoDB to a
Streamlit dashboard.

---

## Team

- K Pradeep Kumar (23BLC1240)
- Vahran P (23BLC1221)
- Ashvath Kumar (23BLC1269)
- K.P Abhishek (23BLC1292) – primary submitter

---

## Folder structure

```text
Ecommerce_BigData_Project/
├── README.md                     # this file
├── PROJECT_OVERVIEW.md           # high-level end-to-end flow
├── requirements.txt              # Python dependencies
├── run_project.sh                # data pipeline entry point only
├── config/                       # paths, settings, Hadoop/Hive XML configs
│   ├── paths.py
│   ├── settings.py
│   ├── settings.sh
│   └── *.xml / jdk-opens.txt
├── data/
│   ├── raw/                      # nine Olist CSVs
│   └── README.md
├── src/
│   ├── cleaning/                 # CSV normalisation for Hive
│   ├── mapreduce/                # Java + Streaming jobs
│   ├── hive/                     # warehouse + analytics HQL
│   ├── spark/                    # ETL + ALS reference
│   ├── sentiment/                # Portuguese lexicon sentiment
│   ├── recommender/              # loader + baseline + NLP recommender
│   ├── database/                 # MongoDB helpers
│   ├── dashboard/                # Streamlit app
│   └── utils/                    # report/slide/figure generators + stage scripts
├── deploy/                       # snapshot exporter + Streamlit Cloud deployment notes
├── tests/                        # unit tests
├── docs/                         # architecture, methodology, viva guide
├── deliverables/                 # DA-1, DA-2, DA-3 reports/slides/screenshots
├── archive/                      # superseded files
├── logs/                         # console transcripts
└── out/                          # generated CSVs, metrics, reports and MR build artifacts
    ├── report/                   # PDF/DOCX report, PPTX slides, figures, screenshots
    └── mapreduce/build/          # compiled Java MR classes and JAR
```

---

## Prerequisites

- macOS (developed and tested on Apple Silicon)
- Homebrew with:
  - `openjdk@21`
  - `hadoop`
  - `hive`
  - `apache-spark`
  - `mongodb-community`
  - `python@3.11`
- Python 3.11+ and the packages in `requirements.txt`
- ~3 GB free RAM for local Spark/Hadoop

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

---

## Quick start

From a clean terminal in the project root:

```bash
# 1. Run the data pipeline (Hadoop/Hive/Spark/MongoDB)
bash run_project.sh

# 2. Start the dashboard
python3 -m streamlit run src/dashboard/app.py --server.port 8501
```

Then open http://localhost:8501.

### Deploy the dashboard online

The public Streamlit deployment uses a bundled snapshot of the MongoDB serving
collections, so it does not need a database server. See
[`deploy/README.md`](deploy/README.md) for the Streamlit Community Cloud steps
and the snapshot export command.

---

## Run individual stages

```bash
source config/settings.sh

bash src/utils/setup_env.sh      # cluster bring-up
bash src/utils/ingest_hdfs.sh    # HDFS raw + clean layers
bash src/utils/run_mapreduce.sh  # Java + Streaming MR jobs
bash src/utils/run_hive.sh       # Hive warehouse + 10 analytics queries
bash src/utils/run_spark.sh      # Spark ETL + ALS reference
bash src/utils/load_mongodb.sh   # aggregates, sentiment, recommendations
```

---

## Run tests

```bash
python3 tests/test_da3.py
```

---

## Regenerate deliverables

```bash
python3 -m src.utils.gen_figures       # out/report/fig1_architecture.png, fig3_workflow.png
python3 -m src.utils.capture_dashboard # out/report/dashboard/*.png
python3 -m src.utils.gen_report        # out/report/*.pdf + *.docx
python3 -m src.utils.gen_slides        # out/report/*.pptx
```

---

## Key results

- Peak GMV: **R$1,153,364.20** in November 2017.
- Top category: **health_beauty** (R$1,412,089.53).
- Top state: **São Paulo (SP)** (R$5,769,703.15).
- Repeat customer rate: **3.00%**.
- On-time deliveries average **4.21★** vs **2.55★** for late deliveries.
- DA-3 NLP-aware recommender HitRate@10 = **0.0654** vs baseline **0.0621**
  on a same-dataset leave-one-out benchmark, an improvement of **0.33
  percentage points** (5.3% relative). Both models use the same held-out set
  and training-data-only popularity, category and sentiment features.
- Evaluation features are built from the training split only. After evaluation,
  the deployed MongoDB recommendations are rebuilt from the full dataset so
  production uses all available historical signal.

---

## Documentation

- `PROJECT_OVERVIEW.md` – plain-language flow from CSV to dashboard.
- `docs/architecture.md` – component diagram and responsibilities.
- `docs/methodology.md` – cleaning, MapReduce, Hive, Spark, NLP, recommender,
  evaluation, limitations.
- `docs/data_dictionary.md` – datasets, fields, derived metrics, MongoDB
  collections.
- `docs/viva_guide.md` – faculty-style code walkthrough with likely questions.

---

## Notes

- The active recommender is the **NLP sentiment-aware** model in
  `src/recommender/loader_and_recommender.py`.
- The Spark ALS recommender is kept as a documented **negative result** because
  the dataset is too sparse (~1.07 purchases per customer).
- All hard-coded user paths were removed; paths are resolved from the project
  root via `config/paths.py`.
