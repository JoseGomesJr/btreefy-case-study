# Documentation & Evaluation Report

This folder contains the written evaluation reports comparing the Behavior Tree (BTreeFy) approach against the Finite State Machine (FSM) implementation.

- `evaluation_report.md` (English)
- `evaluation_report_pt.md` (Portuguese)

These documents reference the charts and tables generated automatically in the `results/` folder by the metrics scripts.

## How to generate or update the report

### 1. Update the Metrics (Tables & Charts)
If you made changes to the code (e.g. modified the FSM architecture, or the BT trees), you first need to re-run the evaluation metrics to update the raw data (`.csv` files) and the plots (`.png` files).

Run the following script from the root of the test project:

```bash
cd tools/metrics
uv run python3 run_all.py
```
*(Note: If you only want to update the code metrics and skip the slow footprint build, you can run `uv run python3 run_all.py --skip-footprint`)*

This script will automatically regenerate:
- `results/report_table.png`
- `results/report_chart.png`

### 2. Export the Markdown to PDF
The evaluation report itself is a Markdown document that embeds the generated PNGs. 
If you want to export `evaluation_report_pt.md` to a beautifully formatted PDF (for example, to include in an academic paper submission or attachment), you can use any standard markdown-to-pdf converter. 

A quick and reliable way using Node.js (`npx`) is:

```bash
# In the docs/ folder:
npx md-to-pdf evaluation_report_pt.md
```

This will instantly generate `evaluation_report_pt.pdf` in the same directory, maintaining all formatting, tables, and images. Alternatively, if you use VS Code, the "Markdown PDF" extension is highly recommended for exporting.
