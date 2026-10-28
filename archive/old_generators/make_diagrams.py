#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: diagrams for the report, rendered with Pillow so the figures
are reproducible from code rather than pasted screenshots.

Produces
    report/fig1_architecture.png   end-to-end implemented pipeline
    report/fig2_mapreduce.png      the map -> combine -> shuffle -> reduce flow
    report/fig3_workflow.png       project progress against the DA-1 timeline
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "report")
os.makedirs(OUT, exist_ok=True)

BLUE = "#1F3B63"
FILL = "#DCE6F1"
ACCENT = "#2E6DA4"
GREEN = "#E2EFDA"
AMBER = "#FFF2CC"

FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]


def load_font(size, bold=False):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=1 if bold else 0)
            except Exception:
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def vertical_flow(steps, path, width=1500, box_w=1180, box_h=120, gap=58,
                  title=None, subtitle=None, fill=FILL, numbered=True):
    font = load_font(34)
    tfont = load_font(42, bold=True)
    sfont = load_font(30)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    margin = 56
    top = margin
    if title:
        top += 70
    if subtitle:
        top += 48

    n = len(steps)
    H = top + n * box_h + (n - 1) * gap + margin
    img = Image.new("RGB", (width, H), "white")
    d = ImageDraw.Draw(img)
    cx = width // 2
    x0, x1 = (width - box_w) // 2, (width - box_w) // 2 + box_w

    y = margin
    if title:
        d.text((cx, y + 26), title, font=tfont, fill=BLUE, anchor="mm")
        y += 70
    if subtitle:
        d.text((cx, y + 18), subtitle, font=sfont, fill="#555555", anchor="mm")
        y += 48

    for i, s in enumerate(steps):
        d.rounded_rectangle([x0, y, x1, y + box_h], radius=20,
                            fill=fill, outline=BLUE, width=3)
        label = f"{i+1}.  {s}" if numbered else s
        lines = wrap(d, label, font, box_w - 70)
        lh = 42
        ty = y + (box_h - len(lines) * lh) // 2 + lh // 2
        for ln in lines:
            d.text((cx, ty), ln, font=font, fill=BLUE, anchor="mm")
            ty += lh
        if i < n - 1:
            ay = y + box_h
            d.line([cx, ay, cx, ay + gap], fill=BLUE, width=5)
            d.polygon([(cx - 15, ay + gap - 20), (cx + 15, ay + gap - 20),
                       (cx, ay + gap)], fill=BLUE)
        y += box_h + gap
    img.save(path)
    print("wrote", os.path.abspath(path))


def fig1():
    vertical_flow([
        "Olist raw CSVs  -  9 files, 1,550,922 rows, 122 MB (Kaggle / Hugging Face mirror)",
        "HDFS landing zone  /olist/raw/<entity>   (hdfs dfs -put, 128 MB blocks, replication 1)",
        "MapReduce cleaning + aggregation   (3 jobs: revenue-by-product, orders-by-month, payment distribution)",
        "Hive warehouse   external tables + orders_partitioned (Parquet, partitioned by purchase month)",
        "Hive HQL analytics   GMV trend, top categories, delivery delays, repeat-customer rate, window functions",
        "Spark ETL   joins across 6 tables -> curated Parquet  /olist/warehouse/olist_curated",
        "Spark SQL analytics   GMV, category revenue, delivery performance, review-vs-lateness",
        "ALS recommender (MLlib, rank=10) trained on held-out split, RMSE reported against a global-mean baseline",
        "MongoDB serving store   one document per customer: { _id, recommendations[ ] }, multikey index on product_id",
        "Report + figures   metrics, query results and diagrams for DA-2",
    ], os.path.join(OUT, "fig1_architecture.png"),
        title="Fig. 1: Implemented end-to-end architecture",
        subtitle="Pseudo-distributed Hadoop 3.5 (HDFS + YARN)  |  Hive 4.2.1  |  Spark 4.2.0  |  MongoDB 8")


