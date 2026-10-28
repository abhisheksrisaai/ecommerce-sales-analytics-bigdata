# Data

## `raw/`

Contains the nine Olist CSV files as released by Olist on Kaggle. These are the
immutable source files for the pipeline.

Do not modify files in this directory; the cleaning step writes the normalised
versions to HDFS `/olist/clean/`.

## `sample/`

Reserved for small sample extracts used in development or demos. Currently
empty; the full pipeline reads from `raw/`.

## Hadoop/MongoDB working data

The shell scripts write transient runtime data (HDFS NameNode/DataNode files,
MongoDB `dbpath`) to `data/hadoop-data/` by default. This directory is created
automatically and is ignored by git.
