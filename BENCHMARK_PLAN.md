# Kế hoạch Benchmark Chess AI

## 1. Mục tiêu
- So sánh AlphaBeta và MCTS trong các điều kiện bật hoặc tắt Opening Book và Heuristic.
- Đủ số lượng ván để nhìn thấy xu hướng rõ ràng.
- Giữ khối lượng vừa phải để phù hợp thời gian có hạn.

## 2. Chỉ số cần theo dõi

### 2.1 Chỉ số kết quả
- W/D/L.
- Win rate (%).
- Score = W + 0.5 x D.
- Kết quả theo màu quân: khi cầm Trắng, khi cầm Đen.

### 2.2 Chỉ số tốc độ
- Thời gian trung bình mỗi nước (avg move time, ms).
- Thời gian dài nhất cho 1 nước (max move time, ms).
- Tổng thời gian mỗi game (ms hoặc s).

### 2.3 Chỉ số chất lượng ván
- Độ dài ván: số plies trung bình.
- Material swing lớn nhất trong mỗi ván (cp).
- Blunder count (ước tính): số nước làm mất >= 300 cp.
- Opening survival rate: tỉ lệ nhập thành trước move 10.
- Win Rate khi hơn vật chất.
- Draw Rate khi thua vật chất.

### 2.4 Chỉ số đặc thù thuật toán
- AlphaBeta: cutoff rate (%)

---

## 3. Kịch bản benchmark chi tiết

### I. AlphaBeta - Không Opening
1. vs Random
- 10 game (5 Trắng - 5 Đen).
- Kỳ vọng: thắng 10/10.

2. vs Minimax
- d_minimax = 3: 10 game.
- Tổng: 10 game.
- Mục tiêu: chứng minh AlphaBeta nhanh hơn và kết quả ngang nhau.

3. vs Stockfish
- d_alphabeta = 3.
- Elo = 100 đến 1200 (tăng 100 mỗi lần)
- Mỗi cặp (depth, elo): 2 game.
- Tổng: 12 x 2 = 24 game.

Tổng block I: 44 game.

### II. AlphaBeta - Có Opening
1. vs Random: 10 game.
2. vs Minimax (d=3): 10 game.
3. vs Stockfish (d=3; elo 100..1200): 24 game.

Tổng block II: 44 game.

### III. AlphaBeta - Có Opening vs Không Opening
- AlphaBeta (opening on) vs AlphaBeta (opening off).
- d = 3: 10 game.
- Tổng: 10 game.
- Mục tiêu: đo đóng góp thực tế của opening book.

### IV. Monte Carlo - Không Heuristic, Không Opening
1. vs Random: 10 game.
2. vs Stockfish
- simulations = 500, 1000, 2000.
- rd = 5
- elo 100..1200 (tăng 100 mỗi lần).
- 2 game mỗi cặp.
- Tổng: 72 game.

Tổng block IV: 82 game.

### V. Monte Carlo - Có Heuristic, Không Opening
vs Stockfish
- simulations = 500, 1000, 2000.
- rd = 5
- elo 100..1200 (tăng 100 mỗi lần).
- 2 game mỗi cặp.
- Tổng: 72 game.

### VI. Monte Carlo - Có Heuristic, Có Opening
vs Stockfish
- simulations = 500, 1000, 2000.
- rd = 5
- elo 100..1200 (tăng 100 mỗi lần).
- 2 game mỗi cặp.
- Tổng: 72 game.

### VII. MCTS đấu lẫn nhau
Mục tiêu: đo tác động độc lập của Heuristic và Opening trong nội bộ MCTS.

1. MCTS (no-heuristic, no-opening) vs MCTS (heuristic, no-opening)
- simulations = 1000, rd = 5.
- 10 game (5 Trắng - 5 Đen).

2. MCTS (no-heuristic, no-opening) vs MCTS (no-heuristic, opening on)
- simulations = 1000, rd = 5.
- 10 game.

3. MCTS (heuristic, no-opening) vs MCTS (heuristic, opening on)
- simulations = 1000, rd = 5.
- 10 game.

Tổng block VII: 30 game.

### VIII. Đối đầu trực tiếp AlphaBeta vs MCTS
Cấu hình cố định d_ab = 3, sim_mcts = 3000, rd = 5, Trắng-Đen: 50%.

1. AlphaBeta (opening off) vs MCTS (no-heuristic, no-opening)
- 10 game.

2. AlphaBeta (opening off) vs MCTS (no-heuristic, opening on)
- 10 game.

3. AlphaBeta (opening off) vs MCTS (heuristic on, opening off)
- 10 game.

4. AlphaBeta (opening off) vs MCTS (heuristic on, opening on)
- 10 game.

5. AlphaBeta (opening on) vs MCTS (heuristic on, opening on)
- 10 game.

Tổng block VIII: 50 game.

---
### VIII. Đối đầu trực tiếp AlphaBeta vs MCTS (Tương tự trên)
Cấu hình cố định d_ab = 3, sim_mcts = 5000, rd = 7, Trắng-Đen: 50%.


## 4. Tổng khối lượng đề xuất
- Tổng đầy đủ theo kịch bản hiện tại: 396 game.

---

