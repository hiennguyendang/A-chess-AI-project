# Bao cao thong ke benchmark (ban gon + de hieu)

Tai lieu nay duoc tao tu dong boi benchmark/generate_block_stats_md.py

Nguon du lieu:
- summary by block: summary_by_block.csv
- game level: merged_results.csv

## 1) Bang tong hop compact

| Block | Research focus | Games | Win rate (%) | Avg plies | Tempo note |
|---|---|---|---|---|---|
| I | AlphaBeta baseline (opening off) | 44 | 44.32 | 68.00 | Black slower |
| II | AlphaBeta + opening | 44 | 35.23 | 67.75 | Black slower |
| III | Opening on vs off (AB internal) | 10 | 50.00 | 84.00 | Black slower |
| IV | MCTS baseline (no heur, no opening) | 82 | 49.39 | 74.41 | White slower |
| V | MCTS + heuristic | 72 | 49.31 | 92.25 | White slower |
| VI | MCTS + heuristic + opening | 72 | 54.17 | 95.76 | White slower |
| VII | MCTS variants head-to-head | 30 | 25.00 | 81.00 | White slower |
| VIII | AlphaBeta vs MCTS direct | 50 | 50.00 | 46.50 | Black slower |

## 2) So sanh key effects (gop block)

| Comparison | Base block | Compared block | Delta win rate (pp) | Delta avg plies | Interpretation |
|---|---|---|---|---|---|
| Opening effect on AlphaBeta | I | II | -9.09 | -0.25 | Opening hurts AB in this run |
| Heuristic effect on MCTS | IV | V | -0.08 | +17.84 | Effect is neutral in this run |
| Opening on top of heuristic | V | VI | +4.86 | +3.51 | Opening + heuristic synergy |
| MCTS variants vs AB direct | III | VIII | +0.00 | -37.50 | Effect is neutral in this run |

## 3) Chi so an theo role engine

| Block | Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus white/black) | Insight |
|---|---|---|---|---|---|---|
| I | alphabeta | 84.09 | 95.45 | 36.36/27.27 | 5177/6185 | Noticeable black-side advantage |
| II | alphabeta | 68.18 | 97.73 | 40.91/54.55 | 4184/6378 | Noticeable black-side advantage |
| III | alphabeta | 50.00 | 50.00 | 100.00/100.00 | 3634/5635 | Side balance relatively stable |
| IV | mcts | 12.20 | 13.41 | 4.88/8.54 | 550/545 | Side balance relatively stable |
| V | mcts_heuristic | 5.56 | 6.94 | 11.11/11.11 | 5085/4966 | Side balance relatively stable |
| VI | mcts_heuristic | 22.22 | 13.89 | 59.72/61.11 | 3423/3163 | Side balance relatively stable |
| VII | mcts_heuristic | 16.67 | 100.00 | 33.33/33.33 | 3862/3643 | Noticeable black-side advantage |
| VIII | alphabeta | 100.00 | 100.00 | 60.00/50.00 | 2506/12773 | Side balance relatively stable |

## 4) Snapshot tung block (ban gon)

### Block I

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| alphabeta | 84.09 | 95.45 | 36.36/27.27 | 5177/6185 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| I.1 (vs Random) | 10 | 5-0-5 | 5.00 | 50.00 | 25.10 | 1755/2279 |
| I.2 (vs Minimax, d=3) | 10 | 0-5-5 | 2.50 | 25.00 | 74.50 | 3075/3295 |
| I.3 (Stockfish, d=3, elo grouped) | 24 | 11-2-11 | 12.00 | 50.00 | 83.17 | 3173/4020 |

### Block II

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| alphabeta | 68.18 | 97.73 | 40.91/54.55 | 4184/6378 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| II.1 (vs Random) | 10 | 5-0-5 | 5.00 | 50.00 | 35.10 | 1640/1429 |
| II.2 (vs Minimax, d=3) | 10 | 0-0-10 | 0.00 | 0.00 | 71.00 | 4721/5667 |
| II.3 (Stockfish, d=3, elo grouped) | 24 | 10-1-13 | 10.50 | 43.75 | 80.00 | 1758/3362 |

### Block III

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| alphabeta | 50.00 | 50.00 | 100.00/100.00 | 3634/5635 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| III (opening on vs off, d=3) | 10 | 0-10-0 | 5.00 | 50.00 | 84.00 | 3634/5635 |

### Block IV

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| mcts | 12.20 | 13.41 | 4.88/8.54 | 550/545 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| IV.1 (vs Random) | 10 | 5-1-4 | 5.50 | 55.00 | 113.10 | 257/279 |
| IV.2 (vs Stockfish, sim=500, elo grouped) | 24 | 11-0-13 | 11.00 | 45.83 | 62.79 | 274/275 |
| IV.2 (vs Stockfish, sim=1000, elo grouped) | 24 | 12-0-12 | 12.00 | 50.00 | 68.83 | 308/305 |
| IV.2 (vs Stockfish, sim=2000, elo grouped) | 24 | 12-0-12 | 12.00 | 50.00 | 75.50 | 399/384 |

### Block V

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| mcts_heuristic | 5.56 | 6.94 | 11.11/11.11 | 5085/4966 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| V.1 (vs Stockfish, sim=500, elo grouped) | 24 | 12-2-10 | 13.00 | 54.17 | 95.25 | 1165/1292 |
| V.1 (vs Stockfish, sim=1000, elo grouped) | 24 | 11-0-13 | 11.00 | 45.83 | 76.96 | 2413/2116 |
| V.1 (vs Stockfish, sim=2000, elo grouped) | 24 | 11-1-12 | 11.50 | 47.92 | 104.54 | 4200/4192 |

