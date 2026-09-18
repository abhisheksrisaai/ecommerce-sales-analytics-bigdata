#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: console-output screenshots for the report appendix.

Each PNG is rendered from the real run transcript in logs/ (content-based
slicing, WARN/INFO noise dropped), styled like a terminal window. Nothing is
retyped, so the screenshots cannot drift from what the cluster printed.

Produces report/ev1_hdfs.png ... report/ev8_mongo_agg.png.
Run:  python3 code/scripts/make_evidence_figs.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
LOGDIR = os.path.join(PROJECT, "logs")
OUT = os.path.join(PROJECT, "report")
os.makedirs(OUT, exist_ok=True)

BAR = "#1F3B63"
BG = "#FFFFFF"
INK = "#141414"
RULE = "#1F3B63"

FONT_SIZE = 26
LINE_H = 34
PAD = 26
BAR_H = 58
MAX_W = 1560

MONO_PATHS = [
    "/System/Library/Fonts/SFMono-Regular.otf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
]


def load_mono(size):
    for p in MONO_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def read(name):
    with open(os.path.join(LOGDIR, name), errors="replace") as fh:
        return [ln.rstrip("\n").rstrip() for ln in fh]


def find(lines, text, start=0):
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    raise SystemExit("marker not found: {0!r}".format(text))


