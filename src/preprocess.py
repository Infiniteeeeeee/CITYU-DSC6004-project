"""Feature engineering for city-level hourly EV charging demand.

Target: `demand` = city-wide hourly total charging volume (kWh).

Features:
  - calendar: hour, dayofweek, is_weekend, month + cyclic sin/cos encodings
  - lag of demand: 1, 2, 3, 24, 168 hours
  - rolling: mean(24h), std(24h), mean(168h)
  - weather: numeric columns from weather.csv (merged on hour)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.load import city_total, load_weather

LAGS = [1, 2, 3, 24, 168]
ROLLING = [24, 168]

WEATHER_COLS = [
    "temp", "feelslike", "humidity", "dew", "precip", "snow", "snowdepth",
    "windgust", "windspeed", "winddir", "pressure", "visibility", "cloudcover",
    "solarradiation", "solarenergy", "uvindex", "conditions",
]


def build_features(city: str, include_weather: bool = True) -> pd.DataFrame:
    """Build the feature matrix + target for one city (hourly)."""
    demand = city_total(city)
    df = pd.DataFrame({"demand": demand})

    # --- calendar features ---
    df["hour"] = df.index.hour
    df["dayofweek"] = df.index.dayofweek
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)
    df["month"] = df.index.month

    # cyclic encodings (help linear models capture periodicity)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)

    # --- lag features ---
    for lag in LAGS:
        df[f"lag_{lag}"] = df["demand"].shift(lag)

    # --- rolling features (past-only: exclude current hour to avoid leakage) ---
    past = df["demand"].shift(1)
    for w in ROLLING:
        df[f"roll_mean_{w}h"] = past.rolling(w).mean()
    df["roll_std_24h"] = past.rolling(24).std()

    # --- weather features ---
    if include_weather:
        w = load_weather(city)
        w = w[~w.index.duplicated()]
        df = df.join(w[WEATHER_COLS], how="left")
        df[WEATHER_COLS] = df[WEATHER_COLS].ffill().bfill()

    return df


def split_train_val_test(
    df: pd.DataFrame,
    val_start: str = "2023-08-01",
    test_start: str = "2023-09-01",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Time-ordered split: Apr–Jul train, Aug val, Sep test (no shuffle).

    Drops the leading rows that carry NaN from lag/rolling features.
    """
    df = df.dropna().copy()
    train = df[df.index < val_start]
    val = df[(df.index >= val_start) & (df.index < test_start)]
    test = df[df.index >= test_start]
    return train, val, test
