"""Interpretability: permutation importance, partial dependence, error decomposition."""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
OUT = os.path.join(ROOT, "results"); os.makedirs(OUT, exist_ok=True)
PANEL = os.path.join(ROOT, "panel")

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]
FEAT_ZH = {"lag1": "前1小时", "lag24": "昨日同时刻", "lag168": "上周同时刻",
           "roll24_mean": "近24h均值", "roll24_std": "近24h波动", "roll168_mean": "近7天均值",
           "hour": "小时", "dow": "星期", "doy": "年内日序", "charger_num": "桩数",
           "area": "站点面积", "poi_density": "POI密度", "lon": "经度", "lat": "纬度"}
LAB = (lambda k: FEAT_ZH.get(k, k)) if CJK else (lambda k: k)

def load(city):
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"),
                    usecols=["timestamp", "site_id", "y"] + FEATS, parse_dates=["timestamp"])
    return d.dropna(subset=FEATS + ["y"])

imp_rows, pdp_rows, err_rows = [], [], []
for city in ["LOA", "MEL"]:
    d = load(city)
    tr = d[d.timestamp < "2023-08-31"]
    te = d[d.timestamp >= "2023-09-01"]
    y_cap = np.percentile(tr["y"], 99.9)
    model = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                          min_samples_leaf=40, random_state=0).fit(tr[FEATS].values, np.log1p(tr["y"].values))
    Xte = te[FEATS].values
    yte = te["y"].values
    pred = np.clip(np.expm1(model.predict(Xte)), 0, y_cap)

    idx = np.random.default_rng(0).choice(len(Xte), size=min(30_000, len(Xte)), replace=False)
    pi = permutation_importance(model, Xte[idx], np.log1p(yte[idx]), n_repeats=3,
                                random_state=0, scoring="neg_mean_absolute_error")
    for k, v in zip(FEATS, pi.importances_mean):
        imp_rows.append(dict(city=city, feature=k, importance=v))

    # partial dependence on a 20k sample
    s = np.random.default_rng(1).choice(len(Xte), size=min(20_000, len(Xte)), replace=False)
    Xs = Xte[s].copy()
    for feat in ["lag24", "roll24_mean", "hour"]:
        j = FEATS.index(feat)
        grid = np.quantile(Xs[:, j], np.linspace(0.05, 0.95, 15))
        for v in grid:
            X2 = Xs.copy(); X2[:, j] = v
            pdp_rows.append(dict(city=city, feature=feat, value=float(v),
                                 pred=float(np.expm1(model.predict(X2)).mean())))

    # per-site error by size quintile, aggregated (avoid tiny denominators)
    te2 = te.copy(); te2["pred"] = pred
    size = te2.groupby("site_id")["y"].mean()
    dec = pd.qcut(size, 5, labels=False, duplicates="drop")
    te2["decile"] = te2["site_id"].map(dec)
    for decile, s2 in te2.groupby("decile"):
        err_rows.append(dict(city=city, decile=int(decile),
                             wape=float(np.abs(s2["y"] - s2["pred"]).sum() / max(s2["y"].sum(), 1e-9)),
                             n=int(s2["site_id"].nunique()),
                             size=float(size[dec == decile].median())))
    print(city, "done; test WAPE=", np.abs(yte - pred).sum() / yte.sum())

imp = pd.DataFrame(imp_rows); imp.to_csv(os.path.join(OUT, "importance.csv"), index=False)
pdp = pd.DataFrame(pdp_rows); pdp.to_csv(os.path.join(OUT, "pdp.csv"), index=False)
err = pd.DataFrame(err_rows); err.to_csv(os.path.join(OUT, "error_by_size.csv"), index=False)

# ---- figure 1: permutation importance ----
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for ax, city in zip(axes, ["LOA", "MEL"]):
    s = imp[imp.city == city].sort_values("importance")
    ax.barh([LAB(f) for f in s.feature], s.importance, color="#2b8cbe")
    ax.set_title(f"{city} " + L("特征重要性（置换法）", "permutation importance"))
    ax.set_xlabel(L("MAE 上升量", "increase in MAE"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_importance.png"), dpi=150); plt.close()

# ---- figure 2: PDP ----
fig, axes = plt.subplots(2, 3, figsize=(14, 7.5))
for i, city in enumerate(["LOA", "MEL"]):
    for j, feat in enumerate(["lag24", "roll24_mean", "hour"]):
        ax = axes[i, j]
        s = pdp[(pdp.city == city) & (pdp.feature == feat)]
        ax.plot(s["value"], s["pred"], marker="o", color="#d7301f")
        ax.set_title(f"{city} · {LAB(feat)}", fontsize=10)
        ax.set_ylabel(L("平均预测值", "mean prediction"), fontsize=8)
        ax.grid(alpha=.25)
        if feat == "hour":
            ax.set_xticks(range(0, 24, 4))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_pdp.png"), dpi=150); plt.close()

# ---- figure 3: error by site size ----
fig, ax = plt.subplots(figsize=(8, 4.2))
for city, color in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    s = err[err.city == city].sort_values("decile")
    ax.plot(s["decile"] + 1, s["wape"], marker="o", color=color, label=city)
ax.set_xlabel(L("站点规模分组（1=最小，5=最大）", "site-size quintile"))
ax.set_ylabel("WAPE")
ax.set_title(L("误差随站点规模变化", "Error by site size"))
ax.legend(frameon=False); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_error_size.png"), dpi=150); plt.close()
print("saved")
