# ♟️ Chess AI Project – Alpha-Beta & MCTS

This project is developed as part of the *Introduction to Artificial Intelligence (CO3061)* course at HCMUT.

It implements a fully functional Chess game with an interactive graphical user interface (GUI), featuring two core AI algorithms:

* **Alpha-Beta Pruning (Minimax optimized)**
* **Monte Carlo Tree Search (MCTS)**

The system allows users to play against AI, compare different algorithms, and adjust difficulty levels dynamically.

---

## 🚀 Features

* ♟️ Full Chess gameplay with legal move generation
* 🧠 Two AI agents:

  * Alpha-Beta with configurable search depth
  * MCTS with configurable simulation count
* ⚖️ AI vs AI comparison mode
* 🎮 Interactive GUI (inspired by chess.com)
* 🎚️ Adjustable difficulty settings
* 🔄 Real-time gameplay interaction

---

## 🧠 AI Algorithms

### Alpha-Beta Pruning

An optimized version of the Minimax algorithm that reduces the number of nodes evaluated in the game tree by pruning branches that cannot affect the final decision.

### Monte Carlo Tree Search (MCTS)

A probabilistic search algorithm that uses random simulations to evaluate moves and progressively improve decision-making over time.

---

## 🏗️ Project Structure

```bash
chess-ai-project/
├── engine/        # Chess logic (rules, board, evaluation)
├── ai/            # AI algorithms (Alpha-Beta, MCTS)
├── gui/           # User interface
├── config/        # Settings (difficulty, modes)
├── tests/         # Testing
├── docs/          # Report & documentation
└── main.py        # Entry point
```

---

## 🎯 Objectives

* Apply AI search algorithms to a complex game (Chess)
* Compare deterministic vs probabilistic approaches
* Analyze performance, speed, and decision quality

---

## 📊 Comparison Goals

* Execution time
* Number of explored nodes / simulations
* Quality of moves

---

## 🛠️ Tech Stack

* Python
* PyQt5 / Pygame (GUI)
* python-chess (optional)

---

## 👥 Contributors

* [Your Name / Team Members]

---

## 📄 License

This project is for academic purposes.