### Block VI

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| mcts_heuristic | 22.22 | 13.89 | 59.72/61.11 | 3423/3163 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| VI.1 (vs Stockfish, sim=500, elo grouped) | 24 | 12-0-12 | 12.00 | 50.00 | 99.58 | 871/742 |
| VI.1 (vs Stockfish, sim=1000, elo grouped) | 24 | 15-1-8 | 15.50 | 64.58 | 81.00 | 1394/1271 |
| VI.1 (vs Stockfish, sim=2000, elo grouped) | 24 | 11-1-12 | 11.50 | 47.92 | 106.71 | 3020/2881 |

### Block VII

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| mcts_heuristic | 16.67 | 100.00 | 33.33/33.33 | 3862/3643 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| VII.1 | 10 | 0-5-5 | 2.50 | 25.00 | 90.50 | 2371/2281 |
| VII.2 | 10 | 5-0-5 | 5.00 | 50.00 | 101.50 | 510/504 |
| VII.3 | 10 | 0-0-10 | 0.00 | 0.00 | 51.00 | 3677/3436 |

### Block VIII

| Focus engine | WR as White (%) | WR as Black (%) | Opening survival W/B (%) | Avg ms (focus W/B) |
|---|---|---|---|---|
| alphabeta | 100.00 | 100.00 | 60.00/50.00 | 2506/12773 |

Bang ket qua rut gon theo nhom I.1/I.2/I.3 (co gom cum elo/sim khi can):

| Group | Games | W-D-L | Score | Win rate (%) | Avg plies | Avg ms W/B |
|---|---|---|---|---|---|---|
| VIII.1 | 10 | 5-0-5 | 5.00 | 50.00 | 29.50 | 1849/3629 |
| VIII.2 | 10 | 5-0-5 | 5.00 | 50.00 | 49.50 | 1352/1358 |
| VIII.3 | 10 | 5-0-5 | 5.00 | 50.00 | 42.50 | 7381/9094 |
| VIII.4 | 10 | 5-0-5 | 5.00 | 50.00 | 54.50 | 6890/28304 |
| VIII.5 | 10 | 5-0-5 | 5.00 | 50.00 | 56.50 | 6809/6124 |

## 5) Bang tong hop goc (tham chieu)

| Block | Games | W | D | L | Score | Win rate (%) | Avg plies | Avg move ms (White) | Avg move ms (Black) | Avg material swing (cp) |
|---|---|---|---|---|---|---|---|---|---|---|
| I | 44 | 16 | 7 | 21 | 19.50 | 44.32 | 68.00 | 2828.41 | 3459.57 | 1906.14 |
| II | 44 | 15 | 1 | 28 | 15.50 | 35.23 | 67.75 | 2404.41 | 3446.46 | 2241.14 |
| III | 10 | 0 | 10 | 0 | 5.00 | 50.00 | 84.00 | 3634.41 | 5634.79 | 925.00 |
| IV | 82 | 40 | 1 | 41 | 40.50 | 49.39 | 74.41 | 318.76 | 316.11 | 2058.17 |
| V | 72 | 34 | 3 | 35 | 35.50 | 49.31 | 92.25 | 2592.89 | 2533.32 | 1699.03 |
| VI | 72 | 38 | 2 | 32 | 39.00 | 54.17 | 95.76 | 1761.66 | 1631.52 | 1872.64 |
| VII | 30 | 5 | 5 | 20 | 7.50 | 25.00 | 81.00 | 2185.95 | 2073.76 | 2075.00 |
| VIII | 50 | 25 | 0 | 25 | 25.00 | 50.00 | 46.50 | 4856.19 | 9701.73 | 2536.00 |

## 6) Cong thuc

- Score = W + 0.5 * D
- WinRate = Score / Games * 100
- WinRate as White(engine X) = (W + 0.5*D tren cac van engine_white == X) / GamesWhite * 100
- WinRate as Black(engine X) = (W + 0.5*D tren cac van engine_black == X, dung result_black) / GamesBlack * 100
- Opening survival White(%) = mean(white_castled_before_10) * 100
- Opening survival Black(%) = mean(black_castled_before_10) * 100

## 7) Nhan dinh sau (tu dong)

- AlphaBeta opening impact (II - I): -9.09 pp. Neu am, opening book hien tai chua tao loi the o bo test nay.
- MCTS heuristic impact (V - IV): -0.08 pp. Day la muc tang/giam do heuristic don le.
- MCTS opening+heuristic synergy (VI - V): +4.86 pp. Neu duong, opening phat huy khi di kem heuristic.
- Block VIII co win rate 50.00% va do dai trung binh 46.50 plies: day la block can bang ket qua nhung cuong do chien thuat cao.
- Toc do Block VIII: white 4856.19 ms vs black 9701.73 ms. Chenh lech lon goi y can kiem tra phan bo engine theo mau.

## 8) Ghi chu

- summary_by_block.csv dang tong hop WDL theo result_white, khong phai theo engine role.
- De ket luan suc manh engine, uu tien bang role-engine (muc 3).
- Blunder trong pipeline hien tai dang de 0, can bo sung evaluator theo ply neu muon dung chi so nay.
