"""
Generador dinámico de clases de cartas MTG desde las cartas actuales
Crea clases Card del motor MTG a partir de las cartas del sistema actual
"""
import sys
import os

# Añadir el directorio del motor MTG al path (ya se hace más abajo)

# Importar desde el motor MTG clonado
# Asegurar que mtg_engine_path está en sys.path antes de importar
mtg_engine_path = os.path.join(os.path.dirname(__file__), '..', '..', 'mtg-engine')
if mtg_engine_path not in sys.path:
    sys.path.insert(0, mtg_engine_path)

try:
    from MTG import card
    from MTG import gameobject
    from MTG import cardtype
except ImportError as e:
    # Si no está disponible, usar fallback
    print(f"⚠ No se pudo importar MTG: {e}")
    card = None
    gameobject = None
    cardtype = None

# Importar desde nuestro engine
try:
    from engine import Carta, ASPECTOS, ASPECTO_MAP
except ImportError:
    # Fallback si no está disponible
    Carta = None
    ASPECTOS = []
    ASPECTO_MAP = {}


# Cache de clases generadas
_generated_card_classes = {}


def generate_card_class(carta: Carta) -> type:
    """Genera dinámicamente una clase Card del motor MTG desde una Carta actual."""
    if card is None or gameobject is None or cardtype is None:
        raise ImportError("Motor MTG no disponible")
    
    # Crear ID único basado en tipo, color y nombre
    card_id = f"api_{carta.tipo}_{carta.color}_{carta.nombre}".replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('-', '_')
    
    # Si ya existe, retornarla
    if card_id in _generated_card_classes:
        return _generated_card_classes[card_id]
    
    # Crear características básicas
    characteristics = gameobject.Characteristics(
        name=carta.nombre,
        types=[cardtype.CardType.SORCERY],  # Por defecto sorcery, se puede cambiar según tipo
        supertype=[],
        color=[],
        mana_cost='',
        text=f'{carta.tipo}:{carta.color}'
    )
    
    # Crear la clase dinámicamente
    class_name = card_id.capitalize()
    card_class = type(
        class_name,
        (card.Card,),
        {
            '__init__': lambda self: super(card.Card, self).__init__(characteristics),
            '_carta_original': carta,  # Guardar referencia a la carta original
            '__repr__': lambda self: f"{class_name}({carta.tipo}:{carta.color}:{carta.nombre})"
        }
    )
    
    # Guardar en cache
    _generated_card_classes[card_id] = card_class
    
    return card_class


def create_mtg_card_instance(carta: Carta):
    """Crea una instancia de Card del motor MTG desde una Carta actual."""
    card_class = generate_card_class(carta)
    instance = card_class()
    # Guardar referencia a la carta original para conversión inversa
    instance._carta_original = carta
    return instance


def create_deck_from_cartas(cartas: list) -> list:
    """Convierte una lista de Cartas actuales a un deck del motor MTG."""
    deck = []
    for carta in cartas:
        mtg_card = create_mtg_card_instance(carta)
        deck.append(mtg_card)
    return deck

