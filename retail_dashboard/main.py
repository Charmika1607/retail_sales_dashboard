"""main.py - Tkinter dashboard UI. Run:  python main.py"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages

import backend as bk
import charts

BG, CARD, DARK = "#f1f5f9", "#ffffff", "#1e293b"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Retail Sales Dashboard")
        self.geometry("1180x740")
        self.configure(bg=BG)
        self.data = None
        self.view = None
        self._styles()
        self._toolbar()
        self._kpi_row()
        self._tabs()
        self.status = tk.StringVar(value="Load a CSV file to begin.")
        tk.Label(self, textvariable=self.status, anchor="w", bg=DARK, fg="white",
                 padx=10).pack(fill="x", side="bottom")

    # ------------------------------------------------------------- layout
    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook.Tab", padding=(16, 6), font=("Segoe UI", 10, "bold"))
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _toolbar(self):
        bar = tk.Frame(self, bg=DARK, pady=8, padx=10)
        bar.pack(fill="x")
        tk.Label(bar, text="Retail Sales Dashboard", bg=DARK, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=(0, 20))
        ttk.Button(bar, text="Load CSV", command=self.load_file,
                   style="Accent.TButton").pack(side="left", padx=4)
        self.filters = {}
        for name in ("Year", "Region", "Category"):
            tk.Label(bar, text=name, bg=DARK, fg="white").pack(side="left", padx=(14, 3))
            cb = ttk.Combobox(bar, values=["All"], state="readonly", width=12)
            cb.set("All")
            cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
            cb.pack(side="left")
            self.filters[name.lower()] = cb
        ttk.Button(bar, text="Reset", command=self.reset).pack(side="left", padx=10)
        ttk.Button(bar, text="Export PDF Report", command=self.export_pdf,
                   style="Accent.TButton").pack(side="right")

    def _kpi_row(self):
        row = tk.Frame(self, bg=BG, pady=10, padx=10)
        row.pack(fill="x")
        self.kpi = {}
        for key, title in (("sales", "Total Sales"), ("profit", "Total Profit"),
                           ("orders", "Orders"), ("aov", "Avg Order Value"),
                           ("growth", "Last Month Growth")):
            card = tk.Frame(row, bg=CARD, padx=14, pady=8, highlightthickness=1,
                            highlightbackground="#e2e8f0")
            card.pack(side="left", expand=True, fill="x", padx=5)
            tk.Label(card, text=title, bg=CARD, fg="#64748b", font=("Segoe UI", 9)).pack(anchor="w")
            lbl = tk.Label(card, text="-", bg=CARD, fg=DARK, font=("Segoe UI", 16, "bold"))
            lbl.pack(anchor="w")
            self.kpi[key] = lbl

    def _tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.canvases = []
        for title, fn in (("Trend & Forecast", charts.trend_chart),
                          ("Category & Region", charts.mix_chart),
                          ("Top Performers", charts.top_chart)):
            frame = tk.Frame(nb, bg=CARD)
            nb.add(frame, text=title)
            fig = Figure(figsize=(9, 5), dpi=100)
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.canvases.append((fig, canvas, fn))
        frame = tk.Frame(nb, bg=CARD)
        nb.add(frame, text="Insights")
        self.text = tk.Text(frame, wrap="word", font=("Segoe UI", 11), bg=CARD,
                            relief="flat", padx=20, pady=15)
        self.text.pack(fill="both", expand=True)

    # ------------------------------------------------------------ actions
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            self.data = bk.load_csv(path)
        except Exception as e:
            messagebox.showerror("Could not load file", str(e))
            return
        for key, values in bk.filter_options(self.data).items():
            self.filters[key]["values"] = values
            self.filters[key].set("All")
        self.status.set(f"Loaded {len(self.data):,} rows from {path.split('/')[-1]}")
        self.refresh()

    def reset(self):
        for cb in self.filters.values():
            cb.set("All")
        if self.data is not None:
            self.refresh()

    def refresh(self):
        if self.data is None:
            return
        self.view = bk.apply_filters(self.data, **{k: cb.get() for k, cb in self.filters.items()})
        k = bk.kpis(self.view)
        c = bk.CURRENCY
        self.kpi["sales"].config(text=f"{c}{k['sales']:,.0f}")
        self.kpi["profit"].config(text="n/a" if k["profit"] is None else f"{c}{k['profit']:,.0f}")
        self.kpi["orders"].config(text=f"{k['orders']:,}")
        self.kpi["aov"].config(text=f"{c}{k['aov']:,.0f}")
        g = k["growth"]
        self.kpi["growth"].config(text="n/a" if g is None else f"{g:+.1f}%",
                                  fg=DARK if g is None else ("#16a34a" if g >= 0 else "#dc2626"))
        for fig, canvas, fn in self.canvases:
            fn(fig, self.view)
            canvas.draw_idle()
        self.text.delete("1.0", "end")
        for line in bk.insights(self.view):
            self.text.insert("end", "•  " + line + "\n\n")
        self.status.set(f"Showing {len(self.view):,} of {len(self.data):,} rows")

    def export_pdf(self):
        if self.view is None or self.view.empty:
            messagebox.showinfo("Nothing to export", "Load data first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        with PdfPages(path) as pdf:
            for fn in (charts.trend_chart, charts.mix_chart, charts.top_chart):
                fig = Figure(figsize=(11, 7))
                fn(fig, self.view)
                pdf.savefig(fig)
            fig = Figure(figsize=(8.5, 11))
            charts.insights_page(fig, bk.insights(self.view))
            pdf.savefig(fig)
        messagebox.showinfo("Done", f"Report saved to:\n{path}")


if __name__ == "__main__":
    App().mainloop()
