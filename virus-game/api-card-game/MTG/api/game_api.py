"""
Game API - Extensión del Game del motor MTG para el juego API Card Game
"""
import sys
import os

# Añadir el directorio del motor MTG al path
mtg_engine_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'mtg-engine')
if mtg_engine_path not in sys.path:
    sys.path.insert(0, mtg_engine_path)

from MTG import game
from MTG.api.aspecto import AspectoPermanent


class APIGame(game.Game):
    """Extensión de Game para el juego API Card Game."""
    
    def __init__(self, decks, test=False):
        super().__init__(decks, test)
        
        # Inicializar code_freeze_shield para cada jugador
        for player in self.players_list:
            player.code_freeze_shield = False
    
    def check_victory(self):
        """Comprueba si hay un ganador.
        Gana el jugador que tenga 4 aspectos saludables."""
        for player in self.players_list:
            aspectos_saludables = sum(
                1 for p in player.battlefield
                if (hasattr(p, 'is_aspecto') and p.is_aspecto and p.is_saludable())
            )
            if aspectos_saludables >= 4:
                return player
        return None
    
    def get_aspectos(self, player):
        """Retorna todos los aspectos de un jugador."""
        return [
            p for p in player.battlefield
            if hasattr(p, 'is_aspecto') and p.is_aspecto
        ]
    
    def get_aspecto_by_type(self, player, aspecto_type):
        """Retorna el aspecto de un tipo específico de un jugador."""
        for asp in self.get_aspectos(player):
            if asp.aspecto_type == aspecto_type:
                return asp
        return None

