from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, List, Tuple


LOG_PATTERN = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+(.*?)\s+-\s+(?:loading_time|elapsed):\s+(\d+)\s+ms",
    re.IGNORECASE,
)


def parse_log_lines(lines: Iterable[str]) -> List[Tuple[str, int]]:
    """Parse lines from a log and return list of (service, loading_time_ms)."""
    entries: List[Tuple[str, int]] = []
    for line in lines:
        m = LOG_PATTERN.search(line)
        if not m:
            continue
        service = m.group(1).strip()
        try:
            ms = int(m.group(2))
        except ValueError:
            continue
        entries.append((service, ms))
    return entries


def process_dir(dir_path: Path, file_glob: str) -> int:
    """Process a PerformanceLog directory and write summary.csv.

    Returns the number of rows written (excluding header).
    """
    files = sorted(dir_path.glob(file_glob))
    all_entries: List[Tuple[str, int]] = []
    for fp in files:
        try:
            # Use utf-8-sig to strip BOM so the first line matches the pattern
            try:
                with fp.open("r", encoding="utf-8-sig", errors="strict") as f:
                    all_entries.extend(parse_log_lines(f))
            except UnicodeError:
                # Fallback to utf-8 with ignore if encoding is inconsistent
                with fp.open("r", encoding="utf-8", errors="ignore") as f:
                    all_entries.extend(parse_log_lines(f))
        except FileNotFoundError:
            continue

    if not all_entries:
        return 0

    out_path = dir_path / "summary.csv"
    with out_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["service", "loading_time_ms"])
        writer.writerows(all_entries)

    return len(all_entries)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract service loading times from PerformanceLog")
    parser.add_argument(
        "--dir",
        dest="single_dir",
        type=Path,
        help="Process a single PerformanceLog directory (e.g., InQuire_2.0.1.0/PerformanceLog)",
    )
    parser.add_argument(
        "--pattern",
        default="*.log",
        help="Glob pattern for log files within --dir (default: *.log)",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine the three generated summaries into result/summary,csv with version headers",
    )
    args = parser.parse_args()

    if args.combine:
        # Combine existing summary.csv files into result/summary.csv
        versions = ["2.0.1.0", "2.0.1.2", "2.0.1.3"]
        version_map = {
            "2.0.1.0": Path("InQuire_2.0.1.0") / "PerformanceLog" / "summary.csv",
            "2.0.1.2": Path("InQuire_2.0.1.2") / "PerformanceLog" / "summary.csv",
            "2.0.1.3": Path("InQuire_2.0.1.3") / "PerformanceLog" / "summary.csv",
        }

        # Load summaries and keep all raw records per service for each version
        from collections import defaultdict

        per_version_lists: dict[str, dict[str, list[int]]] = {}
        all_services: set[str] = set()
        service_order: list[str] = []

        for ver in versions:
            csv_path = version_map[ver]
            svc_to_vals: dict[str, list[int]] = defaultdict(list)
            if csv_path.exists():
                with csv_path.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for row in reader:
                        if len(row) < 2:
                            continue
                        svc, ms = row[0].strip(), row[1].strip()
                        try:
                            ms_i = int(ms)
                        except ValueError:
                            continue
                        svc_to_vals[svc].append(ms_i)
                        if svc not in service_order:
                            service_order.append(svc)
            per_version_lists[ver] = svc_to_vals
            all_services.update(svc_to_vals.keys())

        # Prepare output directory and file
        out_dir = Path("result")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "summary.csv"

        # Write combined CSV: service, 2.0.1.0, 2.0.1.2, 2.0.1.3
        with out_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["service", *versions])
            # Follow original appearance order across source CSVs
            ordered_services = service_order if service_order else sorted(all_services)
            for svc in ordered_services:
                # Determine how many rows are needed for this service
                max_len = 0
                per_ver_lists = []
                for ver in versions:
                    lst = per_version_lists.get(ver, {}).get(svc, [])
                    per_ver_lists.append(lst)
                    if len(lst) > max_len:
                        max_len = len(lst)
                # Emit one row per index position, blank where no value
                for i in range(max_len):
                    row = [svc]
                    for lst in per_ver_lists:
                        row.append(lst[i] if i < len(lst) else "")
                    writer.writerow(row)

        print(f"Wrote combined summary to {out_file}")
        return 0

    if args.single_dir:
        rows = process_dir(args.single_dir, args.pattern)
        if rows <= 0:
            print(f"No matching entries found in {args.single_dir} (pattern {args.pattern})")
        else:
            print(f"Wrote {rows} data rows to {args.single_dir / 'summary.csv'}")
        return 0

    # Default: process known folders based on earlier requirements
    configs = [
        (Path("InQuire_2.0.1.0") / "PerformanceLog", "*.log"),
        (Path("InQuire_2.0.1.2") / "PerformanceLog", "*.log"),
        (Path("InQuire_2.0.1.3") / "PerformanceLog", "*loading.log"),  # ignore *login.log
    ]

    total_written = 0
    for d, pattern in configs:
        if not d.exists():
            continue
        rows = process_dir(d, pattern)
        if rows > 0:
            print(f"Wrote {rows} data rows to {d / 'summary.csv'}")
            total_written += rows
        else:
            print(f"No matching entries found in {d} (pattern {pattern})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
