#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador de assets mínimos para Virus Game:
- Crea PNGs de cartas en assets/cards
- Crea WAVs simples en assets/sfx

No requiere GUI; usa SDL_VIDEODRIVER=dummy.
"""

import os
import math
import wave
import struct
import contextlib

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # type: ignore


ROOT = os.path.dirname(os.path.dirname(__file__))
CARDS_DIR = os.path.join(ROOT, 'assets', 'cards')
SFX_DIR = os.path.join(ROOT, 'assets', 'sfx')


def ensure_dirs() -> None:
    os.makedirs(CARDS_DIR, exist_ok=True)
    os.makedirs(SFX_DIR, exist_ok=True)


def draw_card_surface(tipo: str, color: str, size=(120, 170)) -> pygame.Surface:
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    # Paletas básicas
    if tipo == 'organo':
        base = (0, 168, 107)
    elif tipo == 'virus':
        base = (231, 76, 60)
    elif tipo == 'medicina':
        base = (30, 136, 229)
    else:
        base = (255, 152, 0)
    # Fondo
    surf.fill(base)
    pygame.draw.rect(surf, (255, 215, 0), (0, 0, w, h), 3)
    # Círculo central por color
    color_map = {
        'corazon': (230, 57, 70),
        'cerebro': (106, 153, 78),
        'huesos': (200, 200, 200),
        'estomago': (221, 161, 94),
        'multicolor': (155, 89, 182),
    }
    cc = color_map.get(color, (155, 89, 182))
    pygame.draw.circle(surf, cc, (w // 2, h // 2 - 10), 28)
    pygame.draw.circle(surf, (255, 215, 0), (w // 2, h // 2 - 10), 28, 2)
    # Etiquetas
    font_small = pygame.font.Font(None, 22)
    font_tiny = pygame.font.Font(None, 18)
    txt_tipo = font_small.render(tipo.upper(), True, (255, 255, 255))
    surf.blit(txt_tipo, (w // 2 - txt_tipo.get_width() // 2, 8))
    txt_color = font_tiny.render(color.upper(), True, (255, 255, 255))
    surf.blit(txt_color, (w // 2 - txt_color.get_width() // 2, h - 24))
    return surf


def save_card_pngs() -> None:
    tipos = ['organo', 'virus', 'medicina']
    colores = ['corazon', 'cerebro', 'huesos', 'estomago', 'multicolor']
    for t in tipos:
        for c in colores:
            path = os.path.join(CARDS_DIR, f"{t}_{c}.png")
            if os.path.isfile(path):
                continue
            surf = draw_card_surface(t, c)
            pygame.image.save(surf, path)


def tone_wav(filename: str, freq: float, dur_ms: int = 160, volume: float = 0.35, sample_rate: int = 44100) -> None:
    n_samples = int(sample_rate * dur_ms / 1000.0)
    with contextlib.closing(wave.open(filename, 'w')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            val = volume * math.sin(2 * math.pi * freq * (i / sample_rate))
            wf.writeframes(struct.pack('<h', int(val * 32767)))


def save_sfx() -> None:
    mapping = {
        'place': 660,
        'infect': 200,
        'destroy': 120,
        'cure': 520,
        'vaccinate': 740,
        'immunize': 880,
    }
    for name, freq in mapping.items():
        path = os.path.join(SFX_DIR, f"{name}.wav")
        if os.path.isfile(path):
            continue
        tone_wav(path, freq)


def main() -> None:
    pygame.init()
    ensure_dirs()
    save_card_pngs()
    save_sfx()
    print('Assets generados en assets/cards y assets/sfx')


if __name__ == '__main__':
    main()


