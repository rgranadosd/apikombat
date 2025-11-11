"""
Adaptador entre el sistema actual (GameEngine) y el motor MTG (APIGame)
Permite usar el motor MTG desde virus_game.py manteniendo compatibilidad
"""
import sys
import os
import random

# Añadir el directorio del motor MTG al path
base_path = os.path.dirname(__file__)
project_root = os.path.join(base_path, '..', '..', '..')
mtg_engine_path = os.path.join(project_root, 'mtg-engine')
api_card_game_path = os.path.join(project_root, 'api-card-game')

if mtg_engine_path not in sys.path:
    sys.path.insert(0, mtg_engine_path)
if api_card_game_path not in sys.path:
    sys.path.insert(0, api_card_game_path)

try:
    # Importar desde nuestro api-card-game (que extiende MTG)
    from MTG.api.game_api import APIGame
    from MTG.api.aspecto import AspectoPermanent
    from MTG.api.card_generator import create_deck_from_cartas, create_mtg_card_instance
    # Importar desde nuestro engine
    sys.path.insert(0, project_root)
    from engine import Carta, Jugador, ASPECTOS, ASPECTO_MAP
    MTG_AVAILABLE = True
except Exception as e:
    MTG_AVAILABLE = False
    import traceback
    print(f"⚠ Motor MTG no disponible: {e}")
    traceback.print_exc()


