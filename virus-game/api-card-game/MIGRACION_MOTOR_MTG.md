# Migración del Juego API Card Game al Motor MTG Python Engine

## Resumen

Este documento explica cómo se ha adaptado el juego API Card Game para usar el motor Python MTG Engine, separando la lógica del juego del GUI (Pygame).

## Arquitectura del Motor MTG

### Componentes Principales

1. **Game**: Clase principal que gestiona el estado del juego, turnos, stack, etc.
2. **Player**: Representa a un jugador con sus zonas (library, hand, battlefield, graveyard, exile)
3. **Card**: Clase base para todas las cartas
4. **Permanent**: Objetos que permanecen en el battlefield
5. **Stack**: Sistema de resolución de spells y habilidades
6. **Zones**: Library, Hand, Battlefield, Graveyard, Exile

### Sistema de Habilidades

- **Activated Abilities**: Habilidades que se activan pagando un costo
- **Triggered Abilities**: Habilidades que se activan automáticamente por eventos
- **Static Abilities**: Efectos estáticos que están siempre activos

## Mapeo de Conceptos

### Del Juego Actual al Motor MTG

| Concepto Actual | Concepto MTG | Explicación |
|----------------|---------------|-------------|
| `Jugador.aspectos` (dict) | `Player.battlefield` (zona) | Los aspectos son permanentes en el battlefield |
| `Carta` (simple class) | `Card` (hereda de GameObject) | Las cartas se definen como clases |
| `jugar_carta()` | `play_func()` | El efecto de la carta se define en `play_func` |
| Aspecto vulnerable | `AspectoPermanent.vulnerable` | Estado del permanente |
| Protecciones | `AspectoPermanent.protecciones` | Contador en el permanente |
| Mazo | `Player.library` | Zona de cartas por robar |
| Mano | `Player.hand` | Zona de cartas en mano |
| Descarte | `Player.graveyard` | Zona de cartas descartadas |

## Estructura de Archivos

```
api-card-game/
├── MTG/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── aspecto.py          # Clase AspectoPermanent
│   │   └── game_api.py         # Extensión de Game
│   └── (resto del motor MTG)
├── data/
│   ├── api_cards.txt           # Definiciones de cartas (formato MTG)
│   ├── api_cards.py            # (generado por parser)
│   └── api_name_to_id_dict.pkl # (generado por parser)
└── parser/
    └── parse_api_cards.py      # Parser para generar clases de cartas
```

## Implementación de Cartas

### Formato de Definición (`api_cards.txt`)

Las cartas se definen en `data/api_cards.txt` siguiendo el formato del motor MTG:

```
##############################
# Nombre de la Carta
	Targets:
		# Criterios de selección de objetivos
		lambda self, p: condicion

	Play:
		# Código Python que se ejecuta al jugar la carta
		efecto
```

### Tipos de Cartas

#### 1. Aspectos (Scoring)

**Ejemplo: Aspecto Seguridad**
```python
# En api_cards.txt
##############################
# Aspecto Seguridad
	Play:
		from MTG.api.aspecto import AspectoPermanent
		aspecto = AspectoPermanent('seguridad', controller=self.controller)
		self.controller.battlefield.add(aspecto)
```

#### 2. Ataques/Problemas

**Ejemplo: DoS**
```python
##############################
# DoS (Ataque Seguridad)
	Targets:
		lambda self, p: (hasattr(p, 'is_aspecto') and p.is_aspecto 
			and p.aspecto_type == 'seguridad' 
			and p.controller == self.controller.opponent
			and not p.esta_protegido())

	Play:
		aspecto = self.targets_chosen[0]
		if aspecto.vulnerable:
			aspecto.controller.battlefield.remove(aspecto)
		else:
			aspecto.vulnerar()
```

#### 3. Protecciones

**Ejemplo: OAuth2/JWT**
```python
##############################
# OAuth2/JWT (Protección Seguridad)
	Targets:
		lambda self, p: (hasattr(p, 'is_aspecto') and p.is_aspecto 
			and p.aspecto_type == 'seguridad' 
			and p.controller == self.controller)

	Play:
		aspecto = self.targets_chosen[0]
		if aspecto.vulnerable:
			aspecto.curar()
		aspecto.add_proteccion()
```

