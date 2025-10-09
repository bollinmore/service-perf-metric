from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


def _to_int(s: str) -> int | None:
    try:
        return int(s)
    except Exception:
        return None


def _avg(vals: List[int]) -> int:
    return round(sum(vals) / len(vals)) if vals else 0


def _min(vals: List[int]) -> int:
    return min(vals) if vals else 0


def _max(vals: List[int]) -> int:
    return max(vals) if vals else 0


def _median(vals: List[int]) -> int:
    if not vals:
        return 0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return round((s[mid - 1] + s[mid]) / 2)


def main() -> int:
    src = Path("result") / "summary.csv"
    if not src.exists():
        print(f"Missing input: {src}")
        return 1

    # Read combined summary and gather raw values per version and per service
    versions: List[str] = []
    per_version_values: Dict[str, List[int]] = {}
    per_service_values: Dict[str, Dict[str, List[int]]] = {}

    with src.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or header[0] != "service":
            print("Invalid header: expected first column to be 'service'")
            return 1
        versions = header[1:]
        per_version_values = {v: [] for v in versions}

        for row in reader:
            if not row:
                continue
            service = row[0]
            if service not in per_service_values:
                per_service_values[service] = {v: [] for v in versions}
            for i, v in enumerate(versions, start=1):
                if i >= len(row):
                    continue
                val = _to_int(row[i])
                if val is None:
                    continue
                per_version_values[v].append(val)
                per_service_values[service][v].append(val)

    out_dir = Path("result")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Overall per-version stats
    overall_path = out_dir / "summary_stats.csv"
    with overall_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", *versions])
        writer.writerow(["Average", *[_avg(per_version_values[v]) for v in versions]])
        writer.writerow(["Max", *[_max(per_version_values[v]) for v in versions]])
        writer.writerow(["Min", *[_min(per_version_values[v]) for v in versions]])
        writer.writerow(["Median", *[_median(per_version_values[v]) for v in versions]])

    # Per-service stats
    service_stats_path = out_dir / "service_stats.csv"
    with service_stats_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        cols: List[str] = ["service"]
        for v in versions:
            cols += [f"{v}_avg", f"{v}_max", f"{v}_min", f"{v}_median"]
        writer.writerow(cols)

        # Preserve service appearance order by iterating over input dict
        for service, per_ver in per_service_values.items():
            row: List[object] = [service]
            for v in versions:
                vals = per_ver.get(v, [])
                row += [_avg(vals), _max(vals), _min(vals), _median(vals)]
            writer.writerow(row)

    print(f"Wrote overall stats to {overall_path}")
    print(f"Wrote per-service stats to {service_stats_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

