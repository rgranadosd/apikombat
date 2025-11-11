#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API CARD GAME - Nueva GUI con pygame_cards
Conectado al motor MTG
"""
import pygame
import sys
import os
from typing import List, Dict, Optional, Tuple

# Importar lógica del juego
from engine import Carta, Jugador, GameEngine, ASPECTOS, ASPECTO_MAP

# Importar pygame_cards
from pygame_cards import Card, Deck, Zone, GameUI

# Flag para usar motor MTG (por defecto activado)
USE_MTG_ENGINE = os.getenv('USE_MTG_ENGINE', 'true').lower() not in ('false', '0', 'no', 'off')

if USE_MTG_ENGINE:
    try:
        api_card_game_path = os.path.join(os.path.dirname(__file__), 'api-card-game')
        mtg_engine_path = os.path.join(os.path.dirname(__file__), 'mtg-engine')
        if api_card_game_path not in sys.path:
            sys.path.insert(0, api_card_game_path)
        if mtg_engine_path not in sys.path:
            sys.path.insert(0, mtg_engine_path)
        from api.adapter import MTGAdapter
        mtg_adapter = MTGAdapter()
        print("✓ Motor MTG activado")
    except Exception as e:
        print(f"⚠ No se pudo cargar motor MTG: {e}")
        USE_MTG_ENGINE = False
        mtg_adapter = None
else:
    mtg_adapter = None

pygame.init()
pygame.font.init()

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
FPS = 60

# Colores
COLOR_BOARD = (13, 77, 46)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)


class APICard(Card):
    """Carta personalizada para el juego API Card Game."""
    
    def __init__(self, carta: Carta, image_path: Optional[str] = None):
        super().__init__(id=id(carta), title=carta.nombre, size=(120, 160))
        self.carta = carta  # Referencia a la Carta del engine
        self.image_path = image_path
        self.load_images()
    
    def load_images(self):
        """Carga las imágenes de la carta."""
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.front_image = pygame.image.load(self.image_path).convert_alpha()
                self.front_image = pygame.transform.scale(self.front_image, self.size)
            except:
                self.front_image = self._create_card_front()
        else:
            self.front_image = self._create_card_front()
        
        # Cargar reverso desde assets
        back_path = os.path.join(os.path.dirname(__file__), 'assets', 'cards', 'back.png')
        if os.path.exists(back_path):
            try:
                self.back_image = pygame.image.load(back_path).convert_alpha()
                self.back_image = pygame.transform.scale(self.back_image, self.size)
            except:
                self.back_image = self._create_default_back()
        else:
            self.back_image = self._create_default_back()
    
    def _create_card_front(self) -> pygame.Surface:
        """Crea el frente de la carta con información del tipo."""
        surf = pygame.Surface(self.size, pygame.SRCALPHA)
        
        # Color según tipo
        colors = {
            'fundamental': (100, 150, 200),
            'hack': (200, 100, 100),
            'shield': (100, 200, 100),
            'management': (200, 200, 100),
        }
        color = colors.get(self.carta.tipo, (150, 150, 150))
        
        pygame.draw.rect(surf, color, (0, 0, *self.size), border_radius=8)
        pygame.draw.rect(surf, (255, 255, 255), (5, 5, self.size[0]-10, self.size[1]-10), border_radius=5)
        
        # Título
        font_title = pygame.font.Font(None, 18)
        title = font_title.render(self.carta.nombre[:12], True, (0, 0, 0))
        title_rect = title.get_rect(center=(self.size[0]//2, 30))
        surf.blit(title, title_rect)
        
        # Tipo
        font_type = pygame.font.Font(None, 14)
        tipo_text = font_type.render(self.carta.tipo.upper(), True, (50, 50, 50))
        tipo_rect = tipo_text.get_rect(center=(self.size[0]//2, 50))
        surf.blit(tipo_text, tipo_rect)
        
        # Color/Aspecto
        if self.carta.color in ASPECTO_MAP:
            aspecto_text = font_type.render(ASPECTO_MAP[self.carta.color]['label'][:10], True, (50, 50, 50))
            aspecto_rect = aspecto_text.get_rect(center=(self.size[0]//2, 130))
            surf.blit(aspecto_text, aspecto_rect)
        
        return surf


class APIGameGUI:
    """Interfaz gráfica del juego usando pygame_cards."""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('API Card Game')
        self.clock = pygame.time.Clock()
        
        # Inicializar motor del juego
        self.engine = GameEngine()
        self.use_mtg_engine = USE_MTG_ENGINE and mtg_adapter is not None
        self.mtg_adapter = mtg_adapter if self.use_mtg_engine else None
        
        # Iniciar partida
        self.engine.iniciar_partida()
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                self.mtg_adapter.initialize(self.engine.mazo)
            except Exception as e:
                print(f"⚠ Error inicializando motor MTG: {e}")
                self.use_mtg_engine = False
        
        # Crear estructura de pygame_cards
        self._setup_ui()
        
        # Estado del juego
        self.running = True
        self.selected_card: Optional[APICard] = None
    
    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        # Mazo principal (centro superior)
        self.deck = Deck(position=(WINDOW_WIDTH // 2 - 60, 50))
        
        # Zona de mano del jugador (abajo)
        self.hand_zone = Zone(
            position=(100, WINDOW_HEIGHT - 200),
            size=(WINDOW_WIDTH - 200, 180),
            max_cards=None,
            card_spacing=10
        )
        
        # Zonas de aspectos del jugador (centro izquierda)
        self.player_aspects_zones: Dict[str, Zone] = {}
        aspect_y = WINDOW_HEIGHT // 2 - 100
        for i, aspecto in enumerate(ASPECTOS):
            zone = Zone(
                position=(50 + i * 150, aspect_y),
                size=(140, 200),
                max_cards=1
            )
            self.player_aspects_zones[aspecto] = zone
        
        # Zonas de aspectos del oponente (centro derecha)
        self.opponent_aspects_zones: Dict[str, Zone] = {}
        for i, aspecto in enumerate(ASPECTOS):
            zone = Zone(
                position=(WINDOW_WIDTH - 190 - i * 150, aspect_y),
                size=(140, 200),
                max_cards=1
            )
            self.opponent_aspects_zones[aspecto] = zone
        
        # Zona de descarte (esquina superior derecha)
        self.discard_zone = Zone(
            position=(WINDOW_WIDTH - 170, 50),
            size=(120, 160),
            max_cards=None
        )
        
        # Crear GameUI
        all_zones = (
            [self.hand_zone, self.discard_zone] +
            list(self.player_aspects_zones.values()) +
            list(self.opponent_aspects_zones.values())
        )
        self.game_ui = GameUI(self.screen, self.deck, all_zones)
        
        # Cargar cartas iniciales
        self._load_cards()
    
    def _load_cards(self):
        """Carga las cartas del juego en la interfaz."""
        # Limpiar zonas
        self.hand_zone.clear()
        self.deck.cards.clear()
        
        # Crear cartas para la mano del jugador
        jugador = self.engine.jugadores[0]
        for carta in jugador.mano:
            api_card = APICard(carta)
            self.hand_zone.add_card(api_card)
        
        # Crear cartas para el mazo (mostrar solo la superior)
        if self.engine.mazo:
            top_card = self.engine.mazo[0]
            api_card = APICard(top_card)
            api_card.flipped = True
            self.deck.add_card(api_card)
    
    def _update_aspects(self):
        """Actualiza las zonas de aspectos según el estado del juego."""
        # Limpiar zonas de aspectos
        for zone in self.player_aspects_zones.values():
            zone.clear()
        for zone in self.opponent_aspects_zones.values():
            zone.clear()
        
        # Actualizar aspectos del jugador
        jugador = self.engine.jugadores[0]
        for aspecto, data in jugador.aspectos.items():
            if aspecto in self.player_aspects_zones:
                # Crear carta representando el aspecto
                carta = Carta('fundamental', aspecto, ASPECTO_MAP[aspecto]['label'])
                api_card = APICard(carta)
                self.player_aspects_zones[aspecto].add_card(api_card)
        
        # Actualizar aspectos del oponente
        oponente = self.engine.jugadores[1]
        for aspecto, data in oponente.aspectos.items():
            if aspecto in self.opponent_aspects_zones:
                carta = Carta('fundamental', aspecto, ASPECTO_MAP[aspecto]['label'])
                api_card = APICard(carta)
                api_card.flipped = True  # Mostrar reverso para el oponente
                self.opponent_aspects_zones[aspecto].add_card(api_card)
    
    def _handle_card_play(self, api_card: APICard, target_zone: Zone):
        """Maneja cuando se juega una carta."""
        carta = api_card.carta
        jugador = self.engine.jugadores[0]
        
        # Verificar si es jugable
        jugable, msg = self.engine.es_jugable(carta, jugador)
        if not jugable:
            print(f"No se puede jugar: {msg}")
            return False
        
        # Intentar jugar la carta
        if self.engine.jugar_carta(jugador, carta):
            # Remover de la mano
            jugador.mano.remove(carta)
            self._load_cards()
            self._update_aspects()
            
            # Comprobar victoria
            winner = self.engine.comprobar_victoria()
            if winner:
                print(f"¡Victoria de {winner}!")
                self.running = False
            
            return True
        return False
    
    def handle_event(self, event: pygame.event.Event):
        """Maneja eventos de Pygame."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_SPACE:
                # Robar carta
                if self.engine.mazo:
                    carta = self.engine.mazo.pop(0)
                    self.engine.jugadores[0].mano.append(carta)
                    self._load_cards()
        
        # Delegar a GameUI
        self.game_ui.handle_event(event)
        
        # Detectar si se soltó una carta en una zona de aspecto
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.game_ui.dragged_card:
                pos = event.pos
                for aspecto, zone in self.player_aspects_zones.items():
                    if zone.contains_point(pos):
                        if isinstance(self.game_ui.dragged_card, APICard):
                            self._handle_card_play(self.game_ui.dragged_card, zone)
                        break
    
    def update(self):
        """Actualiza el estado del juego."""
        # Actualizar aspectos periódicamente
        self._update_aspects()
    
    def draw(self):
        """Dibuja el juego."""
        # Fondo
        self.screen.fill(COLOR_BOARD)
        
        # Dibujar UI
        self.game_ui.draw()
        
        # Dibujar información del juego
        self._draw_hud()
        
        pygame.display.flip()
    
    def _draw_hud(self):
        """Dibuja información del juego."""
        font = pygame.font.Font(None, 24)
        
        # Turno actual
        turno_text = font.render(f"Turno: {self.engine.jugadores[self.engine.turno].nombre}", True, COLOR_WHITE)
        self.screen.blit(turno_text, (10, 10))
        
        # Cartas en mano
        mano_count = len(self.engine.jugadores[0].mano)
        mano_text = font.render(f"Cartas en mano: {mano_count}", True, COLOR_WHITE)
        self.screen.blit(mano_text, (10, 40))
        
        # Mazo
        mazo_count = len(self.engine.mazo)
        mazo_text = font.render(f"Cartas en mazo: {mazo_count}", True, COLOR_WHITE)
        self.screen.blit(mazo_text, (10, 70))
    
    def run(self):
        """Bucle principal del juego."""
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()


if __name__ == '__main__':
    game = APIGameGUI()
    game.run()