def render(title, body, path):
    font = load_mono(FONT_SIZE)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    body = [ln.replace("\t", "        ") for ln in body]
    trimmed = []
    for ln in body:
        while probe.textlength(ln, font=font) > MAX_W - 2 * PAD and len(ln) > 4:
            ln = ln[:-2]
        if probe.textlength(ln, font=font) > MAX_W - 2 * PAD:
            ln = ln[: len(ln) - 1] + "\u2026"
        trimmed.append(ln)
    width = max([probe.textlength(t, font=font) for t in [title] + trimmed] + [200])
    width = int(min(width + 2 * PAD, MAX_W))
    height = BAR_H + PAD + len(trimmed) * LINE_H + PAD

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, BAR_H], fill=BAR)
    d.text((PAD, BAR_H // 2), title, font=font, fill="white", anchor="lm")
    y = BAR_H + PAD + LINE_H // 2
    for ln in trimmed:
        d.text((PAD, y), ln, font=font, fill=INK, anchor="lm")
        y += LINE_H
    d.rectangle([0, 0, width - 1, height - 1], outline=RULE, width=2)
    img.save(path)
    print("wrote {0}  ({1} lines)".format(os.path.abspath(path), len(trimmed)))


def section(lines, marker, before=0, after=0):
    i = find(lines, marker)
    return lines[max(0, i - before): i + after + 1]


def ev1_hdfs():
    log = read("01_ingest.log")
    # hdfs dfs -ls excerpt: first entries, an omission marker, last entries
    listing = [ln for ln in log if ln.startswith("drwxr") or ln.startswith("-rw-")]
    body = (["$ hdfs dfs -ls /olist/raw"]
            + listing[:4]
            + ["[... middle entries omitted ...]"]
            + listing[-4:]
            + ["",
               "$ # normalisation report printed by the ingest script:"]
            + section(log, "ENTITY", after=11)
            + ["",
               "$ hdfs dfs -du -h /olist"]
            + section(log, "TOTAL SIZE IN HDFS", after=3))
    render("ev1  -  HDFS ingestion  (logs/01_ingest.log)", body,
           os.path.join(OUT, "ev1_hdfs.png"))


def ev2_mapreduce():
    body = ["$ bash code/scripts/02_run_mapreduce.sh  # job counters, abridged", ""]
    for name, logfile in (("Job 1 - RevenueByProduct (Java)",
                            "mr_revenue_by_product.log"),
                           ("Job 2 - OrdersByMonth (Java)",
                            "mr_orders_by_month.log"),
                           ("Job 3 - PaymentDistribution (Streaming)",
                            "mr_payment_distribution.log")):
        log = read(logfile)
        body.append("--- {0} ---".format(name))
        for key in ("Launched map tasks", "Launched reduce tasks",
                    "Map input records", "Map output records",
                    "Combine input records", "Combine output records",
                    "Reduce input records", "Reduce output records"):
            hit = next((ln.strip() for ln in log if key in ln), None)
            if hit:
                body.append("    " + hit)
        body.append("")
    # the streaming job's answer file, as collected from HDFS
    with open(os.path.join(PROJECT, "out", "payment_distribution",
                           "part-merged.txt")) as fh:
        rows = [ln.rstrip("\n") for ln in fh]
    body.append("$ hdfs dfs -cat /olist/out/payment_distribution/part-* "
                "(type, payments, total, average)")
    body.extend("    " + r.replace("\t", "  |  ") for r in rows)
    render("ev2  -  MapReduce counters and job output", body,
           os.path.join(OUT, "ev2_mapreduce.png"))


def ev3_hive_gmv():
    log = read("hive_02_analytics.log")
    i = find(log, "| year_month")
    body = (["hive>  -- Q1: monthly GMV trend over delivered orders", ""]
            + log[i - 1: i + 26])
    render("ev3  -  Hive HQL result: monthly GMV  (logs/hive_02_analytics.log)",
           body, os.path.join(OUT, "ev3_hive_gmv.png"))


def ev4_hive_categories():
    log = read("hive_02_analytics.log")
    i = find(log, "|        category")
    body = (["hive>  -- Q2: top categories by revenue (first 10 of 15)", ""]
            + log[i - 1: i + 13])
    render("ev4  -  Hive HQL result: top categories",
           body, os.path.join(OUT, "ev4_hive_categories.png"))


def ev5_spark_sql():
    log = [ln for ln in read("04_spark_console.log")
           if not ln.startswith("26/")]
    body = []
    i = find(log, "rows after cleaning and joins")
    body.append("$ spark-submit code/spark/01_etl_analytics.py")
    body.append(log[i])
    j = find(log, "curated Parquet written")
    body.append(log[j])
    body.append("")
    k = find(log, "A1. Monthly GMV trend")
    body.extend(log[k: k + 17])
    render("ev5  -  Spark ETL + Spark SQL  (logs/04_spark_console.log, abridged)",
           body, os.path.join(OUT, "ev5_spark_sql.png"))


def ev6_spark_als():
    log = [ln for ln in read("04_spark_console.log")
           if not ln.startswith("26/")]
    i = find(log, "=== INTERACTION MATRIX ===")
    body = (["$ spark-submit code/spark/02_als_recommender.py", ""]
            + log[i: i + 10]
            + [""])
    j = find(log, "train rows")
    body.append(log[j])
    body.append("")
    body.append(next(ln for ln in log if "RMSE on held-out" in ln))
    body.append(next(ln for ln in log if "RMSE of global-mean" in ln))
    body.append(next(ln for ln in log if "improvement over baseline" in ln))
    body.append("")
    body.append(next(ln for ln in log if "wrote out/recommendations.csv" in ln))
    body.append(next(ln for ln in log if "model saved to" in ln))
    render("ev6  -  ALS recommender evaluation", body,
           os.path.join(OUT, "ev6_spark_als.png"))


def ev7_mongo_rec():
    log = read("mongo_01_load_query.log")
    i = find(log, "connected to MongoDB")
    body = (["$ python3 code/mongo/01_load_and_query.py", ""]
            + log[i: i + 3]
            + [""])
    j = find(log, "Q1. One document read")
    body.extend(log[j: j + 14])
    render("ev7  -  MongoDB serving layer: document lookup + stats",
           body, os.path.join(OUT, "ev7_mongo_rec.png"))


def ev8_mongo_agg():
    log = read("mongo_01_load_query.log")
    body = []
    j = find(log, "Q3. Aggregation pipeline")
    body.extend(log[j: j + 8])
    body.append("")
    j = find(log, "Q4. Multikey index query")
    body.extend(log[j: j + 6])
    body.append("")
    j = find(log, "Q5. High-confidence")
    body.extend(log[j: j + 5])
    body.append("")
    j = find(log, "Indexes on recommendations")
    body.extend(log[j: j + 3])
    render("ev8  -  MongoDB aggregation pipelines and indexes", body,
           os.path.join(OUT, "ev8_mongo_agg.png"))


if __name__ == "__main__":
    ev1_hdfs()
    ev2_mapreduce()
    ev3_hive_gmv()
    ev4_hive_categories()
    ev5_spark_sql()
    ev6_spark_als()
    ev7_mongo_rec()
    ev8_mongo_agg()
