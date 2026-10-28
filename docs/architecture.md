# Architecture

## Component diagram

```text
                    +------------------+
                    | 9 Olist CSVs     |
                    | data/raw/        |
                    +--------+---------+
                             |
              src/utils/ingest_hdfs.sh
                             |
            +----------------v----------------+
            | HDFS /olist/raw (immutable)     |
            | HDFS /olist/clean (normalised)  |
            +----------------+----------------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+----------------+  +----------------+  +------------------+
| MapReduce      |  | Hive           |  | Spark            |
| src/mapreduce/ |  | src/hive/      |  | src/spark/       |
| - RevenueByP.  |  | - warehouse.hql|  | - etl_analytics  |
| - OrdersByMonth|  | - analytics.hql|  | - als_recommender|
| - payment dist.|  +--------+-------+  +--------+---------+
+-----------------+           |                    |
                              |                    |
                              v                    v
                         +----+--------------------+---+
                         | HDFS /olist/warehouse     |
                         | (Parquet fact table)      |
                         +------------+--------------+
                                      |
                                      v
                         +---------------------------+
                         | Portuguese NLP sentiment  |
                         | src/sentiment/            |
                         +------------+--------------+
                                      |
                                      v
                         +---------------------------+
                         | Recommender               |
                         | src/recommender/          |
                         | - baseline                |
                         | - NLP-aware               |
                         +------------+--------------+
                                      |
                                      v
                         +---------------------------+
                         | MongoDB olist_analytics   |
                         | - aggregates              |
                         | - recommendations         |
                         | - product_sentiment       |
                         +------------+--------------+
                                      |
                                      v
                         +---------------------------+
                         | Streamlit dashboard       |
                         | src/dashboard/app.py      |
                         +---------------------------+
```

## Component responsibilities

| Component | Tool | Responsibility |
|---|---|---|
| Storage | HDFS | Cheap, durable storage for raw and cleaned CSVs and Parquet tables. |
| Cleaning | Python + Hadoop | `csv_normalize.py` removes headers, embedded newlines and bad escapes. |
| Batch aggregation | MapReduce | Java and Streaming jobs demonstrate scalable aggregation with combiners and partitioners. |
| Data warehouse | Hive | SQL analytics over external and partitioned Parquet tables. |
| In-memory ETL | Spark | Curated fact table and cross-engine validation of Hive results. |
| NLP | Python | Lexicon-based Portuguese sentiment scoring with negation handling. |
| Recommender | Python | Popularity baseline and NLP-aware model evaluated with leave-one-out. |
| Serving | MongoDB | Document store for per-user recommendation lists and dashboard aggregates. |
| Dashboard | Streamlit + Plotly | Six interactive views over the MongoDB serving layer. |

## Configuration

All local paths are defined in `config/paths.py`. External tool paths and
runtime settings are in `config/settings.py` and `config/settings.sh`.
