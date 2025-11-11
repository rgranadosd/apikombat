<!-- 
  APIKOMBAT project overview README.
  Last updated: 2025-11-11
-->

# APIKOMBAT

Welcome to the main repository of the APIKOMBAT project. Here you will find the tournament documentation, the card game engine, and all supporting resources to run demos or extend the system.

## Repository layout

- `doc/` – Documentation hub covering official rules, gameplay guide, and card descriptions. The file `doc/readme.md` works as the table of contents linking to each topic.
- `virus-game/` – Source code for the **API Kombat** card game:
  - `virus_game.py` and `engine.py` – Entry points to launch the game and its core loop.
  - `api-card-game/` – Adaptation of the MTG engine for the API Kombat deck; includes card definitions (`data/`) and rule modules (`api/`, `MTG/api/`).
  - `mtg-engine/` – Python implementation of the Magic: The Gathering engine reused for the foundational mechanics. Contains rule modules (`MTG/`), card data (`data/`), and parsing tools (`parser/`).
  - `pygame_cards/` – Generic components to render cards, decks, and board zones with Pygame.
  - `assets/` – Art and audio resources: card backs, icons, fonts, and SFX, plus usage notes (`README.txt`).
  - `scripts/` – Utilities to generate or refresh assets from the data files.
  - `requirements.txt` – Python dependencies required to run the game client (`pygame`, `pandas`, `numpy`, etc.).
  - `run_game.sh` and `run_api_game.sh` – Convenience scripts to activate the virtualenv and launch the interface.
  - `venv/` – Optional pre-populated virtual environment (you can recreate it with `python -m venv venv && source venv/bin/activate`).
- `LICENSE` – Project license.

## Getting started

1. Install the dependencies (either inside `virus-game/venv` or using your own virtual environment):
   ```bash
   cd /Users/rafagranados/Develop/apikombat/virus-game
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Launch the GUI:
   ```bash
   python virus_game.py
   ```
   or, for the MTG engine-based interface:
   ```bash
   python api_game_gui.py
   ```

## Recommended documentation

- Check `doc/official_rules.md` to understand the tournament rules and scoring model.
- Review `doc/how_to_play.md` and `doc/cards.md` to master the gameplay flow and the role of each card.
- See `virus-game/api-card-game/README.md` for technical notes on the MTG engine adaptation.

Keep this README updated whenever new modules, assets, or documentation land in the repository.


