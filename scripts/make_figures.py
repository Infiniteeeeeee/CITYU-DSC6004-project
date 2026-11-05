"""Reproduce the CHARGED data-characterisation figures.

Reads every city folder (sites, chargers, volume, e_price, s_price, weather, poi,
distance) and writes 9 figures plus a summary table into ``figures/``.

    python scripts/make_figures.py
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "figures")
CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]

os.makedirs(OUT, exist_ok=True)

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

summary, store = [], {}

for c in CITIES:
    d = os.path.join(BASE, c)
    sites = pd.read_csv(os.path.join(d, "sites.csv")).set_index("site_id")
    chargers = pd.read_csv(os.path.join(d, "chargers.csv"))
    vol = pd.read_csv(os.path.join(d, "volume.csv"), index_col=0, parse_dates=True)
    vol.columns = vol.columns.astype(int)
    ep = pd.read_csv(os.path.join(d, "e_price.csv"), index_col=0).values
    sp = pd.read_csv(os.path.join(d, "s_price.csv"), index_col=0).values
    weather = pd.read_csv(os.path.join(d, "weather.csv"), parse_dates=["time"]).set_index("time")
    poi = pd.read_csv(os.path.join(d, "poi.csv"))

    total_by_site = vol.sum(axis=0)
    active = total_by_site > 0

    x = vol.values.reshape(len(vol) // 24, 24, vol.shape[1])
    m, s = x.mean(axis=1), x.std(axis=1)
    cv = np.where(m > 0, s / np.where(m > 0, m, 1), np.nan)
    site_cv = np.nanmedian(cv, axis=0)[active.values]

    daily = vol.sum(axis=1).resample("D").sum()
    hour_profile = vol.groupby(vol.index.hour).mean().mean(axis=1)

    wd = weather.resample("D").agg({"temp": "mean", "precip": "sum", "humidity": "mean",
                                    "windspeed": "mean", "solarradiation": "mean", "cloudcover": "mean"})
    wd = wd.reindex(daily.index)

    store[c] = {
        "daily": daily,
        "hour_profile": hour_profile / hour_profile.mean(),
        "site_cv": np.clip(site_cv, 1e-3, None),
        "site_total": total_by_site[active],
        "poi": poi["type"].value_counts(),
        "weather": wd,
        "ep": ep, "sp": sp,
    }

    summary.append({
        "city": c, "sites": len(sites), "active_sites": int(active.sum()),
        "zero_pct": 100 * (1 - active.sum() / len(sites)), "chargers": len(chargers),
        "total_GWh": total_by_site.sum() / 1e6,
        "median_site_MWh": total_by_site[active].median() / 1e3,
        "p99_site_MWh": total_by_site[active].quantile(0.99) / 1e3,
        "cv_median": float(np.median(site_cv)),
        "flat_pct": float(100 * np.mean(site_cv < 0.05)),
        "e_price_nonzero_median": float(np.median(ep[ep > 0])) if (ep > 0).any() else np.nan,
        "e_price_zero_pct": float((ep == 0).mean() * 100),
        "s_price_nonzero_pct": float((sp > 0).mean() * 100),
        "poi_rows": len(poi), "poi_types": int(poi["type"].nunique()),
        "weather_null": int(weather.isna().sum().sum()),
    })
    print(f"{c}: sites={len(sites)} active={int(active.sum())} cv_med={np.median(site_cv):.3f} "
          f"flat={100*np.mean(site_cv<0.05):.0f}% total={total_by_site.sum()/1e6:.1f}GWh")
    del vol, ep, sp, poi, weather, x, cv

sm = pd.DataFrame(summary)
sm.to_csv(os.path.join(OUT, "city_summary.csv"), index=False)

# 1 overview
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
ax = axes[0]
xp = np.arange(len(sm))
ax.bar(xp, sm["active_sites"], color="#2b8cbe", label=L("有电量站点", "active"))
ax.bar(xp, sm["sites"] - sm["active_sites"], bottom=sm["active_sites"],
       color="#bdbdbd", label=L("全零站点", "zero-volume"))
for i, r in sm.iterrows():
    ax.text(i, r["sites"] + 40, f"{r['zero_pct']:.0f}%", ha="center", fontsize=9, color="#d7301f")
ax.set_xticks(xp); ax.set_xticklabels(sm["city"])
ax.set_ylabel(L("站点数", "sites")); ax.set_ylim(0, sm["sites"].max() * 1.18)
ax.set_title(L("站点构成（红字：全零站点占比）", "Sites: active vs zero-volume"))
ax.legend(frameon=False)
ax = axes[1]
ax.bar(xp, sm["chargers"], color="#41ab5d")
for i, v in enumerate(sm["chargers"]):
    ax.text(i, v + 40, str(v), ha="center", fontsize=9)
ax.set_xticks(xp); ax.set_xticklabels(sm["city"])
ax.set_ylabel(L("充电桩数", "chargers")); ax.set_title(L("各城市充电桩数量", "Chargers per city"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig1_overview.png"), dpi=150); plt.close()

# 2 daily
fig, axes = plt.subplots(3, 2, figsize=(14, 9), sharex=True)
for ax, c in zip(axes.ravel(), CITIES):
    s = store[c]["daily"]
    ax.plot(s.index, s.values, lw=1.1, color="#2b8cbe")
    ax.set_yscale("log"); ax.grid(alpha=.25)
    ax.set_title(f"{c} " + L("日总电量（对数轴）", "daily volume (log)"), fontsize=10)
fig.suptitle(L("六城市日总充电量（2023-04-01 ~ 09-30）", "Daily total charging volume"), y=1.0)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig2_daily.png"), dpi=150); plt.close()

# 3 hour heatmap
mat = np.array([store[c]["hour_profile"].values for c in CITIES])
fig, ax = plt.subplots(figsize=(12, 3.6))
im = ax.imshow(mat, aspect="auto", cmap="RdYlBu_r", vmin=0.5, vmax=1.5)
ax.set_yticks(range(len(CITIES))); ax.set_yticklabels(CITIES)
ax.set_xticks(range(24)); ax.set_xticklabels(range(24))
ax.set_xlabel(L("小时", "hour of day"))
ax.set_title(L("日内负荷形状（相对城市均值，1.0 = 平均）", "Normalised hour-of-day profile"))
for i in range(len(CITIES)):
    for j in range(24):
        ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=6.5)
plt.colorbar(im, ax=ax, shrink=.9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig3_hour_heatmap.png"), dpi=150); plt.close()

# 4 CV
fig, ax = plt.subplots(figsize=(9.5, 4.8))
bp = ax.boxplot([store[c]["site_cv"] for c in CITIES], tick_labels=CITIES, showfliers=False,
                patch_artist=True, widths=.55)
for p in bp["boxes"]:
    p.set_facecolor("#9ecae1")
for i, c in enumerate(CITIES, start=1):
    ax.text(i, 2.1, f"{sm.loc[sm.city == c, 'flat_pct'].iloc[0]:.0f}%", ha="center", fontsize=9, color="#d7301f")
ax.set_yscale("log"); ax.set_ylim(8e-4, 6)
ax.set_ylabel(L("站点日内变异系数（对数轴）", "per-site intraday CV (log)"))
ax.set_title(L("站点日内波动强度（红字：CV<0.05 的站点占比）", "Intraday variability per site"))
ax.axhline(0.05, color="grey", ls="--", lw=.8)
ax.text(6.55, 0.052, "CV=0.05", fontsize=7, color="grey")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig4_cv.png"), dpi=150); plt.close()

# 5 size + Lorenz
fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
ax = axes[0]
bp = ax.boxplot([np.log10(store[c]["site_total"].values) for c in CITIES], tick_labels=CITIES,
                showfliers=True, patch_artist=True, widths=.55)
for p in bp["boxes"]:
    p.set_facecolor("#a1d99b")
ax.set_ylabel(L("站点总电量 log10(kWh)", "log10 site total (kWh)"))
ax.set_title(L("站点规模分布（跨 2~3 个数量级）", "Site-size distribution"))
ax = axes[1]
for c in CITIES:
    v = np.sort(store[c]["site_total"].values)[::-1]
    ax.plot(np.arange(1, len(v) + 1) / len(v), np.cumsum(v) / v.sum(), label=c, lw=1.2)
ax.plot([0, 1], [0, 1], "k--", lw=.8)
ax.set_xlabel(L("站点累计占比（按电量降序）", "cumulative share of sites"))
ax.set_ylabel(L("累计电量占比", "cumulative share of volume"))
ax.set_title(L("电量集中度（洛伦兹曲线）", "Volume concentration"))
ax.legend(fontsize=8, frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig5_size.png"), dpi=150); plt.close()

# 6 price
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
ax = axes[0]
vals = sm["e_price_nonzero_median"].values
ax.bar(sm["city"], vals, color="#f16913")
ax.set_yscale("log"); ax.set_ylim(0.05, 2000)
for i, (c, v) in enumerate(zip(sm["city"], vals)):
    ax.text(i, v * 1.25, f"{v:.2f}", ha="center", fontsize=9)
    ax.text(i, 0.08, L(f"零值 {sm.loc[sm.city == c, 'e_price_zero_pct'].iloc[0]:.0f}%",
                       f"{sm.loc[sm.city == c, 'e_price_zero_pct'].iloc[0]:.0f}% zero"),
            ha="center", fontsize=8, color="#555")
ax.set_ylabel(L("非零电价中位数（对数轴）", "median non-zero e_price (log)"))
ax.set_title(L("电价：非零值中位数（下方为零值占比）", "Electricity price (non-zero median)"))
ax = axes[1]
ax.bar(sm["city"], sm["s_price_nonzero_pct"], color="#756bb1")
for i, v in enumerate(sm["s_price_nonzero_pct"]):
    ax.text(i, v + 0.4, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_ylabel(L("非零服务费占比 (%)", "% non-zero s_price"))
ax.set_title(L("服务费非零比例（其余城市恒为 0）", "Share of non-zero service price"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig6_price.png"), dpi=150); plt.close()

# 7 weather correlation
vars_ = ["temp", "precip", "humidity", "windspeed", "solarradiation", "cloudcover"]
labels_ = {"temp": L("温度", "temp"), "precip": L("降水", "precip"), "humidity": L("湿度", "humidity"),
           "windspeed": L("风速", "wind"), "solarradiation": L("辐射", "solar"),
           "cloudcover": L("云量", "cloud")}
corr = np.zeros((len(CITIES), len(vars_)))
for i, c in enumerate(CITIES):
    d = store[c]["daily"]; w = store[c]["weather"]
    for j, v in enumerate(vars_):
        corr[i, j] = d.corr(w[v])
fig, ax = plt.subplots(figsize=(8.5, 3.8))
im = ax.imshow(corr, cmap="coolwarm", vmin=-.8, vmax=.8)
ax.set_yticks(range(len(CITIES))); ax.set_yticklabels(CITIES)
ax.set_xticks(range(len(vars_))); ax.set_xticklabels([labels_[v] for v in vars_])
for i in range(len(CITIES)):
    for j in range(len(vars_)):
        ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=8)
ax.set_title(L("日需求与天气变量的相关系数", "Correlation: daily demand vs weather"))
plt.colorbar(im, ax=ax, shrink=.9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig7_weather.png"), dpi=150); plt.close()

# 8 POI
allc = pd.concat({c: store[c]["poi"] for c in CITIES}, axis=1).fillna(0).sum(axis=1)
allc = allc.drop(labels=[k for k in allc.index if str(k).lower() == "other"], errors="ignore")
top8 = allc.sort_values(ascending=False).head(8).index
mat = []
for c in CITIES:
    vc = store[c]["poi"]
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
ax.set_xlabel(L("占比 (%)", "share (%)"))
ax.set_title(L("各城市 POI 构成（统一前 8 类 + other）", "POI composition (common top-8 + other)"))
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig8_poi.png"), dpi=150); plt.close()

# 9 distance
dist = pd.read_csv(os.path.join(BASE, "AMS", "distance.csv"), index_col=0)
dist.columns = dist.columns.astype(int)
sites = pd.read_csv(os.path.join(BASE, "AMS", "sites.csv")).set_index("site_id")
order = sites.loc[dist.index, "longitude"].sort_values().index
D = dist.loc[order, order].values
fig, ax = plt.subplots(figsize=(6.4, 5.4))
im = ax.imshow(D, cmap="viridis")
ax.set_title(L("AMS 站间距离矩阵（按经度排序）", "AMS inter-site distance (sorted by longitude)"))
ax.set_xlabel(L("站点序号", "site index")); ax.set_ylabel(L("站点序号", "site index"))
plt.colorbar(im, ax=ax, label="km", shrink=.9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig9_distance.png"), dpi=150); plt.close()

print(sm.round(2).to_string(index=False))
print("figures written to", OUT)
