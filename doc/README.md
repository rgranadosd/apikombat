# Essential Documents – API Kombat

This folder gathers every file you need to understand the game and reuse it in other projects.

## Files included

1. **`HOW_TO_PLAY.md`**  
   - Full rulebook: objectives, components, card types, turn flow, victory conditions.  
   - Format: Markdown.

2. **`cartas_completas.csv`**  
   - Summary of every card in the deck.  
   - Columns: `tipo`, `color`, `nombre`, `cantidad`, `descripcion`.

3. **`cartas_detalladas.csv`**  
   - Detailed list (one row per card).  
   - Columns: `tipo`, `color`, `nombre`, `cantidad`, `archivo_sugerido`, `icono`, `label`.  
   - Total: 89 rows.

4. **`CARTAS_ESPECIFICAS.md`**  
   - Notes about specific cards.

5. **`DESGLOSE_CARTAS_API.md`**  
   - API-themed card breakdown.

6. **`LISTA_COMPLETA_CARTAS_API.md`**  
   - Complete list of API-themed cards.

7. **`MAPEO_TEMATICA_API_FINAL.md`**  
   - Final mapping of the API theme applied to each card.

## How to reuse these files in other projects

1. Read `REGLAS_DEL_JUEGO.txt` to understand the mechanics.  
2. Use `cartas_completas.csv` or `cartas_detalladas.csv` to generate or port the deck.  
3. Check the `.md` documents for extra design and implementation details.  
4. The game engine lives in `engine.py` (outside this folder).

---

> Keep these files in sync with gameplay or deck changes so the documentation always reflects the current state of the game.

