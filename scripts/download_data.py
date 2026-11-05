#!/usr/bin/env python
"""Download the CHARGED city tables needed by this project.

The raw dataset lives in the public CHARGED repository. We fetch the plain CSV
files directly; the two Amsterdam files larger than 100 MB are shipped there as
a RAR archive and are *not* needed for the main results (see README).

    python scripts/download_data.py                 # all six cities
    python scripts/download_data.py --cities LOA MEL
    python scripts/download_data.py --force         # re-download

After downloading, run ``python scripts/fix_headers.py --apply`` once: the
upstream files contain a malformed info.csv header and a few tables that name
the site column "site" instead of "site_id".
"""
import argparse
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BASE_URL = "https://raw.githubusercontent.com/IntelligentSystemsLab/CHARGED/main/data"

CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]
FILES = ["info.csv", "sites.csv", "chargers.csv", "poi.csv", "weather.csv",
         "distance.csv", "volume.csv", "duration.csv", "e_price.csv", "s_price.csv"]

# files that only exist inside the RAR archive upstream
RAR_ONLY = {("AMS", "duration.csv"), ("AMS", "distance.csv")}


def download(city: str, name: str, force: bool = False) -> bool:
    dst_dir = os.path.join(DATA, city)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name)
    if os.path.exists(dst) and not force:
        print(f"  skip {city}/{name} (exists)")
        return True
    url = f"{BASE_URL}/{city}/{name}"
    tmp = dst + ".part"
    try:
        with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = 100 * done / total
                    print(f"\r  {city}/{name}: {pct:5.1f}%", end="", flush=True)
        print(f"\r  {city}/{name}: done ({os.path.getsize(tmp)/1e6:.1f} MB)")
        os.replace(tmp, dst)
        return True
    except Exception as exc:  # noqa: BLE001
        if os.path.exists(tmp):
            os.remove(tmp)
        print(f"\n  FAILED {city}/{name}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cities", nargs="+", default=CITIES, choices=CITIES)
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    failed = []
    for city in args.cities:
        print(f"[{city}]")
        for name in FILES:
            if (city, name) in RAR_ONLY:
                print(f"  skip {city}/{name}: only inside csv-larger-than-100MB.rar upstream "
                      f"(not needed for the main results)")
                continue
            if not download(city, name, force=args.force):
                failed.append(f"{city}/{name}")

    print("\nDone." if not failed else f"\n{len(failed)} file(s) failed: {failed}")
    print("Next: python scripts/fix_headers.py --apply  (repairs the upstream headers)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
