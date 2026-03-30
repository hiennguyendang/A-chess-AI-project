# REPORT: Evaluation Plan for Alpha-Beta vs MCTS (Pure/Heuristic)

## 1. Report Goal

This report defines a reproducible evaluation plan to compare chess engines in this project:

- Alpha-Beta (fixed depth)
- MCTS Pure (random rollout cutoff -> draw reward)
- MCTS Heuristic (evaluation-at-cutoff rollout)

Main questions:

1. What MCTS settings are competitive with Alpha-Beta depth 3?
2. Does MCTS Heuristic outperform MCTS Pure under the same compute budget?
3. What is the best quality/speed trade-off for practical gameplay?

---

## 2. Engines and Configurations

### 2.1 Alpha-Beta baseline

- Depth: 3 (main baseline)
- Optional stress baseline: depth 4, depth 5

### 2.2 MCTS parameter grid

- Simulations: 800, 1200, 1600, 2200
- Rollout depth: 6, 10, 14
- Mode:
  - Pure (use_heuristic_eval = false)
  - Heuristic (use_heuristic_eval = true)

Total MCTS configs: 4 x 3 x 2 = 24.

---

## 3. Matchup Scenarios

### 3.1 Baseline vs Random

1. Alpha-Beta d3 vs Random
2. MCTS Pure (grid configs) vs Random
3. MCTS Heuristic (grid configs) vs Random

Purpose: quickly verify if each config is at least stronger than random.

### 3.2 Direct Head-to-Head

1. Alpha-Beta d3 vs MCTS Pure
2. Alpha-Beta d3 vs MCTS Heuristic
3. MCTS Pure vs MCTS Heuristic (same sim/depth)

Purpose: isolate the effect of heuristic rollout and compare practical strength.

### 3.3 Stress Tests (optional)

1. Alpha-Beta d4 vs top-3 MCTS configs
2. Alpha-Beta d5 vs top-3 MCTS configs

Purpose: estimate headroom and robustness at stronger baseline.

---

## 4. Fairness and Reproducibility Rules

1. Equal color distribution:
   - 50% games where engine A is White
   - 50% games where engine A is Black
2. Fixed seeds per batch for reproducibility.
3. Same machine, same code version, same runtime settings.
4. Draw handling must be consistent (including 50-move rule claim logic).
5. Keep one variable change per comparison whenever possible.

---

## 5. Required Metrics to Track

### 5.1 Outcome metrics

- Wins, Draws, Losses (W-D-L)
- Score rate:

  ScoreRate = (Wins + 0.5 * Draws) / TotalGames

### 5.2 Side-specific metrics

- Score as White
- Score as Black

### 5.3 Performance metrics

- Average think time per move (ms)
- P95 think time per move (ms)
- Average game length (plies)
- Optional: effective simulations per second for MCTS

### 5.4 Stability metrics

- Standard deviation of score rate across batches
- 95% confidence interval for score rate

### 5.5 Error-quality proxy metrics (optional)

- Material swing after engine moves
- Blunder count (e.g., immediate material loss >= 3 points)

---

## 6. Per-Game Logging Schema

Store one record per game with fields:

- match_id
- scenario_name
- white_engine
- black_engine
- white_params
- black_params
- seed
- result ("1-0", "0-1", "1/2-1/2")
- winner (white/black/draw)
- plies
- avg_move_ms_white
- avg_move_ms_black
- termination_reason (checkmate/stalemate/50-move/max-plies/other)

Recommended output formats:

- CSV for analysis
- Markdown summary table for report readability

---

## 7. Execution Plan

### Phase A: Screening

- Run all 24 MCTS configs vs Alpha-Beta d3
- 30 games per config
- Keep top 5 by score rate and time efficiency

### Phase B: Confirmation

- Run top 5 configs vs Alpha-Beta d3
- 100 games per config
- Compute confidence intervals and side split

### Phase C: Final Validation

- Top 2 configs:
  - vs Random (sanity)
  - vs Alpha-Beta d4 (difficulty check)

---

## 8. Analysis and Decision Criteria

Primary ranking:

1. Highest score rate vs Alpha-Beta d3
2. Lower average move time among similar score configs
3. Better side balance (White vs Black consistency)

Secondary ranking:

- Lower variance across seeds/batches
- Better behavior in stress tests

Final recommendation should provide:

- Best-strength config
- Best-efficiency config
- Suggested default config for UI gameplay

---

## 9. Report Output Structure

1. Introduction and goals
2. Experimental setup and fairness constraints
3. Matchup matrix and parameter grid
4. Results tables
5. Plots (score vs simulations, score vs time)
6. Discussion
7. Final recommendation
8. Limitations and future improvements

---

## 10. Expected Deliverables

- REPORT.md (this plan)
- Raw game logs (CSV)
- Aggregated results table
- Final configuration recommendation for:
  - MCTS Pure
  - MCTS Heuristic
  - Match-equivalent config vs Alpha-Beta d3