class MTGAdapter:
    """Adaptador que permite usar APIGame desde virus_game.py"""
    
    def __init__(self):
        if not MTG_AVAILABLE:
            raise ImportError("Motor MTG no disponible")
        self.mtg_game = None
        self._initialized = False
        self._carta_to_mtg = {}  # Mapeo Carta -> Card MTG
        self._mtg_to_carta = {}  # Mapeo Card MTG -> Carta
    
    def initialize(self, cartas_mazo: list):
        """Inicializa el motor MTG con las cartas del mazo actual."""
        # Crear decks para ambos jugadores (mismo mazo compartido)
        deck1 = create_deck_from_cartas(cartas_mazo)
        deck2 = create_deck_from_cartas(cartas_mazo.copy())
        
        # Crear el juego MTG
        self.mtg_game = APIGame([deck1, deck2], test=False)
        
        # Configurar nombres de jugadores
        self.mtg_game.players_list[0].name = 'TÚ'
        self.mtg_game.players_list[1].name = 'IA'
        
        # Crear mapeos bidireccionales
        for carta, mtg_card in zip(cartas_mazo, deck1):
            self._carta_to_mtg[id(carta)] = mtg_card
            self._mtg_to_carta[id(mtg_card)] = carta
        
        self._initialized = True
    
    def sync_aspectos_to_mtg(self, jugador: Jugador, mtg_player):
        """Sincroniza los aspectos de un Jugador al formato MTG (permanentes en battlefield)."""
        # Obtener aspectos actuales en MTG
        aspectos_mtg = {asp.aspecto_type: asp for asp in self.mtg_game.get_aspectos(mtg_player)}
        
        # Sincronizar cada aspecto
        for color, data in jugador.aspectos.items():
            if color in aspectos_mtg:
                # Actualizar permanente existente
                aspecto_mtg = aspectos_mtg[color]
                aspecto_mtg.vulnerable = data.get('vulnerable', False)
                aspecto_mtg.protecciones = data.get('protecciones', 0)
            else:
                # Crear nuevo permanente
                aspecto_mtg = AspectoPermanent(color, controller=mtg_player)
                aspecto_mtg.vulnerable = data.get('vulnerable', False)
                aspecto_mtg.protecciones = data.get('protecciones', 0)
                mtg_player.battlefield.add(aspecto_mtg)
        
        # Eliminar aspectos que ya no existen
        for aspecto_mtg in list(aspectos_mtg.values()):
            if aspecto_mtg.aspecto_type not in jugador.aspectos:
                mtg_player.battlefield.remove(aspecto_mtg)
                mtg_player.graveyard.add(aspecto_mtg)
    
    def sync_aspectos_from_mtg(self, mtg_player, jugador: Jugador):
        """Sincroniza los aspectos del formato MTG al formato actual."""
        jugador.aspectos = {}
        for aspecto_mtg in self.mtg_game.get_aspectos(mtg_player):
            jugador.aspectos[aspecto_mtg.aspecto_type] = {
                'vulnerable': aspecto_mtg.vulnerable,
                'protecciones': aspecto_mtg.protecciones
            }
    
    def sync_mano_to_mtg(self, jugador: Jugador, mtg_player):
        """Sincroniza la mano de un Jugador al formato MTG."""
        # Limpiar mano MTG
        while len(mtg_player.hand) > 0:
            card = mtg_player.hand[0]
            mtg_player.hand.remove(card)
            mtg_player.library.add(card)
        
        # Añadir cartas de la mano actual
        for carta in jugador.mano:
            if id(carta) in self._carta_to_mtg:
                mtg_card = self._carta_to_mtg[id(carta)]
                if mtg_card in mtg_player.library:
                    mtg_player.library.remove(mtg_card)
                mtg_player.hand.add(mtg_card)
    
    def sync_mano_from_mtg(self, mtg_player, jugador: Jugador):
        """Sincroniza la mano del formato MTG al formato actual."""
        jugador.mano = []
        for mtg_card in mtg_player.hand:
            if id(mtg_card) in self._mtg_to_carta:
                carta = self._mtg_to_carta[id(mtg_card)]
                jugador.mano.append(carta)
    
    def get_mtg_player(self, jugador: Jugador):
        """Obtiene el Player MTG correspondiente a un Jugador."""
        if not self._initialized or not self.mtg_game:
            return None
        # Buscar por índice (asumiendo mismo orden)
        try:
            idx = self.mtg_game.players_list[0].game.players_list.index if hasattr(self.mtg_game.players_list[0], 'game') else None
            # Buscar por nombre (más seguro)
            for mtg_player in self.mtg_game.players_list:
                if mtg_player.name == jugador.nombre:
                    return mtg_player
            # Fallback: usar índice si los nombres coinciden
            if len(self.mtg_game.players_list) == 2:
                if jugador.nombre == 'TÚ':
                    return self.mtg_game.players_list[0]
                elif jugador.nombre == 'IA':
                    return self.mtg_game.players_list[1]
        except Exception:
            pass
        return None
    
    def jugar_carta_mtg(self, jugador: Jugador, carta: Carta) -> bool:
        """Intenta jugar una carta usando el motor MTG."""
        if not self._initialized:
            return False
        
        mtg_player = self.get_mtg_player(jugador)
        if mtg_player is None:
            return False
        
        # Obtener la carta MTG correspondiente
        if id(carta) not in self._carta_to_mtg:
            return False
        
        mtg_card = self._carta_to_mtg[id(carta)]
        
        # Sincronizar estado antes de jugar
        self.sync_aspectos_to_mtg(jugador, mtg_player)
        
        # Por ahora, el motor MTG no tiene implementadas las habilidades de las cartas
        # así que delegamos al motor actual pero mantenemos la sincronización
        # TODO: Implementar play_func para cada tipo de carta en el formato MTG
        # Esto requiere procesar api_cards.txt y generar las clases con sus efectos
        
        # Sincronizar estado después (aunque no hayamos jugado realmente en MTG)
        self.sync_aspectos_from_mtg(mtg_player, jugador)
        
        # Retornar False para que use el motor actual
        return False
    
    def es_jugable_mtg(self, carta: Carta, jugador: Jugador) -> tuple[bool, str]:
        """Verifica si una carta es jugable usando el motor MTG."""
        # Por ahora, delegar al motor actual
        # TODO: Implementar validación usando el motor MTG
        return True, ''
    
    def comprobar_victoria_mtg(self) -> str | None:
        """Comprueba si hay un ganador usando el motor MTG."""
        if not self._initialized:
            return None
        
        winner = self.mtg_game.check_victory()
        if winner:
            return winner.name
        return None
