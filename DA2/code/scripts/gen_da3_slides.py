#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-3 deliverable: generate a 10-12 slide presentation as PPTX.

Run:
    python3 code/scripts/gen_da3_slides.py
"""
import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(PROJECT, "report")
FILE_BASE = "DA3_RegNo_Ecommerce-Sales-Recommendation"

BLUE = RGBColor(0x1F, 0x3B, 0x63)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x55, 0x55, 0x55)

TEAM = ("K PRADEEP KUMAR (23BLC1240) · VAHRAN P (23BLC1221) · "
        "ASHVATH KUMAR (23BLC1269) · K.P ABHISHEK (23BLC1292)")


def load_metrics():
    path = os.path.join(PROJECT, "out", "recommender_metrics.txt")
    if not os.path.exists(path):
        return {}
    return dict(ln.strip().split("=", 1) for ln in open(path) if "=" in ln)


def add_title_slide(prs, title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    # background
    bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BLUE
    bg.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1.5))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(9), Inches(1))
    tf2 = sub_box.text_frame
    tf2.text = subtitle
    p2 = tf2.paragraphs[0]
    p2.font.size = Pt(18)
    p2.font.color.rgb = WHITE
    p2.alignment = PP_ALIGN.CENTER

    team_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(9), Inches(0.8))
    tf3 = team_box.text_frame
    tf3.text = TEAM
    p3 = tf3.paragraphs[0]
    p3.font.size = Pt(14)
    p3.font.color.rgb = WHITE
    p3.alignment = PP_ALIGN.CENTER
    return slide


def add_section_slide(prs, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BLUE
    bg.line.fill.background()

    box = slide.shapes.add_textbox(Inches(0.5), Inches(3), Inches(9), Inches(1.5))
    tf = box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    return slide


def add_content_slide(prs, title, bullets, image_path=None, image_left=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # title bar
    bar = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.1))
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    bar.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.25), Inches(9.2), Inches(0.7))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE

    if image_path and os.path.exists(image_path):
        if image_left:
            left = Inches(0.4)
            text_left = Inches(5.0)
            text_width = Inches(4.6)
        else:
            left = Inches(5.0)
            text_left = Inches(0.4)
            text_width = Inches(4.6)
        try:
            slide.shapes.add_picture(image_path, left, Inches(1.4), width=Inches(4.6))
        except Exception:
            pass
    else:
        text_left = Inches(0.4)
        text_width = Inches(9.2)

    content_box = slide.shapes.add_textbox(text_left, Inches(1.4), text_width, Inches(5.8))
    tf = content_box.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = Pt(18)
        p.font.color.rgb = GRAY
        p.space_after = Pt(10)
    return slide


def add_two_column_slide(prs, title, left_title, left_items, right_title, right_items):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bar = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.1))
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    bar.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.25), Inches(9.2), Inches(0.7))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE

    # left
    lt = slide.shapes.add_textbox(Inches(0.4), Inches(1.3), Inches(4.4), Inches(0.5))
    ltf = lt.text_frame
    ltf.text = left_title
    lp = ltf.paragraphs[0]
    lp.font.size = Pt(22)
    lp.font.bold = True
    lp.font.color.rgb = BLUE

    lb = slide.shapes.add_textbox(Inches(0.4), Inches(1.9), Inches(4.4), Inches(5.3))
    lbf = lb.text_frame
    lbf.word_wrap = True
    for i, item in enumerate(left_items):
        p = lbf.paragraphs[0] if i == 0 else lbf.add_paragraph()
        p.text = item
        p.font.size = Pt(16)
        p.font.color.rgb = GRAY
        p.space_after = Pt(8)

    # right
    rt = slide.shapes.add_textbox(Inches(5.2), Inches(1.3), Inches(4.4), Inches(0.5))
    rtf = rt.text_frame
    rtf.text = right_title
    rp = rtf.paragraphs[0]
    rp.font.size = Pt(22)
    rp.font.bold = True
    rp.font.color.rgb = BLUE

    rb = slide.shapes.add_textbox(Inches(5.2), Inches(1.9), Inches(4.4), Inches(5.3))
    rbf = rb.text_frame
    rbf.word_wrap = True
    for i, item in enumerate(right_items):
        p = rbf.paragraphs[0] if i == 0 else rbf.add_paragraph()
        p.text = item
        p.font.size = Pt(16)
        p.font.color.rgb = GRAY
        p.space_after = Pt(8)
    return slide


def main():
    metrics = load_metrics()
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    dashboard_dir = os.path.join(PROJECT, "report", "dashboard")

    # 1. Title
    add_title_slide(prs,
        "E-Commerce Sales Analytics & Product Recommendation",
        "Hadoop · Hive · Spark · MongoDB | BCSE402L DA-3")

    # 2. Problem Statement
    add_content_slide(prs, "Problem Statement", [
        "Domain: Brazilian Olist e-commerce marketplace",
        "Need: Understand sales trends, geography, payments and delivery quality",
        "Challenge: Build recommendations at scale where single-machine tools fail",
        "Data sparsity: ~1.07 purchases per customer makes collaborative filtering hard",
        "Goal: End-to-end batch Big Data pipeline with honest evaluation and dashboard",
    ])

    # 3. Dataset
    add_content_slide(prs, "Dataset Overview", [
        "9 relational CSVs, ~1.55 M rows, ~122 MB",
        "Orders, items, payments, reviews, products, sellers, customers, geolocation",
        "99,441 orders, 112,650 line items, 93,358 unique customers",
        "Only 3.00% of customers ever order twice",
        "Dataset source: Kaggle / public mirror with SHA-256 manifest",
    ])

    # 4. Architecture
    add_content_slide(prs, "Pipeline Architecture & Stack", [
        "Stack: Hadoop 3.5.0 · Hive 4.2.1 · Spark 4.2.0 · MongoDB 8.3.11 · OpenJDK 21 · Streamlit",
        "Raw CSVs → HDFS /olist/raw (immutable)",
        "Clean layer /olist/clean fixes headers, newlines, quotes",
        "MapReduce: revenue by product, orders by month, payment distribution",
        "Hive: external tables + partitioned Parquet warehouse",
        "Spark: curated fact table + cross-validated SQL analytics",
        "MongoDB: recommendations + dashboard aggregates",
    ], image_path=os.path.join(PROJECT, "report", "fig1_architecture.png"), image_left=True)

    # 6. MapReduce
    add_two_column_slide(prs, "MapReduce Implementation",
        "Java Jobs",
        [
            "RevenueByProduct: 112,650 → 32,951 records via combiner",
            "OrdersByMonth: cleaning inside mapper, 23 monthly counts",
            "Custom partitioner and Hadoop counters",
        ],
        "Streaming Job",
        [
            "Payment distribution in Python",
            "Separate mapper/combiner/reducer",
            "Outputs count, total and average per payment type",
        ])

    # 7. Hive & Spark
    add_two_column_slide(prs, "Hive Warehouse & Spark ETL",
        "Hive",
        [
            "8 external tables over /olist/clean",
            "Managed Parquet table partitioned by month",
            "10 HQL analytics queries, 0 errors",
            "Window functions and dynamic partitioning",
        ],
        "Spark",
        [
            "Joins 6 tables into 112,650-row fact table",
            "Row counts match sources exactly",
            "6 Spark SQL analyses mirror Hive",
            "Cross-engine validation: numbers agree exactly",
        ])

    # 8. Key Results
    add_content_slide(prs, "Key Business Results", [
        "Peak GMV: R$1,153,364.20 in November 2017",
        "Top category: health_beauty with R$1,412,089.53",
        "Top state: São Paulo (SP) with R$5,769,703.15",
        "Credit card dominates: 76,795 transactions",
        "Repeat customer rate: only 3.00%",
        "On-time deliveries: 4.21★ vs late deliveries: 2.55★",
    ], image_path=os.path.join(dashboard_dir, "overview.png"), image_left=True)

    # 9. Recommender
    add_content_slide(prs, "Recommendation System", [
        "ALS experiment: documented negative result due to sparsity",
        "ALS RMSE 0.9702 vs global-mean baseline 0.9324",
        "DA-3 replacement: popularity + category-affinity baseline",
        "Recommends bestsellers from categories the customer bought",
        "Falls back to global bestsellers for cold-start users",
        "HitRate@10 = {} | Precision@10 = {} | Recall@10 = {}".format(
            metrics.get("hit_rate@10", "N/A"),
            metrics.get("precision@10", "N/A"),
            metrics.get("recall@10", "N/A")),
    ])

    # 10. Dashboard
    add_content_slide(prs, "Streamlit Dashboard", [
        "Interactive dashboard over MongoDB serving layer",
        "Views: Overview, Sales Trends, Categories, Geography, Delivery, Recommendations",
        "Pre-computed aggregates enable fast load times",
        "Customer recommendation lookup with model metrics",
        "Screenshots included in DA-3 report appendix",
    ], image_path=os.path.join(dashboard_dir, "sales_trends.png"), image_left=False)

    # 11. Lessons Learned
    add_content_slide(prs, "Lessons Learned", [
        "Clean landing layer is essential for malformed CSVs",
        "Cross-engine validation catches subtle definition bugs",
        "Honest reporting of negative results improves credibility",
        "JDK 21 requires explicit --add-opens across the stack",
        "Document store fits recommendation lists naturally",
        "Pre-compute dashboard aggregates in the serving layer",
    ])

    # 12. Conclusion
    add_content_slide(prs, "Conclusion & Future Scope", [
        "Complete batch Big Data pipeline implemented and evaluated",
        "All DA-1 planned components delivered, including dashboard",
        "Pipeline reproducible via code/scripts/run_all.sh",
        "Future: Spark Structured Streaming for real-time reviews",
        "Future: richer recommender with content/category features",
        "Future: cloud deployment of the dashboard",
    ])

    # 13. Q&A
    add_content_slide(prs, "Thank You", [
        "Questions & Discussion",
        "",
        TEAM,
    ])

    out_path = os.path.join(OUT, FILE_BASE + ".pptx")
    prs.save(out_path)
    print("wrote", out_path)
    print("slides:", len(prs.slides))


if __name__ == "__main__":
    main()
