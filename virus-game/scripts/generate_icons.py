#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador de iconos para la barra inferior del juego:
- sound_on.png / sound_off.png
- new_game.png
- diary.png
- help.png
- toggle_up.png / toggle_down.png

Usa pygame para generar iconos simples y estilizados.
"""

import os
import math
import contextlib

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # type: ignore


ROOT = os.path.dirname(os.path.dirname(__file__))
ICONS_DIR = os.path.join(ROOT, 'assets', 'icons')


def ensure_dirs() -> None:
    os.makedirs(ICONS_DIR, exist_ok=True)


def draw_sound_icon(size: int, enabled: bool) -> pygame.Surface:
    """Dibuja icono de sonido (altavoz)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    color = (255, 255, 255) if enabled else (150, 150, 150)
    
    # Altavoz base (triángulo)
    points = [
        (center - size // 3, center - size // 4),
        (center - size // 3, center + size // 4),
        (center - size // 6, center + size // 6),
        (center - size // 6, center - size // 6),
    ]
    pygame.draw.polygon(surf, color, points)
    
    # Rectángulo del altavoz
    rect_w = size // 8
    rect_h = size // 3
    pygame.draw.rect(surf, color, (center - size // 6 - rect_w, center - rect_h // 2, rect_w, rect_h))
    
    # Ondas de sonido
    if enabled:
        wave_color = (*color[:3], 180)
        for i in range(1, 4):
            wave_radius = size // 4 + i * (size // 8)
            pygame.draw.arc(surf, wave_color, 
                           (center - size // 4, center - size // 4, wave_radius * 2, wave_radius * 2),
                           math.radians(45), math.radians(135), 2)
    
    return surf


def draw_new_game_icon(size: int) -> pygame.Surface:
    """Dibuja icono de nueva partida (flecha circular)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    radius = size // 3
    color = (255, 255, 255)
    
    # Círculo exterior
    pygame.draw.circle(surf, color, (center, center), radius, 2)
    
    # Flecha circular (arco con flecha)
    arrow_points = [
        (center - radius // 2, center),
        (center, center - radius // 2),
        (center + radius // 3, center),
        (center, center + radius // 2),
    ]
    pygame.draw.lines(surf, color, False, arrow_points, 2)
    
    # Punto central
    pygame.draw.circle(surf, color, (center, center), 2)
    
    return surf


def draw_diary_icon(size: int) -> pygame.Surface:
    """Dibuja icono de diario (libro abierto)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    color = (255, 255, 255)
    
    # Libro abierto (dos páginas)
    page_w = size // 3
    page_h = size // 2
    
    # Página izquierda
    pygame.draw.rect(surf, color, (center - page_w - 2, center - page_h // 2, page_w, page_h), 2)
    # Líneas de texto
    for i in range(3):
        y = center - page_h // 2 + 4 + i * 4
        pygame.draw.line(surf, (*color[:3], 150), (center - page_w, y), (center - 4, y), 1)
    
    # Página derecha
    pygame.draw.rect(surf, color, (center + 2, center - page_h // 2, page_w, page_h), 2)
    # Líneas de texto
    for i in range(3):
        y = center - page_h // 2 + 4 + i * 4
        pygame.draw.line(surf, (*color[:3], 150), (center + 4, y), (center + page_w, y), 1)
    
    return surf


def draw_help_icon(size: int) -> pygame.Surface:
    """Dibuja icono de ayuda (signo de interrogación)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    color = (255, 255, 255)
    
    # Círculo exterior
    radius = size // 3
    pygame.draw.circle(surf, color, (center, center), radius, 2)
    
    # Signo de interrogación
    font = pygame.font.Font(None, size // 2)
    text = font.render('?', True, color)
    text_x = center - text.get_width() // 2
    text_y = center - text.get_height() // 2 - 2
    surf.blit(text, (text_x, text_y))
    
    return surf


def draw_toggle_icon(size: int, up: bool) -> pygame.Surface:
    """Dibuja icono de toggle (flecha arriba/abajo)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    color = (255, 255, 255)
    
    # Flecha
    arrow_size = size // 2
    if up:
        # Flecha hacia arriba
        points = [
            (center, center - arrow_size // 2),
            (center - arrow_size // 3, center),
            (center + arrow_size // 3, center),
        ]
    else:
        # Flecha hacia abajo
        points = [
            (center, center + arrow_size // 2),
            (center - arrow_size // 3, center),
            (center + arrow_size // 3, center),
        ]
    pygame.draw.polygon(surf, color, points)
    
    return surf


def save_icons() -> None:
    """Genera y guarda todos los iconos."""
    icon_size = 64  # Tamaño base (se escalará después)
    
    icons = {
        'sound_on.png': (lambda s: draw_sound_icon(s, True)),
        'sound_off.png': (lambda s: draw_sound_icon(s, False)),
        'new_game.png': draw_new_game_icon,
        'diary.png': draw_diary_icon,
        'help.png': draw_help_icon,
        'toggle_up.png': (lambda s: draw_toggle_icon(s, True)),
        'toggle_down.png': (lambda s: draw_toggle_icon(s, False)),
    }
    
    for filename, draw_func in icons.items():
        path = os.path.join(ICONS_DIR, filename)
        if os.path.isfile(path):
            print(f"  Saltando {filename} (ya existe)")
            continue
        try:
            icon = draw_func(icon_size)
            pygame.image.save(icon, path)
            print(f"  ✓ Generado: {filename}")
        except Exception as e:
            print(f"  ✗ Error generando {filename}: {e}")


def main() -> None:
    pygame.init()
    ensure_dirs()
    print("Generando iconos para la barra inferior...")
    save_icons()
    print(f"✓ Iconos generados en {ICONS_DIR}")


if __name__ == '__main__':
    main()

