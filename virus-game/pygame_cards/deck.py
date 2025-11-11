"""
Deck - Clase para gestionar mazos de cartas
"""
import pygame
from typing import List, Optional
from pygame_cards.card import Card


class Deck:
    """Representa un mazo de cartas."""
    
    def __init__(self, position: Optional[tuple] = None):
        self.cards: List[Card] = []
        self.position = position or (50, 50)
        self.rect = pygame.Rect(self.position[0], self.position[1], 120, 160)
        
    def add_card(self, card: Card):
        """Añade una carta al mazo."""
        if card not in self.cards:
            self.cards.append(card)
            card.set_position(self.position[0], self.position[1], animate=False)
    
    def add_cards(self, cards: List[Card]):
        """Añade múltiples cartas al mazo."""
        for card in cards:
            self.add_card(card)
    
    def remove_card(self, card: Card) -> bool:
        """Elimina una carta del mazo."""
        if card in self.cards:
            self.cards.remove(card)
            return True
        return False
    
    def draw_card(self) -> Optional[Card]:
        """Roba una carta del mazo."""
        if self.cards:
            return self.cards.pop(0)
        return None
    
    def shuffle(self):
        """Baraja el mazo."""
        import random
        random.shuffle(self.cards)
    
    def draw(self, surface: pygame.Surface):
        """Dibuja el mazo (solo la carta superior si hay cartas)."""
        if self.cards:
            # Dibujar solo la carta superior
            top_card = self.cards[-1]
            top_card.draw(surface)
        else:
            # Dibujar placeholder de mazo vacío
            pygame.draw.rect(surface, (100, 100, 100), self.rect, border_radius=8)
            font = pygame.font.Font(None, 20)
            text = font.render("Deck", True, (200, 200, 200))
            text_rect = text.get_rect(center=self.rect.center)
            surface.blit(text, text_rect)
    
    def contains_point(self, point: tuple) -> bool:
        """Verifica si un punto está dentro del área del mazo."""
        return self.rect.collidepoint(point)
    
    def get_card_at(self, point: tuple) -> Optional[Card]:
        """Obtiene la carta en un punto específico."""
        for card in reversed(self.cards):  # Reversed para obtener la superior primero
            if card.contains_point(point):
                return card
        return None

