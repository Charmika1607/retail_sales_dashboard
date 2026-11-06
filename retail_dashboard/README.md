# Retail Sales Dashboard (Python + Pandas + Matplotlib + Tkinter)

## Setup
    pip install pandas matplotlib numpy
    python make_sample_data.py     # optional: creates sample_sales.csv for testing
    python main.py                 # click "Load CSV" and pick your dataset

## Files
- backend.py  : CSV loading/cleaning, filters, KPIs, forecast, anomaly detection, insights
- charts.py   : all matplotlib charts
- main.py     : Tkinter UI (filters, KPI cards, tabs, PDF export)

## New features (not in a basic CSV + matplotlib dashboard)
1. 3-month sales forecast (trend + seasonality)
2. Anomaly detection (unusual spike/drop months highlighted)
3. Auto-generated business insights in plain English
4. Interactive Year / Region / Category filters
5. One-click multi-page PDF report export
6. Smart CSV loader (auto-maps column names and date formats)
