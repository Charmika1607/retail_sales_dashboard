"""
backend.py - data loading, cleaning, analytics and the NEW features:
  1. Sales forecast (next 3 months, trend + seasonality)
  2. Anomaly detection (unusual months)
  3. Auto-generated business insights
"""
import pandas as pd
import numpy as np

CURRENCY = "$"

# Different Kaggle files name their columns differently; map them to one standard.
COLUMN_ALIASES = {
    "order_id": ["order id", "order_id", "orderid"],
    "order_date": ["order date", "order_date", "orderdate", "date"],
    "sales": ["sales", "revenue", "amount", "total"],
    "profit": ["profit"],
    "quantity": ["quantity", "qty"],
    "discount": ["discount"],
    "category": ["category"],
    "sub_category": ["sub-category", "sub_category", "subcategory"],
    "region": ["region"],
    "customer": ["customer name", "customer_name", "customer"],
    "product": ["product name", "product_name", "product"],
}


def load_csv(path):
    """Read a CSV, standardise column names, parse dates, drop bad rows."""
    df = None
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        raise ValueError("Could not read the file. Is it a valid CSV?")

    lookup = {c.strip().lower(): c for c in df.columns}
    rename = {}
    for std, names in COLUMN_ALIASES.items():
        for n in names:
            if n in lookup:
                rename[lookup[n]] = std
                break
    df = df.rename(columns=rename)

    missing = [c for c in ("order_date", "sales") if c not in df.columns]
    if missing:
        raise ValueError(f"CSV must contain Order Date and Sales columns. Missing: {missing}")

    # Date formats differ between datasets (dd/mm/yyyy vs mm/dd/yyyy):
    # try both and keep whichever parses more rows.
    a = pd.to_datetime(df["order_date"], dayfirst=True, errors="coerce")
    b = pd.to_datetime(df["order_date"], dayfirst=False, errors="coerce")
    df["order_date"] = a if a.notna().sum() > b.notna().sum() else b

    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    for c in ("profit", "quantity", "discount"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["order_date", "sales"]).sort_values("order_date")
    df["year"] = df["order_date"].dt.year
    if df.empty:
        raise ValueError("No valid rows after cleaning.")
    return df.reset_index(drop=True)


def filter_options(df):
    def opts(col):
        return ["All"] + sorted(df[col].dropna().astype(str).unique()) if col in df else ["All"]
    return {
        "year": ["All"] + [str(y) for y in sorted(df["year"].unique())],
        "region": opts("region"),
        "category": opts("category"),
    }


def apply_filters(df, year="All", region="All", category="All"):
    if year != "All":
        df = df[df["year"] == int(year)]
    if region != "All" and "region" in df:
        df = df[df["region"].astype(str) == region]
    if category != "All" and "category" in df:
        df = df[df["category"].astype(str) == category]
    return df


def kpis(df):
    if df.empty:
        return {"sales": 0, "profit": None, "orders": 0, "aov": 0, "growth": None}
    orders = df["order_id"].nunique() if "order_id" in df else len(df)
    m = monthly_sales(df)
    growth = None
    if len(m) >= 2 and m.iloc[-2] != 0:
        growth = (m.iloc[-1] - m.iloc[-2]) / m.iloc[-2] * 100
    return {
        "sales": df["sales"].sum(),
        "profit": df["profit"].sum() if "profit" in df else None,
        "orders": orders,
        "aov": df["sales"].sum() / orders if orders else 0,
        "growth": growth,
    }


def monthly_sales(df):
    if df.empty:
        return pd.Series(dtype=float)
    return df.set_index("order_date")["sales"].resample("MS").sum()


def group_sum(df, col, value="sales"):
    if col not in df or value not in df:
        return None
    return df.groupby(col)[value].sum().sort_values(ascending=False)


def top_n(df, col, n=10):
    return group_sum(df, col).head(n) if col in df else None


# ---------------------------------------------------------------- NEW FEATURES
def forecast(m, periods=3):
    """Linear trend (+ month-of-year seasonality when >= 24 months of data)."""
    if len(m) < 6:
        return None
    x = np.arange(len(m))
    slope, intercept = np.polyfit(x, m.values, 1)
    season = {}
    if len(m) >= 24:
        resid = pd.Series(m.values - (slope * x + intercept), index=m.index)
        season = resid.groupby(resid.index.month).mean().to_dict()
    idx = pd.date_range(m.index[-1] + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    vals = [max(0.0, slope * (len(m) + i) + intercept + season.get(d.month, 0))
            for i, d in enumerate(idx)]
    return pd.Series(vals, index=idx)


def anomalies(m, z=2.0):
    """Months whose sales sit more than z standard deviations from the trend line."""
    empty = m.iloc[0:0]
    if len(m) < 6:
        return empty
    x = np.arange(len(m))
    slope, intercept = np.polyfit(x, m.values, 1)
    resid = m.values - (slope * x + intercept)
    sd = resid.std()
    if sd == 0:
        return empty
    return m[np.abs(resid / sd) > z]


def insights(df):
    """Plain-English findings generated from the filtered data."""
    out = []
    if df.empty:
        return ["No data for the selected filters."]
    m = monthly_sales(df)
    f = lambda v: f"{CURRENCY}{v:,.0f}"

    out.append(f"Total sales: {f(df['sales'].sum())} across {len(m)} months.")
    if len(m):
        out.append(f"Best month: {m.idxmax():%B %Y} ({f(m.max())}). "
                   f"Weakest month: {m.idxmin():%B %Y} ({f(m.min())}).")
    if len(m) >= 6:
        slope = np.polyfit(np.arange(len(m)), m.values, 1)[0]
        trend = "growing" if slope > 0 else "declining"
        out.append(f"Overall trend is {trend}: about {f(abs(slope))} per month on average.")
    fc = forecast(m)
    if fc is not None:
        out.append("Forecast next 3 months: " +
                   ", ".join(f"{d:%b %Y} {f(v)}" for d, v in fc.items()) + ".")
    for col, label in (("category", "category"), ("region", "region")):
        g = group_sum(df, col)
        if g is not None and len(g):
            share = g.iloc[0] / g.sum() * 100
            out.append(f"Top {label}: {g.index[0]} with {share:.0f}% of sales.")
    if "profit" in df:
        sub = group_sum(df, "sub_category", "profit")
        if sub is not None and len(sub):
            out.append(f"Most profitable sub-category: {sub.index[0]} ({f(sub.iloc[0])}).")
            if sub.iloc[-1] < 0:
                out.append(f"WARNING: {sub.index[-1]} is making a loss ({f(sub.iloc[-1])}).")
        margin = df["profit"].sum() / df["sales"].sum() * 100
        out.append(f"Overall profit margin: {margin:.1f}%.")
    if "discount" in df and "profit" in df:
        hi = df[df["discount"] >= 0.3]
        if len(hi) and hi["profit"].sum() < 0:
            out.append(f"High-discount orders (30%+) lost {f(abs(hi['profit'].sum()))} in total "
                       "- consider limiting heavy discounts.")
    an = anomalies(m)
    if len(an):
        trend_line = np.polyval(np.polyfit(np.arange(len(m)), m.values, 1), np.arange(len(m)))
        for d, v in an.items():
            i = m.index.get_loc(d)
            kind = "spike" if v > trend_line[i] else "drop"
            out.append(f"Unusual {kind} detected in {d:%B %Y} ({f(v)}).")
    return out
