"""LSTM baseline on GPU, per city, same fold-4 split as the ablation (train < Sep, test Sep)."""
import os
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
OUT = os.path.join(ROOT, "results")
PANEL = os.path.join(ROOT, "panel")
DEV = "cuda" if torch.cuda.is_available() else "cpu"

names = {f.name for f in font_manager.fontManager.ttflist}
CJK = next((n for n in ["Microsoft YaHei", "SimHei"] if n in names), None)
if CJK:
    matplotlib.rcParams["font.sans-serif"] = [CJK]
    matplotlib.rcParams["axes.unicode_minus"] = False
L = (lambda zh, en: zh) if CJK else (lambda zh, en: en)

SEQ = 24
torch.manual_seed(0); np.random.seed(0)


class LSTMNet(nn.Module):
    def __init__(self, hidden=64):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden, num_layers=1, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden + 3, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, x, extra):
        if x.dim() == 2:
            x = x.unsqueeze(-1)
        out, _ = self.lstm(x)
        h = out[:, -1, :]
        return self.head(torch.cat([h, extra], dim=1)).squeeze(1)


def run_city(city):
    d = pd.read_csv(os.path.join(PANEL, f"panel_{city}.csv.gz"),
                    usecols=["timestamp", "site_id", "y", "hour", "dow", "charger_num"], parse_dates=["timestamp"])
    wide = d.pivot_table(index="timestamp", columns="site_id", values="y", aggfunc="first")
    hours = wide.index.hour.values
    T, N = wide.shape
    Y = np.log1p(wide.values.astype(np.float32))

    train_mask = wide.index < "2023-08-31"
    mu = np.nanmean(Y[train_mask], axis=0)
    sd = np.nanstd(Y[train_mask], axis=0) + 1e-6
    Z = (Y - mu) / sd

    # sliding windows: input Z[t-SEQ+1..t] -> target Z[t+1]
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(Z, SEQ, axis=0)          # (T-SEQ+1, N, SEQ)
    tgt_idx = np.arange(SEQ - 1, T - 1)                 # target index = t+1
    X = win[:len(tgt_idx)].transpose(0, 1, 2).reshape(-1, SEQ)   # (n_win*N, SEQ)
    Yt = Z[tgt_idx + 1].reshape(-1)
    hour_t = np.repeat(hours[tgt_idx + 1], N)
    dow_t = np.repeat(wide.index[tgt_idx + 1].dayofweek.values, N)
    site_ids = np.tile(wide.columns.values, len(tgt_idx))
    ts_t = np.repeat(wide.index[tgt_idx + 1].values, N)

    valid = ~np.isnan(X).any(1) & ~np.isnan(Yt)
    X, Yt, hour_t, dow_t, site_ids, ts_t = X[valid], Yt[valid], hour_t[valid], dow_t[valid], site_ids[valid], ts_t[valid]

    extra = np.stack([np.sin(2 * np.pi * hour_t / 24), np.cos(2 * np.pi * hour_t / 24),
                      dow_t / 6.0], axis=1).astype(np.float32)

    split_ts = np.datetime64("2023-09-01T00:00:00")
    tr = ts_t < split_ts
    te = ts_t >= split_ts
    print(f"{city}: windows={len(X):,} train={tr.sum():,} test={te.sum():,}")

    # time-based validation for early stopping (last 10% of train)
    order = np.argsort(ts_t[tr])
    tr_idx = np.where(tr)[0][order]
    cut = int(len(tr_idx) * 0.9)
    fit_idx, val_idx = tr_idx[:cut], tr_idx[cut:]

    ds = TensorDataset(torch.from_numpy(X[fit_idx]), torch.from_numpy(extra[fit_idx]),
                       torch.from_numpy(Yt[fit_idx]))
    dl = DataLoader(ds, batch_size=4096, shuffle=True, drop_last=True)
    Xv = torch.from_numpy(X[val_idx]).to(DEV); Ev = torch.from_numpy(extra[val_idx]).to(DEV)
    Yv = torch.from_numpy(Yt[val_idx]).to(DEV)
    Xt = torch.from_numpy(X[te]).to(DEV); Et = torch.from_numpy(extra[te]).to(DEV)

    model = LSTMNet().to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    lossf = nn.MSELoss()
    best, best_state, patience = 1e9, None, 0
    hist = []
    for epoch in range(30):
        model.train()
        tot = 0.0
        for xb, eb, yb in dl:
            xb, eb, yb = xb.to(DEV), eb.to(DEV), yb.to(DEV)
            opt.zero_grad()
            loss = lossf(model(xb, eb), yb)
            loss.backward(); opt.step()
            tot += loss.item() * len(xb)
        model.eval()
        with torch.no_grad():
            vloss = lossf(model(Xv, Ev), Yv).item()
        hist.append((epoch + 1, tot / len(fit_idx), vloss))
        if vloss < best - 1e-5:
            best, best_state, patience = vloss, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 4:
                break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        pz = model(Xt, Et).cpu().numpy()
    site_of = site_ids[te]
    sidx = np.array([np.where(wide.columns.values == s)[0][0] for s in site_of])
    yhat = np.expm1(pz * sd[sidx] + mu[sidx])
    ytrue = np.expm1(Yt[te] * sd[sidx] + mu[sidx])
    wape = np.abs(ytrue - yhat).sum() / max(ytrue.sum(), 1e-9)
    mae = np.abs(ytrue - yhat).mean()
    pd.DataFrame({"timestamp": ts_t[te], "site_id": site_of, "y": ytrue, "pred": yhat}) \
        .to_csv(os.path.join(OUT, f"lstm_pred_{city}.csv"), index=False)
    print(f"{city}: LSTM WAPE={wape:.3f} MAE={mae:.3f} (epochs={len(hist)})")
    return dict(city=city, model="lstm", WAPE=wape, MAE=mae, epochs=len(hist)), hist


rows, fig_data = [], {}
for city in ["LOA", "MEL"]:
    t0 = time.time()
    r, hist = run_city(city)
    rows.append(r); fig_data[city] = hist
    print(f"  {time.time()-t0:.0f}s")

pd.DataFrame(rows).to_csv(os.path.join(OUT, "lstm_results.csv"), index=False)
print(pd.DataFrame(rows).round(3).to_string(index=False))

fig, ax = plt.subplots(figsize=(7, 4))
for city, hist in fig_data.items():
    h = np.array(hist)
    ax.plot(h[:, 0], h[:, 2], marker="o", label=f"{city} val")
ax.set_xlabel("epoch"); ax.set_ylabel("MSE (log1p, z-scored)")
ax.set_title(L("LSTM 验证损失", "LSTM validation loss"))
ax.legend(frameon=False); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_lstm_loss.png"), dpi=150); plt.close()
