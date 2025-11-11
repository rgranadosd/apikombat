"""
Zone - Clase para representar áreas de juego donde se pueden colocar cartas
"""
import pygame
from typing import List, Optional, Tuple
from pygame_cards.card import Card


class Zone:
    """Representa una zona del tablero donde se pueden colocar cartas."""
    
    def __init__(self, position: Tuple[int, int], size: Tuple[int, int], 
                 max_cards: Optional[int] = None, card_spacing: int = 10):
        self.position = position
        self.size = size
        self.rect = pygame.Rect(position[0], position[1], size[0], size[1])
        self.cards: List[Card] = []
        self.max_cards = max_cards
        self.card_spacing = card_spacing
        self.accepts_cards = True
        self.custom_positions: Optional[List[pygame.Rect]] = None
        
    def add_card(self, card: Card, position: Optional[int] = None):
        """Añade una carta a la zona."""
        if self.max_cards and len(self.cards) >= self.max_cards:
            return False
        
        if card in self.cards:
            return False
        
        if position is None:
            self.cards.append(card)
        else:
            self.cards.insert(position, card)
        
        # Actualizar posiciones inmediatamente
        self._update_card_positions()
        return True
    
    def remove_card(self, card: Card) -> bool:
        """Elimina una carta de la zona."""
        if card in self.cards:
            self.cards.remove(card)
            self._update_card_positions()
            return True
        return False
    
    def _update_card_positions(self):
        """Actualiza las posiciones de las cartas en la zona."""
        if not self.cards:
            return
        
        card_width = self.cards[0].size[0] if self.cards else 120
        card_height = self.cards[0].size[1] if self.cards else 160

        if self.custom_positions:
            for i, card in enumerate(self.cards):
                rect = self.custom_positions[min(i, len(self.custom_positions) - 1)]
                x = rect.x + (rect.width - card_width) // 2
                y = rect.y + (rect.height - card_height) // 2
                if hasattr(card, 'set_position_immediate'):
                    card.set_position_immediate(x, y)
                else:
                    card.set_position(x, y, animate=False)
                    card.x = x
                    card.y = y
                    card.target_x = x
                    card.target_y = y
                card.rect.x = x
                card.rect.y = y
            return
        
        # Determinar si apilar verticalmente o horizontalmente
        # Si la zona es más alta que ancha, o si tiene card_spacing <= 2 (mazo/descarte), apilar verticalmente
        stack_vertically = (self.size[1] > self.size[0] * 1.5) or (self.card_spacing <= 2 and self.max_cards is None)
        
        if stack_vertically:
            # Apilar verticalmente (para mazo y descarte)
            # Para apilar como una baraja real, usar espaciado mínimo (superposición)
            # Si el espaciado es muy pequeño (<= 2), apilar superponiendo
            if self.card_spacing <= 2:
                # Apilado superpuesto: todas las cartas en la misma posición base
                # con un pequeño offset para ver que hay múltiples
                # Centrar verticalmente dentro de la zona
                start_y = self.position[1] + (self.size[1] - card_height) // 2
                start_x = self.position[0] + (self.size[0] - card_width) // 2
                
                # Offset muy pequeño para mostrar que hay múltiples cartas
                # Solo las últimas cartas (arriba) se desplazan ligeramente
                max_offset_x = 2  # Offset horizontal muy pequeño
                max_offset_y = 1  # Offset vertical muy pequeño
                
                for i, card in enumerate(self.cards):
                    # Solo las primeras 5 cartas (las visibles) tienen offset
                    # El resto están completamente superpuestas
                    if i < 5:
                        offset_x = int((i / 4) * max_offset_x) if len(self.cards) > 1 else 0
                        offset_y = int((i / 4) * max_offset_y) if len(self.cards) > 1 else 0
                    else:
                        # Cartas más abajo: completamente superpuestas
                        offset_x = max_offset_x
                        offset_y = max_offset_y
                    
                    x = start_x + offset_x
                    y = start_y + offset_y
                    
                    # Usar posición inmediata para apilar correctamente (sin animación)
                    if hasattr(card, 'set_position_immediate'):
                        card.set_position_immediate(x, y)
                    else:
                        # Si no tiene set_position_immediate, usar set_position sin animación
                        card.set_position(x, y, animate=False)
                        # Asegurar que la posición actual sea igual a la target
                        card.x = x
                        card.y = y
                        card.target_x = x
                        card.target_y = y
                    # Asegurar que el rect esté actualizado
                    card.rect.x = x
                    card.rect.y = y
            else:
                # Apilado con espaciado (para otros casos)
                total_height = len(self.cards) * card_height + (len(self.cards) - 1) * self.card_spacing
                
                if total_height > self.size[1]:
                    spacing = max(1, (self.size[1] - len(self.cards) * card_height) / max(1, len(self.cards) - 1))
                else:
                    spacing = self.card_spacing
                
                # Centrar verticalmente el grupo de cartas dentro de la zona
                start_y = self.position[1] + (self.size[1] - total_height) // 2
                start_x = self.position[0] + (self.size[0] - card_width) // 2
                
                max_offset_x = 8
                max_offset_y = 3
                
                for i, card in enumerate(self.cards):
                    offset_x = int((i / max(1, len(self.cards) - 1)) * max_offset_x) if len(self.cards) > 1 else 0
                    offset_y = int((i / max(1, len(self.cards) - 1)) * max_offset_y) if len(self.cards) > 1 else 0
                    
                    x = start_x + offset_x
                    # Apilar desde arriba hacia abajo, centrado en la zona
                    y = int(start_y + i * (card_height + spacing) + offset_y)
                    
                    # Usar posición inmediata para evitar animaciones innecesarias
                    if hasattr(card, 'set_position_immediate'):
                        card.set_position_immediate(x, y)
                    else:
                        card.set_position(x, y, animate=False)
                        # Asegurar que la posición actual sea igual a la target
                        card.x = x
                        card.y = y
                        card.target_x = x
                        card.target_y = y
                    card.rect.x = x
                    card.rect.y = y
        else:
            # Apilar horizontalmente (para manos)
            total_width = len(self.cards) * card_width + (len(self.cards) - 1) * self.card_spacing
            
            if total_width > self.size[0]:
                # Ajustar espaciado si hay demasiadas cartas
                spacing = (self.size[0] - len(self.cards) * card_width) / max(1, len(self.cards) - 1)
            else:
                spacing = self.card_spacing
            
            start_x = self.position[0] + (self.size[0] - total_width) // 2
            
            for i, card in enumerate(self.cards):
                x = int(start_x + i * (card_width + spacing))
                y = self.position[1] + (self.size[1] - card.size[1]) // 2
                # Usar posición inmediata para evitar animaciones innecesarias
                if hasattr(card, 'set_position_immediate'):
                    card.set_position_immediate(x, y)
                else:
                    card.set_position(x, y, animate=False)
                    # Asegurar que la posición actual sea igual a la target
                    card.x = x
                    card.y = y
                    card.target_x = x
                    card.target_y = y
                card.rect.x = x
                card.rect.y = y
    
    def draw(self, surface: pygame.Surface):
        """Dibuja la zona y sus cartas."""
        # Dibujar marcador visual (placeholder) cuando está vacío
        if len(self.cards) == 0:
            if self.custom_positions:
                return
            # Tamaño estándar de una carta
            card_width = 120
            card_height = 160
            
            # Calcular el rectángulo del placeholder centrado en la zona
            placeholder_x = self.rect.x + (self.rect.width - card_width) // 2
            placeholder_y = self.rect.y + (self.rect.height - card_height) // 2
            placeholder_rect = pygame.Rect(placeholder_x, placeholder_y, card_width, card_height)
            
            if self.max_cards == 1:
                # Slot vacío con borde (para fundamentals) - tamaño de carta
                pygame.draw.rect(surface, (235, 235, 225), placeholder_rect, width=3, border_radius=10)
            else:
                # Placeholder para zonas sin límite (descarte, mazo, etc.) - tamaño de carta
                # Borde exterior más visible
                pygame.draw.rect(surface, (235, 235, 225), placeholder_rect, width=3, border_radius=10)
                # Borde interior más sutil
                inner_rect = pygame.Rect(placeholder_rect.x + 5, placeholder_rect.y + 5, 
                                        placeholder_rect.width - 10, placeholder_rect.height - 10)
                pygame.draw.rect(surface, (210, 210, 200), inner_rect, width=1, border_radius=6)
                
                # Dibujar un patrón de cuadrícula sutil para mejor visibilidad
                step = 20
                for i in range(step, placeholder_rect.width, step):
                    pygame.draw.line(surface, (200, 200, 190, 80), 
                                   (placeholder_rect.x + i, placeholder_rect.y + 5), 
                                   (placeholder_rect.x + i, placeholder_rect.y + placeholder_rect.height - 5), 1)
                for i in range(step, placeholder_rect.height, step):
                    pygame.draw.line(surface, (200, 200, 190, 80), 
                                   (placeholder_rect.x + 5, placeholder_rect.y + i), 
                                   (placeholder_rect.x + placeholder_rect.width - 5, placeholder_rect.y + i), 1)
        
        # Dibujar cartas (en orden inverso para que la última añadida quede encima)
        for card in self.cards:
            card.draw(surface)
    
    def contains_point(self, point: tuple) -> bool:
        """Verifica si un punto está dentro de la zona."""
        return self.rect.collidepoint(point)
    
    def get_card_at(self, point: tuple) -> Optional[Card]:
        """Obtiene la carta en un punto específico."""
        for card in reversed(self.cards):  # Reversed para obtener la superior primero
            if card.contains_point(point):
                return card
        return None
    
    def clear(self):
        """Limpia todas las cartas de la zona."""
        self.cards.clear()

