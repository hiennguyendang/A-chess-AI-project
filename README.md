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

## Notes

1. Some Windows environments may show Qt EUDC font warnings; this does not block the app.
2. Performance depends on selected depth/simulations and CPU speed.

## License

This repository is intended for educational/academic use.
