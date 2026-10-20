#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-3 deliverable: generate the 8-10 page final report as DOCX and PDF.

Run:
    python3 code/scripts/gen_da3_report.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(PROJECT, "report")
FILE_BASE = "DA3_RegNo_Ecommerce-Sales-Recommendation"

TEAM = ("Team Members: K PRADEEP KUMAR - 23BLC1240, VAHRAN P - 23BLC1221, "
        "ASHVATH KUMAR - 23BLC1269, K.P ABHISHEK - 23BLC1292")


def load_metrics():
    path = os.path.join(PROJECT, "out", "recommender_metrics.txt")
    if not os.path.exists(path):
        return {}
    return dict(ln.strip().split("=", 1) for ln in open(path) if "=" in ln)


def blocks():
    metrics = load_metrics()
    hit_rate = metrics.get("hit_rate@10", "N/A")
    precision = metrics.get("precision@10", "N/A")
    recall = metrics.get("recall@10", "N/A")

    dashboard_dir = os.path.join(PROJECT, "report", "dashboard")
    overview_png = os.path.join(dashboard_dir, "overview.png")
    sales_png = os.path.join(dashboard_dir, "sales_trends.png")
    cat_png = os.path.join(dashboard_dir, "categories.png")
    geo_png = os.path.join(dashboard_dir, "geography.png")
    deliv_png = os.path.join(dashboard_dir, "delivery.png")
    rec_png = os.path.join(dashboard_dir, "recommendations.png")

    return [
        ("title", "E-Commerce Sales Analytics and Product Recommendation using Hadoop, Hive and Spark"),
        ("subtitle", "BCSE402L - Big Data Analytics (TH)  |  DA-3: Completion &amp; Presentation"),
        ("meta", TEAM),
        ("meta", "Submission Date: 20 October 2026  |  Dataset: Brazilian E-Commerce Public Dataset by Olist"),

        ("h1", "Abstract"),
        ("p", "This project builds an end-to-end batch Big Data analytics pipeline over the Brazilian "
              "Olist e-commerce dataset. Nine relational CSVs (~1.55 M rows, 122 MB) are ingested into HDFS, "
              "cleaned and aggregated with MapReduce, modelled in Hive, cross-validated in Spark, and served "
              "from MongoDB. The pipeline answers business questions around monthly GMV, category and state "
              "revenue, payment preferences, delivery performance and customer repeat behaviour. "
              "A popularity + category-affinity recommender replaces an earlier ALS experiment that failed "
              "because of extreme sparsity, achieving a HitRate@10 of {} on a leave-one-out evaluation. "
              "A Streamlit dashboard provides interactive visualisation over the MongoDB serving store.".format(hit_rate)),

        ("h1", "1. Problem Statement"),
        ("p", "Small and mid-size e-commerce marketplaces need affordable analytics to understand sales trends, "
              "geographic demand, payment behaviour and delivery quality. They also need product recommendations, "
              "but most public datasets are too sparse for collaborative filtering to work out of the box."),
        ("p", "The problem addressed in this project is: <b>design and implement a batch Big Data pipeline that "
              "cleans, warehouses, analyses and serves e-commerce transaction data, and produce honest, evaluated "
              "product recommendations at a scale where single-machine tools become limiting.</b>"),
        ("p", "Why it matters: transaction data has high volume, variety and veracity. The Olist dataset spans "
              "orders, items, payments, reviews, products, sellers, customers and geolocation. Joining and aggregating "
              "these tables exercises the core Big Data concepts taught in BCSE402L."),

        ("h1", "2. Methodology"),
        ("h2", "2.1 Software stack"),
        ("table",
         ["Component", "Version", "Role"],
         [
             ["Apache Hadoop (HDFS + YARN)", "3.5.0", "Distributed storage and resource management, pseudo-distributed"],
             ["Apache Hive", "4.2.1", "SQL warehouse with external and partitioned Parquet tables"],
             ["Apache Spark / PySpark", "4.2.0", "DataFrame ETL, Spark SQL analytics, MLlib ALS experiment"],
             ["MongoDB Community", "8.3.11", "Document serving store for recommendations and aggregates"],
             ["OpenJDK", "21", "Single JDK shared by Hadoop, Hive and Spark"],
             ["Python", "3.11", "PySpark driver, MongoDB loader and dashboard"],
             ["Streamlit", "1.50.0", "Interactive dashboard"],
         ]),

        ("h2", "2.2 Dataset"),
        ("table",
         ["File", "Rows", "Use"],
         [
             ["olist_orders_dataset", "99,441", "Order header, status and timestamps"],
             ["olist_order_items_dataset", "112,650", "Line items: price, freight, product and seller"],
             ["olist_customers_dataset", "99,441", "Customer IDs, unique IDs, city and state"],
             ["olist_products_dataset", "32,951", "Category and physical attributes"],
             ["olist_order_payments_dataset", "103,886", "Payment type, value and installments"],
             ["olist_order_reviews_dataset", "99,224", "Review score and comment text"],
             ["olist_sellers_dataset", "3,095", "Seller location"],
             ["product_category_name_translation", "71", "Portuguese to English category names"],
             ["olist_geolocation_dataset", "1,000,163", "Zip-code lat/long (ingested, not queried)"],
         ]),

        ("h2", "2.3 Pipeline workflow"),
        ("numbered", [
            "<b>Ingestion.</b> Nine CSVs are uploaded to HDFS /olist/raw. A clean layer /olist/clean removes headers and normalises embedded newlines/quotes.",
            "<b>MapReduce.</b> Three jobs compute revenue per product, orders per month and payment-type distribution. Java jobs use combiners and a partitioner; the streaming job uses Python mapper/combiner/reducer scripts.",
            "<b>Hive.</b> Eight external tables and one Parquet table partitioned by purchase month support ten HQL analytics queries.",
            "<b>Spark.</b> A curated Parquet fact table joins six tables. Six Spark SQL analyses mirror the Hive questions for cross-engine validation.",
            "<b>Recommender.</b> An ALS experiment showed the matrix is too sparse. A popularity + category-affinity baseline is trained and evaluated with ranking metrics.",
            "<b>MongoDB.</b> Aggregates and recommendations are loaded as documents and queried with NoSQL operations.",
            "<b>Dashboard.</b> A Streamlit application reads from MongoDB and visualises KPIs, trends, geography, delivery and recommendations.",
        ]),

        ("h2", "2.4 Architecture"),
        ("p", "The architecture is a classic lambda-style batch pipeline. Raw CSVs land in HDFS, are normalised, "
              "aggregated by MapReduce, modelled in Hive, enriched in Spark and served from MongoDB. This separation "
              "lets each tool do what it does best: HDFS for cheap durable storage, MapReduce for scalable aggregation, "
              "Hive for SQL analytics, Spark for in-memory joins and ML, and MongoDB for low-latency serving."),
        ("image", os.path.join(PROJECT, "report", "fig1_architecture.png")),
        ("caption", "Fig. A: End-to-end implemented architecture."),
        ("image", os.path.join(PROJECT, "report", "fig3_workflow.png")),
        ("caption", "Fig. B: Project progress against the DA-1 timeline."),

        ("h1", "3. Implementation"),
        ("h2", "3.1 HDFS ingestion and cleaning"),
        ("p", "Raw files are kept immutable in /olist/raw. The clean layer fixes three concrete problems: "
              "(1) Hive 4.2.1's OpenCSVSerde ignores skip.header.line.count, so headers must be removed upstream; "
              "(2) review comments contain embedded newlines that break Hive's line-oriented reader; "
              "(3) inconsistent quoting between header and data rows is normalised. The result is 120.3 MB HEALTHY "
              "in HDFS with one block per file."),
        ("p", "The normalisation script is a real CSV parser that drops the header and re-serialises each record "
              "onto a single line. Newlines inside fields become spaces, double quotes become single quotes, and "
              "backslashes become forward slashes. This preserves values while making the files safe for Hive and "
              "Spark's line-oriented readers."),

        ("h2", "3.2 MapReduce jobs"),
        ("image", os.path.join(PROJECT, "report", "fig2_mapreduce.png")),
        ("caption", "Fig. B: Map -> Combine -> Shuffle -> Reduce data flow."),
        ("p", "Three MapReduce jobs demonstrate the key MapReduce concepts. Job 1 (RevenueByProduct) is a Java job "
              "that parses the order_items CSV, emits (product_id, line_revenue) pairs, aggregates locally with a "
              "combiner, shuffles by key using a custom partitioner, and sums in three reducers. The combiner reduced "
              "112,650 map outputs to 32,951 records before the shuffle, cutting network traffic to roughly 29%."),
        ("p", "Job 2 (OrdersByMonth) is another Java job that filters for delivered orders, parses timestamps, and counts "
              "orders per month. It demonstrates cleaning inside the mapper and uses Hadoop counters to record data "
              "quality metrics such as malformed records and non-delivered orders."),
        ("p", "Job 3 (PaymentDistribution) is a Hadoop Streaming job written in Python. It reports count, total value "
              "and average value per payment type. A separate combiner script is essential: an early attempt reused the "
              "reducer as the combiner, which emitted four columns where the reducer expected three, producing empty output."),
        ("table",
         ["Job", "Input", "Output", "Technique shown"],
         [
             ["RevenueByProduct (Java)", "112,651", "32,951 product revenues", "Mapper emits (product_id, price+freight); combiner reduces shuffle traffic to ~29%"],
             ["OrdersByMonth (Java)", "99,442", "23 monthly counts", "Cleaning inside mapper: status filter, timestamp parse, null handling"],
             ["Payment distribution (Streaming)", "103,887", "5 payment types", "Python mapper/combiner/reducer with three-column contract"],
         ]),

        ("h2", "3.3 Hive warehouse"),
        ("p", "The warehouse uses eight external tables over /olist/clean and a managed Parquet table partitioned by "
              "purchase_year_month. Dynamic partitioning creates 23 partitions, one per month. Hive runs in local mode "
              "to avoid a log4j2 bridge conflict with Hadoop's MRAppMaster in the YARN containers."),
        ("p", "Ten analytics queries cover the business questions: monthly GMV, top categories, revenue by state, "
              "payment distribution, delivery performance, repeat-customer rate, review distribution, revenue by category "
              "and review sentiment, a window-function query for top categories per month, and a purchase-hour heat map. "
              "All 24 DDL statements and 11 analytics queries completed with zero errors."),

        ("h2", "3.4 Spark ETL and SQL"),
        ("p", "Spark reads the clean CSVs with explicit schemas, casts timestamps and numeric columns, and joins "
              "order_items, orders, customers, products, payments and reviews into a 112,650-row fact table persisted "
              "as Parquet partitioned by purchase_month. Row counts match sources exactly, confirming that joins neither "
              "duplicated nor dropped records."),
        ("p", "Six Spark SQL analyses reproduce the Hive numbers exactly after unifying the revenue definition to "
              "sum(price + freight_value) over delivered orders. Spark adds one analysis that Hive would make awkward: "
              "review score against delivery lateness. Items delivered on time average 4.21 stars while late items average "
              "2.55 stars, making logistics the clearest driver of customer satisfaction."),
        ("table",
         ["Metric", "Hive", "Spark"],
         [
             ["GMV August 2018", "985,491.64", "985,491.64"],
             ["health_beauty revenue", "1,412,089.53", "1,412,089.53"],
             ["bed_bath_table revenue", "1,225,209.26", "1,225,209.26"],
             ["Revenue SP", "5,769,703.15", "5,769,703.15"],
             ["Revenue RJ", "2,055,401.57", "2,055,401.57"],
         ]),

        ("h2", "3.5 MongoDB serving layer"),
        ("p", "MongoDB is used as the serving store because the recommendation output is a per-customer variable-length "
              "list of product ids. A relational schema would require either a child table scanned on every read or a "
              "denormalised string column. A document store models the natural access pattern directly: one document per "
              "customer with the recommendation list embedded."),
        ("p", "For DA-3 the MongoDB layer was extended beyond recommendations to include dashboard aggregates: "
              "monthly_gmv, state_revenue, delivery_performance, payment_distribution, review_distribution, top_products, "
              "category_stats and repeat_customers. A multikey index on recommendations.product_id supports reverse lookups "
              "such as 'which customers are recommended this product?'."),

        ("h1", "4. Results and Discussion"),
        ("h2", "4.1 Business analytics"),
        ("p", "The Hive and Spark analyses produced a consistent set of business metrics. GMV grows from R$46,490.66 "
              "in October 2016 to a peak of R$1,153,364.20 in November 2017, reflecting the Black Friday effect. The "
              "last full month, August 2018, records R$985,491.64."),
        ("p", "The top three categories by revenue are health_beauty (R$1,412,089.53), watches_gifts (R$1,264,333.12) "
              "and bed_bath_table (R$1,225,209.26). These three categories alone account for a large share of total GMV. "
              "Geographically, São Paulo state dominates with R$5,769,703.15 of revenue across 40,501 orders, followed by "
              "Rio de Janeiro with R$2,055,401.57."),
        ("table",
         ["Metric", "Finding"],
         [
             ["Monthly GMV peak", "R$1,153,364.20 in November 2017 (Black Friday effect)"],
             ["Top category", "health_beauty with R$1,412,089.53 revenue"],
             ["Top state", "São Paulo (SP) with R$5,769,703.15 across 40,501 orders"],
             ["Payment preference", "Credit card: 76,795 transactions worth R$12,542,084.19"],
             ["Repeat customer rate", "3.00% (2,801 repeat customers of 93,358 total)"],
             ["Review distribution", "57.78% five-star, 11.51% one-star"],
             ["Delivery insight", "On-time deliveries average 4.21★ vs 2.55★ for late deliveries"],
         ]),

        ("h2", "4.2 Cross-engine validation"),
        ("p", "Hive and Spark were run independently on the same clean data. Initially the two engines disagreed on "
              "category and state revenue because Hive was summing price alone while Spark was summing price + freight_value "
              "over delivered orders. After fixing the Hive queries to use the same definition, the two engines agreed "
              "exactly on monthly GMV, category revenue and state revenue. This agreement is the strongest evidence that "
              "the numbers are correct rather than coincidental."),
        ("p", "The cross-validation exercise also revealed the importance of a clean landing layer. OpenCSVSerde does "
              "not honour skip.header.line.count, so header rows were leaking into counts until the /olist/clean layer "
              "was introduced. With the clean layer in place, row counts match the source files exactly."),

        ("h2", "4.3 Recommender"),
        ("p", "An ALS collaborative-filtering experiment was trained and evaluated during DA-2. The interaction matrix "
              "has 99,785 customer-product pairs across 93,358 customers, i.e. roughly 1.07 purchases per customer. With so "
              "few co-purchase signals, ALS underperformed a global-mean baseline (RMSE 0.9702 vs 0.9324 on the subset of "
              "customers with three or more items). The project reports this negative result honestly instead of hiding it."),
        ("p", "For DA-3 the ALS stage was replaced by a popularity + category-affinity baseline. The model recommends "
              "bestselling products from categories the customer has already purchased, falling back to global bestsellers "
              "for cold-start users. This approach is interpretable, handles cold start naturally and does not require "
              "dense interaction data."),
        ("p", "Leave-one-out evaluation was performed on customers with two or more purchases: one purchased item was "
              "held out, the customer's profile was rebuilt from the remaining items, and the recommender was asked to "
              "predict the held-out item in its top-10 list. The results are:"),
        ("table",
         ["Metric", "Value"],
         [
             ["Eligible customers", metrics.get("eligible_customers", "N/A")],
             ["HitRate@10", hit_rate],
             ["Precision@10", precision],
             ["Recall@10", recall],
             ["F1@10", metrics.get("f1@10", "N/A")],
         ]),
        ("p", "While absolute numbers are modest, they are meaningful for a dataset where 97% of customers never return. "
              "The model outperforms the ALS experiment on the same sparse data and provides a defensible baseline for "
              "the marketplace."),

        ("h1", "5. Dashboard"),
        ("p", "A Streamlit dashboard connects to MongoDB and provides six interactive views: Overview, Sales Trends, "
              "Categories &amp; Products, Geography, Delivery and Recommendations. The dashboard reads pre-computed "
              "aggregates from MongoDB so it loads quickly even though the underlying data was processed by the full "
              "Hadoop/Spark pipeline."),
        ("p", "The Overview page shows total orders, total GMV, top category and repeat-customer rate. Sales Trends "
              "plots monthly GMV and order volume. Categories &amp; Products shows top categories, review-vs-revenue scatter "
              "and top products. Geography visualises revenue and orders by state. Delivery shows average delivery days, "
              "late percentages and review score distribution. Recommendations displays model metrics and a customer lookup."),
        ("shot", overview_png),
        ("caption", "Fig. 1: Dashboard overview with KPIs, category revenue and payment distribution."),
        ("shot", sales_png),
        ("caption", "Fig. 2: Sales Trends view with monthly GMV and order volume."),
        ("shot", cat_png),
        ("caption", "Fig. 3: Categories &amp; Products view."),
        ("shot", geo_png),
        ("caption", "Fig. 4: Geographic distribution of revenue and orders by state."),
        ("shot", deliv_png),
        ("caption", "Fig. 5: Delivery performance and review score distribution."),
        ("shot", rec_png),
        ("caption", "Fig. 6: Recommendations view with model metrics and customer lookup."),

        ("h1", "6. Lessons Learned"),
        ("bullets", [
            "A clean landing layer is essential when source CSVs contain embedded newlines and inconsistent quoting.",
            "Cross-engine validation (Hive vs Spark) exposes subtle definition differences, such as whether freight is included in revenue.",
            "Honest reporting of negative results is better than hiding them; ALS's failure motivated the simpler, better baseline.",
            "JDK 21 strong encapsulation requires explicit --add-opens flags across Hadoop, Hive, Spark and MapReduce task JVMs.",
            "A document store is a natural fit for per-user recommendation lists and aggregate dashboards.",
            "Dashboard aggregates should be pre-computed and stored in the serving layer rather than computed at page load.",
            "Hadoop paths with spaces break URI parsing, so transfers must use relative paths or space-free staging directories.",
        ]),

        ("h1", "7. Conclusion and Future Scope"),
        ("p", "The project demonstrates a complete batch Big Data pipeline over real e-commerce data. All planned "
              "components from DA-1 were implemented, including the dashboard that was deferred to DA-3. The pipeline "
              "is reproducible from a single command (code/scripts/run_all.sh) and every number is traceable to a log file."),
        ("p", "Key outcomes include: (1) a working pseudo-distributed Hadoop/Hive/Spark/MongoDB stack on a laptop; "
              "(2) three MapReduce jobs with combiners and a streaming job; (3) a Hive warehouse with ten analytics queries; "
              "(4) Spark ETL and SQL that cross-validate the Hive results; (5) an evaluated popularity + category-affinity "
              "recommender; and (6) an interactive Streamlit dashboard served from MongoDB."),
        ("p", "Future extensions include:"),
        ("bullets", [
            "Spark Structured Streaming over the review stream to cover the data-streams module in real time.",
            "A more sophisticated recommender using category co-occurrence or content features when purchase history is sparse.",
            "Deployment of the dashboard to a container or cloud platform for live demo access.",
            "Synthetic scale-up of the dataset to test the pipeline at multi-gigabyte size.",
        ]),
    ]


