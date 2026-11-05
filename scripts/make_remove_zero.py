"""Build ``<CITY>_remove_zero`` data folders locally from the raw CHARGED city folders.

The official CHARGED repository ships two variants per city: the raw folder and a
filtered ``<CITY>_remove_zero`` folder. The filtered variant keeps only the sites
that actually recorded charging activity (``total_volume > 0``) and simply drops
the corresponding columns / rows / chargers everywhere else. It is therefore fully
reproducible from the raw folder - downloading roughly 640 MB is not required.

Usage
-----
    python scripts/make_remove_zero.py --src data --dst data --cities AMS SZH
    python scripts/make_remove_zero.py --src data --dst out --cities JHB --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

import pandas as pd

# Matrices with shape (hours, sites): keep only the surviving site columns.
SITE_MATRICES = ["volume.csv", "duration.csv", "e_price.csv", "s_price.csv"]
# Files that do not depend on the site set and can be copied untouched.
COPIED_FILES = ["weather.csv", "poi.csv"]


def _site_id_column(df: pd.DataFrame) -> str:
    """CHARGED is inconsistent: some tables use ``site_id``, others use ``site``."""
    for col in ("site_id", "site"):
        if col in df.columns:
            return col
    raise KeyError(f"no site id column in {list(df.columns)}")


def _subset_sites(df: pd.DataFrame, keep: set[int], id_col: str) -> pd.DataFrame:
    """Keep rows of a site-level table, preserving the original row order."""
    ids = df[id_col].astype(int)
    return df[ids.isin(keep)].reset_index(drop=True)


def _subset_matrix(path: str, keep: set[int]) -> pd.DataFrame:
    """Keep site columns of an (hours, sites) matrix, preserving column order."""
    df = pd.read_csv(path, index_col=0)
    cols = [c for c in df.columns if int(c) in keep]  # original (string-sorted) order
    if len(cols) != len(keep):
        missing = keep - {int(c) for c in cols}
        raise ValueError(f"{os.path.basename(path)}: {len(missing)} site columns missing, e.g. {sorted(missing)[:5]}")
    return df[cols]


def _subset_distance(path: str, keep: set[int]) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    rows = [c for c in df.index if int(c) in keep]
    cols = [c for c in df.columns if int(c) in keep]
    return df.loc[rows, cols]


def build_city(src_dir: str, dst_dir: str, dry_run: bool = False) -> dict:
    sites = pd.read_csv(os.path.join(src_dir, "sites.csv"))
    id_col = _site_id_column(sites)
    sites[id_col] = sites[id_col].astype(int)

    keep = set(sites.loc[sites["total_volume"] > 0, id_col])
    sites_kept = _subset_sites(sites, keep, id_col).rename(columns={id_col: "site_id"})
    dropped = len(sites) - len(sites_kept)

    stats = {
        "sites_before": len(sites),
        "sites_after": len(sites_kept),
        "dropped": dropped,
        "chargers_after": int(sites_kept["charger_num"].sum()),
        "total_volume": float(sites_kept["total_volume"].sum()),
        "total_duration": float(sites_kept["total_duration"].sum()),
    }
    print(f"  {os.path.basename(src_dir)}: {len(sites)} -> {len(sites_kept)} sites "
          f"(dropped {dropped}), {stats['chargers_after']} chargers")

    if dry_run:
        return stats

    os.makedirs(dst_dir, exist_ok=True)

    # 1. site-level table (normalised to `site_id`)
    sites_kept.to_csv(os.path.join(dst_dir, "sites.csv"), index=False)

    # 2. chargers belonging to surviving sites
    chargers = pd.read_csv(os.path.join(src_dir, "chargers.csv"))
    c_id = _site_id_column(chargers)
    chargers[c_id] = chargers[c_id].astype(int)
    chargers_kept = chargers[chargers[c_id].isin(keep)].rename(columns={c_id: "site_id"})
    chargers_kept.to_csv(os.path.join(dst_dir, "chargers.csv"), index=False)

    # 3. hourly matrices
    for name in SITE_MATRICES:
        _subset_matrix(os.path.join(src_dir, name), keep).to_csv(os.path.join(dst_dir, name))

    # 4. distance matrix
    _subset_distance(os.path.join(src_dir, "distance.csv"), keep).to_csv(os.path.join(dst_dir, "distance.csv"))

    # 5. files independent of the site set
    for name in COPIED_FILES:
        shutil.copyfile(os.path.join(src_dir, name), os.path.join(dst_dir, name))

    # 6. metadata, fully recomputed (the official filtered info.csv forgets to
    #    recompute total_duration / total_volume - do not copy that bug)
    meta = pd.read_csv(os.path.join(src_dir, "info.csv")).iloc[0]
    weighted_power = (sites_kept["avg_power"] * sites_kept["charger_num"]).sum() / sites_kept["charger_num"].sum()
    info = pd.DataFrame([{
        "city": meta["city"],
        "country": meta["country"],
        "abbreviation": meta["abbreviation"],
        "total_chargers": stats["chargers_after"],
        "total_sites": stats["sites_after"],
        "DBSCAN_eps": meta["DBSCAN_eps"],
        "total_duration": stats["total_duration"],
        "total_volume": stats["total_volume"],
        "avg_power": weighted_power,
    }])
    info.to_csv(os.path.join(dst_dir, "info.csv"), index=False)
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="data", help="folder containing the raw city folders")
    ap.add_argument("--dst", default="data", help="root folder for the generated <CITY>_remove_zero folders")
    ap.add_argument("--cities", nargs="+", default=["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"])
    ap.add_argument("--dry-run", action="store_true", help="only report how many sites would be kept")
    args = ap.parse_args(argv)

    for city in args.cities:
        src = os.path.join(args.src, city)
        if not os.path.isdir(src):
            print(f"skip {city}: {src} not found", file=sys.stderr)
            continue
        print(f"[{city}]")
        build_city(src, os.path.join(args.dst, f"{city}_remove_zero"), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
