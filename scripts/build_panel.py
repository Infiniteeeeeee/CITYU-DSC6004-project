"""Build the site-hour panel for the requested cities.

Each city is written to ``panel/panel_<CITY>.csv.gz`` with causal features,
a causal peak label (same-hour rolling 28d mean + 2sd, shifted by 1), and two
flags: ``is_active`` (ever produced volume) and ``is_eligible`` (intraday
CV >= 0.05 on the training period - hourly dynamics actually exist).

    python scripts/build_panel.py --cities LOA MEL SZH JHB SPO
"""
import argparse
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "panel")
os.makedirs(OUT, exist_ok=True)


def poi_density(sites, poi, cell=0.005):
    gx = np.floor(poi["longitude"] / cell).astype(int)
    gy = np.floor(poi["latitude"] / cell).astype(int)
    counts = pd.Series(list(zip(gx, gy))).value_counts()
    key = list(zip(np.floor(sites["longitude"] / cell).astype(int),
                   np.floor(sites["latitude"] / cell).astype(int)))
    return pd.Series([counts.get(k, 0) for k in key], index=sites.index).astype(float)


def build_city(city: str) -> None:
    d = os.path.join(BASE, city)
    vol = pd.read_csv(os.path.join(d, "volume.csv"), index_col=0, parse_dates=True)
    vol.columns = vol.columns.astype(int)
    dur = pd.read_csv(os.path.join(d, "duration.csv"), index_col=0, parse_dates=True)
    dur.columns = dur.columns.astype(int)
    sites = pd.read_csv(os.path.join(d, "sites.csv")).set_index("site_id").loc[vol.columns]
    weather = pd.read_csv(os.path.join(d, "weather.csv"), parse_dates=["time"]).set_index("time")
    poi = pd.read_csv(os.path.join(d, "poi.csv"))

    T, N = vol.shape

    # causal peak threshold: same-hour rolling 28d mean + 2sd, excluding current hour
    thr = pd.DataFrame(np.nan, index=vol.index, columns=vol.columns)
    for h in range(24):
        s = vol.iloc[h::24]
        m = s.shift(1).rolling(28, min_periods=14).mean()
        sd = s.shift(1).rolling(28, min_periods=14).std()
        thr.iloc[h::24] = (m + 2 * sd).values
    peak = (vol > thr) & thr.notna()

    feats = {
        "y": vol,
        "duration": dur,
        "lag1": vol.shift(1),
        "lag24": vol.shift(24),
        "lag168": vol.shift(168),
        "roll24_mean": vol.shift(1).rolling(24, min_periods=6).mean(),
        "roll24_std": vol.shift(1).rolling(24, min_periods=6).std(),
        "roll168_mean": vol.shift(1).rolling(168, min_periods=24).mean(),
    }

    # eligibility computed on the training period only (Apr-Jul)
    v = vol.loc[vol.index < "2023-08-01"].values
    x = v.reshape(len(v) // 24, 24, N)
    m_, s_ = x.mean(axis=1), x.std(axis=1)
    cv = np.where(m_ > 0, s_ / np.where(m_ > 0, m_, 1), np.nan)
    site_cv = np.nanmedian(cv, axis=0)
    is_active = (vol.sum(axis=0) > 0).to_numpy()
    is_eligible = is_active & (site_cv >= 0.05)

    df = pd.DataFrame({k: f.to_numpy().ravel() for k, f in feats.items()})
    for c in df.columns:
        df[c] = df[c].astype("float32")
    df["peak"] = peak.to_numpy().ravel().astype("int8")
    df.insert(0, "timestamp", np.repeat(vol.index.values, N))
    df.insert(1, "site_id", np.tile(vol.columns.to_numpy(), T))
    df.insert(0, "city", city)

    df["hour"] = df["timestamp"].dt.hour.astype("int8")
    df["dow"] = df["timestamp"].dt.dayofweek.astype("int8")
    df["doy"] = df["timestamp"].dt.dayofyear.astype("int16")

    wcols = ["temp", "precip", "humidity", "windspeed", "solarradiation", "cloudcover"]
    df = df.merge(weather[wcols], left_on="timestamp", right_index=True, how="left")

    df["charger_num"] = df["site_id"].map(sites["charger_num"]).astype("float32")
    df["area"] = df["site_id"].map(sites["area"]).astype("float32")
    df["lon"] = df["site_id"].map(sites["longitude"]).astype("float32")
    df["lat"] = df["site_id"].map(sites["latitude"]).astype("float32")
    df["poi_density"] = df["site_id"].map(poi_density(sites, poi)).astype("float32")
    df["is_active"] = df["site_id"].map(dict(zip(vol.columns, is_active))).astype("int8")
    df["is_eligible"] = df["site_id"].map(dict(zip(vol.columns, is_eligible))).astype("int8")

    path = os.path.join(OUT, f"panel_{city}.csv.gz")
    df.to_csv(path, index=False, compression="gzip")
    print(f"{city}: rows={len(df):,} sites={N} active={int(is_active.sum())} "
          f"eligible={int(is_eligible.sum())} peak_rate={df['peak'].mean():.2%} "
          f"-> {os.path.getsize(path)/1e6:.0f} MB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", nargs="+", default=["LOA", "MEL"])
    args = ap.parse_args()
    for c in args.cities:
        build_city(c)


if __name__ == "__main__":
    main()
