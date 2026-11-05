"""Schema / consistency checks for the CHARGED city folders.

Run after touching the data (or before a long experiment) to make sure every
city still loads and that the tables agree with each other.

    python scripts/validate_data.py            # all cities
    python scripts/validate_data.py --cities AMS SZH
    python scripts/validate_data.py --quick    # skip the big matrices

Exits with status 1 when any check fails.
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]
INFO_COLUMNS = ["city", "country", "abbreviation", "total_chargers", "total_sites",
                "DBSCAN_eps", "total_duration", "total_volume", "avg_power"]
HOURS = 4392  # 2023-04-01 00:00 .. 2023-09-30 23:00


def check_city(city: str, quick: bool = False) -> list[str]:
    d = os.path.join(DATA_ROOT, city)
    if not os.path.isdir(d):
        return [f"missing folder {d}"]

    info = pd.read_csv(os.path.join(d, "info.csv"))
    sites = pd.read_csv(os.path.join(d, "sites.csv"))
    chargers = pd.read_csv(os.path.join(d, "chargers.csv"))
    weather = pd.read_csv(os.path.join(d, "weather.csv"))

    problems = []
    if list(info.columns) != INFO_COLUMNS:
        problems.append(f"info.csv columns {list(info.columns)}")
    if len(info) != 1:
        problems.append(f"info.csv has {len(info)} rows")
    for name, df in (("sites.csv", sites), ("chargers.csv", chargers)):
        if "site_id" not in df.columns:
            problems.append(f"{name} lacks site_id")
    if len(weather) != HOURS:
        problems.append(f"weather.csv has {len(weather)} rows")
    if int(info.total_sites.iloc[0]) != len(sites):
        problems.append("info.total_sites != len(sites)")
    if int(info.total_chargers.iloc[0]) != len(chargers):
        problems.append("info.total_chargers != len(chargers)")
    if not set(chargers.site_id).issubset(set(sites.site_id)):
        problems.append("chargers reference unknown sites")

    if not quick:
        vol = pd.read_csv(os.path.join(d, "volume.csv"), index_col=0)
        dur = pd.read_csv(os.path.join(d, "duration.csv"), index_col=0)
        ep = pd.read_csv(os.path.join(d, "e_price.csv"), index_col=0)
        sp = pd.read_csv(os.path.join(d, "s_price.csv"), index_col=0)
        dist = pd.read_csv(os.path.join(d, "distance.csv"), index_col=0)
        if len(vol) != HOURS:
            problems.append(f"volume.csv has {len(vol)} hours")
        for name, df in (("volume", vol), ("duration", dur), ("e_price", ep), ("s_price", sp)):
            if df.shape[1] != len(sites):
                problems.append(f"{name}.csv has {df.shape[1]} sites, expected {len(sites)}")
        if dist.shape != (len(sites), len(sites)):
            problems.append(f"distance.csv shape {dist.shape}")
        if sorted(map(int, vol.columns)) != sorted(sites.site_id):
            problems.append("volume columns != site ids")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cities", nargs="+", default=CITIES)
    ap.add_argument("--quick", action="store_true", help="skip volume/duration/price/distance matrices")
    args = ap.parse_args(argv)

    failed = False
    for city in args.cities:
        problems = check_city(city, quick=args.quick)
        status = "OK" if not problems else "FAIL"
        failed |= bool(problems)
        print(f"{city}: {status}")
        for p in problems:
            print(f"    - {p}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