#### 4. Intervenciones

**Ejemplo: Migración**
```python
##############################
# Migración
	Targets:
		lambda self, p: (hasattr(p, 'is_aspecto') and p.is_aspecto 
			and p.controller == self.controller.opponent)

	Play:
		# Robar aspecto del oponente
		aspecto = self.targets_chosen[0]
		aspecto.controller.battlefield.remove(aspecto)
		aspecto.controller = self.controller
		self.controller.battlefield.add(aspecto)
```

## Parser de Cartas

### Generación Automática

El parser `parser/parse_api_cards.py` lee `api_cards.txt` y genera:
1. `data/api_cards.py`: Clases de cartas
2. `data/api_name_to_id_dict.pkl`: Diccionario nombre → ID

**Ejemplo de salida:**
```python
# En api_cards.py
class c001(card.Card):
    "Aspecto Seguridad"
    def __init__(self):
        super(c001, self).__init__(
            gameobject.Characteristics(
                name="Aspecto Seguridad",
                types=[cardtype.CardType.SORCERY],
                ...
            )
        )
        # play_func se asigna desde api_cards.txt
```

## Sistema de Victoria

### Implementación en `APIGame`

```python
def check_victory(self):
    """Gana el jugador con 4 aspectos saludables."""
    for player in self.players_list:
        aspectos_saludables = sum(
            1 for p in player.battlefield
            if (hasattr(p, 'is_aspecto') and p.is_aspecto and p.is_saludable())
        )
        if aspectos_saludables >= 4:
            return player
    return None
```

## Pasos para Completar la Migración

### 1. Crear Parser de Cartas

- [ ] Implementar `parser/parse_api_cards.py`
- [ ] Leer `data/api_cards.txt`
- [ ] Generar clases de cartas en `data/api_cards.py`
- [ ] Generar diccionarios de nombres

### 2. Completar Definiciones de Cartas

- [ ] Todas las cartas de aspecto (17 cartas)
- [ ] Todas las cartas de ataque/problema (29 cartas)
- [ ] Todas las cartas de protección (29 cartas)
- [ ] Todas las cartas de intervención (14 cartas)

### 3. Adaptar Sistema de Turnos

- [ ] Implementar fases del juego (similar a MTG)
- [ ] Sistema de robar cartas (3 cartas al inicio, luego al principio de turno)
- [ ] Sistema de descarte

### 4. Integrar con GUI

- [ ] Modificar `virus_game.py` para usar `APIGame` en lugar de `GameEngine`
- [ ] Adaptar renderizado para leer estado del motor MTG
- [ ] Adaptar eventos de click para usar `play_func()` del motor

### 5. Sistema de IA

- [ ] Adaptar lógica de IA para usar el motor MTG
- [ ] Usar `Player.battlefield` para evaluar estado
- [ ] Usar `stack` para resolver efectos

## Ventajas de la Migración

1. **Separación de responsabilidades**: Lógica vs GUI
2. **Sistema de stack**: Permite efectos más complejos
3. **Habilidades**: Sistema robusto para efectos especiales
4. **Extensibilidad**: Fácil añadir nuevas cartas y mecánicas
5. **Testing**: Más fácil testear la lógica sin GUI

## Consideraciones

### Compatibilidad con Motor MTG

- El motor MTG está diseñado para Magic: The Gathering
- Algunos conceptos (mana, colores de mana) no aplican directamente
- Necesitamos adaptar o simplificar ciertas mecánicas

### Rendimiento

- El motor MTG usa `deepcopy` para rewinding, lo cual puede ser lento
- Considerar optimizaciones para partidas rápidas

## Próximos Pasos

1. Completar parser de cartas
2. Generar todas las clases de cartas
3. Implementar sistema de turnos adaptado
4. Integrar con GUI existente
5. Testing y depuración

