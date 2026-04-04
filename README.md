# Chess AI Project (Alpha-Beta and MCTS)

Desktop chess application with a PyQt5 UI and two AI engines:

1. Alpha-Beta (minimax with pruning)
2. Monte Carlo Tree Search (MCTS)

The app supports human play, AI vs AI automation, and benchmark windows for quick engine comparison.

## Features

1. Full legal chess rules (move validation, check, checkmate, stalemate)
2. Selectable AI engine: Alpha-Beta or MCTS
3. Human vs AI and AI vs AI game modes
4. Separate AI depth controls for White and Black in AI vs AI mode
5. Built-in benchmark modes (10-game windows)

## Project Structure

```text
A-chess-AI-project/
  ai/
    alphabeta.py
    mcts.py
    mcts_evaluator.py
    mcts_heuristic.py
    minimax.py
    opening_book.py
    search_parallel.py
    utils.py
  config/
    settings.py
  engine/
    board.py
    evaluator.py
    move_generator.py
    Rating_AI.py
    rules.py
  gui/
    app.py
    benchmark_window.py
    board_ui.py
    themes.py
  imgs/
    piece/
      *.png
  results/
    merged_results.csv
    summary_by_block.csv
  tests/
    test_ai.py
  main.py
  README.md
  requirements.txt
```

## Requirements

1. Python 3.11 or newer (3.12 recommended)
2. pip

Main dependencies (see requirements.txt):

1. python-chess
2. PyQt5
3. numpy

## Installation

Run from the project root.

### 1) Create virtual environment

```bash
python -m venv .venv
```

### 2) Activate environment and install dependencies

Windows (PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows (cmd):

```bash
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run Application

```bash
python main.py
```

## Usage

### 1) Start menu

Choose one mode, then click Continue:

1. Human vs AI
2. AI vs AI
3. Test Alpha-Beta (10 games)
4. Test Monte Carlo (10 games)

### 2) Mode options

Human vs AI:

1. AI depth
2. Player side (White/Black)
3. AI engine (Alpha-Beta/MCTS)

AI vs AI:

1. White AI (Alpha-Beta/MCTS)
2. White AI depth
3. Black AI (Alpha-Beta/MCTS)
4. Black AI depth

Test modes:

1. Test Alpha-Beta: benchmark Minimax on 10 boards
2. Test Monte Carlo: benchmark MCTS on 10 boards

### 3) In-game screen

1. Chess board
2. Status text (turn/checkmate/stalemate)
3. SAN move history
4. Control buttons (start/stop AI vs AI, restart, back to menu)

## Notes

1. On some Windows machines, Qt may print EUDC font warnings; these are non-blocking.
2. Performance depends on AI depth/simulation settings and CPU speed.

## License

This repository is intended for educational/academic use.
