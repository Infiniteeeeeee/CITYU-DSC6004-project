"""1-day scope: regression baselines + models, peak classification, results & figures."""
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.ensemble import (HistGradientBoostingRegressor, HistGradientBoostingClassifier,
                              RandomForestRegressor)
from sklearn.preprocessing import StandardScaler
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (mean_absolute_error, r2_score, brier_score_loss, log_loss,
                             average_precision_score, precision_recall_fscore_support)
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
OUT = os.path.join(ROOT, "results")
os.makedirs(OUT, exist_ok=True)

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

df = pd.read_csv(os.path.join(ROOT, "panel", "panel_LOA_MEL.csv.gz"), parse_dates=["timestamp"])
print("panel:", df.shape)

FEATS = ["lag1", "lag24", "lag168", "roll24_mean", "roll24_std", "roll168_mean",
         "hour", "dow", "doy", "charger_num", "area", "poi_density", "lon", "lat"]
# linear models must not extrapolate a time trend beyond the training window
FEATS_LIN = [f for f in FEATS if f != "doy"]
for c in FEATS:
    df[c] = df[c].astype("float32")

df = df.dropna(subset=FEATS + ["y"]).reset_index(drop=True)

tr = df["timestamp"] < "2023-08-01"
va = (df["timestamp"] >= "2023-08-02") & (df["timestamp"] < "2023-09-01")
te = df["timestamp"] >= "2023-09-02"
print(f"train {tr.sum():,} | val {va.sum():,} | test {te.sum():,}")


def reg_metrics(t, p):
    t = np.asarray(t, float); p = np.asarray(p, float)
    mae = mean_absolute_error(t, p)
    rmse = float(np.sqrt(np.mean((t - p) ** 2)))
    wape = np.abs(t - p).sum() / max(np.abs(t).sum(), 1e-9)
    r2 = r2_score(t, p) if len(t) > 10 and np.var(t) > 0 else np.nan
    return mae, rmse, wape, r2


def per_site_r2(g):
    out = []
    for _, s in g.groupby("site_id"):
        if len(s) > 24 and s["y"].var() > 0:
            out.append(r2_score(s["y"], s["pred"]))
    return np.array(out) if out else np.array([np.nan])


# ---------------- regression ----------------
rows = []
preds = {}
for city in ["LOA", "MEL"]:
    m_tr = tr & (df["city"] == city)
    m_te = te & (df["city"] == city)
    dtr, dte = df[m_tr], df[m_te]

    site_mean = dtr.groupby("site_id")["y"].mean()
    preds[(city, "constant")] = dte["site_id"].map(site_mean).values
    preds[(city, "t-24")] = dte["lag24"].values
    preds[(city, "t-168")] = dte["lag168"].values

    Xtr, Xte = dtr[FEATS].values, dte[FEATS].values
    ytr = np.log1p(dtr["y"].values)
    scaler = StandardScaler().fit(Xtr)
    y_cap = np.percentile(dtr["y"], 99.9)

    scaler_lin = StandardScaler().fit(dtr[FEATS_LIN].values)
    lr = Ridge(alpha=1.0).fit(scaler_lin.transform(dtr[FEATS_LIN].values), dtr["y"].values)
    p_lin = lr.predict(scaler_lin.transform(dte[FEATS_LIN].values))
    preds[(city, "linear")] = np.clip(p_lin, 0, y_cap)

    hgb = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                        min_samples_leaf=40, random_state=0)
    hgb.fit(Xtr, ytr)
    preds[(city, "hgb")] = np.clip(np.expm1(hgb.predict(Xte)), 0, y_cap)

    idx = np.random.default_rng(0).choice(len(Xtr), size=min(300_000, len(Xtr)), replace=False)
    rf = RandomForestRegressor(n_estimators=80, max_depth=14, min_samples_leaf=10,
                               n_jobs=-1, random_state=0)
    rf.fit(Xtr[idx], ytr[idx])
    preds[(city, "rf")] = np.clip(np.expm1(rf.predict(Xte)), 0, y_cap)

    for model in ["constant", "t-24", "t-168", "linear", "rf", "hgb"]:
        p = preds[(city, model)]
        mae, rmse, wape, r2 = reg_metrics(dte["y"], p)
        tmp = dte[["site_id", "y"]].copy(); tmp["pred"] = p
        ps = per_site_r2(tmp)
        rows.append(dict(city=city, model=model, MAE=mae, RMSE=rmse, WAPE=wape, R2=r2,
                         site_R2_median=np.nanmedian(ps), site_R2_pos=np.nanmean(ps > 0)))
    print(f"regression done: {city}")

