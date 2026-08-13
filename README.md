# Minimax Chess Engine ♟️

A UCI-compatible chess engine built in Python utilizing a custom Minimax algorithm and search heuristics.

## Overview
This project focuses on artificial intelligence decision-making and algorithmic efficiency. The `python-chess` library is used for board representation and legal move validation, while the core search algorithm evaluates potential board states within strict time controls.

## Architecture
* **Minimax with Alpha-Beta Pruning:** The primary search algorithm, optimized to prune unpromising branches.
* **Iterative Deepening & Time Management:** Explores the game tree in increasing depths while managing a phased time budget.
* **Quiescence Search:** A tactical search resolving volatile board states (e.g., capture chains) to mitigate the horizon effect.
* **Transposition Table:** Caches exact evaluations and Alpha/Beta bounds for previously calculated positions to bypass redundant calculations.
* **Move Ordering (MVV-LVA):** Utilizes Most Valuable Victim - Least Valuable Attacker logic to test promising tactical moves first, maximizing cutoffs.
* **Killer Heuristic:** Prioritizes strong, non-capturing positional moves discovered in sibling branches.
* **Null Move Pruning:** Passes the turn in dominant middle-game positions to prune unnecessary search tree sections.

## Evaluation
The engine uses a Tapered Evaluation function to calculate the phase of the game, interpolating between Piece-Square Tables and structural heuristics:
* Centralizing the King in the endgame
* Penalizing doubled pawns
* Evaluating King safety against open and semi-open files
* Promoting endgame pawn pushes

## Tech Stack
* **Language:** Python 3.x
* **Protocol:** UCI (Universal Chess Interface)
* **Dependencies:** `python-chess`

## Installation & Setup

1. Clone the repository:
    git clone https://github.com/Nevin-Justin/Minimax-Chess-Engine.git
    cd Minimax-Chess-Engine

2. Install dependencies:
    pip install chess

## Usage 
This engine speaks the UCI protocol and is designed to be loaded into a Chess GUI (Arena, Cute Chess, etc.).

1. Open your preferred Chess GUI.
2. Navigate to Engines > Install New Engine.
3. Select your Python executable and point it to your main file (e.g., `chess_bot.py`).
4. Start a game and set the engine to play as White or Black.

## License
MIT License