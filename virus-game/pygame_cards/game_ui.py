"""
GameUI - Clase principal para gestionar la interfaz del juego
"""
import pygame
from typing import List, Optional, Tuple
from pygame_cards.deck import Deck
from pygame_cards.zone import Zone
from pygame_cards.card import Card


class GameUI:
    """Gestiona la interfaz de usuario del juego de cartas."""
    
    def __init__(self, screen: pygame.Surface, deck: Deck, zones: List[Zone]):
        self.screen = screen
        self.deck = deck
        self.zones = zones
        self.dragged_card: Optional[Card] = None
        self.drag_offset: Tuple[int, int] = (0, 0)
        self.selected_card: Optional[Card] = None
        
    def handle_event(self, event: pygame.event.Event):
        """Maneja eventos de Pygame."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Click izquierdo
                self._handle_mouse_down(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Soltar click izquierdo
                self._handle_mouse_up(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event.pos)
    
    def _handle_mouse_down(self, pos: Tuple[int, int]):
        """Maneja el evento de presionar el mouse."""
        # Buscar carta en zonas
        for zone in self.zones:
            card = zone.get_card_at(pos)
            if card:
                self.dragged_card = card
                self.drag_offset = (pos[0] - card.rect.x, pos[1] - card.rect.y)
                card.dragging = True
                # Mover carta al final de la lista para que se dibuje encima
                if card in zone.cards:
                    zone.cards.remove(card)
                    zone.cards.append(card)
                return
        
        # Buscar carta en el mazo
        card = self.deck.get_card_at(pos)
        if card:
            self.dragged_card = card
            self.drag_offset = (pos[0] - card.rect.x, pos[1] - card.rect.y)
            card.dragging = True
            return
    
    def _handle_mouse_up(self, pos: Tuple[int, int]):
        """Maneja el evento de soltar el mouse."""
        if not self.dragged_card:
            return
        
        # Guardar referencia antes de resetear
        card = self.dragged_card
        self.dragged_card.dragging = False
        
        # NO mover automáticamente la carta aquí
        # Dejar que el código externo (virus_game.py) decida qué hacer
        # Si el código externo limpia dragged_card, entonces ya se manejó
        # Si no, resetear posición después de un pequeño delay
        # (esto se manejará en virus_game.py si es necesario)
    
    def _handle_mouse_motion(self, pos: Tuple[int, int]):
        """Maneja el movimiento del mouse."""
        if self.dragged_card:
            self.dragged_card.set_position(
                pos[0] - self.drag_offset[0],
                pos[1] - self.drag_offset[1],
                animate=False
            )
    
    def draw(self):
        """Dibuja todos los elementos de la UI."""
        # Dibujar mazo
        self.deck.draw(self.screen)
        
        # Dibujar zonas
        for zone in self.zones:
            zone.draw(self.screen)
        
        # Dibujar carta arrastrada encima de todo
        if self.dragged_card:
            self.dragged_card.draw(self.screen)

