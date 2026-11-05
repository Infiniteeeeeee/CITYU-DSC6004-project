"""Error analysis: demand deciles, flat vs volatile sites, residual ACF, bootstrap CIs."""
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
OUT = os.path.join(ROOT, "results")
PANEL = os.path.join(ROOT, "panel")

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]

dec_rows, acf_rows, boot_rows, flat_rows = [], [], [], []

for city in ["LOA", "MEL"]:
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"), parse_dates=["timestamp"])
    d = d.dropna(subset=FEATS + ["y"])
    tr = d[d.timestamp < "2023-08-31"]
    te = d[d.timestamp >= "2023-09-01"].copy()

    lp = pd.read_csv(os.path.join(OUT, f"lstm_pred_{city}.csv"), parse_dates=["timestamp"])
    te = te.merge(lp[["timestamp", "site_id", "pred"]].rename(columns={"pred": "LSTM"}),
                  on=["timestamp", "site_id"], how="inner")

    y_cap = np.percentile(tr["y"], 99.9)
    sc = StandardScaler().fit(tr[FEATS].values)
    ridge = Ridge(alpha=1.0).fit(sc.transform(tr[FEATS].values), tr["y"].values)
    hgb = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                        min_samples_leaf=40, random_state=0).fit(tr[FEATS].values, np.log1p(tr["y"].values))
    te["Ridge"] = np.clip(ridge.predict(sc.transform(te[FEATS].values)), 0, y_cap)
    te["HGB"] = np.clip(np.expm1(hgb.predict(te[FEATS].values)), 0, y_cap)

    # ---- 1. error by actual-demand decile ----
    te["decile"] = pd.qcut(te["y"], 10, labels=False, duplicates="drop")
    for dec, s in te.groupby("decile"):
        row = dict(city=city, decile=int(dec), mean_y=s["y"].mean(), n=len(s))
        for m in ["LSTM", "Ridge", "HGB"]:
            row[f"wape_{m}"] = np.abs(s["y"] - s[m]).sum() / max(s["y"].sum(), 1e-9)
            row[f"bias_{m}"] = (s[m] - s["y"]).sum() / max(s["y"].sum(), 1e-9)
        dec_rows.append(row)

    # ---- 2. residual autocorrelation (city-level residuals) ----
    te["res_LSTM"] = te["LSTM"] - te["y"]
    g = te.groupby("timestamp")["res_LSTM"].mean()
    x = g.values - g.values.mean()
    denom = (x ** 2).sum()
    for lag in range(1, 73):
        r = (x[:-lag] * x[lag:]).sum() / denom
        acf_rows.append(dict(city=city, lag=lag, acf=r))

    # ---- 3. paired bootstrap over sites (LSTM vs Ridge vs HGB) ----
    site_ids = te["site_id"].unique()
    rng = np.random.default_rng(0)
    by_site = {s: g2 for s, g2 in te.groupby("site_id")}
    for b in range(200):
        samp = rng.choice(site_ids, size=len(site_ids), replace=True)
        sub = pd.concat([by_site[s] for s in samp])
        boot_rows.append(dict(city=city, rep=b,
                              LSTM=np.abs(sub["y"] - sub["LSTM"]).sum() / sub["y"].sum(),
                              Ridge=np.abs(sub["y"] - sub["Ridge"]).sum() / sub["y"].sum(),
                              HGB=np.abs(sub["y"] - sub["HGB"]).sum() / sub["y"].sum()))

    # ---- 4. flat vs eligible sites ----
    for flag, name in [(1, "eligible(CV>=0.05)"), (0, "flat(CV<0.05)")]:
        s = te[te["is_eligible"] == flag]
        if len(s) == 0:
            continue
        row = dict(city=city, group=name, n=len(s), sites=s["site_id"].nunique())
        for m in ["LSTM", "Ridge", "HGB"]:
            row[f"wape_{m}"] = np.abs(s["y"] - s[m]).sum() / max(s["y"].sum(), 1e-9)
        flat_rows.append(row)
    print(city, "done")

dec = pd.DataFrame(dec_rows); dec.to_csv(os.path.join(OUT, "err_decile.csv"), index=False)
acf = pd.DataFrame(acf_rows); acf.to_csv(os.path.join(OUT, "err_acf.csv"), index=False)
boot = pd.DataFrame(boot_rows); boot.to_csv(os.path.join(OUT, "err_bootstrap.csv"), index=False)
flat = pd.DataFrame(flat_rows); flat.to_csv(os.path.join(OUT, "err_flat.csv"), index=False)

print(dec.round(3).to_string(index=False))
print(flat.round(3).to_string(index=False))

# ---- figure: decile errors + bias ----
fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
for ax, city in zip(axes, ["LOA", "MEL"]):
    s = dec[dec.city == city]
    x = s["decile"] + 1
    for m, c, ls in [("LSTM", "#31a354", "-"), ("Ridge", "#d7301f", "--"), ("HGB", "#2b8cbe", ":")]:
        ax.plot(x, s[f"wape_{m}"], marker="o", color=c, ls=ls, label=m)
    ax.set_xlabel(L("真实需求十分位（1=最低，10=最高）", "actual-demand decile"))
    ax.set_ylabel("WAPE"); ax.set_title(city); ax.legend(frameon=False); ax.grid(alpha=.25)
plt.suptitle(L("误差随需求水平变化", "Error by demand level"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_err_decile.png"), dpi=150); plt.close()

# ---- figure: residual ACF ----
fig, ax = plt.subplots(figsize=(7.5, 4.0))
for city, c in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    s = acf[acf.city == city]
    ax.plot(s["lag"], s["acf"], color=c, label=city)
ax.axhline(0, color="k", lw=.8)
ax.set_xlabel(L("滞后（小时）", "lag (hours)")); ax.set_ylabel("ACF")
ax.set_title(L("LSTM 残差自相关", "Residual autocorrelation (LSTM)"))
ax.legend(frameon=False); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_err_acf.png"), dpi=150); plt.close()

# ---- figure: bootstrap CI ----
fig, ax = plt.subplots(figsize=(7.5, 4.0))
pos = 0
ticks, labels = [], []
for city in ["LOA", "MEL"]:
    s = boot[boot.city == city]
    for m, c in [("LSTM", "#31a354"), ("Ridge", "#d7301f"), ("HGB", "#2b8cbe")]:
        v = s[m].values
        ax.errorbar(pos, v.mean(), yerr=[[v.mean() - np.percentile(v, 2.5)], [np.percentile(v, 97.5) - v.mean()]],
                    fmt="o", color=c, capsize=4)
        ticks.append(pos); labels.append(f"{city}\n{m}")
        pos += 1
    pos += 0.5
ax.set_xticks(ticks); ax.set_xticklabels(labels, fontsize=7)
ax.set_ylabel("WAPE（200 次站点自助抽样，95% 区间）")
ax.set_title(L("模型差异的自助置信区间", "Bootstrap CI of model WAPE"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_err_bootstrap.png"), dpi=150); plt.close()
print("saved")