reg_res = pd.DataFrame(rows)
reg_res.to_csv(os.path.join(OUT, "metrics_regression.csv"), index=False)
print(reg_res.round(3).to_string(index=False))

# ---------------- classification ----------------
# peaks only exist where there is demand; restrict to eligible sites
elig = df["is_eligible"] == 1
rows = []
cls_preds = {}
for city in ["LOA", "MEL"]:
    m_tr = tr & elig & (df["city"] == city)
    m_va = va & elig & (df["city"] == city)
    m_te = te & elig & (df["city"] == city)
    dtr, dva, dte = df[m_tr], df[m_va], df[m_te]

    base = dtr["peak"].mean()
    p_base_va = np.full(len(dva), base)
    p_base = np.full(len(dte), base)
    freq_map = dtr.groupby(["hour", "dow"])["peak"].mean().rename("p").reset_index()
    p_freq_va = dva[["hour", "dow"]].merge(freq_map, on=["hour", "dow"], how="left")["p"].fillna(base).values
    p_freq = dte[["hour", "dow"]].merge(freq_map, on=["hour", "dow"], how="left")["p"].fillna(base).values

    Xtr = dtr[FEATS].values; ytr = dtr["peak"].values
    scaler = StandardScaler().fit(Xtr)
    logit = LogisticRegression(max_iter=1000).fit(scaler.transform(Xtr), ytr)
    p_logit_va = logit.predict_proba(scaler.transform(dva[FEATS].values))[:, 1]
    p_logit = logit.predict_proba(scaler.transform(dte[FEATS].values))[:, 1]

    hgbc = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                                          min_samples_leaf=40, random_state=0).fit(Xtr, ytr)
    p_hgb_va = hgbc.predict_proba(dva[FEATS].values)[:, 1]
    p_hgb = hgbc.predict_proba(dte[FEATS].values)[:, 1]

    # isotonic calibration fitted on the validation month
    iso_l = IsotonicRegression(out_of_bounds="clip").fit(p_logit_va, dva["peak"].values)
    p_logit_cal_va, p_logit_cal = iso_l.predict(p_logit_va), iso_l.predict(p_logit)
    iso_h = IsotonicRegression(out_of_bounds="clip").fit(p_hgb_va, dva["peak"].values)
    p_hgb_cal_va, p_hgb_cal = iso_h.predict(p_hgb_va), iso_h.predict(p_hgb)

    def best_thr(y, p):
        ths = np.quantile(p, np.linspace(0.5, 0.999, 200))
        best = (0, -1)
        for th in ths:
            pr, rc, f1, _ = precision_recall_fscore_support(y, (p >= th).astype(int), average="binary", zero_division=0)
            if f1 > best[1]:
                best = (th, f1)
        return best[0]

    candidates = {
        "base_rate": (p_base_va, p_base),
        "hour_dow_freq": (p_freq_va, p_freq),
        "logistic": (p_logit_va, p_logit),
        "logistic_cal": (p_logit_cal_va, p_logit_cal),
        "hgb": (p_hgb_va, p_hgb),
        "hgb_cal": (p_hgb_cal_va, p_hgb_cal),
    }
    for name, (p_va, p_te) in candidates.items():
        th = best_thr(dva["peak"].values, np.asarray(p_va))
        y = dte["peak"].values
        pr, rc, f1, _ = precision_recall_fscore_support(y, (np.asarray(p_te) >= th).astype(int),
                                                        average="binary", zero_division=0)
        rows.append(dict(city=city, model=name, event_rate=y.mean(),
                         Brier=brier_score_loss(y, np.clip(p_te, 0, 1)),
                         logloss=log_loss(y, np.clip(p_te, 1e-6, 1 - 1e-6)),
                         PR_AUC=average_precision_score(y, p_te), precision=pr, recall=rc, F1=f1, threshold=th))
    cls_preds[(city, "hgb")] = (dte["peak"].values, p_hgb_cal)
    cls_preds[(city, "freq")] = (dte["peak"].values, p_freq)
    print(f"classification done: {city}")

