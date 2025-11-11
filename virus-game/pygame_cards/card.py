"""
Card - Clase base para cartas en pygame_cards
"""
import pygame
from typing import Optional, Tuple


class Card:
    """Clase base para representar una carta en el juego."""
    
    def __init__(self, id: int, title: str, size: Tuple[int, int] = (120, 160)):
        self.id = id
        self.title = title
        self.size = size
        self.rect = pygame.Rect(0, 0, size[0], size[1])
        self.flipped = False
        self.selected = False
        self.dragging = False
        self.front_image: Optional[pygame.Surface] = None
        self.back_image: Optional[pygame.Surface] = None
        self.image_path: Optional[str] = None
        
        # Posición y animación
        self.x = 0
        self.y = 0
        self.target_x = 0
        self.target_y = 0
        self.animation_speed = 0.2
        
    def load_images(self):
        """Carga las imágenes de la carta. Debe ser sobrescrito por subclases."""
        if self.image_path:
            try:
                self.front_image = pygame.image.load(self.image_path).convert_alpha()
                self.front_image = pygame.transform.scale(self.front_image, self.size)
            except:
                self.front_image = self._create_default_front()
        else:
            self.front_image = self._create_default_front()
        
        self.back_image = self._create_default_back()
    
    def _create_default_front(self) -> pygame.Surface:
        """Crea una imagen por defecto para el frente de la carta."""
        surf = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (50, 50, 150), (0, 0, *self.size), border_radius=8)
        pygame.draw.rect(surf, (100, 100, 200), (5, 5, self.size[0]-10, self.size[1]-10), border_radius=5)
        
        # Texto del título
        font = pygame.font.Font(None, 20)
        text = font.render(self.title[:15], True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.size[0]//2, self.size[1]//2))
        surf.blit(text, text_rect)
        return surf
    
    def _create_default_back(self) -> pygame.Surface:
        """Crea una imagen por defecto para el reverso de la carta."""
        surf = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (30, 30, 30), (0, 0, *self.size), border_radius=8)
        pygame.draw.rect(surf, (60, 60, 60), (5, 5, self.size[0]-10, self.size[1]-10), border_radius=5)
        return surf
    
    def update(self):
        """Actualiza la posición de la carta con animación suave."""
        if abs(self.x - self.target_x) > 1:
            self.x += (self.target_x - self.x) * self.animation_speed
        else:
            self.x = self.target_x
            
        if abs(self.y - self.target_y) > 1:
            self.y += (self.target_y - self.y) * self.animation_speed
        else:
            self.y = self.target_y
        
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
    
    def set_position(self, x: int, y: int, animate: bool = True):
        """Establece la posición de la carta."""
        if animate:
            self.target_x = x
            self.target_y = y
        else:
            self.x = x
            self.y = y
            self.target_x = x
            self.target_y = y
            self.rect.x = x
            self.rect.y = y
    
    def set_position_immediate(self, x: int, y: int):
        """Establece la posición inmediatamente sin animación."""
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.rect.x = x
        self.rect.y = y
    
    def draw(self, surface: pygame.Surface):
        """Dibuja la carta en la superficie."""
        img = self.back_image if self.flipped else self.front_image
        if img:
            # Asegurar que la posición del rect esté actualizada
            self.rect.x = int(self.x)
            self.rect.y = int(self.y)
            
            # Dibujar la carta
            surface.blit(img, self.rect.topleft)
            
            # Resaltar si está seleccionada (borde dorado brillante muy visible)
            if self.selected:
                # Borde exterior grueso y brillante (dorado)
                pygame.draw.rect(surface, (255, 215, 0), self.rect, 6, border_radius=8)
                # Borde medio (amarillo brillante)
                mid_rect = pygame.Rect(self.rect.x + 3, self.rect.y + 3, 
                                      self.rect.width - 6, self.rect.height - 6)
                pygame.draw.rect(surface, (255, 255, 150), mid_rect, 3, border_radius=6)
                # Borde interior (amarillo claro)
                inner_rect = pygame.Rect(self.rect.x + 6, self.rect.y + 6, 
                                       self.rect.width - 12, self.rect.height - 12)
                pygame.draw.rect(surface, (255, 255, 200), inner_rect, 2, border_radius=4)
            
            # Sombra si está siendo arrastrada
            if self.dragging:
                shadow = pygame.Surface(self.size, pygame.SRCALPHA)
                shadow.fill((0, 0, 0, 100))
                surface.blit(shadow, (self.rect.x + 5, self.rect.y + 5))
    
    def contains_point(self, point: Tuple[int, int]) -> bool:
        """Verifica si un punto está dentro de la carta."""
        return self.rect.collidepoint(point)
    
    def flip(self):
        """Voltea la carta."""
        self.flipped = not self.flipped

