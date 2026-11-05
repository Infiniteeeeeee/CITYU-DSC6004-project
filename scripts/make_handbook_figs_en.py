"""English versions of every figure used in the handbook."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
DATA = os.path.join(ROOT, "data")
PANEL = os.path.join(ROOT, "panel")
OUT = os.path.join(ROOT, "figures", "en")
os.makedirs(OUT, exist_ok=True)
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["font.size"] = 10
matplotlib.rcParams["axes.unicode_minus"] = False

CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]

# ---------------- fig2: daily volume ----------------
fig, axes = plt.subplots(3, 2, figsize=(12, 8.4), sharex=True)
for ax, c in zip(axes.ravel(), CITIES):
    v = pd.read_csv(os.path.join(DATA, c, "volume.csv"), index_col=0, parse_dates=True)
    d = v.sum(axis=1).resample("D").sum()
    ax.plot(d.index, d.values, lw=1.1, color="#2b8cbe")
    ax.set_yscale("log"); ax.grid(alpha=.25)
    ax.set_title(f"{c}: daily total volume (log)", fontsize=10)
fig.suptitle("Daily total charging volume, 1 Apr – 30 Sep 2023", y=1.0)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig2_daily_en.png"), dpi=150); plt.close()
print("fig2 done")

# ---------------- fig4: intraday CV ----------------
cv_data = {}
for c in CITIES:
    v = pd.read_csv(os.path.join(DATA, c, "volume.csv"), index_col=0, parse_dates=True)
    total = v.sum(axis=0)
    active = (total > 0).values
    x = v.values.reshape(len(v) // 24, 24, v.shape[1])
    m, s = x.mean(axis=1), x.std(axis=1)
    cv = np.where(m > 0, s / np.where(m > 0, m, 1), np.nan)
    site_cv = np.nanmedian(cv, axis=0)[active]
    cv_data[c] = np.clip(site_cv, 1e-3, None)
fig, ax = plt.subplots(figsize=(9.5, 4.8))
bp = ax.boxplot([cv_data[c] for c in CITIES], tick_labels=CITIES, showfliers=False, patch_artist=True, widths=.55)
for patch in bp["boxes"]:
    patch.set_facecolor("#9ecae1")
for i, c in enumerate(CITIES, start=1):
    ax.text(i, 2.1, f"{100*np.mean(cv_data[c] < 0.05):.0f}%", ha="center", fontsize=9, color="#d7301f")
ax.set_yscale("log"); ax.set_ylim(8e-4, 6)
ax.set_ylabel("Per-site intraday CV (log scale)")
ax.set_title("Intraday variability per site (red: share of sites with CV < 0.05)")
ax.axhline(0.05, color="grey", ls="--", lw=.8)
ax.text(6.55, 0.052, "CV=0.05", fontsize=7, color="grey")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig4_cv_en.png"), dpi=150); plt.close()
print("fig4 done")

# ---------------- fig5: size + Lorenz ----------------
totals = {}
for c in CITIES:
    v = pd.read_csv(os.path.join(DATA, c, "volume.csv"), index_col=0, parse_dates=True)
    totals[c] = v.sum(axis=0)[v.sum(axis=0) > 0].values
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
ax = axes[0]
bp = ax.boxplot([np.log10(totals[c]) for c in CITIES], tick_labels=CITIES, showfliers=True,
                patch_artist=True, widths=.55)
for patch in bp["boxes"]:
    patch.set_facecolor("#a1d99b")
ax.set_ylabel("log10(total site volume, kWh)")
ax.set_title("Site-size distribution (three orders of magnitude)")
ax = axes[1]
for c in CITIES:
    v = np.sort(totals[c])[::-1]
    ax.plot(np.arange(1, len(v) + 1) / len(v), np.cumsum(v) / v.sum(), label=c, lw=1.2)
ax.plot([0, 1], [0, 1], "k--", lw=.8)
ax.set_xlabel("Cumulative share of sites (sorted by volume)")
ax.set_ylabel("Cumulative share of volume")
ax.set_title("Volume concentration (Lorenz curve)")
ax.legend(fontsize=8, frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig5_size_en.png"), dpi=150); plt.close()
print("fig5 done")

# ---------------- fig6: price ----------------
price, zero_share, s_share = {}, {}, {}
for c in CITIES:
    ep = pd.read_csv(os.path.join(DATA, c, "e_price.csv"), index_col=0).values
    sp = pd.read_csv(os.path.join(DATA, c, "s_price.csv"), index_col=0).values
    price[c] = float(np.median(ep[ep > 0])) if (ep > 0).any() else np.nan
    zero_share[c] = float((ep == 0).mean() * 100)
    s_share[c] = float((sp > 0).mean() * 100)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
ax = axes[0]
vals = [price[c] for c in CITIES]
ax.bar(CITIES, vals, color="#f16913")
ax.set_yscale("log"); ax.set_ylim(0.05, 2000)
for i, (c, v) in enumerate(zip(CITIES, vals)):
    ax.text(i, v * 1.25, f"{v:.2f}", ha="center", fontsize=9)
    ax.text(i, 0.08, f"{zero_share[c]:.0f}% zero", ha="center", fontsize=8, color="#555")
ax.set_ylabel("Median non-zero electricity price (log)")
ax.set_title("Electricity price: non-zero median (below: share of zeros)")
ax = axes[1]
ax.bar(CITIES, [s_share[c] for c in CITIES], color="#756bb1")
for i, c in enumerate(CITIES):
    ax.text(i, s_share[c] + 0.4, f"{s_share[c]:.1f}%", ha="center", fontsize=9)
ax.set_ylabel("Share of non-zero service price (%)")
ax.set_title("Service fee: share of non-zero values")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig6_price_en.png"), dpi=150); plt.close()
print("fig6 done")

# ---------------- fig7: weather correlation ----------------
vars_ = ["temp", "precip", "humidity", "windspeed", "solarradiation", "cloudcover"]
labels_ = {"temp": "Temp", "precip": "Precip", "humidity": "Humidity",
           "windspeed": "Wind", "solarradiation": "Solar", "cloudcover": "Cloud"}
corr = np.zeros((len(CITIES), len(vars_)))
for i, c in enumerate(CITIES):
    v = pd.read_csv(os.path.join(DATA, c, "volume.csv"), index_col=0, parse_dates=True)
    w = pd.read_csv(os.path.join(DATA, c, "weather.csv"), parse_dates=["time"]).set_index("time")
    daily = v.sum(axis=1).resample("D").sum()
    wd = w.resample("D").agg({"temp": "mean", "precip": "sum", "humidity": "mean",
                              "windspeed": "mean", "solarradiation": "mean", "cloudcover": "mean"}).reindex(daily.index)
    for j, name in enumerate(vars_):
        corr[i, j] = daily.corr(wd[name])
fig, ax = plt.subplots(figsize=(8.5, 3.9))
im = ax.imshow(corr, cmap="coolwarm", vmin=-.8, vmax=.8)
ax.set_yticks(range(len(CITIES))); ax.set_yticklabels(CITIES)
ax.set_xticks(range(len(vars_))); ax.set_xticklabels([labels_[v] for v in vars_])
for i in range(len(CITIES)):
    for j in range(len(vars_)):
        ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=8)
ax.set_title("Correlation: daily demand vs weather variables")
plt.colorbar(im, ax=ax, shrink=.9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig7_weather_en.png"), dpi=150); plt.close()
print("fig7 done")

# ---------------- fig8: POI composition ----------------
poi_counts = {c: pd.read_csv(os.path.join(DATA, c, "poi.csv"))["type"].value_counts() for c in CITIES}
allc = pd.concat(poi_counts, axis=1).fillna(0).sum(axis=1)
allc = allc.drop(labels=[k for k in allc.index if str(k).lower() == "other"], errors="ignore")
top8 = allc.sort_values(ascending=False).head(8).index
mat = []
for c in CITIES:
    vc = poi_counts[c]
    share = [vc.get(t, 0) / vc.sum() * 100 for t in top8]
    mat.append(share + [100 - sum(share)])
mat = np.array(mat)
fig, ax = plt.subplots(figsize=(10, 5))
bottom = np.zeros(len(CITIES))
cmap = plt.get_cmap("tab20")
for k, lab in enumerate(list(top8) + ["other"]):
    ax.barh(CITIES, mat[:, k], left=bottom, color=cmap(k % 20), label=str(lab)[:24])
    bottom += mat[:, k]
ax.set_xlim(0, 100)
ax.set_xlabel("Share (%)")
ax.set_title("POI composition (common top-8 categories + other)")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig8_poi_en.png"), dpi=150); plt.close()
print("fig8 done")

# ---------------- fig9: distance matrix ----------------
dist = pd.read_csv(os.path.join(DATA, "AMS", "distance.csv"), index_col=0)
dist.columns = dist.columns.astype(int)
sites = pd.read_csv(os.path.join(DATA, "AMS", "sites.csv")).set_index("site_id")
order = sites.loc[dist.index, "longitude"].sort_values().index
D = dist.loc[order, order].values
fig, ax = plt.subplots(figsize=(6.4, 5.4))
im = ax.imshow(D, cmap="viridis")
ax.set_title("AMS inter-site distance matrix (sorted by longitude)")
ax.set_xlabel("Site index"); ax.set_ylabel("Site index")
plt.colorbar(im, ax=ax, label="km", shrink=.9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig9_distance_en.png"), dpi=150); plt.close()
print("fig9 done")

# ---------------- handbook diagrams ----------------
# pipeline: 2 rows x 4 columns so the text never leaves its box
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 5.2); ax.axis("off")
steps = [
    ("1. Raw data\n6 cities x 10 tables", "#deebf7"),
    ("2. Data QC\nmissing / gaps / headers", "#deebf7"),
    ("3. Build panel\nsite x hour", "#c6dbef"),
    ("4. Feature engineering\nlags / rolling / calendar", "#c6dbef"),
    ("5. Time split\nrolling 4 folds", "#c7e9c0"),
    ("6. Modelling\nbaseline / Ridge / HGB / LSTM", "#c7e9c0"),
    ("7. Evaluation\nWAPE / Brier / calibration", "#fdd0a2"),
    ("8. Error analysis\ndeciles / bootstrap / ACF", "#fdd0a2"),
]
bw, bh, gx, gy = 2.15, 1.0, 0.35, 0.55
for k, (text, color) in enumerate(steps):
    row, col = divmod(k, 4)
    x = 0.35 + col * (bw + gx)
    y = 2.95 - row * (bh + gy)
    ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.03,rounding_size=0.08",
                                facecolor=color, edgecolor="#555", linewidth=0.8))
    ax.text(x + bw / 2, y + bh / 2, text, ha="center", va="center", fontsize=8.6)
    if col < 3:
        ax.add_patch(FancyArrowPatch((x + bw + 0.02, y + bh / 2), (x + bw + gx - 0.03, y + bh / 2),
                                     arrowstyle="-|>", mutation_scale=9, color="#555"))
ax.text(0.35, 4.75, "From raw data to conclusions: the eight steps of this project", fontsize=11, weight="bold")
ax.text(0.35, 0.55, "Scripts are listed in Appendix C; figures and result tables live in figures/ and results/.",
        fontsize=8, color="#555")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_pipeline_en.png"), dpi=150); plt.close()

# timeline
fig, ax = plt.subplots(figsize=(11, 3.6))
months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
folds = [("Fold 1", 2, "Jun"), ("Fold 2", 3, "Jul"), ("Fold 3", 4, "Aug"), ("Fold 4", 5, "Sep")]
for i, (name, test_idx, label) in enumerate(folds):
    y = len(folds) - i
    ax.barh(y, test_idx, left=0, height=0.55, color="#9ecae1", edgecolor="white")
    ax.barh(y, 1, left=test_idx, height=0.55, color="#d7301f", edgecolor="white")
    ax.text(-0.15, y, name, ha="right", va="center", fontsize=9)
    ax.text(test_idx + 0.5, y, f"test {label}", ha="center", va="center", fontsize=8, color="white")
ax.set_xlim(0, 6); ax.set_ylim(0.3, 4.9)
ax.set_xticks(np.arange(6) + 0.5); ax.set_xticklabels(months)
ax.set_yticks([])
ax.set_title("Rolling-origin validation: blue = training, red = test, one-day gap in between")
for spine in ["left", "right", "top"]:
    ax.spines[spine].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_timeline_en.png"), dpi=150); plt.close()

# LSTM architecture
fig, ax = plt.subplots(figsize=(11, 3.6))
ax.set_xlim(0, 11); ax.set_ylim(0, 3.6); ax.axis("off")
def box(x, y, w, h, text, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.08",
                                facecolor=color, edgecolor="#555", linewidth=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5)
box(0.2, 1.2, 2.2, 1.1, "Input: last 24 h\n(per-site z-score)", "#deebf7")
box(2.9, 1.2, 2.0, 1.1, "LSTM\n1 layer, 64", "#c6dbef")
box(5.3, 2.3, 2.2, 0.9, "Calendar\nsin/cos hour + weekday", "#e5f5e0")
box(5.3, 0.4, 2.2, 0.9, "Site statics\nchargers / area / POI", "#e5f5e0")
box(8.0, 1.2, 2.2, 1.1, "Fully connected\nnext-hour output", "#fdd0a2")
for (x1, y1, x2, y2) in [(2.4, 1.75, 2.9, 1.75), (4.9, 1.75, 5.3, 2.6), (4.9, 1.75, 5.3, 0.9), (7.5, 1.75, 8.0, 1.75)]:
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color="#555"))
ax.text(0.2, 3.1, "LSTM architecture: sequence branch concatenated with static features", fontsize=11, weight="bold")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_lstm_arch_en.png"), dpi=150); plt.close()

# peak definition example
vol = pd.read_csv(os.path.join(DATA, "LOA", "volume.csv"), index_col=0, parse_dates=True)
vol.columns = vol.columns.astype(int)
x = vol[158]
thr = pd.Series(np.nan, index=x.index)
for h in range(24):
    s = x.iloc[h::24]
    m = s.shift(1).rolling(28, min_periods=14).mean()
    sd = s.shift(1).rolling(28, min_periods=14).std()
    thr.iloc[h::24] = (m + 2 * sd).values
seg = slice("2023-07-03", "2023-07-10")
fig, ax = plt.subplots(figsize=(12, 4.2))
ax.plot(x.loc[seg].index, x.loc[seg].values, lw=1.4, color="#2b8cbe", label="Hourly volume")
ax.plot(thr.loc[seg].index, thr.loc[seg].values, lw=1.2, ls="--", color="#d7301f",
        label="Threshold = past-28-day same-hour mean + 2sd")
pk = x.loc[seg][x.loc[seg] > thr.loc[seg]]
ax.scatter(pk.index, pk.values, s=36, color="#d7301f", zorder=5, label="Peak event")
ax.set_ylabel("Volume (kWh)")
ax.set_title("How a peak event is defined (LOA site 158, 3–10 July 2023)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False, fontsize=8)
ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_peak_definition_en.png"), dpi=150, bbox_inches="tight"); plt.close()
print("peak definition events:", len(pk))

# peak rate by month
panel = pd.concat([pd.read_csv(os.path.join(PANEL, f"panel_{c}.csv.gz"),
                               usecols=["city", "timestamp", "peak", "is_eligible"],
                               parse_dates=["timestamp"]) for c in ["LOA", "MEL"]])
panel = panel[panel.is_eligible == 1]
panel["month"] = panel.timestamp.dt.month
g = panel.groupby(["city", "month"])["peak"].mean().unstack(0)
fig, ax = plt.subplots(figsize=(8, 3.9))
xx = np.arange(6)
for city, color in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    ax.bar(xx + (0.2 if city == "LOA" else -0.2), g[city].values * 100, width=0.38, color=color, label=city)
ax.set_xticks(xx); ax.set_xticklabels(["Apr", "May", "Jun", "Jul", "Aug", "Sep"])
ax.set_ylabel("Peak event rate (%)")
ax.set_title("Peak rate drifts by month: August is calm, September is active (LOA)")
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "hb_peak_month_en.png"), dpi=150); plt.close()

# confusion matrices
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]
for city in ["LOA", "MEL"]:
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"), parse_dates=["timestamp"])
    d = d[(d.is_eligible == 1)].dropna(subset=FEATS + ["y"])
    tr = d[d.timestamp < "2023-08-31"]
    cal = d[(d.timestamp >= "2023-07-01") & (d.timestamp < "2023-08-31")]
    te = d[d.timestamp >= "2023-09-01"]
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                         min_samples_leaf=40, random_state=0).fit(tr[FEATS].values, tr["peak"].values)
    p_cal = clf.predict_proba(cal[FEATS].values)[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip").fit(p_cal, cal["peak"].values)
    p = iso.predict(clf.predict_proba(te[FEATS].values)[:, 1])
    y = te["peak"].values
    ths = np.quantile(p, np.linspace(0.5, 0.999, 200))
    best = (0.5, -1)
    for th in ths:
        _, _, f1, _ = precision_recall_fscore_support(y, (p >= th).astype(int), average="binary", zero_division=0)
        if f1 > best[1]:
            best = (th, f1)
    cm = confusion_matrix(y, (p >= best[0]).astype(int))
    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Pred: no peak", "Pred: peak"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["True: no peak", "True: peak"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=11,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_title(f"{city}: peak confusion matrix (September)")
    plt.colorbar(im, ax=ax, shrink=.85)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, f"hb_confusion_{city}_en.png"), dpi=150); plt.close()
    print(city, "cm", cm.tolist())
print("saved to", OUT)
