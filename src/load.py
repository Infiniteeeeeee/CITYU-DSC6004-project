"""Data loading helpers for the CHARGED dataset.

Layout per city (all hourly, 2023-04-01 -> 2023-09-30):
  volume.csv     wide: rows=time, cols=site IDs, values=kWh   (TARGET)
  duration.csv   wide: rows=time, cols=site IDs, values=h
  weather.csv    long: columns include 'time', temp, humidity, ...
  sites.csv      site metadata (site_id, lon, lat, charger_num, ...)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]


def _path(city: str, fname: str) -> Path:
    return DATA_DIR / city / fname


def load_wide(city: str, fname: str) -> pd.DataFrame:
    """Load a wide time-series CSV (volume / duration).

    First column is parsed as a datetime index; remaining columns are site IDs.
    """
    df = pd.read_csv(_path(city, fname), index_col=0, parse_dates=True)
    df.index.name = "time"
    df.index = pd.to_datetime(df.index)
    return df


def load_volume(city: str) -> pd.DataFrame:
    return load_wide(city, "volume.csv")


def load_duration(city: str) -> pd.DataFrame:
    return load_wide(city, "duration.csv")


def city_total(city: str, fname: str = "volume.csv") -> pd.Series:
    """Aggregate across sites -> city-level hourly total."""
    return load_wide(city, fname).sum(axis=1).rename("demand")


def load_weather(city: str) -> pd.DataFrame:
    df = pd.read_csv(_path(city, "weather.csv"))
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
    return df


def load_sites(city: str) -> pd.DataFrame:
    return pd.read_csv(_path(city, "sites.csv"))
