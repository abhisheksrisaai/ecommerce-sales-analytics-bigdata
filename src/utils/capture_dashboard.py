#!/usr/bin/env python3
"""Capture clean dashboard screenshots for the DA-3 report.

This script uses the `agent-browser` CLI to navigate every tab of the running
Streamlit dashboard, take full-page screenshots, crop the Streamlit chrome,
and save the results to `out/report/dashboard/`.

Prerequisites:
    - Streamlit dashboard is running on the configured port (default 8501).
    - `agent-browser` is installed and available on PATH.

Run:
    python3 -m src.utils.capture_dashboard

Dependencies:
    Pillow.
"""
import os
import subprocess
import sys
import time

from PIL import Image

# Allow imports from the project root when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import REPORT_DIR
from config.settings import DASHBOARD_PORT

OUT_DIR = os.path.join(REPORT_DIR, "dashboard")
DASHBOARD_URL = f"http://localhost:{DASHBOARD_PORT}"
TABS = [
    ("🏠 Overview", "overview"),
    ("📈 Sales Trends", "sales_trends"),
    ("🏷️ Categories & Products", "categories"),
    ("🗺️ Geography", "geography"),
    ("🚚 Delivery", "delivery"),
    ("🎯 Recommendations", "recommendations"),
]


def run(cmd, env=None, **kwargs):
    """Run a shell command, raising on failure.

    Parameters
    ----------
    cmd : str
        Shell command to execute.
    env : dict, optional
        Environment variables for the subprocess.
    **kwargs
        Passed to `subprocess.run`.

    Returns
    -------
    subprocess.CompletedProcess
    """
    return subprocess.run(cmd, shell=True, check=True, text=True, env=env, **kwargs)


def crop_and_save(src, dst):
    """Crop the full screenshot to remove Streamlit sidebar/top chrome.

    Parameters
    ----------
    src : str
        Path to the raw full-page screenshot.
    dst : str
        Path to write the cropped screenshot.
    """
    img = Image.open(src)
    w, h = img.size
    # Crop left sidebar (~260 px) and top banner (~70 px), keep main content.
    left = min(260, w // 5)
    top = 70
    right = w
    bottom = h
    cropped = img.crop((left, top, right, bottom))
    # Resize to a readable width if very large
    if cropped.width > 1280:
        ratio = 1280 / cropped.width
        cropped = cropped.resize((1280, int(cropped.height * ratio)), Image.Resampling.LANCZOS)
    cropped.save(dst, "PNG")
    os.remove(src)


def main():
    """Navigate the dashboard tabs and capture screenshots."""
    os.makedirs(OUT_DIR, exist_ok=True)
    session = "olist-dashboard-final"
    env = os.environ.copy()
    env["AGENT_BROWSER_SESSION"] = session

    # Open dashboard
    run(f'agent-browser open {DASHBOARD_URL}', env=env)
    run('agent-browser wait --text "Executive Summary"', env=env)
    time.sleep(2)

    for label, fname in TABS:
        print(f"Capturing {label} ...")
        run(f'agent-browser find text "{label}" click', env=env)
        heading_wait = {
            "overview": "Revenue by Category",
            "sales_trends": "Sales Trends",
            "categories": "Categories & Products",
            "geography": "Geography",
            "delivery": "Delivery Performance",
            "recommendations": "Product Recommendations",
        }[fname]
        run(f'agent-browser wait --text "{heading_wait}"', env=env)
        time.sleep(2)
        raw_path = os.path.join(OUT_DIR, f"{fname}_raw.png")
        run(f'agent-browser screenshot --full "{raw_path}"', env=env)
        time.sleep(1)
        crop_and_save(raw_path, os.path.join(OUT_DIR, f"{fname}.png"))

    run('agent-browser close', env=env)
    print("Done.")


if __name__ == "__main__":
    main()
