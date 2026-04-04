from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

BLOCK_ORDER = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def to_float(v: str) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def score_from_wdl(w: int, d: int) -> float:
    return w + 0.5 * d


def win_rate_from_score(score: float, n: int) -> float:
    return (score / n * 100.0) if n else 0.0


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def block_prefix(block_id: str) -> str:
    return block_id.split(".")[0]


def avg(values: Iterable[float]) -> float:
    vals = list(values)
    return (sum(vals) / len(vals)) if vals else 0.0


def group_rows_by_block(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in rows:
        grouped[block_prefix(r["block_id"])].append(r)
    return grouped


def summarize_wdl_for_result_field(rows: List[Dict[str, str]], result_field: str) -> Tuple[int, int, int]:
    w = d = l = 0
    for r in rows:
        outcome = (r.get(result_field) or "").strip().upper()
        if outcome == "W":
            w += 1
        elif outcome == "L":
            l += 1
        else:
            d += 1
    return w, d, l


def scenario_table(block_rows: List[Dict[str, str]]) -> List[List[str]]:
    by_scenario: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in block_rows:
        by_scenario[r["block_id"]].append(r)

    out: List[List[str]] = []
    for scenario_id in sorted(by_scenario.keys()):
        rows = by_scenario[scenario_id]
        w, d, l = summarize_wdl_for_result_field(rows, "result_white")
        n = len(rows)
        score = score_from_wdl(w, d)
        wr = win_rate_from_score(score, n)
        cond = scenario_id.split(".", 1)[1] if "." in scenario_id else scenario_id
        out.append([
            scenario_id,
            cond,
            str(n),
            str(w),
            str(d),
            str(l),
            f"{score:.2f}",
            f"{wr:.2f}",
        ])
    return out


def engine_color_table(block_rows: List[Dict[str, str]]) -> List[List[str]]:
    engines = sorted({r["engine_white"] for r in block_rows} | {r["engine_black"] for r in block_rows})
    out: List[List[str]] = []

    for eng in engines:
        as_white = [r for r in block_rows if r["engine_white"] == eng]
        as_black = [r for r in block_rows if r["engine_black"] == eng]

        w_w, d_w, _ = summarize_wdl_for_result_field(as_white, "result_white")
        n_w = len(as_white)
        score_w = score_from_wdl(w_w, d_w)
        wr_w = win_rate_from_score(score_w, n_w)

        w_b, d_b, _ = summarize_wdl_for_result_field(as_black, "result_black")
        n_b = len(as_black)
        score_b = score_from_wdl(w_b, d_b)
        wr_b = win_rate_from_score(score_b, n_b)

        out.append([
            eng,
            str(n_w),
            f"{score_w:.2f}",
            f"{wr_w:.2f}",
            str(n_b),
            f"{score_b:.2f}",
            f"{wr_b:.2f}",
        ])

    return out


def quality_table(block_rows: List[Dict[str, str]]) -> List[List[str]]:
    by_scenario: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in block_rows:
        by_scenario[r["block_id"]].append(r)

    out: List[List[str]] = []
    for scenario_id in sorted(by_scenario.keys()):
        rows = by_scenario[scenario_id]

        avg_plies = avg(to_float(r.get("plies", "")) for r in rows)
        avg_w_ms = avg(to_float(r.get("avg_move_ms_white", "")) for r in rows)
        avg_b_ms = avg(to_float(r.get("avg_move_ms_black", "")) for r in rows)
        p95_w_ms = avg(to_float(r.get("p95_move_ms_white", "")) for r in rows)
        p95_b_ms = avg(to_float(r.get("p95_move_ms_black", "")) for r in rows)
        avg_swing = avg(to_float(r.get("max_material_swing_cp", "")) for r in rows)

        open_w = avg(to_float(r.get("white_castled_before_10", "")) for r in rows) * 100.0
        open_b = avg(to_float(r.get("black_castled_before_10", "")) for r in rows) * 100.0

        out.append([
            scenario_id,
            f"{avg_plies:.2f}",
            f"{avg_w_ms:.2f}",
            f"{avg_b_ms:.2f}",
            f"{p95_w_ms:.2f}",
            f"{p95_b_ms:.2f}",
            f"{avg_swing:.2f}",
            f"{open_w:.2f}",
            f"{open_b:.2f}",
        ])

    return out


def scenario_compact_stats(block_rows: List[Dict[str, str]]) -> List[Dict[str, float | str]]:
    by_scenario: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in block_rows:
        by_scenario[r["block_id"]].append(r)

    out: List[Dict[str, float | str]] = []
    for scenario_id, rows in by_scenario.items():
        w, d, _ = summarize_wdl_for_result_field(rows, "result_white")
        n = len(rows)
        out.append(
            {
                "scenario": scenario_id,
                "games": float(n),
                "score": score_from_wdl(w, d),
                "wr": win_rate_from_score(score_from_wdl(w, d), n),
                "plies": avg(to_float(r.get("plies", "")) for r in rows),
            }
        )
    return out


def top_bottom_scenarios_table(block_rows: List[Dict[str, str]], top_n: int = 2) -> str:
    stats = scenario_compact_stats(block_rows)
    if not stats:
        return markdown_table(["Type", "Scenario", "Games", "Win rate (%)", "Avg plies"], [])

    stats_sorted = sorted(stats, key=lambda x: (float(x["wr"]), float(x["games"]), str(x["scenario"])))
    bottom = stats_sorted[:top_n]
    top = list(reversed(stats_sorted[-top_n:]))

    headers = ["Type", "Scenario", "Games", "Win rate (%)", "Avg plies"]
    rows: List[List[str]] = []
    for item in top:
        rows.append([
            "Top",
            str(item["scenario"]),
            str(int(item["games"])),
            f"{float(item['wr']):.2f}",
            f"{float(item['plies']):.2f}",
        ])
    for item in bottom:
        rows.append([
            "Bottom",
            str(item["scenario"]),
            str(int(item["games"])),
            f"{float(item['wr']):.2f}",
            f"{float(item['plies']):.2f}",
        ])

    return markdown_table(headers, rows)


def summarize_rows(rows: List[Dict[str, str]]) -> Dict[str, float]:
    w, d, l = summarize_wdl_for_result_field(rows, "result_white")
    n = len(rows)
    sc = score_from_wdl(w, d)
    return {
        "games": float(n),
        "w": float(w),
        "d": float(d),
        "l": float(l),
        "score": sc,
        "wr": win_rate_from_score(sc, n),
        "plies": avg(to_float(r.get("plies", "")) for r in rows),
        "ms_w": avg(to_float(r.get("avg_move_ms_white", "")) for r in rows),
        "ms_b": avg(to_float(r.get("avg_move_ms_black", "")) for r in rows),
    }


def _extract_int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def block_group_label(block: str, scenario_id: str) -> str:
    if block in {"I", "II"}:
        if scenario_id.startswith(f"{block}.3"):
            d = _extract_int(r"\.d(\d+)", scenario_id)
            return f"{block}.3 (Stockfish, d={d if d is not None else '?'}, elo grouped)"
        if scenario_id.startswith(f"{block}.2"):
            d = _extract_int(r"\.d(\d+)", scenario_id)
            return f"{block}.2 (vs Minimax, d={d if d is not None else '?'})"
        if scenario_id.startswith(f"{block}.1"):
            return f"{block}.1 (vs Random)"
        return scenario_id

    if block == "III":
        d = _extract_int(r"\.d(\d+)", scenario_id)
        return f"III (opening on vs off, d={d if d is not None else '?'})"

    if block == "IV":
        if scenario_id.startswith("IV.1"):
            return "IV.1 (vs Random)"
        sim = _extract_int(r"\.sim(\d+)", scenario_id)
        if sim is not None:
            return f"IV.2 (vs Stockfish, sim={sim}, elo grouped)"
        return "IV.2 (vs Stockfish, grouped)"

    if block in {"V", "VI"}:
        sim = _extract_int(r"\.sim(\d+)", scenario_id)
        if sim is not None:
            return f"{block}.1 (vs Stockfish, sim={sim}, elo grouped)"
        return f"{block}.1 (vs Stockfish, grouped)"

    if block in {"VII", "VIII"}:
        prefix = ".".join(scenario_id.split(".")[:2])
        return prefix

    return scenario_id


def block_compact_group_table(block: str, block_rows: List[Dict[str, str]]) -> str:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in block_rows:
        lbl = block_group_label(block, r.get("block_id", ""))
        grouped[lbl].append(r)

    headers = [
        "Group",
        "Games",
        "W-D-L",
        "Score",
        "Win rate (%)",
        "Avg plies",
        "Avg ms W/B",
    ]

    def order_key(label: str) -> Tuple[int, int, str]:
        base_num = _extract_int(r"\.(\d+)", label) or 99
        sim_num = _extract_int(r"sim=(\d+)", label)
        return (base_num, sim_num if sim_num is not None else -1, label)

    rows: List[List[str]] = []
    for lbl in sorted(grouped.keys(), key=order_key):
        m = summarize_rows(grouped[lbl])
        rows.append([
            lbl,
            str(int(m["games"])),
            f"{int(m['w'])}-{int(m['d'])}-{int(m['l'])}",
            f"{m['score']:.2f}",
            f"{m['wr']:.2f}",
            f"{m['plies']:.2f}",
            f"{m['ms_w']:.0f}/{m['ms_b']:.0f}",
        ])

    return markdown_table(headers, rows)


def markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    line_head = "| " + " | ".join(headers) + " |"
    line_sep = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = [line_head, line_sep]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def build_summary_table(summary_rows: List[Dict[str, str]]) -> str:
    order_idx = {b: i for i, b in enumerate(BLOCK_ORDER)}
    rows_sorted = sorted(summary_rows, key=lambda r: order_idx.get(r.get("block", ""), 999))
    headers = [
        "Block",
        "Games",
        "W",
        "D",
        "L",
        "Score",
        "Win rate (%)",
        "Avg plies",
        "Avg move ms (White)",
        "Avg move ms (Black)",
        "Avg material swing (cp)",
    ]
    rows: List[List[str]] = []
    for r in rows_sorted:
        rows.append([
            r.get("block", ""),
            r.get("games", ""),
            r.get("W", ""),
            r.get("D", ""),
            r.get("L", ""),
            r.get("score", ""),
            r.get("win_rate_percent", ""),
            r.get("avg_plies", ""),
            r.get("avg_move_ms_white", ""),
            r.get("avg_move_ms_black", ""),
            r.get("avg_material_swing_cp", ""),
        ])
    return markdown_table(headers, rows)


def summary_index(summary_rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {r.get("block", ""): r for r in summary_rows}


def find_score_rate(summary_rows: List[Dict[str, str]], block: str) -> Tuple[float, float, float, float, float]:
    idx = summary_index(summary_rows)
    row = idx.get(block, {})
    return (
        to_float(row.get("score", "0")),
        to_float(row.get("win_rate_percent", "0")),
        to_float(row.get("avg_plies", "0")),
        to_float(row.get("avg_move_ms_white", "0")),
        to_float(row.get("avg_move_ms_black", "0")),
    )


def engine_role_metrics(rows: List[Dict[str, str]], engine: str) -> Dict[str, float]:
    as_white = [r for r in rows if r.get("engine_white") == engine]
    as_black = [r for r in rows if r.get("engine_black") == engine]

    w_w, d_w, _ = summarize_wdl_for_result_field(as_white, "result_white")
    w_b, d_b, _ = summarize_wdl_for_result_field(as_black, "result_black")

    n_w = len(as_white)
    n_b = len(as_black)
    score_w = score_from_wdl(w_w, d_w)
    score_b = score_from_wdl(w_b, d_b)

    return {
        "games_white": float(n_w),
        "score_white": score_w,
        "wr_white": win_rate_from_score(score_w, n_w),
        "games_black": float(n_b),
        "score_black": score_b,
        "wr_black": win_rate_from_score(score_b, n_b),
        "avg_ms_white": avg(to_float(r.get("avg_move_ms_white", "")) for r in as_white),
        "avg_ms_black": avg(to_float(r.get("avg_move_ms_black", "")) for r in as_black),
    }


def opening_survival(rows: List[Dict[str, str]]) -> Tuple[float, float]:
    return (
        avg(to_float(r.get("white_castled_before_10", "")) for r in rows) * 100.0,
        avg(to_float(r.get("black_castled_before_10", "")) for r in rows) * 100.0,
    )


def block_compact_table(summary_rows: List[Dict[str, str]]) -> str:
    headers = [
        "Block",
        "Research focus",
        "Games",
        "Win rate (%)",
        "Avg plies",
        "Tempo note",
    ]

    focus = {
        "I": "AlphaBeta baseline (opening off)",
        "II": "AlphaBeta + opening",
        "III": "Opening on vs off (AB internal)",
        "IV": "MCTS baseline (no heur, no opening)",
        "V": "MCTS + heuristic",
        "VI": "MCTS + heuristic + opening",
        "VII": "MCTS variants head-to-head",
        "VIII": "AlphaBeta vs MCTS direct",
    }

    idx = summary_index(summary_rows)
    rows: List[List[str]] = []
    for b in BLOCK_ORDER:
        r = idx.get(b)
        if not r:
            continue
        ms_w = to_float(r.get("avg_move_ms_white", "0"))
        ms_b = to_float(r.get("avg_move_ms_black", "0"))
        tempo = "Black slower" if ms_b > ms_w else "White slower"
        rows.append([
            b,
            focus.get(b, ""),
            r.get("games", ""),
            r.get("win_rate_percent", ""),
            r.get("avg_plies", ""),
            tempo,
        ])

    return markdown_table(headers, rows)


def key_comparison_table(summary_rows: List[Dict[str, str]]) -> str:
    headers = [
        "Comparison",
        "Base block",
        "Compared block",
        "Delta win rate (pp)",
        "Delta avg plies",
        "Interpretation",
    ]

    rows: List[List[str]] = []

    def add_cmp(label: str, b0: str, b1: str, note_pos: str, note_neg: str) -> None:
        _, wr0, pl0, _, _ = find_score_rate(summary_rows, b0)
        _, wr1, pl1, _, _ = find_score_rate(summary_rows, b1)
        d_wr = wr1 - wr0
        d_pl = pl1 - pl0
        if abs(d_wr) < 0.25:
            note = "Effect is neutral in this run"
        else:
            note = note_pos if d_wr > 0 else note_neg
        rows.append([
            label,
            b0,
            b1,
            f"{d_wr:+.2f}",
            f"{d_pl:+.2f}",
            note,
        ])

    add_cmp("Opening effect on AlphaBeta", "I", "II", "Opening helps AB", "Opening hurts AB in this run")
    add_cmp("Heuristic effect on MCTS", "IV", "V", "Heuristic helps", "Heuristic not yet helpful")
    add_cmp("Opening on top of heuristic", "V", "VI", "Opening + heuristic synergy", "Opening adds noise")
    add_cmp("MCTS variants vs AB direct", "III", "VIII", "Cross-family matchup is favorable", "Cross-family matchup is tougher")

    return markdown_table(headers, rows)


def block_deep_table(summary_rows: List[Dict[str, str]], by_block: Dict[str, List[Dict[str, str]]]) -> str:
    headers = [
        "Block",
        "Focus engine",
        "WR as White (%)",
        "WR as Black (%)",
        "Opening survival W/B (%)",
        "Avg ms (focus white/black)",
        "Insight",
    ]

    focus_engine = {
        "I": "alphabeta",
        "II": "alphabeta",
        "III": "alphabeta",
        "IV": "mcts",
        "V": "mcts_heuristic",
        "VI": "mcts_heuristic",
        "VII": "mcts_heuristic",
        "VIII": "alphabeta",
    }

    rows: List[List[str]] = []
    for b in BLOCK_ORDER:
        block_rows = by_block.get(b, [])
        if not block_rows:
            continue
        eng = focus_engine.get(b, "")
        m = engine_role_metrics(block_rows, eng) if eng else {
            "wr_white": 0.0,
            "wr_black": 0.0,
            "avg_ms_white": 0.0,
            "avg_ms_black": 0.0,
        }
        ow, ob = opening_survival(block_rows)

        side_bias = m["wr_black"] - m["wr_white"]
        if side_bias > 10:
            insight = "Noticeable black-side advantage"
        elif side_bias < -10:
            insight = "Noticeable white-side advantage"
        else:
            insight = "Side balance relatively stable"

        rows.append([
            b,
            eng,
            f"{m['wr_white']:.2f}",
            f"{m['wr_black']:.2f}",
            f"{ow:.2f}/{ob:.2f}",
            f"{m['avg_ms_white']:.0f}/{m['avg_ms_black']:.0f}",
            insight,
        ])

    return markdown_table(headers, rows)


def build_markdown(summary_rows: List[Dict[str, str]], merged_rows: List[Dict[str, str]], top_n: int = 2) -> str:
    by_block = group_rows_by_block(merged_rows)

    parts: List[str] = []
    parts.append("# Bao cao thong ke benchmark (ban gon + de hieu)")
    parts.append("")
    parts.append("Tai lieu nay duoc tao tu dong boi benchmark/generate_block_stats_md.py")
    parts.append("")
    parts.append("Nguon du lieu:")
    parts.append("- summary by block: summary_by_block.csv")
    parts.append("- game level: merged_results.csv")
    parts.append("")
    parts.append("## 1) Bang tong hop compact")
    parts.append("")
    parts.append(block_compact_table(summary_rows))
    parts.append("")
    parts.append("## 2) So sanh key effects (gop block)")
    parts.append("")
    parts.append(key_comparison_table(summary_rows))
    parts.append("")
    parts.append("## 3) Chi so an theo role engine")
    parts.append("")
    parts.append(block_deep_table(summary_rows, by_block))
    parts.append("")
    parts.append("## 4) Snapshot tung block (ban gon)")
    parts.append("")

    focus_engine = {
        "I": "alphabeta",
        "II": "alphabeta",
        "III": "alphabeta",
        "IV": "mcts",
        "V": "mcts_heuristic",
        "VI": "mcts_heuristic",
        "VII": "mcts_heuristic",
        "VIII": "alphabeta",
    }

    for block in BLOCK_ORDER:
        block_rows = by_block.get(block, [])
        if not block_rows:
            continue

        eng = focus_engine.get(block, "")
        m = engine_role_metrics(block_rows, eng) if eng else {
            "wr_white": 0.0,
            "wr_black": 0.0,
            "avg_ms_white": 0.0,
            "avg_ms_black": 0.0,
        }
        ow, ob = opening_survival(block_rows)

        parts.append(f"### Block {block}")
        parts.append("")
        parts.append(
            markdown_table(
                [
                    "Focus engine",
                    "WR as White (%)",
                    "WR as Black (%)",
                    "Opening survival W/B (%)",
                    "Avg ms (focus W/B)",
                ],
                [[
                    eng,
                    f"{m['wr_white']:.2f}",
                    f"{m['wr_black']:.2f}",
                    f"{ow:.2f}/{ob:.2f}",
                    f"{m['avg_ms_white']:.0f}/{m['avg_ms_black']:.0f}",
                ]],
            )
        )
        parts.append("")
        parts.append("Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):")
        parts.append("")
        parts.append(block_compact_group_table(block, block_rows))
        parts.append("")

    parts.append("## 5) Bang tong hop goc (tham chieu)")
    parts.append("")
    parts.append(build_summary_table(summary_rows))
    parts.append("")
    parts.append("## 6) Cong thuc")
    parts.append("")
    parts.append("- Score = W + 0.5 * D")
    parts.append("- WinRate = Score / Games * 100")
    parts.append("- WinRate as White(engine X) = (W + 0.5*D tren cac van engine_white == X) / GamesWhite * 100")
    parts.append("- WinRate as Black(engine X) = (W + 0.5*D tren cac van engine_black == X, dung result_black) / GamesBlack * 100")
    parts.append("- Opening survival White(%) = mean(white_castled_before_10) * 100")
    parts.append("- Opening survival Black(%) = mean(black_castled_before_10) * 100")
    parts.append("")

    parts.append("## 7) Nhan dinh sau (tu dong)")
    parts.append("")
    _, wr_i, _, _, _ = find_score_rate(summary_rows, "I")
    _, wr_ii, _, _, _ = find_score_rate(summary_rows, "II")
    _, wr_iv, _, _, _ = find_score_rate(summary_rows, "IV")
    _, wr_v, _, _, _ = find_score_rate(summary_rows, "V")
    _, wr_vi, _, _, _ = find_score_rate(summary_rows, "VI")
    _, wr_viii, pl_viii, msw_viii, msb_viii = find_score_rate(summary_rows, "VIII")

    parts.append(f"- AlphaBeta opening impact (II - I): {wr_ii - wr_i:+.2f} pp. Neu am, opening book hien tai chua tao loi the o bo test nay.")
    parts.append(f"- MCTS heuristic impact (V - IV): {wr_v - wr_iv:+.2f} pp. Day la muc tang/giam do heuristic don le.")
    parts.append(f"- MCTS opening+heuristic synergy (VI - V): {wr_vi - wr_v:+.2f} pp. Neu duong, opening phat huy khi di kem heuristic.")
    parts.append(f"- Block VIII co win rate {wr_viii:.2f}% va do dai trung binh {pl_viii:.2f} plies: day la block can bang ket qua nhung cuong do chien thuat cao.")
    parts.append(f"- Toc do Block VIII: white {msw_viii:.2f} ms vs black {msb_viii:.2f} ms. Chenh lech lon goi y can kiem tra phan bo engine theo mau.")
    parts.append("")

    parts.append("## 8) Ghi chu")
    parts.append("")
    parts.append("- summary_by_block.csv dang tong hop WDL theo result_white, khong phai theo engine role.")
    parts.append("- De ket luan suc manh engine, uu tien bang role-engine (muc 3).")
    parts.append("- Blunder trong pipeline hien tai dang de 0, can bo sung evaluator theo ply neu muon dung chi so nay.")

    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-block markdown statistics report")
    parser.add_argument("--merged", default="merged_results.csv", help="Path to merged game-level CSV")
    parser.add_argument("--summary", default="summary_by_block.csv", help="Path to summary-by-block CSV")
    parser.add_argument("--out", default="BLOCK_STATS_SUMMARY.md", help="Output markdown file path")
    parser.add_argument("--top-n", type=int, default=2, help="Top and bottom scenarios shown per block")
    args = parser.parse_args()

    merged_path = Path(args.merged).resolve()
    summary_path = Path(args.summary).resolve()
    out_path = Path(args.out).resolve()

    if not merged_path.exists():
        raise FileNotFoundError(f"Merged file not found: {merged_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary file not found: {summary_path}")

    merged_rows = load_csv(merged_path)
    summary_rows = load_csv(summary_path)

    md = build_markdown(summary_rows=summary_rows, merged_rows=merged_rows, top_n=max(1, args.top_n))
    out_path.write_text(md, encoding="utf-8")

    print(f"Generated markdown report: {out_path}")
    print(f"Rows: merged={len(merged_rows)}, summary={len(summary_rows)}")


if __name__ == "__main__":
    main()
