#!/usr/bin/env python3
"""Generate architecture and workflow figures for the DA-3 report using PIL.

This script produces two PNG files used by the report generator:
- `out/report/fig1_architecture.png`: end-to-end pipeline diagram.
- `out/report/fig3_workflow.png`: DA-1 / DA-2 / DA-3 timeline.

Run:
    python3 -m src.utils.gen_figures

Dependencies:
    Pillow.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# Allow imports from the project root when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import REPORT_DIR

OUT = REPORT_DIR

BLUE = "#1F3B63"
LIGHT_BLUE = "#4A90E2"
GREEN = "#2E8B57"
ORANGE = "#D2691E"
GRAY = "#777777"
BG = "#FAFAFA"


def get_fonts():
    # Try common system fonts; fall back to default
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.dfont",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    font_path = None
    for c in candidates:
        if os.path.exists(c):
            font_path = c
            break
    if font_path is None:
        return ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()
    return (ImageFont.truetype(font_path, 16),
            ImageFont.truetype(font_path, 13),
            ImageFont.truetype(font_path, 11))


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_rounded_box(draw, xy, fill, outline="black", width=2, radius=12):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_centered_text(draw, text, x, y, font, fill="white"):
    w, h = text_size(draw, text, font)
    draw.text((x - w/2, y - h/2), text, font=font, fill=fill)


def draw_arrow(draw, x1, y1, x2, y2):
    draw.line([(x1, y1), (x2, y2)], fill="black", width=2)
    # arrowhead
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    arr_len = 8
    arr_ang = math.pi / 6
    ax1 = x2 - arr_len * math.cos(angle - arr_ang)
    ay1 = y2 - arr_len * math.sin(angle - arr_ang)
    ax2 = x2 - arr_len * math.cos(angle + arr_ang)
    ay2 = y2 - arr_len * math.sin(angle + arr_ang)
    draw.polygon([(x2, y2), (ax1, ay1), (ax2, ay2)], fill="black")


def gen_architecture():
    W, H = 1000, 600
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f, box_f, note_f = get_fonts()

    draw_centered_text(draw, "DA-3 End-to-End Batch Pipeline Architecture", W/2, 30, title_f, BLUE)

    # Source
    draw_rounded_box(draw, (80, 70, 280, 135), GRAY)
    draw_centered_text(draw, "9 Olist CSVs", 180, 95, box_f)
    draw_centered_text(draw, "(~1.55 M rows)", 180, 115, note_f)
    draw_arrow(draw, 180, 135, 180, 165)

    # HDFS raw
    draw_rounded_box(draw, (80, 165, 280, 230), LIGHT_BLUE)
    draw_centered_text(draw, "HDFS /olist/raw", 180, 190, box_f)
    draw_centered_text(draw, "(immutable)", 180, 210, note_f)
    draw_arrow(draw, 280, 197, 360, 197)

    # HDFS clean
    draw_rounded_box(draw, (360, 165, 620, 230), LIGHT_BLUE)
    draw_centered_text(draw, "HDFS /olist/clean", 490, 190, box_f)
    draw_centered_text(draw, "(headers, newlines fixed)", 490, 210, note_f)

    # Processing engines row
    engines = [
        (100, 280, "MapReduce\n3 jobs", BLUE),
        (300, 280, "Hive\nwarehouse", BLUE),
        (500, 280, "Spark\nETL / SQL", BLUE),
        (700, 280, "Portuguese NLP\nsentiment", BLUE),
    ]
    for x, y, text, color in engines:
        draw_rounded_box(draw, (x, y, x+170, y+85), color)
        lines = text.split("\n")
        off = -((len(lines)-1) * 12) / 2
        for i, ln in enumerate(lines):
            draw_centered_text(draw, ln, x+85, y+35+off+i*22, box_f)

    # arrows from clean to first three engines
    for x in [185, 385, 585]:
        draw_arrow(draw, x, 230, x, 280)
    # arrow from clean/reviews to NLP
    draw_arrow(draw, 585, 230, 785, 280)

    # Recommender
    draw_rounded_box(draw, (560, 405, 800, 470), GREEN)
    draw_centered_text(draw, "Recommender", 680, 428, box_f)
    draw_centered_text(draw, "Baseline + NLP-aware", 680, 450, note_f)
    draw_arrow(draw, 585, 365, 620, 405)
    draw_arrow(draw, 785, 365, 750, 405)

    # MongoDB
    draw_rounded_box(draw, (560, 500, 800, 555), ORANGE)
    draw_centered_text(draw, "MongoDB serving layer", 680, 527, box_f)
    draw_arrow(draw, 680, 470, 680, 500)

    # Dashboard
    draw_rounded_box(draw, (850, 500, 980, 555), ORANGE)
    draw_centered_text(draw, "Streamlit", 915, 520, box_f)
    draw_centered_text(draw, "Dashboard", 915, 538, note_f)
    draw_arrow(draw, 800, 527, 850, 527)

    # Stack note
    draw.text((40, 570), "Stack: Hadoop 3.5.0 · Hive 4.2.1 · Spark 4.2.0 · MongoDB 8.3.11 · OpenJDK 21 · Streamlit 1.50.0",
              font=note_f, fill=GRAY)

    path = os.path.join(OUT, "fig1_architecture.png")
    img.save(path, "PNG")
    print("wrote", path)


def gen_workflow():
    W, H = 1000, 450
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f, box_f, note_f = get_fonts()

    draw_centered_text(draw, "DA-1 / DA-2 / DA-3 Project Timeline", W/2, 30, title_f, BLUE)

    # timeline arrow
    draw.line([(60, 180), (940, 180)], fill="black", width=3)
    # arrowhead
    draw.polygon([(940, 180), (925, 172), (925, 188)], fill="black")

    phases = [
        ("Phase 1\nEnvironment &\nHDFS ingestion", 130, BLUE),
        ("Phase 2\nMapReduce\ncleaning & jobs", 290, BLUE),
        ("Phase 3\nHive\nwarehouse", 450, BLUE),
        ("Phase 4\nSpark ETL\n& SQL", 610, BLUE),
        ("Phase 5\nMongoDB\nserving layer", 770, BLUE),
        ("Phase 6\nDA-3: NLP,\ndashboard &\ndeliverables", 930, GREEN),
    ]
    for text, x, color in phases:
        draw_rounded_box(draw, (x-70, 100, x+70, 160), color)
        lines = text.split("\n")
        off = -((len(lines)-1) * 11) / 2
        for i, ln in enumerate(lines):
            draw_centered_text(draw, ln, x, 122+off+i*18, note_f)
        # connector to timeline
        draw.line([(x, 160), (x, 180)], fill="black", width=2)

    # DA labels
    labels = [
        ("DA-1\ncompleted", 210, 260),
        ("DA-2\ncompleted", 530, 260),
        ("DA-3\ncompleted", 850, 260),
    ]
    for text, x, y in labels:
        lines = text.split("\n")
        off = -((len(lines)-1) * 12) / 2
        for i, ln in enumerate(lines):
            draw_centered_text(draw, ln, x, y+off+i*18, box_f, GREEN)

    draw_centered_text(draw, "All deliverables generated: report, presentation, dashboard screenshots, tests, MongoDB serving layer.",
                       W/2, 360, note_f, GRAY)

    path = os.path.join(OUT, "fig3_workflow.png")
    img.save(path, "PNG")
    print("wrote", path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    gen_architecture()
    gen_workflow()
