# Chess AI Project (Alpha-Beta and MCTS)

This project is a desktop chess application with a PyQt5 interface and two AI engines:

1. Alpha-Beta (Minimax with pruning)
2. Monte Carlo Tree Search (MCTS)

It supports human play, AI vs AI automation, and 10-board benchmark windows for quick engine comparison.

## Highlights

1. Full legal chess gameplay with move validation and check/checkmate/stalemate detection
2. Two AI engines: Alpha-Beta and MCTS
3. Layered UI flow:
   1. Step 1: choose game mode
   2. Step 2: mode-specific options
   3. In-game: board + status + move history
4. AI vs AI with separate depth control for White and Black
5. 10-game benchmark windows for:
   1. Minimax vs Random
   2. MCTS vs Random
6. Custom piece sprites loaded from `imgs/piece`
7. End-of-game overlay text in the board center: `White win`, `Black win`, or `Draw`

## Project Structure

```text
A-chess-AI-project/
  ai/
    alphabeta.py
    mcts.py
    minimax.py
    utils.py
  config/
    settings.py
  docs/
    report.md
  engine/
    board.py
    evaluator.py
    move_generator.py
    rules.py
  gui/
    app.py
    benchmark_window.py
    board_ui.py
    themes.py
  imgs/
    piece/
      bb.png bk.png bn.png bp.png bq.png br.png
      wb.png wk.png wn.png wp.png wq.png wr.png
  tests/
    test_ai.py
    test_ai_vs_random.py
  main.py
  requirements.txt
```

## Requirements

1. Python 3.11+ (Python 3.12 recommended)
2. pip

Dependencies are listed in `requirements.txt`:

1. python-chess
2. PyQt5
3. numpy

## Installation

From the project root:

```bash
python -m venv .venv
```

### Windows (PowerShell)

```bash
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Windows (cmd)

```bash
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### macOS/Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the Application

```bash
python main.py
```

## How to Use

### 1) Start Menu (Mode Selection)

Choose one of these modes, then click `Continue`:

1. Human vs AI
2. AI vs AI
3. Test Alpha-Beta (10 games)
4. Test Monte Carlo (10 games)

### 2) Options (Mode-Specific)

The options screen is dynamic and only shows relevant controls.

#### Human vs AI

1. AI Depth
2. Your Side (White/Black)
3. AI Engine (Alpha-Beta/MCTS)

Click `Start Game`.

#### AI vs AI

1. White AI (Alpha-Beta/MCTS)
2. White AI Depth
3. Black AI (Alpha-Beta/MCTS)
4. Black AI Depth

Click `Start Game`.

#### Test Modes

1. Test Alpha-Beta (10 boards): uses selected depth for Minimax benchmark
2. Test Monte Carlo (10 boards): opens MCTS benchmark window

Click `Open Test`.

### 3) In-Game Screen

You will see:

1. Chess board
2. Status text (`Turn`, `Checkmate`, `Stalemate`)
3. Move history in SAN format
4. Control buttons (`Start/Stop AI vs AI`, `Restart Game`, `Back To Menu`)

When a game ends, a large yellow message appears at the center of the board:

1. `White win`
2. `Black win`
3. `Draw`

## Piece Assets

The UI loads piece images from `imgs/piece` using this naming convention:

1. White: `wp`, `wn`, `wb`, `wr`, `wq`, `wk`
2. Black: `bp`, `bn`, `bb`, `br`, `bq`, `bk`

If a sprite is missing, the board falls back to Unicode rendering.

## Testing

Run all tests:

```bash
pytest -q
```

Run only core smoke tests:

```bash
pytest -q tests/test_ai.py
```

Run benchmark tests:

```bash
pytest -q tests/test_ai_vs_random.py
```

Enable strict benchmark checks (10/10 wins expected):

```bash
# PowerShell
$env:STRICT_RANDOM_BENCH = "1"
pytest -q tests/test_ai_vs_random.py
```

```bash
# cmd
set STRICT_RANDOM_BENCH=1
pytest -q tests/test_ai_vs_random.py
```

## Notes

1. Some Windows environments may show Qt EUDC font warnings; this does not block the app.
2. Performance depends on selected depth/simulations and CPU speed.

## License

This repository is intended for educational/academic use.