## 5. Mẫu log đề xuất cho mỗi game

### 5.1 CSV header đề xuất
game_id,block_id,engine_white,engine_black,opening_white,opening_black,heuristic_white,heuristic_black,depth_white,depth_black,sim_white,sim_black,stockfish_elo,result_white,result_black,plies,avg_move_ms_white,p95_move_ms_white,max_move_ms_white,avg_move_ms_black,p95_move_ms_black,max_move_ms_black,max_material_swing_cp,blunder_white,blunder_black,white_castled_before_10,black_castled_before_10

### 5.2 Quy ước giá trị
- result_white: W, D, L.
- result_black: L, D, W.
- opening_white hoặc opening_black: on, off.
- heuristic_white hoặc heuristic_black: on, off, na.
- depth_*: dùng cho AlphaBeta hoặc Minimax, không dùng thì để trống.
- sim_*: dùng cho MCTS, không dùng thì để trống.
- stockfish_elo: chỉ điền khi có Stockfish.

### 5.3 Example
001,IV,mcts,stockfish,off,na,off,na,, ,1000,,600,L,W,88,42.1,95.4,188.0,11.2,20.3,45.0,520,3,0,1,1,0,0,0


---

## 6. Kế hoạch tự động hóa và chạy phân tán trên 3 máy

### 6.1 Mục tiêu vận hành
- Tự động chạy benchmark theo danh sách kịch bản đã chốt.
- Lưu log có cấu trúc thống nhất để ghép dữ liệu tự động.
- Chạy song song trên 3 máy để rút ngắn thời gian.

### 6.2 Chuẩn hóa output để dễ ghép
- Mỗi máy ghi file CSV riêng, không ghi đè.
- Quy ước tên file:
	- `results_[scenario].csv`

    - note: scenario là thứ tự của kịch bản (xem phần 3)

### 6.3 Chia việc cụ thể cho 3 máy

#### Máy Hiên (126 game)
- Block I: 44 game.
- Block V: 72 game.
- Block VIII: chạy thêm 10 game đầu của block này.

#### Máy Huy (126 game)
- Block II: 44 game.
- Block VI: 72 game.
- Block VIII: chạy thêm 10 game tiếp theo của block này.

#### Máy Nam (144 game)
- Block III: 12 game.
- Block IV: 72 game.
- Block VII: 30 game.
- Block VIII: chạy phần còn lại 30 game.

### 6.4 Lệnh chạy tự động cho 3 máy

Script chính:
- `benchmark/run_distributed_benchmark.py`

Chuẩn cài đặt Stockfish cho cả 3 máy (khuyến nghị):
1. Cài bằng winget:
```bash
winget install Stockfish.Stockfish
```
2. Kiểm tra:
```bash
where stockfish
```
3. Thiết lập biến môi trường chung (mỗi máy tự trỏ đúng local path):
```powershell
setx STOCKFISH_PATH "C:\Users\<username>\AppData\Local\Microsoft\WinGet\Packages\Stockfish.Stockfish_Microsoft.Winget.Source_8wekyb3d8bbwe\stockfish\stockfish.exe"
```
4. Mở terminal mới, kiểm tra lại:
```powershell
echo $env:STOCKFISH_PATH
```

Ghi chú:
- Script sẽ ưu tiên theo thứ tự: `--stockfish-path` -> `STOCKFISH_PATH` -> auto-detect.
- Nếu truyền path sai, script sẽ cảnh báo và tự fallback.

Lệnh mẫu:

Máy Hiên:
```bash
python benchmark/run_distributed_benchmark.py --machine-id hien --skip-existing-scenarios --out-dir benchmark_results --alphabeta-processes 6 --minimax-processes 6 --mcts-threads 6 --show-ui
```

Máy Huy:
```bash
python benchmark/run_distributed_benchmark.py --machine-id huy --skip-existing-scenarios --out-dir benchmark_results --alphabeta-processes 6 --minimax-processes 6 --mcts-threads 6 --show-ui
```

Máy Nam:
```bash
python benchmark/run_distributed_benchmark.py --machine-id nam --skip-existing-scenarios --out-dir benchmark_results --alphabeta-processes 6 --minimax-processes 6 --mcts-threads 6 --show-ui
```

Tham số bổ sung (tuỳ chọn):
- `--move-time-ms 100`
- `--max-plies 240`
- `--seed 42`
- `--alphabeta-processes 6`
- `--minimax-processes 6`
- `--mcts-threads 6`

Lưu ý công bằng khi đo tốc độ:
- Nếu so sánh tốc độ giữa các thuật toán, giữ cố định các cờ song song ở mọi máy và mọi lần chạy.
- Không chạy nhiều benchmark cùng lúc trên cùng 1 máy khi đang đo thời gian, vì sẽ làm nhiễu chỉ số time.

### 6.5 Ghép kết quả tự động

Script merge:
- `benchmark/merge_results.py`

Lệnh mẫu:
```bash
python benchmark/merge_results.py --in-dir benchmark_results --merged merged_results.csv --summary summary_by_block.csv
```

Output:
- `merged_results.csv`: toàn bộ game-level data.
- `summary_by_block.csv`: tổng hợp theo block I..VIII.

