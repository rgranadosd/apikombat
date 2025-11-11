# API Card Game - Motor MTG Adaptation

Este es el juego de cartas API adaptado al motor Python MTG Engine.

## Estructura

- `data/`: Definiciones de cartas y datos del juego
- `MTG/api/`: Extensiones específicas del juego API sobre el motor MTG

## Cómo ejecutar

```bash
python -m api_card_game.game
```

## Conceptos clave

### Aspectos como Permanentes
Los aspectos (Seguridad, Documentación, Gobierno, Performance) son permanentes en el battlefield de cada jugador.

### Tipos de Cartas
- **Aspectos (Scoring)**: Colocan un permanente de aspecto en el battlefield
- **Ataques/Problemas**: Spells que vulneran o destruyen aspectos del oponente
- **Protecciones**: Spells que curan y fortalecen aspectos propios
- **Intervenciones**: Spells especiales con efectos únicos (Migración, Refactoring, etc.)

### Sistema de Victoria
Gana el jugador que tenga 4 aspectos saludables (no vulnerables) en su battlefield.

