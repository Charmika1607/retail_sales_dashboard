"""Creates sample_sales.csv (Superstore-style) so you can test before downloading real data."""
import numpy as np, pandas as pd
rng = np.random.default_rng(7)
n = 4000
dates = pd.to_datetime("2022-01-01") + pd.to_timedelta(rng.integers(0, 4 * 365, n), unit="D")
cats = {"Technology": ["Phones", "Laptops"], "Furniture": ["Chairs", "Tables"],
        "Office Supplies": ["Paper", "Binders"]}
rows = []
for i, d in enumerate(dates):
    cat = rng.choice(list(cats))
    sub = rng.choice(cats[cat])
    sales = rng.gamma(2, 120) * (1.4 if d.month in (11, 12) else 1) * (1 + (d.year - 2022) * 0.12)
    disc = rng.choice([0, 0.1, 0.2, 0.4])
    rows.append(dict(**{"Order ID": f"CA-{i//2}", "Order Date": d.strftime("%d/%m/%Y"),
        "Region": rng.choice(["West", "East", "Central", "South"]), "Customer Name": f"Customer {rng.integers(1,60)}",
        "Category": cat, "Sub-Category": sub, "Product Name": f"{sub} Model {rng.integers(1,15)}",
        "Sales": round(sales, 2), "Quantity": int(rng.integers(1, 6)), "Discount": disc,
        "Profit": round(sales * (0.25 - disc * 0.9) + rng.normal(0, 5), 2)}))
pd.DataFrame(rows).to_csv("sample_sales.csv", index=False)
print("sample_sales.csv created")