cls_res = pd.DataFrame(rows)
cls_res.to_csv(os.path.join(OUT, "metrics_classification.csv"), index=False)
print(cls_res.round(3).to_string(index=False))

# ---------------- figures ----------------
# 1 predicted vs actual (LOA, hgb)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, city in zip(axes, ["LOA", "MEL"]):
    m_te = te & (df["city"] == city)
    y = df.loc[m_te, "y"].values
    p = preds[(city, "hgb")]
    ax.hexbin(np.log1p(y), np.log1p(p), gridsize=60, bins="log", cmap="viridis")
    lim = [0, np.log1p(np.percentile(y, 99.5))]
    ax.plot(lim, lim, "r--", lw=1)
    ax.set_xlabel(L("真实值 log1p(kWh)", "actual log1p(kWh)"))
    ax.set_ylabel(L("预测值 log1p(kWh)", "predicted log1p(kWh)"))
    ax.set_title(f"{city} HGB " + L("测试集", "test"))
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_pred_vs_actual.png"), dpi=150); plt.close()

# 2 calibration
fig, ax = plt.subplots(figsize=(5.2, 4.6))
for city, color in [("LOA", "#2b8cbe"), ("MEL", "#d7301f")]:
    y, p = cls_preds[(city, "hgb")]
    bins = np.quantile(p, np.linspace(0, 1, 11))
    idx = np.digitize(p, bins[1:-1])
    xs, ys = [], []
    for b in range(10):
        m = idx == b
        if m.sum() > 50:
            xs.append(p[m].mean()); ys.append(y[m].mean())
    ax.plot(xs, ys, "o-", color=color, label=f"{city} HGB")
ax.plot([0, 1], [0, 1], "k--", lw=1)
ax.set_xlabel(L("预测概率", "predicted probability"))
ax.set_ylabel(L("实际频率", "observed frequency"))
ax.set_title(L("峰值分类校准曲线（测试集）", "Calibration (test)"))
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_calibration.png"), dpi=150); plt.close()

# 3 WAPE by hour
fig, ax = plt.subplots(figsize=(8, 4.2))
for city, ls in [("LOA", "-"), ("MEL", "--")]:
    m_te = te & (df["city"] == city)
    dte = df[m_te]
    for model, color in [("t-24", "grey"), ("hgb", "#2b8cbe")]:
        p = preds[(city, model)]
        tmp = pd.DataFrame({"hour": dte["hour"].values, "y": dte["y"].values, "e": np.abs(dte["y"].values - p)})
        g = tmp.groupby("hour").sum()
        ax.plot(g.index, g["e"] / g["y"], ls, color=color, lw=1.6,
                label=f"{city} {model}")
ax.set_xlabel(L("小时", "hour")); ax.set_ylabel("WAPE")
ax.set_title(L("分时段误差（HGB vs t-24）", "WAPE by hour"))
ax.legend(fontsize=7, frameon=False, ncol=2)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_wape_hour.png"), dpi=150); plt.close()

print("\nsaved to", OUT)
