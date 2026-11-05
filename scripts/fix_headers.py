"""Repair malformed CSV headers in the CHARGED city folders (idempotent).

Two defects exist in the upstream data:

1. ``info.csv`` for LOA / MEL / SPO / SZH has a missing comma, so two columns are
   merged into ``total_siteBSCAN_eps`` (8 names for 9 values). Any reader that
   trusts the header silently shifts every column by one.
2. ``sites.csv`` (MEL, SPO) and ``chargers.csv`` (LOA, SPO, SZH) name the foreign
   key ``site`` instead of ``site_id``, which breaks code that joins on
   ``site_id`` (e.g. the official ``EVDataset`` loader).

The fix rewrites **only the header line**; the remaining bytes are streamed
through untouched. Original headers are stored in ``scripts/header_backup.json``
so the operation can be reverted.

Usage
-----
    python scripts/fix_headers.py --dry-run     # report only
    python scripts/fix_headers.py --apply       # rewrite headers
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys

DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "header_backup.json")
CITIES = ["AMS", "JHB", "LOA", "MEL", "SPO", "SZH"]
SITE_KEYED = {"sites.csv", "chargers.csv"}


def _parse_header(raw: bytes) -> tuple[list[str], bytes]:
    """Return (fields, line-ending) for a raw first line."""
    text = raw.decode("utf-8-sig")
    ending = b"\r\n" if text.endswith("\r\n") else b"\n"
    return next(csv.reader([text.rstrip("\r\n")])), ending


def plan_fix(filename: str, fields: list[str]) -> list[str] | None:
    """Return the corrected field list, or None when the header is already fine."""
    fixed = list(fields)
    if len(fixed) == 8 and fixed[4] == "total_siteBSCAN_eps":
        fixed[4:5] = ["total_sites", "DBSCAN_eps"]
    if filename in SITE_KEYED and "site" in fixed:
        fixed[fixed.index("site")] = "site_id"
    return fixed if fixed != fields else None


def body_digest(path: str) -> str:
    """sha256 of everything after the first line (used to prove data is untouched)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        f.readline()
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rewrite_header(path: str, fields: list[str], ending: bytes) -> None:
    """Replace the first line, streaming the rest of the file verbatim."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(fields)
    new_header = buf.getvalue().encode("utf-8") + ending

    tmp = path + ".tmp"
    with open(path, "rb") as src, open(tmp, "wb") as dst:
        src.readline()  # drop old header
        dst.write(new_header)
        shutil.copyfileobj(src, dst, length=1 << 20)
    os.replace(tmp, path)


def revert() -> int:
    """Restore the original header lines recorded in the backup file."""
    with open(BACKUP_PATH, encoding="utf-8") as f:
        backup = json.load(f)
    for rel, original in sorted(backup.items()):
        city, filename = rel.split("/", 1)
        path = os.path.join(DATA_ROOT, city, filename)
        if not os.path.exists(path):
            print(f"missing: {rel}", file=sys.stderr)
            continue
        with open(path, "rb") as f:
            fields, ending = _parse_header(f.readline())
        before_body = body_digest(path)
        rewrite_header(path, next(csv.reader([original])), ending)
        if body_digest(path) != before_body:  # pragma: no cover
            raise RuntimeError(f"data bytes changed for {rel}!")
        print(f"[{city}] {filename}: restored {len(next(csv.reader([original])))}-field header")
    print(f"reverted {len(backup)} file(s)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="rewrite the headers (default: dry run)")
    ap.add_argument("--dry-run", action="store_true", help="report only (default)")
    ap.add_argument("--revert", action="store_true", help="restore original headers from header_backup.json")
    args = ap.parse_args(argv)
    if args.revert:
        return revert()
    apply = args.apply and not args.dry_run

    backup: dict[str, str] = {}
    if os.path.exists(BACKUP_PATH):
        with open(BACKUP_PATH, encoding="utf-8") as f:
            backup = json.load(f)

    planned, skipped = [], []
    for city in CITIES:
        city_dir = os.path.join(DATA_ROOT, city)
        if not os.path.isdir(city_dir):
            print(f"skip missing city folder: {city_dir}", file=sys.stderr)
            continue
        for filename in sorted(os.listdir(city_dir)):
            if not filename.endswith(".csv"):
                continue
            path = os.path.join(city_dir, filename)
            with open(path, "rb") as f:
                raw_header = f.readline()
            fields, ending = _parse_header(raw_header)
            fixed = plan_fix(filename, fields)
            if fixed is None:
                skipped.append(f"{city}/{filename}")
                continue
            planned.append((city, filename, path, fields, fixed, ending, raw_header))

    for city, filename, path, fields, fixed, ending, raw_header in planned:
        print(f"[{city}] {filename}")
        print(f"  before ({len(fields)}): {','.join(fields)}")
        print(f"  after  ({len(fixed)}): {','.join(fixed)}")
        if not apply:
            continue
        before_body = body_digest(path)
        rel = f"{city}/{filename}"
        backup.setdefault(rel, raw_header.decode("utf-8-sig").rstrip("\r\n"))
        rewrite_header(path, fixed, ending)
        after_body = body_digest(path)
        if before_body != after_body:  # pragma: no cover - safety net
            raise RuntimeError(f"data bytes changed for {rel}!")
        print(f"  written, body sha256 unchanged ({before_body[:12]}...)")

    print(f"\n{'applied' if apply else 'planned'}: {len(planned)} file(s); untouched: {len(skipped)}")

    if apply and planned:
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"original headers saved to {os.path.relpath(BACKUP_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
