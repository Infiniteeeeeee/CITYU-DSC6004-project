"""English versions of the model-diagnostic figures that need predictions."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
PANEL = os.path.join(ROOT, "panel")
OUT = os.path.join(ROOT, "figures", "en")
os.makedirs(OUT, exist_ok=True)
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["font.size"] = 10
matplotlib.rcParams["axes.unicode_minus"] = False

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]

preds = {}
models = {}
for city in ["LOA", "MEL"]:
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"), parse_dates=["timestamp"])
    d = d.dropna(subset=FEATS + ["y"])
    tr = d[d.timestamp < "2023-08-31"]
    te = d[d.timestamp >= "2023-09-01"]
    y_cap = np.percentile(tr["y"], 99.9)
    model = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                          min_samples_leaf=40, random_state=0).fit(tr[FEATS].values, np.log1p(tr["y"].values))
    p = np.clip(np.expm1(model.predict(te[FEATS].values)), 0, y_cap)
    preds[city] = (te, p)
    models[city] = model
    print(city, "done")

# ---------- predicted vs actual ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, city in zip(axes, ["LOA", "MEL"]):
    te, p = preds[city]
    y = te["y"].values
    ax.hexbin(np.log1p(y), np.log1p(p), gridsize=60, bins="log", cmap="viridis")
    lim = [0, np.log1p(np.percentile(y, 99.5))]
    ax.plot(lim, lim, "r--", lw=1)
    ax.set_xlabel("Actual log1p(kWh)"); ax.set_ylabel("Predicted log1p(kWh)")
    ax.set_title(f"{city}: HGB, September test set")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_pred_vs_actual_en.png"), dpi=150); plt.close()

# ---------- WAPE by hour ----------
fig, ax = plt.subplots(figsize=(8, 4.2))
for city, ls in [("LOA", "-"), ("MEL", "--")]:
    te, p = preds[city]
    y = te["y"].values
    for name, pred, color in [("t-24", te["lag24"].values, "grey"), ("HGB", p, "#2b8cbe")]:
        tmp = pd.DataFrame({"hour": te["hour"].values, "y": y, "e": np.abs(y - pred)})
        g = tmp.groupby("hour").sum()
        ax.plot(g.index, g["e"] / g["y"], ls, color=color, lw=1.6, label=f"{city} {name}")
ax.set_xlabel("Hour of day"); ax.set_ylabel("WAPE")
ax.set_title("WAPE by hour (HGB vs t-24)")
ax.legend(fontsize=7, frameon=False, ncol=2)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_wape_hour_en.png"), dpi=150); plt.close()

# ---------- error by site size ----------
fig, ax = plt.subplots(figsize=(8, 4.2))
for city, color in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    te, p = preds[city]
    te2 = te.copy(); te2["pred"] = p
    size = te2.groupby("site_id")["y"].mean()
    dec = pd.qcut(size, 5, labels=False, duplicates="drop")
    te2["q"] = te2["site_id"].map(dec)
    xs, ys = [], []
    for q, s in te2.groupby("q"):
        xs.append(q + 1)
        ys.append(np.abs(s["y"] - s["pred"]).sum() / max(s["y"].sum(), 1e-9))
    ax.plot(xs, ys, marker="o", color=color, label=city)
ax.set_xlabel("Site-size quintile (1 = smallest, 5 = largest)")
ax.set_ylabel("WAPE")
ax.set_title("Error by site size")
ax.legend(frameon=False); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_error_size_en.png"), dpi=150); plt.close()

# ---------- partial dependence ----------
fig, axes = plt.subplots(2, 3, figsize=(12, 7.2))
for i, city in enumerate(["LOA", "MEL"]):
    te, _ = preds[city]
    Xte = te[FEATS].values
    s = np.random.default_rng(1).choice(len(Xte), size=min(20000, len(Xte)), replace=False)
    Xs = Xte[s].copy()
    for j, feat in enumerate(["lag24", "roll24_mean", "hour"]):
        ax = axes[i, j]
        idx = FEATS.index(feat)
        grid = np.quantile(Xs[:, idx], np.linspace(0.05, 0.95, 15))
        vals = []
        for v in grid:
            X2 = Xs.copy(); X2[:, idx] = v
            vals.append(float(np.expm1(models[city].predict(X2)).mean()))
        ax.plot(grid, vals, marker="o", color="#d7301f")
        ax.set_title(f"{city} - {feat}", fontsize=10)
        ax.set_ylabel("Mean prediction", fontsize=8)
        ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_pdp_en.png"), dpi=150); plt.close()
print("saved diagnostics")
