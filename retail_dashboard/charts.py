"""charts.py - all matplotlib drawing lives here (used by the UI and the PDF export)."""
import textwrap
import backend as bk

BLUE, ORANGE, RED, GREEN, GREY = "#2563eb", "#f59e0b", "#dc2626", "#16a34a", "#6b7280"
C = bk.CURRENCY


def _empty(fig, msg="No data available"):
    fig.clear()
    fig.add_subplot(111).text(0.5, 0.5, msg, ha="center", va="center", color=GREY)
    fig.axes[0].axis("off")


def _money(ax, axis="y"):
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: f"{C}{v/1000:,.0f}k" if abs(v) >= 1000 else f"{C}{v:,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def trend_chart(fig, df):
    m = bk.monthly_sales(df)
    if m.empty:
        return _empty(fig)
    fig.clear()
    ax = fig.add_subplot(111)
    ax.plot(m.index, m.values, marker="o", ms=4, color=BLUE, label="Actual sales")
    fc = bk.forecast(m)
    if fc is not None:
        ax.plot([m.index[-1], *fc.index], [m.iloc[-1], *fc.values],
                "--", marker="o", ms=4, color=ORANGE, label="Forecast (3 months)")
    an = bk.anomalies(m)
    if len(an):
        ax.scatter(an.index, an.values, s=110, facecolors="none",
                   edgecolors=RED, linewidths=2, zorder=5, label="Unusual month")
    ax.set_title("Monthly Sales Trend, Forecast & Anomalies", fontweight="bold")
    ax.grid(alpha=0.25)
    ax.legend()
    _money(ax)
    fig.autofmt_xdate()
    fig.tight_layout()


def mix_chart(fig, df):
    if df.empty:
        return _empty(fig)
    fig.clear()
    cat = bk.group_sum(df, "category")
    reg = bk.group_sum(df, "region")
    if cat is None and reg is None:
        return _empty(fig, "CSV has no Category / Region columns")
    ax1 = fig.add_subplot(121)
    if cat is not None:
        x = range(len(cat))
        if "profit" in df:
            prof = bk.group_sum(df, "category", "profit").reindex(cat.index)
            ax1.bar([i - 0.2 for i in x], cat.values, 0.4, color=BLUE, label="Sales")
            ax1.bar([i + 0.2 for i in x], prof.values, 0.4, color=GREEN, label="Profit")
            ax1.legend()
        else:
            ax1.bar(x, cat.values, color=BLUE)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(cat.index)
        ax1.set_title("Sales by Category", fontweight="bold")
        _money(ax1)
    ax2 = fig.add_subplot(122)
    if reg is not None:
        ax2.pie(reg.values, labels=reg.index, autopct="%1.0f%%", startangle=90,
                colors=[BLUE, ORANGE, GREEN, RED, GREY][:len(reg)])
        ax2.set_title("Sales Share by Region", fontweight="bold")
    fig.tight_layout()


def top_chart(fig, df):
    if df.empty:
        return _empty(fig)
    prod, cust = bk.top_n(df, "product", 8), bk.top_n(df, "customer", 8)
    if prod is None and cust is None:
        return _empty(fig, "CSV has no Product / Customer columns")
    fig.clear()
    for pos, data, title, color in ((211, prod, "Top 8 Products", BLUE),
                                    (212, cust, "Top 8 Customers", ORANGE)):
        if data is None:
            continue
        ax = fig.add_subplot(pos)
        labels = [textwrap.shorten(str(s), 38) for s in data.index][::-1]
        ax.barh(labels, data.values[::-1], color=color)
        ax.set_title(title, fontweight="bold")
        ax.tick_params(axis="y", labelsize=8)
        _money(ax, "x")
    fig.tight_layout()


def insights_page(fig, lines):
    fig.clear()
    fig.text(0.06, 0.94, "Business Insights", fontsize=16, fontweight="bold")
    y = 0.88
    for line in lines:
        wrapped = textwrap.fill("- " + line, 95)
        fig.text(0.06, y, wrapped, fontsize=10, va="top")
        y -= 0.045 * (wrapped.count("\n") + 1) + 0.01
