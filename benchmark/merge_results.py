from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


EXPECTED_COLUMNS = [
    "game_id",
    "block_id",
    "engine_white",
    "engine_black",
    "opening_white",
    "opening_black",
    "heuristic_white",
    "heuristic_black",
    "depth_white",
    "depth_black",
    "sim_white",
    "sim_black",
    "stockfish_elo",
    "result_white",
    "result_black",
    "plies",
    "avg_move_ms_white",
    "p95_move_ms_white",
    "max_move_ms_white",
    "avg_move_ms_black",
    "p95_move_ms_black",
    "max_move_ms_black",
    "max_material_swing_cp",
    "blunder_white",
    "blunder_black",
    "white_castled_before_10",
    "black_castled_before_10",
]


def parse_result(rows: List[Dict[str, str]]) -> Dict[str, float]:
    w = d = l = 0
    for r in rows:
        if r["result_white"] == "W":
            w += 1
        elif r["result_white"] == "L":
            l += 1
        else:
            d += 1
    n = len(rows)
    score = w + 0.5 * d
    win_rate = (score / n * 100.0) if n else 0.0

    def avg(field: str) -> float:
        vals = [float(r[field]) for r in rows if r.get(field, "").strip()]
        return (sum(vals) / len(vals)) if vals else 0.0

    return {
        "games": float(n),
        "W": float(w),
        "D": float(d),
        "L": float(l),
        "score": float(score),
        "win_rate": float(win_rate),
        "avg_plies": avg("plies"),
        "avg_move_ms_white": avg("avg_move_ms_white"),
        "avg_move_ms_black": avg("avg_move_ms_black"),
        "avg_material_swing_cp": avg("max_material_swing_cp"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge benchmark scenario CSV files and produce summary")
    parser.add_argument("--in-dir", default="benchmark_results", help="Input directory containing results_*.csv")
    parser.add_argument("--merged", default="merged_results.csv", help="Merged output CSV path")
    parser.add_argument("--summary", default="summary_by_block.csv", help="Summary output CSV path")
    args = parser.parse_args()

    in_dir = Path(args.in_dir).resolve()
    if not in_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {in_dir}")

    files = sorted(in_dir.glob("results_*.csv"))
    if not files:
        raise FileNotFoundError(f"No results_*.csv files found in {in_dir}")

    merged_path = Path(args.merged).resolve()
    summary_path = Path(args.summary).resolve()

    all_rows: List[Dict[str, str]] = []
    for f in files:
        with f.open("r", newline="", encoding="utf-8") as rf:
            reader = csv.DictReader(rf)
            if reader.fieldnames is None:
                continue
            missing = [c for c in EXPECTED_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise ValueError(f"File {f} is missing columns: {missing}")
            for row in reader:
                all_rows.append({k: row.get(k, "") for k in EXPECTED_COLUMNS})

    all_rows.sort(key=lambda r: (r["block_id"], r["game_id"]))

    with merged_path.open("w", newline="", encoding="utf-8") as wf:
        writer = csv.DictWriter(wf, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    by_block: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in all_rows:
        prefix = row["block_id"].split(".")[0]
        by_block[prefix].append(row)

    summary_header = [
        "block",
        "games",
        "W",
        "D",
        "L",
        "score",
        "win_rate_percent",
        "avg_plies",
        "avg_move_ms_white",
        "avg_move_ms_black",
        "avg_material_swing_cp",
    ]

    with summary_path.open("w", newline="", encoding="utf-8") as sf:
        writer = csv.DictWriter(sf, fieldnames=summary_header)
        writer.writeheader()
        for block in sorted(by_block.keys()):
            m = parse_result(by_block[block])
            writer.writerow(
                {
                    "block": block,
                    "games": int(m["games"]),
                    "W": int(m["W"]),
                    "D": int(m["D"]),
                    "L": int(m["L"]),
                    "score": f"{m['score']:.2f}",
                    "win_rate_percent": f"{m['win_rate']:.2f}",
                    "avg_plies": f"{m['avg_plies']:.2f}",
                    "avg_move_ms_white": f"{m['avg_move_ms_white']:.2f}",
                    "avg_move_ms_black": f"{m['avg_move_ms_black']:.2f}",
                    "avg_material_swing_cp": f"{m['avg_material_swing_cp']:.2f}",
                }
            )

    print(f"Merged {len(files)} files, total rows: {len(all_rows)}")
    print(f"Merged CSV: {merged_path}")
    print(f"Summary CSV: {summary_path}")


if __name__ == "__main__":
    main()