def pdf_safe(text):
    import re
    parts = re.split(r"(&(?:amp|lt|gt|quot|apos|bull);)", text)
    return "".join(part if i % 2 else part.replace("&", "&amp;")
                   for i, part in enumerate(parts))


def plain(text):
    return (text.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&bull;", "*"))


# ---------------- DOCX renderer ----------------
def render_docx(blocks, path):
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    for s in ("Normal",):
        st = doc.styles[s]
        st.font.name = "Calibri"
        st.font.size = Pt(10.5)
    BLUE = RGBColor(0x1F, 0x3B, 0x63)

    def heading(text, size, before=10, after=4):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        r = p.add_run(plain(text))
        r.bold = True
        r.font.size = Pt(size)
        r.font.color.rgb = BLUE
        return p

    def rich(paragraph, text):
        import re
        for token in re.split(r"(<b>.*?</b>)", plain(text)):
            if token.startswith("<b>"):
                r = paragraph.add_run(token[3:-4])
                r.bold = True
            else:
                paragraph.add_run(token)

    for b in blocks:
        kind = b[0]
        if kind == "title":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(plain(b[1]))
            r.bold = True
            r.font.size = Pt(15)
            r.font.color.rgb = BLUE
        elif kind == "subtitle":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(plain(b[1]))
            r.bold = True
            r.font.size = Pt(11)
        elif kind == "meta":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(plain(b[1]))
            r.font.size = Pt(9.5)
            r.italic = True
        elif kind == "h1":
            heading(b[1], 13)
        elif kind == "h2":
            heading(b[1], 11.5, before=7, after=2)
        elif kind == "p":
            rich(doc.add_paragraph(), b[1])
        elif kind == "bullets":
            for it in b[1]:
                rich(doc.add_paragraph(style="List Bullet"), it)
        elif kind == "numbered":
            for it in b[1]:
                rich(doc.add_paragraph(style="List Number"), it)
        elif kind == "table":
            headers, rows = b[1], b[2]
            t = doc.add_table(rows=1 + len(rows), cols=len(headers))
            t.style = "Table Grid"
            for j, h in enumerate(headers):
                c = t.rows[0].cells[j]
                c.text = ""
                r = c.paragraphs[0].add_run(h)
                r.bold = True
                r.font.size = Pt(9)
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    c = t.rows[i + 1].cells[j]
                    c.text = ""
                    rich(c.paragraphs[0], val)
                    for run in c.paragraphs[0].runs:
                        run.font.size = Pt(9)
            doc.add_paragraph()
        elif kind in ("image", "shot"):
            if os.path.exists(b[1]):
                doc.add_picture(b[1], width=Inches(5.7 if kind == "image" else 6.2))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif kind == "caption":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(b[1])
            r.italic = True
            r.font.size = Pt(8.5)
    doc.save(path)


# ---------------- PDF renderer ----------------
def render_pdf(blocks, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Image, Table, TableStyle)
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    BLUE = HexColor("#1F3B63")
    st_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14,
                              leading=18, alignment=1, textColor=BLUE, spaceAfter=4)
    st_sub = ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=10,
                            leading=13, alignment=1, spaceAfter=2)
    st_meta = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=8.5,
                             leading=11, alignment=1, spaceAfter=2)
    st_h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=12,
                           leading=15, textColor=BLUE, spaceBefore=9, spaceAfter=4)
    st_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5,
                           leading=13, textColor=BLUE, spaceBefore=5, spaceAfter=2)
    st_body = ParagraphStyle("b", fontName="Helvetica", fontSize=9,
                             leading=12, spaceAfter=4)
    st_bul = ParagraphStyle("bl", parent=st_body, leftIndent=14, spaceAfter=2)
    st_cap = ParagraphStyle("c", fontName="Helvetica-Oblique", fontSize=8.5,
                            leading=11, alignment=1, spaceAfter=6)

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=16*mm,
                            rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm)
    avail_w = A4[0] - 32*mm
    story = []
    for b in blocks:
        kind = b[0]
        if kind == "title":
            story.append(Paragraph(pdf_safe(b[1]), st_title))
        elif kind == "subtitle":
            story.append(Paragraph(pdf_safe(b[1]), st_sub))
        elif kind == "meta":
            story.append(Paragraph(pdf_safe(b[1]), st_meta))
        elif kind == "h1":
            story.append(Paragraph(pdf_safe(b[1]), st_h1))
        elif kind == "h2":
            story.append(Paragraph(pdf_safe(b[1]), st_h2))
        elif kind == "p":
            story.append(Paragraph(pdf_safe(b[1]), st_body))
        elif kind == "bullets":
            for it in b[1]:
                story.append(Paragraph("&bull; " + pdf_safe(it), st_bul))
        elif kind == "numbered":
            for i, it in enumerate(b[1], 1):
                story.append(Paragraph("{0}. {1}".format(i, pdf_safe(it)), st_bul))
        elif kind == "table":
            headers, rows = b[1], b[2]
            ncol = len(headers)
            if ncol == 3:
                widths = [avail_w*0.22, avail_w*0.26, avail_w*0.52]
            elif ncol == 2:
                widths = [avail_w*0.35, avail_w*0.65]
            else:
                widths = [avail_w/float(ncol)] * ncol
            cell = ParagraphStyle("tc", fontName="Helvetica", fontSize=7.4, leading=9.2)
            cellb = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7.4, leading=9.2)
            data = [[Paragraph(pdf_safe(h), cellb) for h in headers]] + \
                   [[Paragraph(pdf_safe(v), cell) for v in row] for row in rows]
            t = Table(data, colWidths=widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#7F7F7F")),
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#DCE6F1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))
        elif kind in ("image", "shot"):
            path = b[1] if os.path.isabs(b[1]) else os.path.join(PROJECT, b[1])
            if os.path.exists(path):
                iw, ih = ImageReader(path).getSize()
                w = avail_w * (0.66 if kind == "image" else 0.95)
                story.append(Image(path, width=w,
                                   height=w * ih / float(iw), hAlign="CENTER"))
        elif kind == "caption":
            story.append(Paragraph(b[1], st_cap))
    doc.build(story)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    bl = blocks()
    docx_path = os.path.join(OUT, FILE_BASE + ".docx")
    pdf_path = os.path.join(OUT, FILE_BASE + ".pdf")
    render_docx(bl, docx_path)
    render_pdf(bl, pdf_path)
    print("wrote", docx_path)
    print("wrote", pdf_path)