def fig2():
    """MapReduce shuffle, drawn as three columns: map tasks, shuffle, reducers."""
    width, height = 1500, 900
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    f = load_font(26)
    fb = load_font(30, bold=True)
    ft = load_font(38, bold=True)
    d.text((width // 2, 40), "Fig. 2: Map -> Combine -> Shuffle -> Reduce data flow",
           font=ft, fill=BLUE, anchor="mm")

    def box(x, y, w, h, text, fill=FILL, font=f):
        d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill,
                            outline=BLUE, width=3)
        lines = wrap(d, text, font, w - 26)
        lh = 32
        ty = y + (h - len(lines) * lh) // 2 + lh // 2
        for ln in lines:
            d.text((x + w // 2, ty), ln, font=font, fill=BLUE, anchor="mm")
            ty += lh

    col_y = 110
    box(70, col_y, 320, 96, "Input split: split 1 of the CSV block", "#FFFFFF", fb)
    box(560, col_y, 380, 96, "Map task  parse, clean, emit (product_id, amount)", "#FFFFFF", fb)
    box(1110, col_y, 320, 96, "Combiner  local sum per product", GREEN, fb)

    ys = [260, 400, 540]
    map_out = [
        "(G1, 58.90)  (B2, 239.90)\n(G1, 12.50)  (C7, 45.00)",
        "(G1, 99.00)  (A3, 15.75)\n(B2, 10.00)",
        "(C7, 8.25)   (A3, 120.00)\n(G1, 33.00)",
    ]
    combined = [
        "G1 -> 71.40\nB2 -> 239.90\nC7 -> 45.00",
        "G1 -> 99.00\nA3 -> 15.75\nB2 -> 10.00",
        "C7 -> 8.25\nA3 -> 120.00\nG1 -> 33.00",
    ]
    for i, y in enumerate(ys):
        box(70, y, 320, 120, "split {}".format(i + 1), "#FFFFFF", f)
        box(560, y, 380, 120, map_out[i], "#FFFFFF", f)
        box(1110, y, 320, 120, combined[i], GREEN, f)

    # arrows between columns
    for y in ys:
        d.line([390, y + 60, 556, y + 60], fill=BLUE, width=4)
        d.polygon([(556, y + 60), (540, y + 52), (540, y + 68)], fill=BLUE)
        d.line([940, y + 60, 1106, y + 60], fill=BLUE, width=4)
        d.polygon([(1106, y + 60), (1090, y + 52), (1090, y + 68)], fill=BLUE)

    # shuffle band
    d.rounded_rectangle([70, 690, 1430, 780], radius=14, fill=AMBER,
                        outline=BLUE, width=3)
    d.text((750, 722),
           "SHUFFLE  -  partition by hash(product_id), sort by key, spill to disk, fetch over HTTP",
           font=f, fill=BLUE, anchor="mm")
    d.text((750, 756),
           "all pairs for one product land in the same reducer; the combiner has already shrunk each partition",
           font=load_font(23), fill="#555555", anchor="mm")

    # reducers
    box(150, 820, 380, 60, "Reducer 1  sum -> part-r-00000", "#FFFFFF", f)
    box(560, 820, 380, 60, "Reducer 2  sum -> part-r-00001", "#FFFFFF", f)
    box(970, 820, 380, 60, "Reducer 3  sum -> part-r-00002", "#FFFFFF", f)
    img.save(os.path.join(OUT, "fig2_mapreduce.png"))
    print("wrote", os.path.abspath(os.path.join(OUT, "fig2_mapreduce.png")))


def fig3():
    """Progress against the DA-1 timeline."""
    rows = [
        ("Phase 1  Setup + dataset", "4 - 10 Aug", "Hadoop 3.5 pseudo-distributed, Hive 4.2.1, Spark 4.2.0, MongoDB; dataset downloaded (9 CSVs, 122 MB)", GREEN),
        ("Phase 2  Ingestion + cleaning", "11 - 24 Aug", "HDFS landing zone /olist/raw with one directory per entity; cleaning rules embedded in the MapReduce mappers", GREEN),
        ("Phase 3  MapReduce + Hive", "25 Aug - 7 Sep", "3 MapReduce jobs (2 Java, 1 Streaming); Hive warehouse with 8 external tables + 1 partitioned Parquet table; 10 HQL analytics queries", GREEN),
        ("Phase 4  Spark ETL + ALS", "8 - 19 Sep", "Spark ETL joining 6 tables to curated Parquet; 6 Spark SQL analyses; ALS recommender trained and evaluated on a held-out split", GREEN),
        ("Phase 5  MongoDB + dashboard", "20 Sep - 12 Oct", "MongoDB serving store populated (recommendations + category_stats) and queried with 5 NoSQL queries; dashboard pending", GREEN),
        ("Phase 6  Final report + slides", "13 - 20 Oct", "DA-2 report complete; DA-3 deliverables pending", AMBER),
    ]
    width = 1600
    f = load_font(24)
    fb = load_font(25, bold=True)
    ft = load_font(38, bold=True)
    row_h = 128
    top = 130
    height = top + len(rows) * row_h + 60
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    d.text((width // 2, 46), "Fig. 3: Project progress against the DA-1 timeline",
           font=ft, fill=BLUE, anchor="mm")
    hdr = load_font(25, bold=True)
    d.text((60, top - 34), "Phase", font=hdr, fill=BLUE)
    d.text((430, top - 34), "Planned", font=hdr, fill=BLUE)
    d.text((640, top - 34), "Status and evidence", font=hdr, fill=BLUE)

    y = top
    for name, window, detail, fill in rows:
        d.rounded_rectangle([48, y, width - 48, y + row_h - 14], radius=14,
                            fill=fill, outline=BLUE, width=2)
        for i, ln in enumerate(wrap(d, name, fb, 350)):
            d.text((70, y + 30 + i * 30), ln, font=fb, fill=BLUE)
        for i, ln in enumerate(wrap(d, window, f, 190)):
            d.text((430, y + 30 + i * 30), ln, font=f, fill=BLUE)
        for i, ln in enumerate(wrap(d, detail, f, width - 700)):
            d.text((640, y + 22 + i * 29), ln, font=f, fill="#333333")
        y += row_h
    img.save(os.path.join(OUT, "fig3_workflow.png"))
    print("wrote", os.path.abspath(os.path.join(OUT, "fig3_workflow.png")))


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
