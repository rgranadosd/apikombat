#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API CARD GAME - New UI with pygame_cards
Connected to the MTG engine
"""
import pygame
import sys
import os
import argparse
import math
import random
import time
from typing import List, Dict, Optional, Tuple, Set

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:
    np = None  # type: ignore
    _HAS_NUMPY = False

# Import game logic
from engine import Carta, Jugador, GameEngine, ASPECTOS, ASPECTO_MAP

# Import pygame_cards
from pygame_cards import Card, Deck, Zone, GameUI

# Flag to use the MTG engine (enabled by default)
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
        print("✓ MTG engine enabled")
    except Exception as e:
        print(f"⚠ Could not load MTG engine: {e}")
        USE_MTG_ENGINE = False
        mtg_adapter = None
else:
    mtg_adapter = None

pygame.init()
pygame.font.init()

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
FPS = 60

# Colors
COLOR_BOARD = (20, 30, 70)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_SURFACE = (30, 48, 96)
COLOR_PANEL = (45, 64, 120)
COLOR_ACCENT_ORANGE = (255, 120, 40)
COLOR_ACCENT_ORANGE_HOVER = (255, 160, 80)
COLOR_ACCENT_CYAN = (0, 200, 220)
COLOR_ACCENT_CYAN_HOVER = (60, 240, 255)
COLOR_TEXT_MUTED = (190, 200, 230)
COLOR_PLACEHOLDER_ACTIVE = (120, 200, 255)
COLOR_PLACEHOLDER_INACTIVE = (120, 150, 200)
COLOR_PLACEHOLDER_BORDER = (235, 235, 255)
COLOR_TOAST_BORDER = (255, 120, 40)
COLOR_TOAST_GLOW = (0, 200, 220)

CARD_WIDTH = 120
CARD_HEIGHT = 160


def _render_text_fit(text: str, color: Tuple[int, int, int], max_width: int, base_size: int = 18) -> Tuple[pygame.Surface, pygame.font.Font]:
    """Render text reducing the size until it fits max_width."""
    size = base_size
    chosen_font = pygame.font.Font(None, size)
    surface = chosen_font.render(text, True, color)
    while surface.get_width() > max_width and size > 10:
        size -= 2
        chosen_font = pygame.font.Font(None, size)
        surface = chosen_font.render(text, True, color)
    return surface, chosen_font


class APICard(Card):
    """Custom card for the API Card Game."""
    
    def __init__(self, carta: Carta, image_path: Optional[str] = None, is_vulnerable: bool = False, protecciones: int = 0):
        super().__init__(id=id(carta), title=carta.nombre, size=(120, 160))
        self.carta = carta  # Reference to the engine card
        self.image_path = image_path
        self.is_vulnerable = is_vulnerable  # Vulnerable state (Alerts)
        self.protecciones = protecciones  # Number of protections
        self.load_images()
    
    def load_images(self):
        """Load the card images."""
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.front_image = pygame.image.load(self.image_path).convert_alpha()
                self.front_image = pygame.transform.scale(self.front_image, self.size)
            except:
                self.front_image = self._create_card_front()
        else:
            self.front_image = self._create_card_front()
        
        # Load card back from assets
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
        """Create the front of the card with its metadata."""
        surf = pygame.Surface(self.size, pygame.SRCALPHA)
        
        # Color by type
        colors = {
            'fundamental': (58, 110, 200),
            'hack': (190, 80, 80),
            'shield': (80, 190, 150),
            'management': (200, 180, 80),
        }
        color = colors.get(self.carta.tipo, (160, 160, 180))
        
        # If the card is vulnerable (Alerts), use a red/orange hint
        if self.is_vulnerable:
            color = (220, 100, 50)  # Orange/red to highlight vulnerability
        
        pygame.draw.rect(surf, color, (0, 0, *self.size), border_radius=12)
        
        # Inner background - darker when vulnerable
        bg_color = (210, 210, 220) if self.is_vulnerable else (245, 245, 255)
        pygame.draw.rect(surf, bg_color, (6, 6, self.size[0]-12, self.size[1]-12), border_radius=10)
        
        # Title
        title_color = (200, 0, 0) if self.is_vulnerable else (0, 0, 0)
        title_surface, _ = _render_text_fit(self.carta.nombre, title_color, self.size[0] - 16, base_size=20)
        title_rect = title_surface.get_rect(center=(self.size[0]//2, 30))
        surf.blit(title_surface, title_rect)
        
        # Type
        font_type = pygame.font.Font(None, 14)
        tipo_text = font_type.render(self.carta.tipo.upper(), True, (40, 40, 70))
        tipo_rect = tipo_text.get_rect(center=(self.size[0]//2, 52))
        surf.blit(tipo_text, tipo_rect)
        
        # State: vulnerable (Alerts) or protected
        if self.is_vulnerable:
            # Show "ALERTS" in red
            estado_text = font_type.render("⚠ ALERTS", True, (200, 0, 0))
            estado_rect = estado_text.get_rect(center=(self.size[0]//2, 70))
            surf.blit(estado_text, estado_rect)
        elif self.protecciones > 0:
            # Show number of protections
            proteccion_text = font_type.render(f"🛡 {self.protecciones}", True, (0, 130, 120))
            proteccion_rect = proteccion_text.get_rect(center=(self.size[0]//2, 70))
            surf.blit(proteccion_text, proteccion_rect)
        
        # Aspect/Domain label
        if self.carta.color in ASPECTO_MAP:
            aspecto_label = ASPECTO_MAP[self.carta.color]['label']
            aspecto_surface, _ = _render_text_fit(aspecto_label, (40, 40, 70), self.size[0] - 20, base_size=16)
            aspecto_rect = aspecto_surface.get_rect(center=(self.size[0]//2, 128))
            surf.blit(aspecto_surface, aspecto_rect)
        
        return surf


class APIGameGUI:
    """Graphical interface for the game using pygame_cards."""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('API Card Game')
        self.clock = pygame.time.Clock()
        
        # Initialize game engine
        self.engine = GameEngine()
        
        # Store last AI action message (displayed on the HUD)
        self.last_ai_action_message = ""
        self.use_mtg_engine = USE_MTG_ENGINE and mtg_adapter is not None
        self.mtg_adapter = mtg_adapter if self.use_mtg_engine else None
        
        # Start a new match
        self.engine.iniciar_partida()
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                self.mtg_adapter.initialize(self.engine.mazo)
            except Exception as e:
                print(f"⚠ Error initializing MTG engine: {e}")
                self.use_mtg_engine = False
        
        # Game state (initialize BEFORE calling _setup_ui)
        self.running = True
        self.selected_card: Optional[APICard] = None
        self.discard_selection: List[int] = []  # Indices of cards selected for discard (legacy behavior)
        self.cartas_multi_drag: List[int] = []  # Indices involved in multi-drag
        self.multi_drag_cards_refs: List[APICard] = []
        self.multi_drag_offsets: Dict[APICard, Tuple[int, int]] = {}
        self.selected_hand_idx: Optional[int] = None  # Selected card index in hand
        self.turn_action: str = 'none'  # 'none' | 'play' | 'discard'
        self.drag_origin_pos: Optional[Tuple[int, int]] = None
        self.drag_origin_zone: Optional[Zone] = None
        self.drag_origin_index: Optional[int] = None
        self.auto_play_enabled: bool = False
        self._last_auto_toggle: float = 0.0
        
        # Bottom control buttons
        button_y = WINDOW_HEIGHT - 60
        button_width = 150
        button_height = 38
        self.btn_start_rect = pygame.Rect(30, button_y, button_width, button_height)
        spacing = 20
        self.btn_quit_rect = pygame.Rect(self.btn_start_rect.right + spacing, button_y, button_width, button_height)
        print(f"[DEBUG UI] Button 'New game': {self.btn_start_rect}, 'Quit': {self.btn_quit_rect}")
        
        # Toast message registry (author, message, timestamp)
        self.message_toasts: List[Tuple[str, str, float]] = []
        self.toast_duration = 4.0
        self.toast_anim_time = 0.35
        self.modal_victoria_visible = False
        self.modal_victoria_jugador: Optional[str] = None
        self.modal_rect = pygame.Rect(0, 0, 0, 0)
        self.modal_close_rect = pygame.Rect(0, 0, 0, 0)
        self.modal_btn_new = pygame.Rect(0, 0, 0, 0)
        self.modal_btn_quit = pygame.Rect(0, 0, 0, 0)
        self.modal_victoria_ack = False
        
        # Board title
        self.board_title_surface: Optional[pygame.Surface] = None
        self.board_title_shadow: Optional[pygame.Surface] = None
        self.board_title_pos: Tuple[int, int] = (0, 0)
        self._init_board_title()
        
        # Player avatars
        self.avatar_max_size = (80, 80)
        self.avatar_margin = 35
        self.player_avatar_color: Optional[pygame.Surface] = None
        self.player_avatar_gray: Optional[pygame.Surface] = None
        self.bot_avatar_color: Optional[pygame.Surface] = None
        self.bot_avatar_gray: Optional[pygame.Surface] = None
        self.latest_toast_text: Optional[Tuple[str, str]] = None
        self._load_avatar_assets()
        
        # Visual effects collection (e.g. destruction explosions)
        self.active_effects: List[Dict] = []
        
        # Build pygame_cards structures
        self._setup_ui()
    
    def _init_board_title(self) -> None:
        """Prepare the 'APIKOMBAT' heading in the center of the table."""
        font_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'mkmyth.ttf')
        try:
            title_font = pygame.font.Font(font_path, 120)
        except Exception:
            title_font = pygame.font.Font(None, 120)
        
        text = "APIKOMBAT"
        main_color = (220, 45, 45)
        shadow_color = (60, 10, 10)
        
        # Render principal
        base_text = title_font.render(text, True, main_color).convert_alpha()
        width, height = base_text.get_size()
        
        # Aplicar degradado vertical (rojo intenso → burdeos)
        gradient_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        top_color = (255, 120, 130)
        bottom_color = (120, 10, 10)
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
            pygame.draw.line(gradient_surface, (r, g, b), (0, y), (width, y))
        base_text.blit(gradient_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        # Highlight the top with a soft glow limited to the glyph mask
        highlight_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        highlight_height = int(height * 0.45)
        for y in range(highlight_height):
            intensity = int(90 * (1 - y / max(1, highlight_height)))
            pygame.draw.line(highlight_surface, (255, 220, 220, intensity), (0, y), (width, y))
        # Apply a mask to prevent rectangular edges
        text_mask = pygame.mask.from_surface(base_text)
        mask_surface = text_mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        mask_surface.set_colorkey((0, 0, 0))
        highlight_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        base_text.blit(highlight_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        base_text.set_alpha(220)
        
        # Build the expanded surface that will hold outline and glow layers
        margin = 40
        final_width = width + margin * 2
        final_height = height + margin * 2
        final_surface = pygame.Surface((final_width, final_height), pygame.SRCALPHA)
        
        # Multiple outline offsets
        outline_text = title_font.render(text, True, shadow_color).convert_alpha()
        outline_positions = [
            (-5, 0), (5, 0), (0, -5), (0, 5),
            (-4, -4), (4, -4), (-4, 4), (4, 4),
            (-2, 2), (2, 2), (-2, -2), (2, -2)
        ]
        for ox, oy in outline_positions:
            pos = (margin + ox, margin + oy)
            final_surface.blit(outline_text, pos)
        
        # Outer glow
        glow_scale = 1.18
        glow_size = (int(width * glow_scale), int(height * glow_scale))
        glow_surface = pygame.transform.smoothscale(base_text, glow_size)
        glow_surface.set_alpha(120)
        glow_surface.fill((255, 120, 120, 0), special_flags=pygame.BLEND_RGBA_MULT)
        glow_pos = (
            margin + (width - glow_size[0]) // 2,
            margin + (height - glow_size[1]) // 2
        )
        final_surface.blit(glow_surface, glow_pos)
        
        # Composite the main text
        final_surface.blit(base_text, (margin, margin))
        
        self.board_title_surface = final_surface
        self.board_title_shadow = None
        
        x = WINDOW_WIDTH // 2 - self.board_title_surface.get_width() // 2 - 80
        y = WINDOW_HEIGHT // 2 - self.board_title_surface.get_height() // 2
        self.board_title_pos = (x, y)
    
    def _setup_ui(self):
        """Configure the user interface."""
        # MAIN DECK – aligned to the turn indicator
        # The indicator sits at WINDOW_WIDTH - 520, so the deck is aligned accordingly
        deck_x = WINDOW_WIDTH - 520  # Aligned with turn indicator
        deck_y = WINDOW_HEIGHT // 2 - 80  # Vertical center (adjusted to card height)
        self.deck_zone = Zone(
            position=(deck_x, deck_y),
            size=(140, 180),  # Same size as fundamentals
            max_cards=None,
            card_spacing=1  # Minimal spacing so cards stack
        )
        # Legacy deck (shows only the top card for compatibility)
        self.deck = Deck(position=(deck_x + 10, deck_y))
        
        # Prepare static placeholders for both hands (aligned with deck and discard)
        slot_width = CARD_WIDTH
        slot_height = CARD_HEIGHT
        slot_spacing = 160  # Keep same spacing used between deck and discard
        hand_width = slot_width + slot_spacing * 2
        base_x = deck_x - slot_spacing
        top_y = deck_y - slot_height - 40
        bottom_y = deck_y + 180 + 40  # 180 = deck height, 40 = breathing room

        self.player2_hand_slot_rects = [
            pygame.Rect(base_x + i * slot_spacing, top_y, slot_width, slot_height) for i in range(3)
        ]
        self.player1_hand_slot_rects = [
            pygame.Rect(base_x + i * slot_spacing, bottom_y, slot_width, slot_height) for i in range(3)
        ]

        # PLAYER 1 (YOU) hand zone – bottom
        self.player1_hand_zone = Zone(
            position=(base_x, bottom_y),
            size=(hand_width, slot_height),
            max_cards=3,
            card_spacing=10
        )
        self.player1_hand_zone.custom_positions = self.player1_hand_slot_rects
        
        # PLAYER 2 (AI) hand zone – top (cards face down)
        self.player2_hand_zone = Zone(
            position=(base_x, top_y),
            size=(hand_width, slot_height),
            max_cards=3,
            card_spacing=10
        )
        self.player2_hand_zone.custom_positions = self.player2_hand_slot_rects
        
        # FUNDAMENTAL (ASPECT) HOLDERS – close to each player for quick glance
        
        # Aspect zones for PLAYER 1 (YOU) – right above the hand (bottom)
        self.player1_aspects_zones: Dict[str, Zone] = {}
        aspect_size = (140, 180)
        center_y_player1 = bottom_y + slot_height // 2
        aspect_y_player1 = center_y_player1 - aspect_size[1] // 2
        for i, aspecto in enumerate(ASPECTOS):
            zone_x = 100 + i * 150
            zone = Zone(
                position=(zone_x, aspect_y_player1),
                size=aspect_size,
                max_cards=1
            )
            self.player1_aspects_zones[aspecto] = zone
        
        # Aspect zones for PLAYER 2 (AI) – right below the hand (top)
        self.player2_aspects_zones: Dict[str, Zone] = {}
        center_y_player2 = top_y + slot_height // 2
        aspect_y_player2 = center_y_player2 - aspect_size[1] // 2
        for i, aspecto in enumerate(ASPECTOS):
            zone_x = 100 + i * 150
            zone = Zone(
                position=(zone_x, aspect_y_player2),
                size=aspect_size,
                max_cards=1
            )
            self.player2_aspects_zones[aspecto] = zone
        
        # DISCARD HOLDER – next to the deck, aligned vertically
        discard_x = WINDOW_WIDTH - 520 + 160  # Deck width (140px) + 20px gap
        discard_y = WINDOW_HEIGHT // 2 - 80  # Same height as the deck (card-adjusted)
        self.discard_zone = Zone(
            position=(discard_x, discard_y),
            size=(140, 180),  # Same size as fundamentals
            max_cards=None,
            card_spacing=1  # Minimal spacing to stack
        )
        
        # Create GameUI with all zones
        all_zones = (
            [self.player1_hand_zone, self.player2_hand_zone, self.discard_zone, self.deck_zone] +
            list(self.player1_aspects_zones.values()) +
            list(self.player2_aspects_zones.values())
        )
        self.game_ui = GameUI(self.screen, self.deck, all_zones)
        
        # Load initial cards
        self._load_cards()
        # Initialize discard pile visuals
        self._update_discard()
    
    def _load_cards(self):
        """Load the engine cards into the interface."""
        # Clear zones
        self.player1_hand_zone.clear()
        self.player2_hand_zone.clear()
        self.deck.cards.clear()
        self.deck_zone.clear()
        
        # Create cards for PLAYER 1 (YOU) – visible
        jugador1 = self.engine.jugadores[0]
        for i, carta in enumerate(jugador1.mano):
            api_card = APICard(carta)
            # Mark as selected if it is in the discard_selection list
            if i in self.discard_selection:
                api_card.selected = True
            self.player1_hand_zone.add_card(api_card)
        
        # Create cards for PLAYER 2 (AI) – face down
        jugador2 = self.engine.jugadores[1]
        for carta in jugador2.mano:
            api_card = APICard(carta)
            api_card.flipped = True  # Oponent cards stay face down
            self.player2_hand_zone.add_card(api_card)
        
        # Populate the DECK (show remaining cards stacked)
        if self.engine.mazo:
            # Show up to the last 10 cards (newest on top)
            cartas_visibles = self.engine.mazo[-10:] if len(self.engine.mazo) > 10 else self.engine.mazo
            for carta in reversed(cartas_visibles):  # Reverse so the newest is placed last (visible)
                api_card = APICard(carta)
                api_card.flipped = True  # Deck cards remain face down
                self.deck_zone.add_card(api_card)
            
            # Also mirror the top card in the legacy Deck object
            top_card = self.engine.mazo[-1]  # Last card (next to draw)
            api_card = APICard(top_card)
            api_card.flipped = True
            self.deck.add_card(api_card)
    
    def _update_aspects(self):
        """Refresh aspect (fundamental) zones according to engine state."""
        # Clear aspect zones
        for zone in self.player1_aspects_zones.values():
            zone.clear()
        for zone in self.player2_aspects_zones.values():
            zone.clear()
        
        # Player 1 (YOU) aspects – keep every slot visible whether occupied or not
        jugador1 = self.engine.jugadores[0]
        for aspecto in ASPECTOS:
            if aspecto in self.player1_aspects_zones:
                if aspecto in jugador1.aspectos:
                    # Aspect unlocked – create a card that represents its current state
                    data = jugador1.aspectos[aspecto]
                    carta = Carta('fundamental', aspecto, ASPECTO_MAP[aspecto]['label'])
                    is_vulnerable = data.get('vulnerable', False)
                    protecciones = data.get('protecciones', 0)
                    api_card = APICard(carta, is_vulnerable=is_vulnerable, protecciones=protecciones)
                    # Regenerate image so the state is reflected
                    api_card.front_image = api_card._create_card_front()
                    self.player1_aspects_zones[aspecto].add_card(api_card)
                # Otherwise the slot stays empty to signal what's missing
        
        # Player 2 (AI) aspects – same logic
        jugador2 = self.engine.jugadores[1]
        for aspecto in ASPECTOS:
            if aspecto in self.player2_aspects_zones:
                if aspecto in jugador2.aspectos:
                    # Aspect unlocked
                    data = jugador2.aspectos[aspecto]
                    carta = Carta('fundamental', aspecto, ASPECTO_MAP[aspecto]['label'])
                    is_vulnerable = data.get('vulnerable', False)
                    protecciones = data.get('protecciones', 0)
                    api_card = APICard(carta, is_vulnerable=is_vulnerable, protecciones=protecciones)
                    # Opponent aspects are displayed face up
                    # Regenerate the image to mirror the state
                    api_card.front_image = api_card._create_card_front()
                    self.player2_aspects_zones[aspecto].add_card(api_card)
                # Otherwise leave the placeholder empty
    
    def _update_discard(self):
        """Update the discard holder with the discarded cards."""
        # Clear discard zone
        self.discard_zone.clear()
        
        # Add every card from the discard pile (they stack vertically)
        # The most recent cards appear on top
        if self.engine.descarte:
            for carta in reversed(self.engine.descarte):  # Reverse to show the latest cards
                api_card = APICard(carta)
                # Show cards FACE DOWN in the discard (legacy behavior)
                api_card.flipped = True
                self.discard_zone.add_card(api_card)
            
            # Force a position refresh after adding every card
            self.discard_zone._update_card_positions()
            
            # Debug: verify cards were added
            print(f"[DEBUG] Discard pile updated: {len(self.engine.descarte)} cards in engine, {len(self.discard_zone.cards)} cards in zone")
            if len(self.discard_zone.cards) > 0:
                first_card = self.discard_zone.cards[0]
                print(f"[DEBUG] First card: rect={first_card.rect}, x={first_card.x}, y={first_card.y}")
    
    def _handle_card_play(self, api_card: APICard, target_zone: Zone):
        """Handle when the player drops a card to play."""
        carta = api_card.carta
        jugador_actual = self.engine.jugadores[self.engine.turno]

        print(f"[DEBUG PLAY] turn_action={self.turn_action}, carta={carta.nombre}")

        if self.turn_action == 'discard':
            print("⚠ BLOCKED: you already discarded cards this turn. Wait for the next turn to play.")
            return False
        if self.turn_action == 'play':
            print("⚠ BLOCKED: you already played a card this turn.")
            return False

        if jugador_actual != self.engine.jugadores[0]:
            print(f"⚠ BLOCKED: It's not your turn – current turn: {jugador_actual.nombre}, attempted play: {carta.nombre}")
            if api_card not in self.player1_hand_zone.cards:
                self.player1_hand_zone.add_card(api_card)
            self._restore_player_hand_layout()
            self._reset_drag_tracking()
            return False

        print(f"✓ Player attempts to play: {carta.nombre} ({carta.tipo})")

        if carta not in jugador_actual.mano:
            print("The card is not in the hand")
            self._restore_player_hand_layout()
            self._reset_drag_tracking()
            return False

        jugable, msg = self.engine.es_jugable(carta, jugador_actual)
        if not jugable:
            print(f"Cannot play: {msg}")
            self.last_player_action_message = f"Could not play {carta.nombre}: {msg}"
            self._push_message(self.last_player_action_message, jugador_actual.nombre)
            try:
                self.engine._diario(f"[{jugador_actual.nombre}] Failed attempt with {carta.nombre}: {msg}")
            except Exception:
                pass
            self._restore_player_hand_layout()
            self._reset_drag_tracking()
            return False

        if api_card in self.player1_hand_zone.cards:
            self.player1_hand_zone.remove_card(api_card)

        if self.game_ui.dragged_card is api_card:
            self.game_ui.dragged_card = None

        opponent_idx = 1 if jugador_actual == self.engine.jugadores[0] else 0
        opponent_before: Set[str] = set(self.engine.jugadores[opponent_idx].aspectos.keys())

        if not self.engine.jugar_carta(jugador_actual, carta):
            detalle = self.engine.last_action_detail or "the play was rejected"
            print(f"⚠ The move was rejected by the engine: {detalle}")
            self.player1_hand_zone.add_card(api_card)
            self._restore_player_hand_layout()
            self.last_player_action_message = f"{carta.nombre}: {detalle}"
            self._push_message(self.last_player_action_message, jugador_actual.nombre)
            try:
                self.engine._diario(f"[{jugador_actual.nombre}] {self.last_player_action_message}")
            except Exception:
                pass
            self._reset_drag_tracking()
            return False

        self._maybe_trigger_destruction_effect(opponent_idx, opponent_before)

        if carta in jugador_actual.mano:
            jugador_actual.mano.remove(carta)

        if carta.tipo not in ('fundamental', 'aspecto'):
            if carta not in self.engine.descarte:
                self.engine.descarte.append(carta)

        self._load_cards()
        self._update_aspects()
        self._update_discard()

        start_time = time.time()
        while time.time() - start_time < 0.3:
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return False

        if not self.engine.mazo:
            print(f"  [DEBUG DRAW] Deck empty. Trying to recycle discard pile (discard={len(self.engine.descarte)})")
            self.engine._recycle_discard()
        if self.engine.mazo:
            print(f"  [DEBUG DRAW] Deck before drawing: {len(self.engine.mazo)} card(s)")
            nueva_carta = self.engine.mazo.pop()
            jugador_actual.mano.append(nueva_carta)
            print(f"  Drew 1 card from the deck to keep 3 cards in hand (deck now {len(self.engine.mazo)} card(s)).")
            self._animate_draw_from_deck(nueva_carta, jugador_actual, duration=0.4)
        else:
            print("  [DEBUG DRAW] No card drawn: deck and discard pile are empty.")
            if jugador_actual == self.engine.jugadores[0]:
                self.last_player_action_message = "Empty deck: unable to draw a card"

        self._load_cards()
        self._update_aspects()
        self._update_discard()

        detalle = self.engine.last_action_detail
        player_msg = f"You played {carta.nombre}"
        if detalle:
            player_msg += f" - {detalle}"
        self.last_player_action_message = player_msg
        self._push_message(player_msg, jugador_actual.nombre)
        try:
            self.engine._diario(f"[{jugador_actual.nombre}] {player_msg}")
        except Exception:
            pass

        self.turn_action = 'play'
        self._change_turn()
        print("  Card played successfully. Turn finished.")
        return True
    
    def _perform_discard_indices(self, jugador: Jugador, indices: List[int], cambiar_turno: bool = True, animar_desde_mano: bool = True) -> None:
        """Discard multiple indices and draw the same amount (delegates to the engine).
        
        Args:
            jugador: Owner of the cards.
            indices: Indices to discard.
            cambiar_turno: Whether the turn should advance afterwards.
            animar_desde_mano: Whether to animate from hand to discard.
                Must be False when the user already dragged the card to the discard pile to avoid duplicate animations.
        """
        import time
        
        # Determine whether the player is the AI
        es_ia = (jugador == self.engine.jugadores[1])

        if es_ia and self.turn_action == 'play':
            print("⚠ BLOCKED: the AI already played a card this turn and shouldn't discard now.")
            return
        if not es_ia and self.turn_action == 'discard':
            print("⚠ BLOCKED: you already discarded this turn.")
            return

        # Whether player or AI, capture card positions BEFORE discarding
        cartas_a_descartar = []
        hand_zone = self.player2_hand_zone if es_ia else self.player1_hand_zone
        
        if hand_zone:
            # Reload cards temporarily to fetch positions
            self._load_cards()
            for idx in sorted(indices, reverse=True):
                if 0 <= idx < len(jugador.mano):
                    carta = jugador.mano[idx]
                    # Find the card in the visual zone
                    for api_card in hand_zone.cards:
                        if api_card.carta == carta:
                            cartas_a_descartar.append({
                                'carta': carta,
                                'from_pos': (
                                    api_card.rect.x,
                                    api_card.rect.y
                                ),
                                'index': idx
                            })
                    break
        
        # ANIMATION 1: First animate cards from hand to discard
        # (while they are still visually in hand, so the motion is shown)
        if animar_desde_mano and cartas_a_descartar and self.discard_zone:
            for carta_info in cartas_a_descartar:
                to_pos = (
                    self.discard_zone.rect.centerx - CARD_WIDTH // 2,
                    self.discard_zone.rect.centery - CARD_HEIGHT // 2,
                )
                flipped = True
                # hide_from_hand=True hides the card from the hand while animating
                # so it does not appear duplicated
                self._animate_card_movement(carta_info['carta'], carta_info['from_pos'], to_pos, duration=0.4, flipped=flipped, hide_from_hand=True)
        
        # Remember cards before discarding to identify the new ones later
        cartas_antes = set(jugador.mano)
        
        # NOW call the engine method (BACKEND) – this removes cards from the hand
        num, drawn = self.engine.descartar_indices(jugador, indices)
        
        # Update the UI to visually remove the cards from hand
        # BUT do not load the new cards yet (that happens after the animation)
        # Just update the hand without the discarded cards
        hand_zone = self.player2_hand_zone if es_ia else self.player1_hand_zone
        
        # Remove discarded cards from the visual zone
        # IMPORTANT: remove in reverse order so indices stay valid
        cartas_a_remover = []
        for idx in sorted(indices, reverse=True):
            if idx < len(hand_zone.cards):
                cartas_a_remover.append(hand_zone.cards[idx])
        
        for card in cartas_a_remover:
            hand_zone.remove_card(card)
        
        # Refresh discard pile
        self._update_discard()
        
        # Show the empty slots for a brief moment (0.3 seconds)
        start_time = time.time()
        while time.time() - start_time < 0.3:
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
            # Process events to keep the window responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                return
        
        # Identify the drawn cards (those present now but not before)
        cartas_despues = set(jugador.mano)
        cartas_robadas = list(cartas_despues - cartas_antes)
        
        # ANIMATION 2: Animate the drawn cards from the deck into the empty slots
        # IMPORTANT: the new cards are NOT in the UI yet, only in the engine state
        if cartas_robadas and self.deck_zone:
            # The discarded indices correspond to the empty slots
            # The engine inserts the new cards in those same indices
            indices_descartados = sorted(indices)
            for i, nueva_carta in enumerate(cartas_robadas):
                # Use the corresponding index (first drawn → first discarded index, etc.)
                target_index = indices_descartados[i] if i < len(indices_descartados) else None
                self._animate_draw_from_deck(nueva_carta, jugador, duration=0.4, target_index=target_index)
        
        # Clear selections/states (FRONTEND)
            self.discard_selection.clear()
        self.selected_hand_idx = None
        self.cartas_multi_drag.clear()
        
        # Final UI refresh (FRONTEND) – NOW load every card including the new ones
        self._load_cards()
        self._update_discard()
        
        # Automatically advance the turn after drawing (if requested)
        if cambiar_turno:
            print(f"  Switching turn after discard... (previous: {self.engine.jugadores[self.engine.turno].nombre}, index: {self.engine.turno})")

            # Record message according to the active player
            if es_ia:
                self.last_ai_action_message = f"AI discarded {num} card(s) and drew {drawn}"
                self._push_message(self.last_ai_action_message, jugador.nombre)
                try:
                    self.engine._diario(f"[{jugador.nombre}] {self.last_ai_action_message}")
                except Exception:
                    pass
            else:
                self.last_player_action_message = f"Discarded {num} card(s) and drew {drawn}"
                self._push_message(self.last_player_action_message, jugador.nombre)
                try:
                    self.engine._diario(f"[{jugador.nombre}] {self.last_player_action_message}")
                except Exception:
                    pass

            # Mark the action taken and switch turn
            self.turn_action = 'discard'
            self._change_turn()
    
    def _get_event_name(self, event_type: int) -> str:
        """Convert the event code into a descriptive label."""
        event_names = {
            pygame.QUIT: "QUIT (close window)",
            pygame.KEYDOWN: "KEYDOWN (key pressed)",
            pygame.KEYUP: "KEYUP (key released)",
            pygame.MOUSEBUTTONDOWN: "MOUSEBUTTONDOWN (mouse pressed)",
            pygame.MOUSEBUTTONUP: "MOUSEBUTTONUP (mouse released)",
            pygame.MOUSEMOTION: "MOUSEMOTION (mouse moved)",
            pygame.ACTIVEEVENT: "ACTIVEEVENT (focus changed)",
            pygame.VIDEORESIZE: "VIDEORESIZE (window resized)",
        }
        return event_names.get(event_type, f"EVENT_UNKNOWN ({event_type})")
    
    def handle_event(self, event: pygame.event.Event):
        """Handle pygame events."""
        if event.type == pygame.QUIT:
            self.running = False
            return

        if self.modal_victoria_visible:
            self._handle_modal_event(event)
            return

        jugador_actual = self.engine.jugadores[self.engine.turno]
        es_turno_jugador = (jugador_actual == self.engine.jugadores[0])
        
        # Debug: check turn info for every important event
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.KEYDOWN):
            if not hasattr(self, '_last_event_debug'):
                self._last_event_debug = 0
            import time
            current_time = time.time()
            if current_time - self._last_event_debug > 1.0:  # At most once per second
                self._last_event_debug = current_time
                event_name = self._get_event_name(event.type)
                # Attach additional info depending on event type
                extra_info = ""
                if event.type == pygame.KEYDOWN:
                    key_name = pygame.key.name(event.key) if hasattr(event, 'key') else "?"
                    extra_info = f" - Key: {key_name}"
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    button_name = {1: "left", 2: "middle", 3: "right", 4: "wheel up", 5: "wheel down"}.get(event.button, f"button {event.button}")
                    extra_info = f" - Button: {button_name}, Pos: ({event.pos[0]}, {event.pos[1]})"
                print(f"[DEBUG EVENT] Turn: {jugador_actual.nombre}, is_player_turn={es_turno_jugador}, {event_name}{extra_info}")
        
        if event.type == pygame.KEYDOWN:
            # Ignore modifier keys pressed alone (CMD, Ctrl, Shift, Alt) to avoid crashes
            if event.key in (pygame.K_LMETA, pygame.K_RMETA, pygame.K_LCTRL, pygame.K_RCTRL, 
                             pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LALT, pygame.K_RALT):
                # Only log, do nothing
                return
            if getattr(event, "repeat", 0):
                return
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_f:
                mods = pygame.key.get_mods()
                uso_ctrl = bool(mods & (pygame.KMOD_CTRL | pygame.KMOD_META))
                self.auto_play_enabled = not self.auto_play_enabled
                estado = "enabled" if self.auto_play_enabled else "disabled"
                combinacion = "Ctrl+F" if uso_ctrl else "F"
                print(f"[AUTO-PLAY] ({combinacion}) AI vs AI mode {estado}")
                self._ai_turn_started = False
                self._last_ai_action_time = 0
                self.last_player_action_message = f"Auto-play {estado.upper()}"
                self._push_message(self.last_player_action_message, "System")
        elif hasattr(event, "key") and event.key == pygame.K_d:
                # Key D: discard selected cards and end the turn
                try:
                    if es_turno_jugador and self.discard_selection:
                        idxs = sorted(self.discard_selection, reverse=True)
                        # Change the turn after discarding multiple cards
                        self._perform_discard_indices(jugador_actual, idxs, cambiar_turno=True)
                    elif es_turno_jugador and self.selected_hand_idx is not None:
                        # Discard only the selected card and change turn
                        self._perform_discard_indices(jugador_actual, [self.selected_hand_idx], cambiar_turno=True)
                except Exception as e:
                    print(f"⚠ Error discarding with D: {e}")
                    import traceback
                    traceback.print_exc()
        
        # IMPORTANT: handle multi-selection BEFORE GameUI so it does not intercept the event
        # Manage clicks on hand cards (multi-selection with Cmd/Ctrl)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_ui_buttons(event.pos):
                return

            self.drag_origin_pos = None
            self.drag_origin_zone = None
            self.drag_origin_index = None

            try:
                pos = event.pos

                if not es_turno_jugador:
                    print(f"⚠ BLOCKED: It's not your turn to select cards – current turn: {jugador_actual.nombre}")
                    return

                if hasattr(self, 'player1_hand_zone') and self.player1_hand_zone.cards:
                    for i, api_card in enumerate(self.player1_hand_zone.cards):
                        try:
                            if not api_card.contains_point(pos):
                                continue

                            try:
                                mods = pygame.key.get_mods()
                            except Exception as e:
                                print(f"⚠ Error fetching modifiers: {e}")
                                mods = 0

                            has_modifier = bool(mods & (pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_META | pygame.KMOD_ALT))

                            if has_modifier:
                                if i in self.discard_selection:
                                    self.discard_selection.remove(i)
                                    print(f"✗ Card {i} deselected. Total: {len(self.discard_selection)}")
                                else:
                                    self.discard_selection.append(i)
                                    self.discard_selection.sort()
                                    print(f"✓ Card {i} selected. Total: {len(self.discard_selection)} cards selected")
                                self.selected_hand_idx = i
                                self._load_cards()
                                return

                            if self.discard_selection and i in self.discard_selection:
                                self.cartas_multi_drag = self.discard_selection.copy()
                                print(f"Dragging {len(self.cartas_multi_drag)} cards to DISCARD")
                                self._init_multi_drag(api_card, i)
                            else:
                                self.discard_selection.clear()
                                self.cartas_multi_drag.clear()
                                self.selected_hand_idx = i
                                self.multi_drag_cards_refs.clear()
                                self.multi_drag_offsets.clear()

                            self.drag_origin_pos = api_card.rect.center
                            self.drag_origin_zone = self.player1_hand_zone
                            self.drag_origin_index = i
                            break
                        except Exception as e:
                            print(f"⚠ Error processing card {i}: {e}")
                            continue
            except Exception as e:
                print(f"⚠ Error handling click: {e}")
                import traceback
                traceback.print_exc()
        
        # IMPORTANT: only allow interactions during the player's turn
        if not es_turno_jugador:
            # If it's not the player's turn, ignore all interaction events
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                # Cancel any active drag
                if self.game_ui.dragged_card:
                    dragged_card = self.game_ui.dragged_card
                    if dragged_card in self.player1_hand_zone.cards:
                        dragged_card.set_position_immediate(dragged_card.x, dragged_card.y)
                    self.game_ui.dragged_card = None
                    return
    
        # Let pygame_cards process the event (after our selection handling)
        self.game_ui.handle_event(event)

        # While dragging a group, reposition the companion cards
        if event.type == pygame.MOUSEMOTION and self.game_ui.dragged_card and self.cartas_multi_drag:
            base_card = self.game_ui.dragged_card
            for card in self.multi_drag_cards_refs:
                offset = self.multi_drag_offsets.get(card, (0, 0))
                card.set_position_immediate(base_card.rect.x + offset[0], base_card.rect.y + offset[1])

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = event.pos
            dragged_card = self.game_ui.dragged_card

            if self.discard_zone.contains_point(pos):
                if jugador_actual != self.engine.jugadores[0]:
                    print(f"⚠ BLOCKED: It's not your turn to discard – current turn: {jugador_actual.nombre}")
                    self._restore_player_hand_layout()
                    self._reset_drag_tracking()
                    return

                if dragged_card and isinstance(dragged_card, APICard):
                    carta = dragged_card.carta
                    if carta in jugador_actual.mano:
                        if self.cartas_multi_drag:
                            idxs = [idx for idx in self.cartas_multi_drag if 0 <= idx < len(jugador_actual.mano)]
                            if idxs:
                                self._perform_discard_indices(jugador_actual, idxs, cambiar_turno=True, animar_desde_mano=False)
                                self._reset_drag_tracking(clear_selection=True)
                                return
                        else:
                            idx = jugador_actual.mano.index(carta)
                            self._perform_discard_indices(jugador_actual, [idx], cambiar_turno=True, animar_desde_mano=False)
                            self._reset_drag_tracking(clear_selection=True)
                            return

                self._restore_player_hand_layout()
                self._reset_drag_tracking()
                return

            if not dragged_card or not isinstance(dragged_card, APICard):
                self._reset_drag_tracking()
                return

            jugador_actual = self.engine.jugadores[self.engine.turno]
            if jugador_actual != self.engine.jugadores[0]:
                print(f"⚠ BLOCKED: It's not your turn – current turn: {jugador_actual.nombre}")
                self._restore_player_hand_layout()
                self._reset_drag_tracking()
                return

            carta = dragged_card.carta
            handled = False

            if carta.tipo in ('fundamental', 'aspecto'):
                for aspecto, zone in self.player1_aspects_zones.items():
                    if zone.contains_point(pos):
                        aspecto_libre = aspecto not in jugador_actual.aspectos
                        if aspecto_libre and (carta.color == aspecto or carta.color == 'multicolor'):
                            handled = self._handle_card_play(dragged_card, zone)
                        break

            elif carta.tipo in ('hack', 'ataque', 'problema'):
                rival = self.engine.jugadores[1]
                for aspecto, zone in self.player2_aspects_zones.items():
                    if zone.contains_point(pos):
                        if aspecto in rival.aspectos and (carta.color == aspecto or carta.color == 'multicolor'):
                            handled = self._handle_card_play(dragged_card, zone)
                        break

            elif carta.tipo in ('shield', 'proteccion'):
                for aspecto, zone in self.player1_aspects_zones.items():
                    if zone.contains_point(pos):
                        if aspecto in jugador_actual.aspectos and (carta.color == aspecto or carta.color == 'multicolor'):
                            handled = self._handle_card_play(dragged_card, zone)
                        break

            elif carta.tipo in ('management', 'intervencion'):
                rival = self.engine.jugadores[1]
                for aspecto, zone in self.player2_aspects_zones.items():
                    if zone.contains_point(pos):
                        if aspecto in rival.aspectos:
                            handled = self._handle_card_play(dragged_card, zone)
                        break

            if handled:
                self._reset_drag_tracking(clear_selection=True)
                return

            if self.drag_origin_zone is self.player1_hand_zone and self.drag_origin_index is not None:
                if dragged_card in self.player1_hand_zone.cards:
                    try:
                        self.player1_hand_zone.cards.remove(dragged_card)
                    except ValueError:
                        pass
                    insert_index = min(self.drag_origin_index, len(self.player1_hand_zone.cards))
                    self.player1_hand_zone.cards.insert(insert_index, dragged_card)

            self._restore_player_hand_layout()
            self.last_player_action_message = "Move cancelled: the card returns to its original position."
            self._reset_drag_tracking(clear_selection=True)
    
    def _restore_player_hand_layout(self) -> None:
        """Reposition the player's hand cards following the engine order."""
        if not hasattr(self, "player1_hand_zone"):
            return

        mano = self.engine.jugadores[0].mano if self.engine.jugadores else []
        order_map = {id(carta): idx for idx, carta in enumerate(mano)}

        def order_key(api_card: APICard) -> int:
            return order_map.get(id(api_card.carta), len(order_map))

        try:
            self.player1_hand_zone.cards.sort(key=order_key)
            self.player1_hand_zone._update_card_positions()
        except Exception as e:
            print(f"⚠ Error restoring hand layout: {e}")

    def _reset_drag_tracking(self, clear_selection: bool = False) -> None:
        """Clear drag tracking and optionally the current selection."""
        self.game_ui.dragged_card = None
        self.drag_origin_pos = None
        self.drag_origin_zone = None
        self.drag_origin_index = None
        self.cartas_multi_drag.clear()
        self.multi_drag_cards_refs.clear()
        self.multi_drag_offsets.clear()

        if clear_selection:
            self.discard_selection.clear()
            self.selected_hand_idx = None

    def _init_multi_drag(self, base_card: APICard, base_index: int) -> None:
        """Prepare the list of cards that accompany a multi-card drag."""
        self.multi_drag_cards_refs.clear()
        self.multi_drag_offsets.clear()

        if not self.cartas_multi_drag or len(self.cartas_multi_drag) <= 1:
            return

        extra_indices = [idx for idx in self.cartas_multi_drag if idx != base_index]
        extra_indices.sort()

        for offset_pos, idx in enumerate(extra_indices):
            if 0 <= idx < len(self.player1_hand_zone.cards):
                card = self.player1_hand_zone.cards[idx]
                if card is base_card:
                    continue
                self.multi_drag_cards_refs.append(card)

                if len(self.cartas_multi_drag) == 2:
                    offsets = [(18, 14)]
                else:
                    offsets = [(16, 12), (32, 24)]

                offset_x, offset_y = offsets[min(offset_pos, len(offsets) - 1)]
                self.multi_drag_offsets[card] = (offset_x, offset_y)
                card.set_position_immediate(base_card.rect.x + offset_x, base_card.rect.y + offset_y)

    
    def update(self):
        """Update the game state."""
        # Refresh aspects periodically
        self._update_aspects()
        # Refresh discard periodically (only if there are changes)
        # Do not force updates here to avoid unnecessary rebuilds
        
        # AI logic: play automatically if it's its turn
        jugador_actual = self.engine.jugadores[self.engine.turno]
        es_turno_ia = (jugador_actual == self.engine.jugadores[1])
        
        # Detect victory and stop auto-play if needed
        ganador = self.engine.comprobar_victoria()
        if ganador:
            jugador1_nombre = self.engine.jugadores[0].nombre
            winner_is_player = (ganador == jugador1_nombre)
            mensaje = "You won the match" if winner_is_player else f"{ganador} won the match"
            self.last_player_action_message = mensaje
            if winner_is_player:
                self._push_message("You won the match", "System")
            else:
                self.last_ai_action_message = mensaje
                self._push_message(mensaje, "System")

            if not self.modal_victoria_ack and not self.modal_victoria_visible:
                self.modal_victoria_visible = True
                self.modal_victoria_jugador = ganador

            if self.auto_play_enabled:
                print(f"[AUTO-PLAY] disabled: match finished ({ganador})")
            self.auto_play_enabled = False
            if hasattr(self, '_ai_turn_started'):
                self._ai_turn_started = False
            if hasattr(self, '_last_ai_action_time'):
                self._last_ai_action_time = 0
            return
        
        # Debug: log turn information every few seconds to avoid flooding
        if not hasattr(self, '_last_turn_debug'):
            self._last_turn_debug = 0
        import time
        current_time = time.time()
        if current_time - self._last_turn_debug > 2.0:  # Every 2 seconds
            self._last_turn_debug = current_time
            turno_info = f"Current turn: {jugador_actual.nombre} (index: {self.engine.turno})"
            estado_turno = "AI TURN" if es_turno_ia else "PLAYER TURN"
            print(f"[DEBUG TURN] {turno_info}, State: {estado_turno}")
        
        if es_turno_ia:
            # Try to play a card automatically (legacy wrapper)
            self._ai_play_card()
        else:
            # If it's not the AI's turn, reset flags only when auto-play is inactive
            if not self.auto_play_enabled and hasattr(self, '_ai_turn_started') and self._ai_turn_started:
                print(f"[DEBUG] Resetting AI flags (turn changed to {jugador_actual.nombre})")
                self._ai_turn_started = False
                self._last_ai_action_time = 0  # Reset the timer as well
    
    def _animate_card_movement(self, carta: Carta, from_pos: Tuple[int, int], to_pos: Tuple[int, int], duration: float = 0.5, flipped: bool = False, hide_from_hand: bool = False):
        """Animate a card moving from one position to another.
        
        Args:
            carta: Card to animate.
            from_pos: Starting position (x, y).
            to_pos: Ending position (x, y).
            duration: Animation duration in seconds.
            flipped: Whether the card should show face down.
            hide_from_hand: If True, temporarily hide the card from the hand during the animation.
        """
        import time
        start_time = time.time()
        start_x, start_y = from_pos
        end_x, end_y = to_pos
        
        # Create a temporary card for the animation
        temp_card = APICard(carta)
        temp_card.set_position_immediate(start_x, start_y)
        temp_card.flipped = flipped  # Respect the flipped parameter
        
        # If hide_from_hand, temporarily remove the card from the visual hand
        original_api_card = None
        if hide_from_hand:
            # Look for the card in both hand zones and remove it temporarily
            for zone in [self.player1_hand_zone, self.player2_hand_zone]:
                for api_card in list(zone.cards):
                    if api_card.carta == carta:
                        original_api_card = api_card
                        zone.remove_card(api_card)
                break
                if original_api_card:
                    break
        
        # Animate until complete
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            progress = min(elapsed / duration, 1.0)  # Clamp to 1.0
            # Use easing for smooth animation
            eased = progress * (2 - progress)  # Ease out
            
            current_x = start_x + (end_x - start_x) * eased
            current_y = start_y + (end_y - start_y) * eased
            temp_card.set_position_immediate(int(current_x), int(current_y))
            
            # Draw the animated card
            self.draw()
            temp_card.draw(self.screen)
            pygame.display.flip()

            # Control animation FPS
            self.clock.tick(60)

            # Process events to keep the window responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return False
        
        # Ensure the card ends exactly at destination
        temp_card.set_position_immediate(end_x, end_y)
        
        # If we removed the card temporarily, don't re-add it (UI reload happens later)
    
    def _get_hand_position_for_index(self, target_player: Jugador, index: int) -> Tuple[int, int]:
        """Calculate the hand slot position for a specific index."""
        if target_player == self.engine.jugadores[0]:
            rects = getattr(self, 'player1_hand_slot_rects', [])
        else:
            rects = getattr(self, 'player2_hand_slot_rects', [])

        if rects:
            safe_index = max(0, min(index, len(rects) - 1))
            rect = rects[safe_index]
            return (rect.centerx - CARD_WIDTH // 2, rect.centery - CARD_HEIGHT // 2)

        # Fallback when placeholders are not defined
        if target_player == self.engine.jugadores[0]:
            target_zone = self.player1_hand_zone
        else:
            target_zone = self.player2_hand_zone

        if not target_zone:
            return (0, 0)

        card_width = CARD_WIDTH
        card_spacing = 10
        total_width = len(target_player.mano) * card_width + (len(target_player.mano) - 1) * card_spacing
        start_x = target_zone.rect.x + (target_zone.rect.width - total_width) // 2

        x = start_x + index * (card_width + card_spacing)
        y = target_zone.rect.centery - CARD_HEIGHT // 2

        return (x, y)
    
    def _animate_draw_from_deck(self, carta: Carta, target_player: Jugador, duration: float = 0.4, target_index: Optional[int] = None):
        """Animate drawing a card from the deck into a player's hand."""
        if not self.deck_zone:
            return
        
        # Determine the destination zone by player
        if target_player == self.engine.jugadores[0]:
            # Human player (bottom)
            target_zone = self.player1_hand_zone
            flipped = False  # Cards stay visible to the player
        else:
            # AI (top)
            target_zone = self.player2_hand_zone
            flipped = True  # Cards stay face down for the AI
        
        if not target_zone:
            return
        
        # Source and destination positions
        from_pos = (
            self.deck_zone.rect.centerx - CARD_WIDTH // 2,
            self.deck_zone.rect.centery - CARD_HEIGHT // 2,
        )
        
        # If a specific index is provided, use that placeholder
        if target_index is not None:
            to_pos = self._get_hand_position_for_index(target_player, target_index)
        else:
            to_pos = self._get_hand_position_for_index(target_player, len(target_player.mano) - 1)
        
        # Animate the motion
        self._animate_card_movement(carta, from_pos, to_pos, duration=duration, flipped=flipped)

        # Ensure the card shows up immediately in the hand
        target_zone_cards = target_zone.cards
        insert_at = target_index if target_index is not None else len(target_zone_cards)
        insert_at = max(0, min(insert_at, len(target_zone_cards)))

        new_api_card = APICard(carta)
        new_api_card.flipped = flipped
        new_api_card.set_position_immediate(*to_pos)

        target_zone_cards.insert(insert_at, new_api_card)
        target_zone._update_card_positions()
    
    def _auto_play_turn(self, jugador_idx: int) -> None:
        """Automatically execute the indicated player's turn."""
        import time
 
        # Prevent the AI from acting too quickly (give time to notice turn changes)
        if not hasattr(self, '_last_ai_action_time'):
            self._last_ai_action_time = 0
 
        if not hasattr(self, '_ai_turn_started'):
            self._ai_turn_started = False
 
        current_time = time.time()
        jugador = self.engine.jugadores[jugador_idx]
        es_ia = (jugador_idx == 1)
 
        delay = 0.5
        if self.auto_play_enabled:
            delay = 0.05
        elif not es_ia:
            delay = 0.1

        if not self._ai_turn_started:
            self._ai_turn_started = True
            prefijo = "🤖" if es_ia else "AUTO"
            print(f"{prefijo} ===== AUTO TURN ({jugador.nombre}) ===== Hand: {len(jugador.mano)} cards")
            print(f"{prefijo} Cards in hand: {[c.nombre + ' (' + c.tipo + ')' for c in jugador.mano]}")
            self._last_ai_action_time = current_time - delay
            return

        if current_time - self._last_ai_action_time < delay:
            return
 
        carta_jugada = False
        carta_jugada_info: Optional[Tuple[Carta, Optional[Tuple[int, int]]]] = None
        prefijo = "🤖" if es_ia else "AUTO"
        print(f"{prefijo} Checking {len(jugador.mano)} cards in hand...")
 
        for carta in list(jugador.mano):
            opponent_idx = 1 if jugador_idx == 0 else 0
            opponent_before: Set[str] = set(self.engine.jugadores[opponent_idx].aspectos.keys())
            jugable, msg = self.engine.es_jugable(carta, jugador)
            print(f"  - {carta.nombre} ({carta.tipo}): playable={jugable}, msg='{msg}'")
            if not jugable:
                continue
 
            print(f"{prefijo} tries to play: {carta.nombre} ({carta.tipo}) - {msg}")
            resultado = self.engine.jugar_carta(jugador, carta)
            print(f"  Result of jugar_carta: {resultado}, last_action_detail: '{self.engine.last_action_detail}'")
 
            if not resultado:
                print(f"✗ {prefijo} could not play {carta.nombre}: {self.engine.last_action_detail}")
                continue
 
            self._maybe_trigger_destruction_effect(opponent_idx, opponent_before)

            action_msg = f"{jugador.nombre} played: {carta.nombre} ({carta.tipo})"
            if self.engine.last_action_detail:
                action_msg += f" - {self.engine.last_action_detail}"
            print(f"✓ {action_msg}")
            if es_ia:
                self.last_ai_action_message = action_msg
            else:
                self.last_player_action_message = action_msg
            try:
                self.engine._diario(f"[{jugador.nombre}] {action_msg}")
            except Exception:
                pass
 
            from_pos = None
            hand_zone = self.player2_hand_zone if es_ia else self.player1_hand_zone
            if hand_zone.cards and self.discard_zone:
                for api_card in hand_zone.cards:
                    if api_card.carta == carta:
                        from_pos = (api_card.rect.x, api_card.rect.y)
                        break
 
            if carta in jugador.mano:
                jugador.mano.remove(carta)
                print(f"  Card removed from hand. Hand now: {len(jugador.mano)} cards")
            if carta.tipo not in ('fundamental', 'aspecto'):
                if carta not in self.engine.descarte:
                    self.engine.descarte.append(carta)
                    print(f"  Card added to discard pile. Discard now has: {len(self.engine.descarte)} cards")
 
            if len(self.engine.mazo) > 0 or self.engine.descarte:
                if not self.engine.mazo:
                    self.engine._recycle_discard()
                if self.engine.mazo:
                    nueva_carta = self.engine.mazo.pop()
                    jugador.mano.append(nueva_carta)
                    print(f"  {jugador.nombre} drew 1 card from the deck to keep 3 cards in hand.")
                    self._animate_draw_from_deck(nueva_carta, jugador, duration=0.4)
 
            self._load_cards()
            self._update_aspects()
            self._update_discard()
 
            if from_pos and self.discard_zone:
                carta_jugada_info = (carta, from_pos)
 
            carta_jugada = True
            break
 
        # If there are no playable cards, the AI must discard before passing the turn
        if carta_jugada:
            if carta_jugada_info and self.discard_zone:
                carta_animada, from_pos = carta_jugada_info
                to_pos = (
                    self.discard_zone.rect.centerx - CARD_WIDTH // 2,
                    self.discard_zone.rect.centery - CARD_HEIGHT // 2,
                )
                self._animate_card_movement(carta_animada, from_pos, to_pos, duration=0.4)
                self._load_cards()
                self._update_discard()
 
            self.turn_action = 'play'
            self._change_turn()
            self._ai_turn_started = False
            self._last_ai_action_time = current_time
            return
 
        if not carta_jugada:
            # RULE: cannot pass turn without discarding if the deck still has cards
            if len(self.engine.mazo) > 0 or len(self.engine.descarte) > 0:
                wait_descartar = 1.5
                if self.auto_play_enabled:
                    wait_descartar = 0.2
                # Wait a moment before discarding (to show the AI is "thinking")
                if current_time - self._last_ai_action_time >= wait_descartar:
                    # The AI must discard 1, 2, or 3 cards (random/first)
                    num_to_discard = min(len(jugador.mano), 3)  # At most 3, or all if fewer
                    if num_to_discard > 0:
                        indices_to_discard = list(range(num_to_discard))
                        print(f"{prefijo}: No playable cards. Discarding {num_to_discard} card(s)...")
                        mensaje_desc = f"{jugador.nombre} discarded {num_to_discard} card(s)"
                        if es_ia:
                            self.last_ai_action_message = mensaje_desc
                            self._push_message(mensaje_desc, jugador.nombre)
                        else:
                            self.last_player_action_message = mensaje_desc
                            self._push_message(mensaje_desc, jugador.nombre)

                        self._perform_discard_indices(jugador, indices_to_discard, cambiar_turno=True)

                        self._ai_turn_started = False
                        self._last_ai_action_time = current_time
                        return
        else:
            # Only if the deck AND discard pile are empty can the turn be skipped
            if current_time - self._last_ai_action_time >= 1.5:
                wait_pasar = 1.5
                if self.auto_play_enabled:
                    wait_pasar = 0.2
                print(f"{prefijo}: No playable cards and the deck is empty. Passing turn...")
                mensaje = f"{jugador.nombre} passed turn (empty deck)"
                if es_ia:
                    self.last_ai_action_message = mensaje
                    self._push_message(mensaje, jugador.nombre)
                else:
                    self.last_player_action_message = mensaje
                    self._push_message(mensaje, jugador.nombre)
                self.turn_action = 'none'
                try:
                    self.engine._diario(f"[{jugador.nombre}] {mensaje}")
                except Exception:
                    pass
                self._change_turn()

                self._ai_turn_started = False
                self._last_ai_action_time = current_time
                return
 
    def draw(self):
        """Render the entire game frame."""
        # Background
        self._draw_background()

        # Draw hand placeholders before cards so they remain underneath
        self._draw_hand_placeholders()
        
        # Draw UI
        self.game_ui.draw()
        
        # Highlight valid zones if a card is being dragged
        if self.game_ui.dragged_card:
            self._draw_valid_zones_highlight()

        # Overlay active visual effects (explosions, etc.)
        self._draw_active_effects()
        
        # Draw game information (HUD)
        self._draw_hud()
        
        # Draw animated toasts on top of the HUD
        self._draw_toasts()
        
        # Draw bottom buttons
        self._draw_ui_buttons()

        if self.modal_victoria_visible:
            self._draw_victory_modal()
        
        pygame.display.flip()

    def _draw_background(self) -> None:
        """Paint the tabletop background with a gradient and subtle grid."""
        self.screen.fill(COLOR_BOARD)

        gradient = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(WINDOW_HEIGHT):
            factor = y / WINDOW_HEIGHT
            r = int(COLOR_BOARD[0] + (COLOR_SURFACE[0] - COLOR_BOARD[0]) * factor)
            g = int(COLOR_BOARD[1] + (COLOR_SURFACE[1] - COLOR_BOARD[1]) * factor)
            b = int(COLOR_BOARD[2] + (COLOR_SURFACE[2] - COLOR_BOARD[2]) * factor)
            pygame.draw.line(gradient, (r, g, b, 255), (0, y), (WINDOW_WIDTH, y))
        self.screen.blit(gradient, (0, 0))

        grid_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        grid_color = (255, 255, 255, 20)
        step = 80
        for x in range(0, WINDOW_WIDTH, step):
            pygame.draw.line(grid_surface, grid_color, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, step):
            pygame.draw.line(grid_surface, grid_color, (0, y), (WINDOW_WIDTH, y))
        self.screen.blit(grid_surface, (0, 0))
        
        # Central title
        if self.board_title_surface:
            x, y = self.board_title_pos
            if self.board_title_shadow:
                self.screen.blit(self.board_title_shadow, (x + 6, y + 6))
            self.screen.blit(self.board_title_surface, (x, y))

    def _draw_hand_placeholders(self):
        """Draw the fixed hand placeholders aligned with deck and discard."""
        if not hasattr(self, 'player1_hand_slot_rects') or not hasattr(self, 'player2_hand_slot_rects'):
            return

        jugador_actual = self.engine.jugadores[self.engine.turno]
        jugador1 = self.engine.jugadores[0]
        jugador2 = self.engine.jugadores[1]

        is_player_turn = (jugador_actual == jugador1)
        is_ai_turn = (jugador_actual == jugador2)

        player_base = COLOR_PLACEHOLDER_ACTIVE if is_player_turn else COLOR_PLACEHOLDER_INACTIVE
        player_border = COLOR_PLACEHOLDER_BORDER
        ai_base = COLOR_PLACEHOLDER_ACTIVE if is_ai_turn else COLOR_PLACEHOLDER_INACTIVE
        ai_border = COLOR_PLACEHOLDER_BORDER

        def draw_slot(rect: pygame.Rect, base_rgb, border_rgb):
            outer_rect = rect.inflate(18, 18)
            overlay = pygame.Surface((outer_rect.width, outer_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (*base_rgb, 65), overlay.get_rect(), border_radius=18)
            self.screen.blit(overlay, outer_rect.topleft)

            pygame.draw.rect(self.screen, border_rgb, rect.inflate(10, 10), width=2, border_radius=16)
            inner = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(inner, (*base_rgb, 45), inner.get_rect(), border_radius=12)
            self.screen.blit(inner, rect.topleft)
            pygame.draw.rect(self.screen, (255, 255, 255, 40), rect, width=1, border_radius=12)

        for rect in self.player2_hand_slot_rects:
            draw_slot(rect, ai_base, ai_border)
        for rect in self.player1_hand_slot_rects:
            draw_slot(rect, player_base, player_border)
    
    def _draw_valid_zones_highlight(self):
        """Highlight valid zones where the dragged card can be released."""
        if not self.game_ui.dragged_card or not isinstance(self.game_ui.dragged_card, APICard):
            return
        
        carta = self.game_ui.dragged_card.carta
        jugador_actual = self.engine.jugadores[self.engine.turno]
        
        # Only the human player sees valid zones
        if jugador_actual != self.engine.jugadores[0]:
            return
        
        # Highlight color (bright gold)
        highlight_color = (255, 215, 0)  # Gold
        highlight_alpha = 180
        
        # Create an alpha surface for highlights
        highlight_surf = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        def highlight_rect(rect: pygame.Rect):
            pygame.draw.rect(highlight_surf, (*highlight_color, highlight_alpha), rect, width=4, border_radius=10)
            inner = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, rect.height - 4)
            pygame.draw.rect(highlight_surf, (*highlight_color, highlight_alpha // 3), inner, border_radius=8)

        def highlight_zone(zone: Zone):
            if not zone:
                return
            highlight_rect(zone.rect)
            if getattr(zone, 'cards', None):
                for card in zone.cards:
                    card_rect = pygame.Rect(card.rect.x - 3, card.rect.y - 3, card.rect.width + 6, card.rect.height + 6)
                    highlight_rect(card_rect)

        # 1. DISCARD is always valid for any card
        highlight_zone(self.discard_zone)
        
        # 2. Check aspect zones depending on card type
        if carta.tipo == 'fundamental' or carta.tipo == 'aspecto':
            # Fundamentals can be placed on player 1 aspects
            # Confirm it's playable overall
            jugable, _ = self.engine.es_jugable(carta, jugador_actual)
            if jugable:
                # If multicolor, highlight every available aspect
                if carta.color == 'multicolor':
                    # Highlight all aspects the player does not have
                    for aspecto, zone in self.player1_aspects_zones.items():
                        if aspecto not in jugador_actual.aspectos:
                            highlight_zone(zone)
                else:
                    # Specific color: highlight ONLY that aspect (if not already owned)
                    if carta.color in self.player1_aspects_zones and carta.color not in jugador_actual.aspectos:
                        zone = self.player1_aspects_zones[carta.color]
                        highlight_zone(zone)
        
        elif carta.tipo == 'hack' or carta.tipo == 'ataque' or carta.tipo == 'problema':
            # Attacks can target player 2 (opponent) aspects
            jugable, _ = self.engine.es_jugable(carta, jugador_actual)
            if jugable:
                # Highlight every aspect the opponent currently has
                rival = self.engine.jugadores[1]
                for aspecto, zone in self.player2_aspects_zones.items():
                    # Highlight only if the rival has that aspect
                    if aspecto in rival.aspectos:
                        highlight_zone(zone)
        
        elif carta.tipo == 'shield' or carta.tipo == 'proteccion':
            # Shields can be applied to player 1 aspects
            jugable, _ = self.engine.es_jugable(carta, jugador_actual)
            if jugable:
                # Highlight every aspect the player possesses
                for aspecto, zone in self.player1_aspects_zones.items():
                    if aspecto in jugador_actual.aspectos:
                        highlight_zone(zone)
        
        elif carta.tipo == 'management' or carta.tipo == 'intervencion':
            # Management cards can target player 2 aspects (for steals/swaps)
            jugable, _ = self.engine.es_jugable(carta, jugador_actual)
            if jugable:
                # Depending on subtype, they target different zones
                if carta.color in ('migration', 'refactoring', 'thief', 'transplant'):
                    # They can target player 2 aspects that the rival owns
                    rival = self.engine.jugadores[1]
                    for aspecto, zone in self.player2_aspects_zones.items():
                        if aspecto in rival.aspectos:
                            highlight_zone(zone)

        # Blit highlight overlay
        self.screen.blit(highlight_surf, (0, 0))
    
    def _draw_hud(self):
        """Render the HUD information."""
        font = pygame.font.Font(None, 24)
        font_big = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 18)
        
        # Current turn and players
        jugador_actual = self.engine.jugadores[self.engine.turno]
        jugador1 = self.engine.jugadores[0]
        jugador2 = self.engine.jugadores[1]
        es_turno_jugador = (jugador_actual == jugador1)

        # Avatars aligned with each hand
        player_avatar_rect = self._compute_avatar_rect_left(
            getattr(self, 'player1_hand_slot_rects', []),
            list(self.player1_aspects_zones.values()) if hasattr(self, 'player1_aspects_zones') else None
        )
        ai_avatar_rect = self._compute_avatar_rect_left(
            getattr(self, 'player2_hand_slot_rects', []),
            list(self.player2_aspects_zones.values()) if hasattr(self, 'player2_aspects_zones') else None
        )
        self._draw_avatar(player_avatar_rect, es_turno_jugador, is_player=True)
        self._draw_avatar(ai_avatar_rect, not es_turno_jugador, is_player=False)

        # Information aligned with the avatars
        label_font = pygame.font.Font(None, 26)

        mano1_count = len(jugador1.mano)
        mano1_text = font_small.render(f"Cards: {mano1_count}", True, COLOR_WHITE)
        label_color_player = COLOR_ACCENT_CYAN if es_turno_jugador else COLOR_TEXT_MUTED
        tu_label = label_font.render("YOU", True, label_color_player)
        tu_label_y = player_avatar_rect.top - tu_label.get_height() - 6
        self.screen.blit(tu_label, (player_avatar_rect.centerx - tu_label.get_width() // 2, tu_label_y))

        base_y_player = player_avatar_rect.bottom + 6
        self.screen.blit(
            mano1_text,
            (player_avatar_rect.centerx - mano1_text.get_width() // 2, base_y_player)
        )

        fundamentals1_count = jugador1.aspectos_saludables()
        fundamentals1_text = font_small.render(f"Fundamentals: {fundamentals1_count}/4", True, COLOR_TEXT_MUTED)
        fundamentals_y = base_y_player + mano1_text.get_height() + 4
        self.screen.blit(
            fundamentals1_text,
            (player_avatar_rect.centerx - fundamentals1_text.get_width() // 2, fundamentals_y)
        )

        mano2_count = len(jugador2.mano)
        mano2_text = font_small.render(f"Cards: {mano2_count}", True, COLOR_WHITE)
        label_color_ai = COLOR_ACCENT_ORANGE if not es_turno_jugador else COLOR_TEXT_MUTED
        ia_label = label_font.render("AI", True, label_color_ai)
        ia_label_y = ai_avatar_rect.top - ia_label.get_height() - 6
        self.screen.blit(ia_label, (ai_avatar_rect.centerx - ia_label.get_width() // 2, ia_label_y))

        base_y_ai = ai_avatar_rect.bottom + 6
        self.screen.blit(
            mano2_text,
            (ai_avatar_rect.centerx - mano2_text.get_width() // 2, base_y_ai)
        )

        fundamentals2_count = jugador2.aspectos_saludables()
        fundamentals2_text = font_small.render(f"Fundamentals: {fundamentals2_count}/4", True, COLOR_TEXT_MUTED)
        fundamentals2_y = base_y_ai + mano2_text.get_height() + 4
        self.screen.blit(
            fundamentals2_text,
            (ai_avatar_rect.centerx - fundamentals2_text.get_width() // 2, fundamentals2_y)
        )

        # Deck – aligned with the turn indicator
        mazo_count = len(self.engine.mazo)
        deck_rect = pygame.Rect(self.deck_zone.position, self.deck_zone.size)
        deck_overlay = pygame.Surface(deck_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(deck_overlay, (20, 80, 140, 140), deck_overlay.get_rect(), border_radius=18)
        pygame.draw.rect(deck_overlay, (COLOR_ACCENT_CYAN[0], COLOR_ACCENT_CYAN[1], COLOR_ACCENT_CYAN[2], 160),
                         deck_overlay.get_rect(), width=3, border_radius=18)
        self.screen.blit(deck_overlay, deck_rect.topleft)

        deck_label_font = pygame.font.Font(None, 26)
        deck_count_font = pygame.font.Font(None, 48)
        mazo_label = deck_label_font.render("DECK", True, COLOR_ACCENT_CYAN)
        mazo_text = deck_count_font.render(str(mazo_count), True, COLOR_WHITE)
        self.screen.blit(mazo_label, (deck_rect.centerx - mazo_label.get_width() // 2, deck_rect.top - mazo_label.get_height() - 12))
        self.screen.blit(mazo_text, (deck_rect.centerx - mazo_text.get_width() // 2,
                                     deck_rect.top + deck_rect.height // 2 - mazo_text.get_height() // 2))
        
        # Discard instructions (visible when relevant)
        if self.discard_selection:
            discard_count = len(self.discard_selection)
            # Main instruction
            instruction = font.render(f"✓ {discard_count} CARD(S) SELECTED", True, (255, 255, 100))
            self.screen.blit(instruction, (10, WINDOW_HEIGHT - 60))
            
            # Discard methods
            method1 = font_small.render("Method 1: Click a selected card and drag it to DISCARD", True, (200, 255, 200))
            self.screen.blit(method1, (10, WINDOW_HEIGHT - 40))
            
            method2 = font_small.render("Method 2: Press D to discard them all", True, (200, 255, 200))
            self.screen.blit(method2, (10, WINDOW_HEIGHT - 22))
            
            # Cancel hint
            cancel = font_small.render("(Normal click on another card to cancel)", True, (150, 150, 150))
            self.screen.blit(cancel, (10, WINDOW_HEIGHT - 5))
        elif self.game_ui.dragged_card:
            # Hint while dragging a card
            hint = font_small.render("Drop on DISCARD to discard, or on a valid zone to play", True, (200, 200, 255))
            self.screen.blit(hint, (10, WINDOW_HEIGHT - 30))
        
        # Discard holder label (mirrors deck label)
        descarte_count = len(self.engine.descarte)
        discard_rect = pygame.Rect(self.discard_zone.position, self.discard_zone.size)
        discard_overlay = pygame.Surface(discard_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(discard_overlay, (120, 50, 10, 140), discard_overlay.get_rect(), border_radius=18)
        pygame.draw.rect(discard_overlay, (COLOR_ACCENT_ORANGE[0], COLOR_ACCENT_ORANGE[1], COLOR_ACCENT_ORANGE[2], 160),
                         discard_overlay.get_rect(), width=3, border_radius=18)
        self.screen.blit(discard_overlay, discard_rect.topleft)

        discard_label_font = pygame.font.Font(None, 26)
        discard_count_font = pygame.font.Font(None, 48)
        descarte_label = discard_label_font.render("DISCARD", True, COLOR_ACCENT_ORANGE)
        descarte_text = discard_count_font.render(str(descarte_count), True, COLOR_WHITE)
        self.screen.blit(descarte_label, (discard_rect.centerx - descarte_label.get_width() // 2,
                                          discard_rect.top - descarte_label.get_height() - 12))
        self.screen.blit(descarte_text, (discard_rect.centerx - descarte_text.get_width() // 2,
                                         discard_rect.top + discard_rect.height // 2 - descarte_text.get_height() // 2))
        
        # Draw aspect labels below each holder
        for aspecto in ASPECTOS:
            label_text = ASPECTO_MAP[aspecto]['label']

            # Label for player 1
            zone1 = self.player1_aspects_zones.get(aspecto)
            if zone1:
                label1_surface, _ = _render_text_fit(label_text, (200, 200, 200), zone1.size[0], base_size=18)
                label1_x = zone1.position[0] + (zone1.size[0] - label1_surface.get_width()) // 2
                label1_y = zone1.position[1] + zone1.size[1] + 25
                self.screen.blit(label1_surface, (label1_x, label1_y))

            # Label for player 2
            zone2 = self.player2_aspects_zones.get(aspecto)
            if zone2:
                label2_surface, _ = _render_text_fit(label_text, (200, 200, 200), zone2.size[0], base_size=18)
                label2_x = zone2.position[0] + (zone2.size[0] - label2_surface.get_width()) // 2
                label2_y = zone2.position[1] + zone2.size[1] + 25
                self.screen.blit(label2_surface, (label2_x, label2_y))
    
    def _draw_ui_buttons(self) -> None:
        """Draw the bottom control buttons."""
        font = pygame.font.Font(None, 28)

        def draw_button(rect: pygame.Rect, text: str,
                        base_color: Tuple[int, int, int], hover_color: Tuple[int, int, int],
                        border_color: Tuple[int, int, int]):
            is_hover = rect.collidepoint(pygame.mouse.get_pos())
            color = hover_color if is_hover else base_color
            button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(button_surface, (*color, 220), button_surface.get_rect(), border_radius=16)
            glow_rect = rect.inflate(12, 12)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (*border_color, 70), glow_surface.get_rect(), border_radius=18)
            self.screen.blit(glow_surface, glow_rect.topleft)
            self.screen.blit(button_surface, rect.topleft)
            pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=16)
            label = font.render(text, True, COLOR_BLACK)
            label_x = rect.centerx - label.get_width() // 2
            label_y = rect.centery - label.get_height() // 2
            self.screen.blit(label, (label_x, label_y))

        draw_button(self.btn_start_rect, "New Game",
                    COLOR_ACCENT_CYAN, COLOR_ACCENT_CYAN_HOVER, COLOR_ACCENT_ORANGE)
        draw_button(self.btn_quit_rect, "Quit",
                    COLOR_ACCENT_ORANGE, COLOR_ACCENT_ORANGE_HOVER, COLOR_ACCENT_CYAN)

    def run(self):
        """Main game loop."""
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            
            self.update()

            # Auto-play: when enabled and it's the player's turn, run automatic turn
            if self.auto_play_enabled:
                jugador_actual = self.engine.jugadores[self.engine.turno]
                if jugador_actual == self.engine.jugadores[0]:
                    self._auto_play_turn(0)

            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        ganador = self.engine.comprobar_victoria()
        if ganador:
            etiqueta = "YOU" if ganador == self.engine.jugadores[0].nombre else ganador
            print(f"[END] Match finished. Winner: {etiqueta}")

    def _reset_turn_flags(self):
        """Reset internal state associated with the current turn."""
        self.turn_action = 'none'
        if hasattr(self, '_ai_turn_started'):
            self._ai_turn_started = False
        if hasattr(self, '_last_ai_action_time'):
            self._last_ai_action_time = 0

    def _change_turn(self):
        """Advance the engine turn and refresh the interface."""
        import time

        turno_anterior = self.engine.jugadores[self.engine.turno].nombre
        self.engine.siguiente_turno()
        nuevo_jugador = self.engine.jugadores[self.engine.turno]
        print(f"✓ Turn changed: {turno_anterior} → {nuevo_jugador.nombre}")

        # Reset internal flags for the new turn
        self._reset_turn_flags()

        # If the new turn belongs to the AI, record the timestamp for the initial delay
        if nuevo_jugador == self.engine.jugadores[1]:
            self._last_ai_action_time = time.time()

        # Refresh UI
        self._load_cards()
        self._update_aspects()
        self._update_discard()

    def _ai_play_card(self):
        """Compatibility helper: executes the traditional AI auto-turn."""
        self._auto_play_turn(1)

    def _handle_ui_buttons(self, pos: Tuple[int, int]) -> bool:
        """Handle interaction with the bottom buttons."""
        if self.btn_start_rect.collidepoint(pos):
            self._start_new_game()
            return True
        if self.btn_quit_rect.collidepoint(pos):
            self._abandon_game()
            return True
        return False

    def _start_new_game(self) -> None:
        """Restart the match while keeping the current configuration."""
        print("[UI] New game requested")
        self._push_message("New game started", "System")
        self.engine.iniciar_partida()
        self._reset_turn_flags()
        self.last_ai_action_message = ""
        self.last_player_action_message = "New game started"
        self.modal_victoria_visible = False
        self.modal_victoria_jugador = None
        self.modal_victoria_ack = False
        self._load_cards()
        self._update_aspects()
        self._update_discard()
        if self.auto_play_enabled:
            self._ai_turn_started = False
            self._last_ai_action_time = 0

    def _abandon_game(self) -> None:
        """Abandon the current match."""
        print("[UI] Abandon match")
        self._push_message("Match abandoned", "System")
        self.last_player_action_message = "Match abandoned"
        self.auto_play_enabled = False
        self._ai_turn_started = False
        self._last_ai_action_time = 0
        self.modal_victoria_visible = False
        self.running = False

    def _maybe_trigger_destruction_effect(self, affected_player_idx: int, aspects_before: Set[str]) -> None:
        """Spawn a destruction effect if a fundamental was removed."""
        detail = (self.engine.last_action_detail or "").lower()
        if "destroys aspect" not in detail:
            return
        aspects_after = set(self.engine.jugadores[affected_player_idx].aspectos.keys())
        destroyed = aspects_before - aspects_after
        for aspect in destroyed:
            self._spawn_destruction_effect(affected_player_idx, aspect)

    def _spawn_destruction_effect(self, player_idx: int, aspect: str) -> None:
        zones = self.player1_aspects_zones if player_idx == 0 else self.player2_aspects_zones
        zone = zones.get(aspect)
        if not zone:
            return
        center_x = zone.position[0] + zone.size[0] // 2
        center_y = zone.position[1] + zone.size[1] // 2
        max_radius = max(zone.size) // 2
        effect = {
            "type": "destroy",
            "center": (center_x, center_y),
            "start": time.time(),
            "duration": 0.65,
            "max_radius": max_radius,
            "particles": self._create_explosion_particles(max_radius),
        }
        self.active_effects.append(effect)

    def _create_explosion_particles(self, radius: int) -> List[Dict[str, float]]:
        particles: List[Dict[str, float]] = []
        for _ in range(18):
            angle = random.uniform(0, math.tau)
            distance = random.uniform(radius * 0.35, radius * 1.3)
            velocity = (math.cos(angle) * distance, math.sin(angle) * distance)
            particle = {
                "velocity": velocity,
                "size": random.randint(3, 6),
                "alpha": random.randint(140, 210),
                "color": random.choice([(255, 210, 150), (255, 150, 110), (255, 90, 70)]),
            }
            particles.append(particle)
        return particles

    def _draw_active_effects(self) -> None:
        if not self.active_effects:
            return
        now = time.time()
        remaining: List[Dict] = []
        for effect in self.active_effects:
            elapsed = now - effect["start"]
            duration = effect.get("duration", 0.6)
            progress = elapsed / duration if duration > 0 else 1.0
            if progress >= 1.0:
                continue
            if effect.get("type") == "destroy":
                self._draw_destruction_effect(effect, progress)
            remaining.append(effect)
        self.active_effects = remaining

    def _draw_destruction_effect(self, effect: Dict, progress: float) -> None:
        cx, cy = effect["center"]
        max_radius = effect.get("max_radius", 60)
        radius = max(4, int(max_radius * progress))
        flash_alpha = max(0, int(220 * (1 - progress)))

        if flash_alpha > 0:
            flash_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surface, (255, 205, 145, flash_alpha), (radius, radius), radius)
            outline_alpha = max(0, flash_alpha - 120)
            if outline_alpha > 0:
                pygame.draw.circle(
                    flash_surface,
                    (255, 250, 235, outline_alpha),
                    (radius, radius),
                    max(2, int(radius * 0.6)),
                    width=3,
                )
            self.screen.blit(flash_surface, (cx - radius, cy - radius))

        decay = max(0.0, 1.0 - progress)
        for particle in effect.get("particles", []):
            offset_x, offset_y = particle["velocity"]
            px = cx + offset_x * progress
            py = cy + offset_y * progress
            size = max(1, int(particle["size"] * decay))
            alpha = max(0, int(particle["alpha"] * decay))
            if alpha <= 0:
                continue
            pygame.draw.circle(
                self.screen,
                (*particle["color"], alpha),
                (int(px), int(py)),
                size,
            )

    def _push_message(self, mensaje: str, autor: str = "") -> None:
        """Add a toast-style message with the current timestamp."""
        if not mensaje or not mensaje.strip():
            return
        import time
        clean_message = mensaje.strip()
        self.message_toasts.append((autor, clean_message, time.time()))
        self.latest_toast_text = (autor, clean_message)
        if len(self.message_toasts) > 10:
            self.message_toasts = self.message_toasts[-10:]

    def _cleanup_toasts(self) -> None:
        """Remove expired toasts."""
        import time
        now = time.time()
        self.message_toasts = [toast for toast in self.message_toasts if now - toast[2] <= self.toast_duration]

    def _load_avatar_assets(self):
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets', 'players')
        player_path = os.path.join(assets_dir, 'player.png')
        bot_path = os.path.join(assets_dir, 'bot.png')

        def load_avatar(path: str) -> Optional[pygame.Surface]:
            if not os.path.exists(path):
                print(f"[WARN] Avatar not found: {path}")
                return None
            try:
                image = pygame.image.load(path).convert_alpha()
                return self._scale_avatar_to_canvas(image, self.avatar_max_size)
            except Exception as exc:
                print(f"[WARN] Could not load avatar {path}: {exc}")
                return None

        self.player_avatar_color = load_avatar(player_path)
        self.bot_avatar_color = load_avatar(bot_path)
        self.player_avatar_gray = self._convert_avatar_to_grayscale(self.player_avatar_color)
        self.bot_avatar_gray = self._convert_avatar_to_grayscale(self.bot_avatar_color)

    def _scale_avatar_to_canvas(self, image: pygame.Surface, max_size: Tuple[int, int]) -> pygame.Surface:
        max_w, max_h = max_size
        iw, ih = image.get_size()
        if iw == 0 or ih == 0:
            return pygame.Surface(max_size, pygame.SRCALPHA)

        scale = min(max_w / iw, max_h / ih)
        new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
        scaled = pygame.transform.smoothscale(image, new_size)

        canvas = pygame.Surface(max_size, pygame.SRCALPHA)
        offset_x = (max_w - new_size[0]) // 2
        offset_y = (max_h - new_size[1]) // 2
        canvas.blit(scaled, (offset_x, offset_y))
        return canvas

    def _convert_avatar_to_grayscale(self, image: Optional[pygame.Surface]) -> Optional[pygame.Surface]:
        if image is None:
            return None
        gray = image.copy()
        if _HAS_NUMPY:
            arr = pygame.surfarray.array3d(gray)
            luminance = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype('uint8')
            arr[:, :, 0] = luminance
            arr[:, :, 1] = luminance
            arr[:, :, 2] = luminance
            pygame.surfarray.blit_array(gray, arr)
            alpha = pygame.surfarray.array_alpha(image).copy()
            pygame.surfarray.pixels_alpha(gray)[:] = alpha
        else:
            gray.fill((160, 160, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return gray

    def _compute_avatar_rect_left(
        self,
        slot_rects: List[pygame.Rect],
        reference_zones: Optional[List[Zone]] = None
    ) -> pygame.Rect:
        if not slot_rects:
            return pygame.Rect(0, 0, 0, 0)

        first = slot_rects[0]
        last = slot_rects[-1]
        width, height = self.avatar_max_size

        hand_left = first.left

        zone_right = None
        if reference_zones:
            zone_right = max((zone.position[0] + zone.size[0]) for zone in reference_zones if zone is not None)

        if zone_right is None or zone_right >= hand_left:
            x = hand_left - self.avatar_margin - width
        else:
            target_center_x = (zone_right + hand_left) / 2
            x = int(target_center_x - width / 2)

        x = max(10, min(WINDOW_WIDTH - width - 10, x))

        slots_center_y = (first.centery + last.centery) // 2
        y = int(slots_center_y - height / 2)

        return pygame.Rect(x, y, width, height)

    def _draw_avatar(self, rect: pygame.Rect, is_active: bool, is_player: bool) -> None:
        if rect.width == 0 or rect.height == 0:
            return

        if is_player:
            active_img = self.player_avatar_color
            inactive_img = self.player_avatar_gray
        else:
            active_img = self.bot_avatar_color
            inactive_img = self.bot_avatar_gray

        image = active_img if is_active else inactive_img
        if image is None:
            return

        self.screen.blit(image, rect.topleft)

    def _get_avatar_for(self, autor: str, prefer_gray: bool = False) -> Optional[pygame.Surface]:
        """Return the avatar associated with the given author."""
        if not autor:
            return None

        autor_norm = autor.strip().lower().replace("\u00fa", "u")
        jugador1 = self.engine.jugadores[0].nombre.strip().lower()
        jugador2 = self.engine.jugadores[1].nombre.strip().lower()
        jugador1_norm = jugador1.replace("\u00fa", "u")
        jugador2_norm = jugador2.replace("\u00fa", "u")

        if autor_norm in ("tu", "you", jugador1_norm):
            return self.player_avatar_gray if prefer_gray else self.player_avatar_color
        if autor_norm in ("ia", jugador2_norm, jugador2, "ia (oponente)", "oponente"):
            return self.bot_avatar_gray if prefer_gray else self.bot_avatar_color

        return None

    def _get_toast_avatar(self, autor: str) -> Optional[pygame.Surface]:
        avatar = self._get_avatar_for(autor, prefer_gray=False)
        if avatar is None:
            return None
        target = 56
        return pygame.transform.smoothscale(avatar, (target, target))

    def _handle_modal_event(self, event: pygame.event.Event) -> None:
        """Handle interaction with the victory modal window."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.modal_close_rect.collidepoint(event.pos):
                self.modal_victoria_ack = True
                self.modal_victoria_visible = False
                self.modal_victoria_jugador = None
                return
            if self.modal_btn_new.collidepoint(event.pos):
                self.modal_victoria_ack = True
                self.modal_victoria_visible = False
                self._start_new_game()
                return
            if self.modal_btn_quit.collidepoint(event.pos):
                self.modal_victoria_ack = True
                self.modal_victoria_visible = False
                self._abandon_game()
                return
            if not self.modal_rect.collidepoint(event.pos):
                self.modal_victoria_ack = True
                self.modal_victoria_visible = False
                self.modal_victoria_jugador = None
                return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.modal_victoria_ack = True
                self.modal_victoria_visible = False
                self.modal_victoria_jugador = None
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.modal_victoria_ack = True
                self.modal_victoria_visible = False
                self._start_new_game()
                return

    def _draw_toasts(self) -> None:
        """Draw the most recent toast message with a smooth animation."""
        import time

        self._cleanup_toasts()

        toast_entry: Optional[Tuple[str, str, float]] = None
        use_fallback = False

        if self.message_toasts:
            toast_entry = self.message_toasts[-1]
        elif self.latest_toast_text:
            autor, mensaje = self.latest_toast_text
            toast_entry = (autor, mensaje, time.time())
            use_fallback = True

        if not toast_entry:
            return

        autor, mensaje, timestamp = toast_entry
        now = time.time()
        elapsed = max(0.0, now - timestamp)

        appear_time = self.toast_anim_time
        total_time = self.toast_duration

        if use_fallback:
            progress = 1.0
        else:
            if elapsed >= total_time:
                return
            progress_in = min(1.0, elapsed / appear_time) if appear_time > 0 else 1.0
            progress_out = 1.0
            if elapsed > total_time - appear_time:
                remaining = max(0.0, total_time - elapsed)
                progress_out = min(1.0, remaining / appear_time) if appear_time > 0 else 0.0
            progress = max(0.0, min(progress_in, progress_out))

        if progress <= 0.0:
            return

        font_message = pygame.font.Font(None, 30)
        message_text = mensaje.strip()

        if autor:
            prefix = autor.strip().lower() + ":"
            if message_text.lower().startswith(prefix):
                message_text = message_text[len(prefix):].strip()

        message_surface = font_message.render(message_text, True, (20, 30, 60))
        padding_y = 18
        padding_x = 28
        spacing = 18

        avatar_surface = self._get_toast_avatar(autor)
        avatar_width = avatar_surface.get_width() if avatar_surface else 0

        box_width = padding_x * 2 + message_surface.get_width() + (avatar_width + spacing if avatar_surface else 0)
        box_height = max(message_surface.get_height(), avatar_width) + padding_y * 2

        base_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        alpha = int(220 * progress)
        pygame.draw.rect(base_surface, (255, 255, 255, alpha), base_surface.get_rect(), border_radius=18)
        pygame.draw.rect(base_surface, (*COLOR_TOAST_BORDER, int(240 * progress)), base_surface.get_rect(), width=3, border_radius=18)

        glow_surface = pygame.Surface((box_width + 20, box_height + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (*COLOR_TOAST_GLOW, int(80 * progress)), glow_surface.get_rect(), border_radius=22)

        if avatar_surface:
            avatar_y = (box_height - avatar_surface.get_height()) // 2
            base_surface.blit(avatar_surface, (padding_x, avatar_y))
            text_x = padding_x + avatar_surface.get_width() + spacing
        else:
            text_x = padding_x

        text_y = (box_height - message_surface.get_height()) // 2
        base_surface.blit(message_surface, (text_x, text_y))

        hidden_y = -box_height - 20
        visible_y = 24
        draw_y = hidden_y + (visible_y - hidden_y) * progress
        draw_x = (WINDOW_WIDTH - box_width) // 2

        glow_x = draw_x - 10
        glow_y = draw_y - 10

        self.screen.blit(glow_surface, (glow_x, glow_y))
        self.screen.blit(base_surface, (draw_x, draw_y))

    def _draw_victory_modal(self) -> None:
        """Render the victory modal window."""
        if not self.modal_victoria_visible or not self.modal_victoria_jugador:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 20, 60, 180))
        self.screen.blit(overlay, (0, 0))

        modal_width = 620
        modal_height = 420
        modal_x = (WINDOW_WIDTH - modal_width) // 2
        modal_y = (WINDOW_HEIGHT - modal_height) // 2
        self.modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)

        modal_surface = pygame.Surface(self.modal_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(modal_surface, (242, 246, 255, 245), modal_surface.get_rect(), border_radius=24)
        pygame.draw.rect(modal_surface, COLOR_ACCENT_ORANGE, modal_surface.get_rect(), width=4, border_radius=24)

        glow_surface = pygame.Surface((modal_width + 30, modal_height + 30), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (*COLOR_ACCENT_CYAN, 80), glow_surface.get_rect(), border_radius=28)
        self.screen.blit(glow_surface, (modal_x - 15, modal_y - 15))

        titulo_font = pygame.font.Font(None, 52)
        texto_font = pygame.font.Font(None, 30)
        ganador_norm = self.modal_victoria_jugador.strip().lower()
        jugador1 = self.engine.jugadores[0].nombre.strip().lower()
        jugador2 = self.engine.jugadores[1].nombre.strip().lower()

        if ganador_norm == jugador1:
            ganador_label = "YOU"
        elif ganador_norm == jugador2:
            ganador_label = "AI"
        else:
            ganador_label = self.modal_victoria_jugador

        titulo_texto = f"{ganador_label} has won"
        titulo_surface = titulo_font.render(titulo_texto, True, COLOR_ACCENT_ORANGE)
        modal_surface.blit(titulo_surface, ((modal_width - titulo_surface.get_width()) // 2, 36))

        avatar_surface = self._get_avatar_for(self.modal_victoria_jugador, prefer_gray=False)
        if avatar_surface is not None:
            avatar_size = 150
            avatar_scaled = pygame.transform.smoothscale(avatar_surface, (avatar_size, avatar_size))
            avatar_x = modal_width // 2 - avatar_size // 2
            avatar_y = 120
            modal_surface.blit(avatar_scaled, (avatar_x, avatar_y))
        else:
            trophy_surface = pygame.Surface((140, 140), pygame.SRCALPHA)
            pygame.draw.rect(trophy_surface, COLOR_ACCENT_ORANGE, (40, 30, 60, 70), border_radius=12)
            pygame.draw.rect(trophy_surface, COLOR_ACCENT_ORANGE, (55, 20, 30, 20), border_radius=8)
            pygame.draw.polygon(trophy_surface, COLOR_ACCENT_ORANGE, [(35, 40), (40, 30), (40, 100), (35, 90)])
            pygame.draw.polygon(trophy_surface, COLOR_ACCENT_ORANGE, [(105, 40), (100, 30), (100, 100), (105, 90)])
            trophy_rect = trophy_surface.get_rect(center=(modal_width // 2, 190))
            modal_surface.blit(trophy_surface, trophy_rect.topleft)

        button_width = 200
        button_height = 48
        button_spacing = 24
        buttons_y = modal_height - button_height - 90
        total_buttons_width = button_width * 2 + button_spacing
        first_button_x = (modal_width - total_buttons_width) // 2

        self.modal_btn_new = pygame.Rect(self.modal_rect.x + first_button_x,
                                         self.modal_rect.y + buttons_y,
                                         button_width, button_height)
        self.modal_btn_quit = pygame.Rect(self.modal_rect.x + first_button_x + button_width + button_spacing,
                                          self.modal_rect.y + buttons_y,
                                          button_width, button_height)

        def draw_modal_button(rect: pygame.Rect, text: str,
                              base_color: Tuple[int, int, int], hover_color: Tuple[int, int, int],
                              border_color: Tuple[int, int, int]) -> None:
            is_hover = rect.collidepoint(pygame.mouse.get_pos())
            color = hover_color if is_hover else base_color
            button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(button_surface, (*color, 230), button_surface.get_rect(), border_radius=16)
            pygame.draw.rect(button_surface, border_color, button_surface.get_rect(), width=2, border_radius=16)
            label = texto_font.render(text, True, COLOR_BLACK)
            label_x = rect.x + rect.width // 2 - label.get_width() // 2
            label_y = rect.y + rect.height // 2 - label.get_height() // 2
            self.screen.blit(button_surface, rect.topleft)
            self.screen.blit(label, (label_x, label_y))

        close_size = 36
        close_x = self.modal_rect.right - close_size - 24
        close_y = self.modal_rect.top + 24
        self.modal_close_rect = pygame.Rect(close_x, close_y, close_size, close_size)

        close_surface = pygame.Surface(self.modal_close_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(close_surface, (0, 0, 0, 0), close_surface.get_rect())
        close_hover = self.modal_close_rect.collidepoint(pygame.mouse.get_pos())
        close_color = COLOR_ACCENT_CYAN if close_hover else COLOR_ACCENT_ORANGE
        close_text = pygame.font.Font(None, 40).render("X", True, close_color)
        close_text_pos = (self.modal_close_rect.width // 2 - close_text.get_width() // 2,
                          self.modal_close_rect.height // 2 - close_text.get_height() // 2)
        close_surface.blit(close_text, close_text_pos)

        self.screen.blit(modal_surface, self.modal_rect.topleft)
        self.screen.blit(close_surface, self.modal_close_rect.topleft)

        draw_modal_button(self.modal_btn_new, "New Game", COLOR_ACCENT_CYAN,
                          COLOR_ACCENT_CYAN_HOVER, COLOR_ACCENT_ORANGE)
        draw_modal_button(self.modal_btn_quit, "Quit", COLOR_ACCENT_ORANGE,
                          COLOR_ACCENT_ORANGE_HOVER, COLOR_ACCENT_CYAN)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='API Card Game')
    parser.add_argument('--autopilot', action='store_true', help='enable AI vs AI mode from the start')
    args = parser.parse_args()

    game = APIGameGUI()
    if args.autopilot:
        game.auto_play_enabled = True
        game._ai_turn_started = False
        game._last_ai_action_time = 0
        game.last_player_action_message = "Auto-play ENABLED"
        print('[AUTO-PLAY] --autopilot enabled: AI vs AI mode active from the start')
    game.run()

