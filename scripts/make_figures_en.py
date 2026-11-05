"""English versions of the figures used in the short report (no CJK, checked for overlap)."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
FIG = os.path.join(ROOT, "figures", "en")
RES = os.path.join(ROOT, "results", "en")
DATA = os.path.join(ROOT, "data")
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["font.size"] = 10
matplotlib.rcParams["axes.unicode_minus"] = False

CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]
COL = {"LOA": "#2b8cbe", "MEL": "#d7301f"}

# ---------- 1. overview ----------
sm = pd.read_csv(os.path.join(ROOT, "figures", "city_summary.csv"))
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
ax = axes[0]
x = np.arange(len(sm))
ax.bar(x, sm["active_sites"], color="#2b8cbe", label="Active sites")
ax.bar(x, sm["sites"] - sm["active_sites"], bottom=sm["active_sites"], color="#bdbdbd", label="Zero-volume sites")
for i, r in sm.iterrows():
    ax.text(i, r["sites"] + 40, f"{r['zero_pct']:.0f}%", ha="center", fontsize=9, color="#d7301f")
ax.set_xticks(x); ax.set_xticklabels(sm["city"])
ax.set_ylabel("Number of sites"); ax.set_ylim(0, sm["sites"].max() * 1.18)
ax.set_title("Site composition (red: share of zero-volume sites)")
ax.legend(frameon=False)
ax = axes[1]
ax.bar(x, sm["chargers"], color="#41ab5d")
for i, v in enumerate(sm["chargers"]):
    ax.text(i, v + 40, str(v), ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(sm["city"])
ax.set_ylabel("Number of chargers"); ax.set_title("Chargers per city")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig1_overview_en.png"), dpi=150); plt.close()

# ---------- 2. hour-of-day heatmap ----------
prof = {}
for c in CITIES:
    v = pd.read_csv(os.path.join(DATA, c, "volume.csv"), index_col=0, parse_dates=True)
    h = v.groupby(v.index.hour).mean().mean(axis=1)
    prof[c] = (h / h.mean()).values
mat = np.array([prof[c] for c in CITIES])
fig, ax = plt.subplots(figsize=(11.5, 3.7))
im = ax.imshow(mat, aspect="auto", cmap="RdYlBu_r", vmin=0.5, vmax=1.5)
ax.set_yticks(range(len(CITIES))); ax.set_yticklabels(CITIES)
ax.set_xticks(range(24)); ax.set_xticklabels(range(24))
ax.set_xlabel("Hour of day")
ax.set_title("Normalised hour-of-day profile (1.0 = city mean)")
for i in range(len(CITIES)):
    for j in range(24):
        ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=6.5)
plt.colorbar(im, ax=ax, shrink=.9, label="ratio to mean")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig3_hour_heatmap_en.png"), dpi=150); plt.close()
print("heatmap done")

# ---------- 3. rolling CV WAPE ----------
cv = pd.read_csv(os.path.join(ROOT, "results", "rolling_cv.csv")).dropna(subset=["WAPE"])
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=False)
for ax, city in zip(axes, ["LOA", "MEL"]):
    sub = cv[cv.city == city]
    for model, color, marker in [("t-24", "grey", "o"), ("ridge", "#d7301f", "s"), ("hgb", "#2b8cbe", "^")]:
        s = sub[sub.model == model].sort_values("fold")
        label = {"t-24": "t-24 baseline", "ridge": "Ridge", "hgb": "HGB"}[model]
        ax.plot(s["fold"], s["WAPE"], marker=marker, color=color, label=label)
    ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["Jun", "Jul", "Aug", "Sep"])
    ax.set_xlabel("Test month"); ax.set_ylabel("WAPE"); ax.set_title(city)
    ax.grid(alpha=.25)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.93))
fig.suptitle("Rolling-origin validation: WAPE by test month", y=0.99)
plt.tight_layout(rect=(0, 0, 1, 0.86)); plt.savefig(os.path.join(FIG, "fig_cv_wape_en.png"), dpi=150); plt.close()

# ---------- 4. classification CV ----------
cls = pd.read_csv(os.path.join(ROOT, "results", "rolling_cv.csv"))
cls = cls[cls.model == "peak_hgb"]
fig, ax = plt.subplots(figsize=(7.8, 4.2))
for city in ["LOA", "MEL"]:
    s = cls[cls.city == city].sort_values("fold")
    ax.plot(s["fold"], s["PR_AUC"], marker="o", color=COL[city], label=f"{city} PR-AUC")
    ax.plot(s["fold"], s["Brier"] * 10, marker="x", ls="--", color=COL[city], label=f"{city} Brier x10")
ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["Jun", "Jul", "Aug", "Sep"])
ax.set_xlabel("Test month")
ax.set_title("Rolling-origin validation: peak classification")
ax.legend(fontsize=8, frameon=False, ncol=2); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_cv_class_en.png"), dpi=150); plt.close()

# ---------- 5. peak definitions ----------
pdef = pd.read_csv(os.path.join(ROOT, "results", "peak_definitions.csv"))
fig, ax = plt.subplots(figsize=(8.0, 4.2))
x = np.arange(len(pdef))
ax.bar(x - 0.2, pdef["event_rate_test"] * 100, width=0.4, color="#2b8cbe", label="Test event rate (%)")
ax.bar(x + 0.2, pdef["PR_AUC"], width=0.4, color="#d7301f", label="PR-AUC")
ax.set_xticks(x); ax.set_xticklabels(["mean + 2sd", "median x4", "train P95"])
ax.set_title("Sensitivity to the peak definition (LOA, September)")
ax.legend(frameon=False)
for i, v in enumerate(pdef["event_rate_test"] * 100):
    ax.text(i - 0.2, v + 0.3, f"{v:.1f}", ha="center", fontsize=8)
for i, v in enumerate(pdef["PR_AUC"]):
    ax.text(i + 0.2, v + 0.02, f"{v:.2f}", ha="center", fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_peak_defs_en.png"), dpi=150); plt.close()

# ---------- 6. model comparison ----------
cmp_df = pd.read_csv(os.path.join(ROOT, "results", "compare_lstm.csv"))
fig, ax = plt.subplots(figsize=(8.0, 4.2))
cities = ["LOA", "MEL"]
models = ["t-24", "Ridge", "HGB", "LSTM"]
colors = ["grey", "#d7301f", "#2b8cbe", "#31a354"]
x = np.arange(len(cities))
for i, (m, c) in enumerate(zip(models, colors)):
    vals = [cmp_df[(cmp_df.city == cc) & (cmp_df.model == m)]["WAPE"].iloc[0] for cc in cities]
    ax.bar(x + (i - 1.5) * 0.2, vals, width=0.2, color=c, label=m)
    for xi, v in zip(x + (i - 1.5) * 0.2, vals):
        ax.text(xi, v + 0.008, f"{v:.3f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(cities)
ax.set_ylabel("WAPE"); ax.set_title("Models on identical test rows (September)")
ax.set_ylim(0, 0.64)
ax.legend(frameon=False, ncol=4, fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_lstm_compare_en.png"), dpi=150); plt.close()

# ---------- 7. error by demand decile ----------
dec = pd.read_csv(os.path.join(ROOT, "results", "err_decile.csv"))
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, city in zip(axes, ["LOA", "MEL"]):
    s = dec[dec.city == city]
    x = s["decile"] + 1
    for m, c, ls in [("LSTM", "#31a354", "-"), ("Ridge", "#d7301f", "--"), ("HGB", "#2b8cbe", ":")]:
        ax.plot(x, s[f"wape_{m}"].clip(lower=1e-3), marker="o", color=c, ls=ls, label=m)
    ax.set_yscale("log"); ax.set_xlabel("Actual-demand decile (1 = lowest)")
    ax.set_ylabel("WAPE (log scale)"); ax.set_title(city)
    ax.legend(frameon=False); ax.grid(alpha=.25)
fig.suptitle("Error by demand level: the lowest decile dominates", y=0.99)
plt.tight_layout(rect=(0, 0, 1, 0.94)); plt.savefig(os.path.join(FIG, "fig_err_decile_en.png"), dpi=150); plt.close()

# ---------- 8. bootstrap ----------
boot = pd.read_csv(os.path.join(ROOT, "results", "err_bootstrap.csv"))
fig, ax = plt.subplots(figsize=(8.2, 4.3))
pos = 0
ticks, labels = [], []
for city in ["LOA", "MEL"]:
    s = boot[boot.city == city]
    for m, c in [("LSTM", "#31a354"), ("Ridge", "#d7301f"), ("HGB", "#2b8cbe")]:
        v = s[m].values
        lo, hi = np.percentile(v, 2.5), np.percentile(v, 97.5)
        ax.errorbar(pos, v.mean(), yerr=[[v.mean() - lo], [hi - v.mean()]], fmt="o", color=c, capsize=4)
        ticks.append(pos); labels.append(f"{city}\n{m}")
        pos += 1
    pos += 0.6
ax.set_xticks(ticks); ax.set_xticklabels(labels, fontsize=7.5)
ax.set_ylabel("WAPE (200 site-level bootstrap, 95% CI)")
ax.set_title("Model differences with bootstrap confidence intervals")
ax.set_xlim(-0.5, pos - 0.4)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_err_bootstrap_en.png"), dpi=150); plt.close()

# ---------- 9. residual ACF ----------
acf = pd.read_csv(os.path.join(ROOT, "results", "err_acf.csv"))
fig, ax = plt.subplots(figsize=(7.8, 4.2))
for city in ["LOA", "MEL"]:
    s = acf[acf.city == city]
    ax.plot(s["lag"], s["acf"], color=COL[city], label=city)
ax.axhline(0, color="k", lw=.8)
ax.set_xlabel("Lag (hours)"); ax.set_ylabel("ACF")
ax.set_title("Residual autocorrelation (LSTM)")
ax.legend(frameon=False); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_err_acf_en.png"), dpi=150); plt.close()

# ---------- 10. permutation importance ----------
imp = pd.read_csv(os.path.join(ROOT, "results", "importance.csv"))
name_map = {"lag1": "t-1 (last hour)", "lag24": "t-24 (yesterday)", "lag168": "t-168 (last week)",
            "roll24_mean": "24h rolling mean", "roll24_std": "24h rolling std",
            "roll168_mean": "7d rolling mean", "hour": "Hour of day", "dow": "Day of week",
            "doy": "Day of year", "charger_num": "Charger count", "area": "Site area",
            "poi_density": "POI density", "lon": "Longitude", "lat": "Latitude"}
fig, axes = plt.subplots(1, 2, figsize=(10, 5.2))
for ax, city in zip(axes, ["LOA", "MEL"]):
    s = imp[imp.city == city].sort_values("importance")
    ax.barh([name_map.get(f, f) for f in s.feature], s.importance, color="#2b8cbe")
    ax.set_title(f"{city}: permutation importance")
    ax.set_xlabel("Increase in MAE")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_importance_en.png"), dpi=150); plt.close()

print("saved to", FIG)
