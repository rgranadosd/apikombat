#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API CARD GAME (Pygame-CE)
UI tipo juego con tablero, mano, slots de aspectos de API y simple IA
"""

import pygame
import random
import sys
from typing import List, Dict, Optional, Tuple
from collections import Counter
import os
import math
import json
from datetime import datetime

# Importar lógica del juego desde engine
from engine import (
    Carta, Jugador, GameEngine,
    ASPECTOS, ASPECTO_MAP, ATAQUES_SEGURIDAD, PROTECCIONES_SEGURIDAD,
    COLORS, COLOR_MAP
)

# Flag para usar motor MTG (por defecto activado)
# Para desactivar: USE_MTG_ENGINE=false python3 virus_game.py
USE_MTG_ENGINE = os.getenv('USE_MTG_ENGINE', 'true').lower() not in ('false', '0', 'no', 'off')

if USE_MTG_ENGINE:
    try:
        # Intentar importar el adaptador MTG
        api_card_game_path = os.path.join(os.path.dirname(__file__), 'api-card-game')
        mtg_engine_path = os.path.join(os.path.dirname(__file__), 'mtg-engine')
        if api_card_game_path not in sys.path:
            sys.path.insert(0, api_card_game_path)
        if mtg_engine_path not in sys.path:
            sys.path.insert(0, mtg_engine_path)
        from api.adapter import MTGAdapter
        mtg_adapter = MTGAdapter()
        print("✓ Motor MTG activado (por defecto)")
    except Exception as e:
        import traceback
        print(f"⚠ No se pudo cargar motor MTG: {e}")
        traceback.print_exc()
        print("  Usando motor actual (GameEngine)")
        USE_MTG_ENGINE = False
        mtg_adapter = None
else:
    mtg_adapter = None

pygame.init()
pygame.font.init()

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
FPS = 60

# Dimensiones estándar de cartas - TODAS usan el mismo tamaño (jugador 2)
# Tamaño base: 60% de 280×380 = 168×228, pero usando 120×163 (igual a jugador 2)
CARD_WIDTH = 120
CARD_HEIGHT = 163
# Radio base para esquinas redondeadas - se calculará dinámicamente
CARD_BORDER_RADIUS_BASE = 8  # Mantenido para compatibilidad con código existente

def get_card_border_radius(width: int, height: int) -> int:
    """Calcula el radio de borde dinámicamente basado en el tamaño de la carta.
    Usa min(width, height) / 4 para un redondeo profesional y visible.
    El radio nunca puede ser mayor que min(width, height) / 2."""
    return min(int(min(width, height) / 4), int(min(width, height) / 2))

# Radio estándar para cartas de tamaño CARD_WIDTH x CARD_HEIGHT
CARD_BORDER_RADIUS = get_card_border_radius(CARD_WIDTH, CARD_HEIGHT)

COLOR_GOLD = (255, 215, 0)
COLOR_BOARD = (13, 77, 46)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (231, 76, 60)
COLOR_GREEN = (46, 204, 113)
COLOR_BLUE = (52, 152, 219)
COLOR_ORANGE = (230, 126, 34)
COLOR_BLACK = (0, 0, 0)
# Esquema solicitado
COLOR_TEAL = (0, 168, 107)           # verde_azulado (base aspectos)
COLOR_RED_INTENSE = (220, 30, 30)     # rojo_intenso (ataque / aspecto vulnerable)
COLOR_BLUE_BRIGHT = (80, 160, 255)    # azul_brillante (protegido)
COLOR_SILVER = (192, 192, 192)        # gris_plata (fortalecido / comodín)
COLOR_YELLOW = (255, 214, 0)          # amarillo (intervenciones)

# Constantes de aspectos y cartas ahora están en engine.py
# Se importan desde engine al inicio del archivo

# === Render helpers (centralizados) ===
def apply_rounded_clip(surface: pygame.Surface) -> pygame.Surface:
    """Aplica recorte redondeado eliminando completamente las esquinas negras.
    Usa BLEND_RGBA_MIN para forzar que las esquinas queden con alfa 0."""
    if surface is None:
        return surface
    
    # Convertir a formato con alpha si no lo tiene
    if not surface.get_flags() & pygame.SRCALPHA:
        surface = surface.convert_alpha()
    else:
        surface = surface.convert_alpha()
    
    w, h = surface.get_size()
    r = get_card_border_radius(w, h)
    
    if r <= 0:
        return surface
    
    # Crear máscara con SRCALPHA y fondo totalmente transparente
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 0))
    # Dibujar rectángulo blanco redondeado (esquinas transparentes)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=r)
    
    # Aplicar máscara usando BLEND_RGBA_MIN (esquinas quedan con alfa 0)
    out = surface.copy().convert_alpha()
    out.blit(mask, (0, 0), None, pygame.BLEND_RGBA_MIN)
    return out


def blit_rounded_panel(screen: pygame.Surface, x: int, y: int, w: int, h: int,
                       bg_rgba: Tuple[int, int, int, int] = (0, 0, 0, 0),
                       border_rgba: Optional[Tuple[int, int, int, int]] = None,
                       border_px: int = 0,
                       radius: Optional[int] = None) -> None:
    """Crea y blitea un panel redondeado con fondo y borde opcionales."""
    radius_val = radius if radius is not None else get_card_border_radius(w, h)
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    if bg_rgba is not None:
        pygame.draw.rect(panel, bg_rgba, (0, 0, w, h), border_radius=radius_val)
    if border_rgba is not None and border_px > 0:
        pygame.draw.rect(panel, border_rgba, (0, 0, w, h), border_px, border_radius=radius_val)
    screen.blit(panel, (x, y))


def blit_rounded_border(screen: pygame.Surface, x: int, y: int, w: int, h: int,
                        border_rgba: Tuple[int, int, int, int], border_px: int,
                        radius: Optional[int] = None) -> None:
    """Crea y blitea solo un borde redondeado (sin fondo)."""
    blit_rounded_panel(screen, x, y, w, h, bg_rgba=(0, 0, 0, 0),
                       border_rgba=border_rgba, border_px=border_px, radius=radius)


def blit_card_clean(screen: pygame.Surface, surface: pygame.Surface, x: int, y: int) -> None:
    """Blitea una carta garantizando que esté completamente limpia y recortada.
    FORZA la limpieza de fondo negro Y el recorte incluso si ya fue aplicado anteriormente."""
    if surface is None:
        return
    # Asegurar que tiene SRCALPHA
    if not surface.get_flags() & pygame.SRCALPHA:
        surface = surface.convert_alpha()
    else:
        surface = surface.convert_alpha()
    
    # PRIMERO: Eliminar cualquier fondo negro u oscuro (RGB < 40)
    w, h = surface.get_size()
    cleaned = pygame.Surface((w, h), pygame.SRCALPHA)
    cleaned.fill((0, 0, 0, 0))
    for px in range(w):
        for py in range(h):
            try:
                pixel = surface.get_at((px, py))
                r, g, b, a = pixel
                # Si es muy oscuro (negro), hacerlo transparente
                if r < 40 and g < 40 and b < 40 and a > 200:
                    cleaned.set_at((px, py), (0, 0, 0, 0))
                else:
                    cleaned.set_at((px, py), pixel)
            except:
                cleaned.set_at((px, py), (0, 0, 0, 0))
    
    # SEGUNDO: FORZAR recorte redondeado (elimina cualquier artefacto en las esquinas)
    cleaned = apply_rounded_clip(cleaned)
    # Blitear
    screen.blit(cleaned, (x, y))


# Clases Carta y Jugador ahora están en engine.py
# Se importan desde engine al inicio del archivo

class VirusGame(GameEngine):
    def __init__(self, headless: bool = False):
        # Inicializar el engine (sin renderizado)
        super().__init__(trace_enabled=False)
        self.headless = headless
        self.screen = None
        self.clock = pygame.time.Clock()
        if not headless:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.display.set_caption('API Card Game')
        
        self.nivel_ia = 'facil'
        
        # Inicializar adaptador MTG si está activo
        self.use_mtg_engine = USE_MTG_ENGINE and mtg_adapter is not None
        if self.use_mtg_engine:
            self.mtg_adapter = mtg_adapter
        else:
            self.mtg_adapter = None
        
        # Fuentes: cargar TTF si existe; fallback seguro
        font_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'Inter-SemiBold.ttf')
        def load_font(size: int) -> pygame.font.Font:
            if os.path.isfile(font_path):
                try:
                    return pygame.font.Font(font_path, size)
                except Exception:
                    pass
            return pygame.font.Font(None, size)
        self.font_large = load_font(32)
        self.font_medium = load_font(24)
        self.font_small = load_font(18)
        self.font_tiny = load_font(14)
        
        # Fuente Orbitron para "Player 1" y "Player 2"
        orbitron_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'Orbitron.ttf')
        def load_orbitron_font(size: int) -> pygame.font.Font:
            if os.path.isfile(orbitron_path):
                try:
                    return pygame.font.Font(orbitron_path, size)
                except Exception as e:
                    print(f"[DEBUG] Error cargando Orbitron.ttf: {e}")
                    return load_font(size)  # Fallback a fuente por defecto
            else:
                print(f"[DEBUG] No se encontró Orbitron.ttf en: {orbitron_path}")
                return load_font(size)  # Fallback a fuente por defecto
        self.font_orbitron = load_orbitron_font(24)
        
        self.carta_arrastrando: Optional[Tuple[Carta, int, int]] = None
        self.cartas_multi_drag: List[int] = []  # índices de cartas en drag múltiple
        self.fly_anim = None  # {'card': Carta, 'x':float,'y':float,'sx':int,'sy':int,'ex':int,'ey':int,'t':int,'steps':int,'angle':float,'on_done':callable}
        self.card_animations: List[Dict] = []  # Animaciones de cartas (escala, fade, etc.)
        self._draw_queue: List[Tuple[Carta, Tuple[int, int], Tuple[int, int]]] = []
        self.is_dragging: bool = False
        # Autoplay IA vs IA y trazas
        self.autoplay: bool = False  # Desactivado por defecto para permitir juego manual
        # trace_enabled ya está en GameEngine
        self.last_auto_ms: int = 0
        self.hover_hand_idx: Optional[int] = None
        self.fx_active = {}
        self.particles: List[Dict] = []  # {'x','y','vx','vy','life','color','size'}
        self.tweens: List[Dict] = []     # {'t':0,'dur':N,'update':callable,'on_done':callable}
        self.selected_hand_idx: Optional[int] = None
        self.status_msg: str = ''
        self.discard_selection: List[int] = []  # índices seleccionados para descartar
        self.post_discard_waiting: bool = False  # tras descartar, solo permitir Pasar Turno
        self.jugada_idx: int = 1
        self.stalled_steps: int = 0
        self.blocked: bool = False
        self.game_over: bool = False  # Flag para detener el juego cuando hay victoria
        self.winner: Optional[str] = None  # Ganador de la partida

        # Assets
        self.assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        self.cards_dir = os.path.join(self.assets_dir, 'cards')
        self.sfx_dir = os.path.join(self.assets_dir, 'sfx')
        # trace_file_path y diario_path ya están en GameEngine
        
        # El diario ya se limpia en GameEngine.__init__
        
        self.card_images: Dict[str, pygame.Surface] = {}
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.card_back: Optional[pygame.Surface] = None
        # Assets de jugadores (genéricos: uno para humanos, uno para bots)
        self.player_image: Optional[pygame.Surface] = None  # Imagen para jugadores humanos
        self.bot_image: Optional[pygame.Surface] = None     # Imagen para bots
        self.player_avatar_generated: Optional[pygame.Surface] = None  # Avatar generado para humanos
        self.bot_avatar_generated: Optional[pygame.Surface] = None      # Avatar generado para bots
        # Iconos de la barra inferior (definir antes de _load_assets)
        self.icons_dir = os.path.join(self.assets_dir, 'icons')
        self.icon_sound_on: Optional[pygame.Surface] = None
        self.icon_sound_off: Optional[pygame.Surface] = None
        self.icon_new_game: Optional[pygame.Surface] = None
        self.icon_diary: Optional[pygame.Surface] = None
        self.icon_help: Optional[pygame.Surface] = None
        self.icon_toggle_up: Optional[pygame.Surface] = None
        self.icon_toggle_down: Optional[pygame.Surface] = None
        self._load_assets()

        # Sonido
        self.sound_enabled: bool = True

        # Fondo cacheado (textura tapiz)
        self.bg_surface: Optional[pygame.Surface] = None
        self.last_action_detail: str = ''
        self.hover_help_text: str = ''
        self.hover_help_pos: Optional[Tuple[int, int]] = None
        # Diario en pantalla: lista de (texto, color)
        self.diario_lines: List[Tuple[str, Tuple[int, int, int]]] = []
        self.diario_scroll: int = 0  # 0 = al final (últimas líneas)
        self.diario_max_lines_mem: int = 1000
        self.diario_open: bool = False  # Estado: cerrado por defecto
        self.diario_icon_rect: Optional[pygame.Rect] = None  # Rectángulo del icono del diario
        self.diario_close_rect: Optional[pygame.Rect] = None  # Rectángulo del botón X
        
        # Ayuda: mismo comportamiento que el diario
        self.ayuda_open: bool = False  # Estado: cerrado por defecto
        self.ayuda_icon_rect: Optional[pygame.Rect] = None  # Rectángulo del icono de ayuda
        self.ayuda_close_rect: Optional[pygame.Rect] = None  # Rectángulo del botón X

        # Barra inferior collapsable
        self.bottom_bar_collapsed: bool = False  # Estado: expandida por defecto
        self.bottom_bar_toggle_rect: Optional[pygame.Rect] = None  # Rectángulo del botón toggle

        # Mapeo de imágenes para slots (aspectos en tablero) por estado
        self.slot_image_cache: Dict[Tuple[str, str, Tuple[int, int]], Optional[pygame.Surface]] = {}

        # Theme (opcional) cargado desde assets/theme.json
        self.theme: Dict = {}

    # ---------- Sistema de animaciones mejorado (similar a Phaser) ----------
    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        """Easing suave: empieza rápido y termina lento"""
        return 1 - (1 - t) ** 3
    
    @staticmethod
    def _ease_in_out_cubic(t: float) -> float:
        """Easing suave: empieza lento, acelera, termina lento"""
        return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    
    @staticmethod
    def _ease_out_back(t: float) -> float:
        """Easing con rebote sutil al final"""
        c1, c2 = 1.70158, 2.70158
        return 1 + c2 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
    
    @staticmethod
    def _ease_out_elastic(t: float) -> float:
        """Easing elástico (rebote)"""
        c4 = (2 * math.pi) / 3
        return 0 if t == 0 else (1 if t == 1 else pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1)
    
    def _add_tween(self, dur: int, update_cb, on_done=None, easing='out_cubic') -> None:
        """Añade un tween con función de easing opcional"""
        easing_func = {
            'linear': lambda t: t,
            'out_cubic': self._ease_out_cubic,
            'in_out_cubic': self._ease_in_out_cubic,
            'out_back': self._ease_out_back,
            'out_elastic': self._ease_out_elastic,
        }.get(easing, self._ease_out_cubic)
        
        self.tweens.append({
            't': 0, 
            'dur': max(1, dur), 
            'update': update_cb, 
            'on_done': on_done,
            'easing': easing_func
        })

    def _tick_tweens(self) -> None:
        """Actualiza todos los tweens activos con easing aplicado"""
        if not self.tweens:
            return
        remaining = []
        for tw in self.tweens:
            tw['t'] += 1
            p = min(1.0, tw['t'] / float(tw['dur']))
            # Aplicar función de easing
            eased_p = tw.get('easing', lambda t: t)(p)
            try:
                tw['update'](eased_p)
            except Exception:
                pass
            if p < 1.0:
                remaining.append(tw)
            else:
                cb = tw.get('on_done')
                if cb:
                    try:
                        cb()
                    except Exception:
                        pass
        self.tweens = remaining

    def _emit_particles(self, x: int, y: int, color: Tuple[int, int, int], count: int = 12) -> None:
        for _ in range(count):
            ang = random.random() * 6.283
            speed = 1.5 + random.random() * 2.5
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            self.particles.append({'x': x, 'y': y, 'vx': vx, 'vy': vy, 'life': 30, 'color': color, 'size': 3})

    def _tick_particles(self) -> None:
        if not self.particles:
            return
        alive = []
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.04
            p['life'] -= 1
            if p['life'] > 0:
                alive.append(p)
        self.particles = alive

    # Métodos de lógica del juego ahora están en GameEngine (engine.py)
    # Se sobrescriben solo los que necesitan funcionalidad adicional (UI/efectos)
    
    def iniciar_partida(self):
        """Sobrescribe el método del engine para agregar limpieza de UI."""
        # Llamar al método del engine para la lógica base
        super().iniciar_partida()
        
        # Inicializar motor MTG si está activo
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                self.mtg_adapter.initialize(self.mazo)
                # Sincronizar estado inicial
                for i, jugador in enumerate(self.jugadores):
                    mtg_player = self.mtg_adapter.mtg_game.players_list[i]
                    self.mtg_adapter.sync_aspectos_to_mtg(jugador, mtg_player)
                    self.mtg_adapter.sync_mano_to_mtg(jugador, mtg_player)
            except Exception as e:
                print(f"⚠ Error inicializando motor MTG: {e}")
                self.use_mtg_engine = False
        
        # Limpiar UI específica de renderizado
        self.diario_lines = []
        self.diario_scroll = 0
        # CRÍTICO: Limpiar caché de imágenes para regenerar con el método correcto de recorte
        self.slot_image_cache.clear()
        # IMPORTANTE: Desactivar autoplay al iniciar nueva partida (modo manual por defecto)
        self.autoplay = False
    
    def jugar_carta(self, jugador: Jugador, carta: Carta) -> bool:
        # Si está activo el motor MTG, sincronizar estado antes de jugar
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                mtg_player = self.mtg_adapter.get_mtg_player(jugador)
                if mtg_player:
                    self.mtg_adapter.sync_aspectos_to_mtg(jugador, mtg_player)
            except Exception as e:
                print(f"⚠ Error sincronizando con motor MTG: {e}")
        
        # Jugar carta con motor actual (GameEngine)
        # TODO: Cuando el motor MTG tenga las habilidades implementadas, jugar aquí
        
        # Motor actual (GameEngine)
        # Management (antes intervenciones/tratamientos)
        if carta.tipo in ('management', 'intervencion'):
            return self._jugar_intervencion(jugador, carta)
        # Compatibilidad: mantener tratamiento para código legacy
        if carta.tipo == 'tratamiento':
            return self._jugar_intervencion(jugador, carta)
        # Fundamentals (antes aspectos/órganos)
        if carta.tipo in ('fundamental', 'aspecto', 'organo'):
            # Verificar límite de aspectos
            if len(jugador.aspectos) >= 4:
                self.last_action_detail = f"ERROR: Ya tienes 4 aspectos (máximo permitido)"
                return False
            # Resolver color específico si es multicolor
            color_final = carta.color
            if carta.color == 'multicolor':
                color_resuelto = self._resolver_destino_color(jugador, carta)
                if color_resuelto is None:
                    self.last_action_detail = f"ERROR: Ya tienes todos los aspectos disponibles (4/4)"
                    return False  # No hay slot disponible
                color_final = color_resuelto
            # Verificar que no exista ya ese aspecto
            if color_final in jugador.aspectos:
                asp_existente = jugador.aspectos[color_final]
                estado = "vulnerable" if asp_existente.get('vulnerable', False) else "saludable"
                protecciones = asp_existente.get('protecciones', 0)
                estado_prot = f", {protecciones} protección(es)" if protecciones > 0 else ""
                self.last_action_detail = f"ERROR: Ya tienes el aspecto {ASPECTO_MAP[color_final]['label']} ({estado}{estado_prot})"
                return False
            jugador.aspectos[color_final] = {'vulnerable': False, 'protecciones': 0}
            self._trigger_fx(color_final, 'place')
            self._play_sfx('place')
            self.last_action_detail = f"coloca aspecto {ASPECTO_MAP[color_final]['label']}"
            return True
        # Hacks (antes ataques/problemas/virus)
        if carta.tipo in ('hack', 'ataque', 'problema', 'virus'):
            objetivo = self._opponent_of(jugador)
            # Verificar si el objetivo tiene escudo (code freeze) activo
            if objetivo.treatment_shield:
                objetivo.treatment_shield = False
                self.last_action_detail = f"ATAQUE bloqueado - CODE FREEZE de {objetivo.nombre} anula el ataque"
                # Registrar en diario que el escudo se consumió
                try:
                    self._diario(f"    [INFO] 🛡️ Code Freeze de [{objetivo.nombre}] consumido - bloqueó un ataque.")
                except Exception:
                    pass
                return True
            # Resolver color específico si es multicolor
            color_final = carta.color
            if carta.color == 'multicolor':
                color_resuelto = self._resolver_destino_color(objetivo, carta)
                if color_resuelto is None:
                    return False  # No hay aspecto objetivo disponible
                color_final = color_resuelto
            if color_final not in objetivo.aspectos:
                return False
            asp = objetivo.aspectos[color_final]
            # Cualquier protección (>= 1) protege contra ataques/problemas
            if asp.get('protecciones', 0) >= 1:
                self.last_action_detail = f"ATACA a {objetivo.nombre}: bloqueado - {ASPECTO_MAP[color_final]['label']} protegido"
                return False
            if asp.get('vulnerable', False):
                del objetivo.aspectos[color_final]
                self._trigger_fx(color_final, 'destroy')
                self._play_sfx('destroy')
                self.last_action_detail = f"ATACA a {objetivo.nombre}: destruye aspecto {ASPECTO_MAP[color_final]['label']} (ya estaba vulnerable)"
            else:
                asp['vulnerable'] = True
                self._trigger_fx(color_final, 'infect')
                self._play_sfx('infect')
                self.last_action_detail = f"ATACA a {objetivo.nombre}: vulnera aspecto {ASPECTO_MAP[color_final]['label']}"
            return True
        # Shields (antes protecciones/medicina)
        if carta.tipo in ('shield', 'proteccion', 'medicina'):
            # Resolver color específico si es multicolor
            color_final = carta.color
            if carta.color == 'multicolor':
                color_resuelto = self._resolver_destino_color(jugador, carta)
                if color_resuelto is None:
                    return False  # No hay aspecto objetivo disponible
                color_final = color_resuelto
            if color_final not in jugador.aspectos:
                return False
            asp = jugador.aspectos[color_final]
            # Cura vulnerabilidades si está vulnerable
            if asp.get('vulnerable', False):
                asp['vulnerable'] = False
                self._trigger_fx(color_final, 'cure')
                self._play_sfx('cure')
                self.last_action_detail = f"DEFIENDE: cura vulnerabilidad en {ASPECTO_MAP[color_final]['label']}"
            pre = asp.get('protecciones', 0)
            asp['protecciones'] = min(2, asp.get('protecciones', 0) + 1)
            if asp['protecciones'] >= 2 and pre < 2:
                self._trigger_fx(color_final, 'immunize')
                self._play_sfx('immunize')
                self.last_action_detail = f"DEFIENDE: fortalece aspecto {ASPECTO_MAP[color_final]['label']}"
            elif asp['protecciones'] >= 1 and pre < 1:
                self._trigger_fx(color_final, 'vaccinate')
                self._play_sfx('vaccinate')
                self.last_action_detail = f"DEFIENDE: protege aspecto {ASPECTO_MAP[color_final]['label']}"
            elif not self.last_action_detail:
                self.last_action_detail = f"DEFIENDE: refuerza protección en {ASPECTO_MAP[color_final]['label']}"
            
            # Sincronizar estado con motor MTG después de jugar
            if self.use_mtg_engine and self.mtg_adapter:
                try:
                    mtg_player = self.mtg_adapter.get_mtg_player(jugador)
                    if mtg_player:
                        self.mtg_adapter.sync_aspectos_from_mtg(mtg_player, jugador)
                except Exception as e:
                    print(f"⚠ Error sincronizando desde motor MTG: {e}")
            
            return True
        return False

    def _jugar_intervencion(self, jugador: Jugador, carta: Carta, target_color: Optional[str] = None) -> bool:
        """Juega una intervención (antes tratamiento)."""
        return self._jugar_tratamiento(jugador, carta, target_color)
    
    def _jugar_tratamiento(self, jugador: Jugador, carta: Carta, target_color: Optional[str] = None) -> bool:
        """Función legacy - usa _jugar_intervencion."""
        objetivo = self._opponent_of(jugador)
        # Si el rival tiene guante y este tratamiento le afectaría, consumir y anular
        def consumes_shield_if_affects(target: Jugador) -> bool:
            if target.treatment_shield:
                target.treatment_shield = False
                self.last_action_detail = f"TRATAMIENTO anulado por GUANTE de {target.nombre}"
                # Registrar en diario que el escudo se consumió
                try:
                    self._diario(f"    [INFO] 🛡️ Escudo de [{target.nombre}] consumido - bloqueó un tratamiento.")
                except Exception:
                    pass
                return True
            return False

        subtipo = carta.color
        # Compatibilidad: mantener nombres antiguos
        if subtipo == 'ladrón' or subtipo == 'migracion':
            if consumes_shield_if_affects(objetivo):
                return True
            # Si el usuario indicó un color objetivo, validar ese color
            if target_color is not None:
                if target_color not in objetivo.aspectos:
                    # El rival no tiene ese aspecto
                    self.last_action_detail = f"ERROR: {objetivo.nombre} no tiene el aspecto {ASPECTO_MAP[target_color]['label']}"
                    try:
                        self._diario(f"    [ERROR] MIGRACIÓN falla: {objetivo.nombre} no tiene {ASPECTO_MAP[target_color]['label']}")
                    except Exception:
                        pass
                    return False
                if target_color in jugador.aspectos:
                    # Ya tienes ese aspecto, no puedes robarlo
                    self.last_action_detail = f"ERROR: Ya tienes el aspecto {ASPECTO_MAP[target_color]['label']}, no puedes robarlo"
                    try:
                        self._diario(f"    [ERROR] MIGRACIÓN falla: Ya tienes {ASPECTO_MAP[target_color]['label']}, solo puedes robar aspectos que no tienes")
                    except Exception:
                        pass
                    return False
                if target_color in objetivo.aspectos and target_color not in jugador.aspectos:
                    # Copiar el estado completo del aspecto (no solo la referencia)
                    jugador.aspectos[target_color] = {
                        'vulnerable': objetivo.aspectos[target_color].get('vulnerable', False),
                        'protecciones': objetivo.aspectos[target_color].get('protecciones', 0)
                    }
                    del objetivo.aspectos[target_color]
                    self.last_action_detail = f"roba aspecto {ASPECTO_MAP[target_color]['label']} a {objetivo.nombre}"
                    self._trigger_fx(target_color, 'place')
                    return True
                return False
            # robar el primer aspecto que no tengas
            for color, data in list(objetivo.aspectos.items()):
                if color not in jugador.aspectos:
                    # Copiar el estado completo del aspecto (no solo la referencia)
                    jugador.aspectos[color] = {
                        'vulnerable': data.get('vulnerable', False),
                        'protecciones': data.get('protecciones', 0)
                    }
                    del objetivo.aspectos[color]
                    self.last_action_detail = f"roba aspecto {ASPECTO_MAP[color]['label']} a {objetivo.nombre}"
                    self._trigger_fx(color, 'place')
                    return True
            return False
        if subtipo == 'trasplante' or subtipo == 'refactoring':
            if consumes_shield_if_affects(objetivo):
                return True
            if not jugador.aspectos or not objetivo.aspectos:
                return False
            # Si se especificó un target_color, intercambiar ese aspecto del oponente
            if target_color is not None:
                # Validar que el oponente tiene ese aspecto
                if target_color not in objetivo.aspectos:
                    self.last_action_detail = f"ERROR: {objetivo.nombre} no tiene el aspecto {ASPECTO_MAP[target_color]['label']}"
                    return False
                # Buscar un aspecto tuyo diferente para intercambiar
                color_tuyo = None
                for c in jugador.aspectos.keys():
                    if c != target_color:  # No intercambiar el mismo aspecto
                        color_tuyo = c
                        break
                if color_tuyo is None:
                    # Si solo tienes aspectos del mismo tipo, usar el primero
                    color_tuyo = next(iter(jugador.aspectos.keys()))
                # Si el intercambio es del mismo aspecto (mismo color), no hacer nada
                if color_tuyo == target_color:
                    self.last_action_detail = f"REFACTORING sin efecto: ambos seleccionan {ASPECTO_MAP[target_color]['label']}"
                    return True
                # Realizar intercambio
                temp = jugador.aspectos[color_tuyo].copy()
                jugador.aspectos[target_color] = objetivo.aspectos[target_color].copy()
                del objetivo.aspectos[target_color]
                objetivo.aspectos[color_tuyo] = temp
                del jugador.aspectos[color_tuyo]
                self.last_action_detail = f"intercambia {ASPECTO_MAP[color_tuyo]['label']} ↔ {ASPECTO_MAP[target_color]['label']} con {objetivo.nombre}"
                return True
            # Sin target_color: elegir intercambio simple (comportamiento antiguo)
            color_a = next(iter(jugador.aspectos.keys()))
            color_b = next(iter(objetivo.aspectos.keys()))
            # Si son el mismo aspecto, no hacer nada para evitar pérdida por borrado
            if color_a == color_b:
                self.last_action_detail = f"REFACTORING sin efecto: ambos tienen {ASPECTO_MAP[color_a]['label']}"
                return True
            if color_b in jugador.aspectos and color_a in objetivo.aspectos:
                # evitar duplicados sin cambio real
                pass
            temp = jugador.aspectos[color_a].copy()
            jugador.aspectos[color_b] = objetivo.aspectos[color_b].copy()
            del objetivo.aspectos[color_b]
            objetivo.aspectos[color_a] = temp
            del jugador.aspectos[color_a]
            self.last_action_detail = f"intercambia {ASPECTO_MAP[color_a]['label']} ↔ {ASPECTO_MAP[color_b]['label']} con {objetivo.nombre}"
            return True
        if subtipo == 'contagio' or subtipo == 'activo_activo':
            if consumes_shield_if_affects(objetivo):
                return True
            # Vulnerar un aspecto del rival que exista y no esté fortalecido
            for color, asp_mio in jugador.aspectos.items():
                if asp_mio.get('vulnerable', False) and color in objetivo.aspectos:
                    asp_rival = objetivo.aspectos[color]
                    if asp_rival.get('protecciones', 0) < 2 and not asp_rival.get('vulnerable', False):
                        asp_rival['vulnerable'] = True
                        self._trigger_fx(color, 'infect')
                        self.last_action_detail = f"Activo-Activo: vulnera {ASPECTO_MAP[color]['label']} de {objetivo.nombre}"
                        return True
            return False
        if subtipo == 'guante' or subtipo == 'code_freeze':
            jugador.treatment_shield = True
            self.last_action_detail = "activa CODE FREEZE: anula el próximo ataque o intervención en tu contra"
            return True
        if subtipo == 'error' or subtipo == 'rollback':
            # quitar una protección del rival si tiene
            for color, asp in objetivo.aspectos.items():
                if asp.get('protecciones', 0) > 0:
                    asp['protecciones'] -= 1
                    self.last_action_detail = f"Rollback: reduce protección en {ASPECTO_MAP[color]['label']} de {objetivo.nombre}"
                    self._trigger_fx(color, 'destroy')
                    return True
            return False
        return False
    
    def es_jugable(self, carta: Carta, jugador: Jugador) -> Tuple[bool, str]:
        # Si está activo el motor MTG, intentar usarlo primero
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                mtg_player = self.mtg_adapter.get_mtg_player(jugador)
                if mtg_player:
                    self.mtg_adapter.sync_aspectos_to_mtg(jugador, mtg_player)
                    ok, msg = self.mtg_adapter.es_jugable_mtg(carta, jugador)
                    if ok or msg:  # Si retorna algo útil, usarlo
                        return ok, msg
            except Exception as e:
                print(f"⚠ Error en motor MTG, usando motor actual: {e}")
                # Continuar con motor actual si falla
        
        # Motor actual (GameEngine)
        # Management (antes intervenciones/tratamientos)
        if carta.tipo in ('management', 'intervencion', 'tratamiento'):
            subt = carta.color
            rival = self._opponent_of(jugador)
            if subt == 'ladrón' or subt == 'migracion':
                # puedes jugar si el rival tiene algún aspecto que tú no tengas
                for color in rival.aspectos.keys():
                    if color not in jugador.aspectos:
                        return True, ''
                return False, 'El rival no tiene aspectos que puedas robar'
            if subt == 'trasplante' or subt == 'refactoring':
                if jugador.aspectos and rival.aspectos:
                    return True, ''
                return False, 'Ambos deben tener al menos un aspecto'
            if subt in ('contagio', 'activo_activo', 'mirroring'):
                # Verificar si tienes algún aspecto vulnerable
                tiene_vulnerable = False
                aspectos_vulnerables = []
                aspectos_compatibles = []
                for color, asp in jugador.aspectos.items():
                    if asp.get('vulnerable', False):
                        tiene_vulnerable = True
                        aspectos_vulnerables.append(color)
                        # Verificar si el rival tiene el mismo aspecto
                        if color in rival.aspectos:
                            asp_rival = rival.aspectos[color]
                            # Verificar condiciones: no fortalecido (2 protecciones) y no ya vulnerable
                            if asp_rival.get('protecciones', 0) >= 2:
                                aspectos_compatibles.append(f"{ASPECTO_MAP[color]['label']} (fortalecido)")
                                continue  # Está fortalecido, probar con otro aspecto
                            if asp_rival.get('vulnerable', False):
                                aspectos_compatibles.append(f"{ASPECTO_MAP[color]['label']} (ya vulnerable)")
                                continue  # Ya está vulnerable, probar con otro aspecto
                        return True, ''
                if not tiene_vulnerable:
                    return False, 'Necesitas tener al menos un aspecto vulnerable'
                # Construir mensaje descriptivo
                if aspectos_compatibles:
                    aspectos_str = ", ".join([ASPECTO_MAP[o]['label'] for o in aspectos_vulnerables])
                    return False, f'Aspectos vulnerables: {aspectos_str}. El rival no tiene aspectos compatibles: {", ".join(aspectos_compatibles)}'
                # El rival no tiene los mismos aspectos que tú tienes vulnerables
                aspectos_str = ", ".join([ASPECTO_MAP[o]['label'] for o in aspectos_vulnerables])
                return False, f'Tienes {aspectos_str} vulnerable(s), pero el rival NO tiene esos aspectos. Activo-Activo requiere que el rival tenga el mismo aspecto.'
            if subt == 'guante' or subt == 'code_freeze':
                return True, ''
            if subt == 'error' or subt == 'rollback':
                for asp in rival.aspectos.values():
                    if asp.get('protecciones', 0) > 0:
                        return True, ''
                return False, 'El rival no tiene protecciones para eliminar'
            return False, 'Intervención desconocida'
        # Fundamentals (antes aspectos/órganos)
        if carta.tipo in ('fundamental', 'aspecto', 'organo'):
            if carta.color == 'multicolor':
                # Aspecto multicolor: puedes colocarlo si hay al menos un slot libre
                if len(jugador.aspectos) < 4:
                    return True, ''
                return False, 'Ya tienes 4 aspectos'
            if carta.color in jugador.aspectos:
                return False, f'Ya tienes el aspecto {ASPECTO_MAP[carta.color]["label"]}'
            return True, ''
        # Hacks (antes ataques/problemas/virus)
        if carta.tipo in ('hack', 'ataque', 'problema', 'virus'):
            objetivo = self._opponent_of(jugador)
            if carta.color == 'multicolor':
                # Ataque/Problema multicolor: puedes atacar cualquier aspecto del rival
                for color, asp in objetivo.aspectos.items():
                    if asp.get('protecciones', 0) < 1:  # Sin protección
                        return True, ''
                if objetivo.aspectos:
                    return False, 'Todos los aspectos del rival están protegidos'
                return False, 'El rival no tiene aspectos'
            if carta.color not in objetivo.aspectos:
                return False, f'El rival no tiene el aspecto {ASPECTO_MAP[carta.color]["label"]}'
            asp = objetivo.aspectos[carta.color]
            if asp.get('protecciones', 0) >= 1:
                return False, f'Aspecto {ASPECTO_MAP[carta.color]["label"]} protegido'
            return True, ''
        # Protecciones (antes medicina)
        if carta.tipo == 'proteccion' or carta.tipo == 'medicina':
            if carta.color == 'multicolor':
                # Protección multicolor: puedes defender cualquier aspecto tuyo
                if jugador.aspectos:
                    return True, ''
                return False, 'No tienes aspectos'
            if carta.color not in jugador.aspectos:
                return False, f'No tienes el aspecto {ASPECTO_MAP[carta.color]["label"]}'
            return True, ''
        return True, ''
    
    # FUNCIÓN OBSOLETA: jugar_ia() ya no se usa
    # Ahora usamos _auto_play_current_turn() que maneja ambos jugadores en modo autoplay
    
    def comprobar_victoria(self) -> Optional[str]:
        """Sobrescribe para usar motor MTG si está activo."""
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                winner = self.mtg_adapter.comprobar_victoria_mtg()
                if winner:
                    return winner
            except Exception as e:
                print(f"⚠ Error en motor MTG, usando motor actual: {e}")
        # Motor actual (GameEngine)
        return super().comprobar_victoria()
    
    def siguiente_turno(self):
        """Sobrescribe el método del engine para agregar reset de UI y modo en diario."""
        # resetear estado de post-descartar
        self.post_discard_waiting = False
        prev = self.jugadores[self.turno]
        
        # Sincronizar estado con motor MTG antes de cambiar turno
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                for i, jugador in enumerate(self.jugadores):
                    mtg_player = self.mtg_adapter.mtg_game.players_list[i]
                    self.mtg_adapter.sync_aspectos_to_mtg(jugador, mtg_player)
                    self.mtg_adapter.sync_mano_to_mtg(jugador, mtg_player)
            except Exception as e:
                print(f"⚠ Error sincronizando con motor MTG: {e}")
        
        # Llamar al método del engine para la lógica base
        super().siguiente_turno()
        
        # Sincronizar estado desde motor MTG después de cambiar turno
        if self.use_mtg_engine and self.mtg_adapter:
            try:
                for i, jugador in enumerate(self.jugadores):
                    mtg_player = self.mtg_adapter.mtg_game.players_list[i]
                    self.mtg_adapter.sync_aspectos_from_mtg(mtg_player, jugador)
                    self.mtg_adapter.sync_mano_from_mtg(mtg_player, jugador)
            except Exception as e:
                print(f"⚠ Error sincronizando desde motor MTG: {e}")
        
        # Agregar información de modo al diario
        jugador = self.jugadores[self.turno]
        try:
            modo = "AUTO" if self.autoplay else "MANUAL"
            # Actualizar última línea del diario con modo (si existe)
            if self.diario_lines and len(self.diario_lines) > 0:
                last_msg = self.diario_lines[-2][0] if len(self.diario_lines) >= 2 else ""
                if f"[{prev.nombre}] → Fin jugada" in last_msg and modo not in last_msg:
                    # Reemplazar última línea con modo
                    self.diario_lines[-2] = (f"   [{prev.nombre}] → Fin jugada {self.jugada_idx-1}. Turno de [{jugador.nombre}] ({modo})", self.diario_lines[-2][1])
        except Exception:
            pass
    
    # _trace está en GameEngine (engine.py), se puede usar directamente

    def _diario(self, message: str) -> None:
        """Sobrescribe el método del engine para agregar renderizado en pantalla."""
        # Llamar al método del engine para escribir en archivo
        super()._diario(message)
        # Memoria en pantalla (renderizado)
        try:
            color = COLOR_WHITE
            has_tu = 'TÚ' in message
            has_ia = 'IA' in message
            if has_tu and not has_ia:
                color = COLOR_GREEN
            elif has_ia and not has_tu:
                color = COLOR_BLUE
            if message.startswith('Fin jugada'):
                color = COLOR_RED
            if 'Partida iniciada' in message:
                color = COLOR_GOLD
            self.diario_lines.append((message, color))
            # Línea en blanco tras cada entrada solo en el panel
            self.diario_lines.append(("", COLOR_WHITE))
            # Dos saltos tras "Partida iniciada" en el panel
            if 'Partida iniciada' in message:
                self.diario_lines.append(("", COLOR_WHITE))
            if len(self.diario_lines) > self.diario_max_lines_mem:
                self.diario_lines = self.diario_lines[-self.diario_max_lines_mem:]
        except Exception:
            pass

    def _auto_play_current_turn(self) -> None:
        # No jugar si el juego ya terminó
        if self.game_over or self.blocked:
            return
        # Automatiza la jugada del jugador en turno (ambos bandos)
        jugador = self.jugadores[self.turno]
        
        # Intentar jugar una carta válida priorizando tipo
        prioridad = {'organo': 0, 'medicina': 1, 'virus': 2}
        jugadas: List[Tuple[int, Carta]] = []
        for idx, carta in enumerate(jugador.mano):
            ok, _ = self.es_jugable(carta, jugador)
            if ok:
                jugadas.append((idx, carta))
        if jugadas:
            jugadas.sort(key=lambda t: prioridad.get(t[1].tipo, 99))
            idx, carta = jugadas[0]
            self._trace(f"[AUTO] {jugador.nombre} juega {carta.tipo}:{carta.color}")
            
            # Calcular posiciones para animación de vuelo
            if jugador.nombre == 'IA':
                # Carta de la IA: empieza desde su mano (arriba)
                start_x = WINDOW_WIDTH // 2 - 20
                start_y = 90
                start = (start_x, start_y)
            else:
                # Carta del jugador: desde su mano
                start = self._hand_card_center(idx)
            
            # Calcular destino según tipo de carta
            end = self._calcular_destino_carta(jugador, carta)
            
            # Animar el vuelo de la carta
            self._start_fly_animation(carta, start, end, lambda: self._commit_play(jugador, carta))
            # Resetear contador de turnos sin jugadas
            self.stalled_steps = 0
            return

        # Si no hay jugables: descartar 1-3 y pasar
        if len(jugador.mano) > 0:
            # Incrementar contador de turnos sin jugadas
            self.stalled_steps += 1
            
            # DETECCIÓN DE BLOQUEO: Si han pasado 50 turnos sin jugadas, la partida está bloqueada
            if self.stalled_steps >= 50:
                self._diario(f"\n⚠️ PARTIDA BLOQUEADA - {self.stalled_steps} turnos consecutivos sin jugadas válidas.")
                self._diario(f"Estado final: [TÚ] {self.jugadores[0].aspectos_saludables()} aspectos saludables, [IA] {self.jugadores[1].aspectos_saludables()} aspectos saludables.\n")
                self.blocked = True
                self.autoplay = False
                self.status_msg = f'Partida bloqueada ({self.stalled_steps} turnos sin jugadas).'
                return
            
            n = min(3, len(jugador.mano))
            n = random.randint(1, n)
            indices = random.sample(range(len(jugador.mano)), n)
            self._trace(f"[AUTO] {jugador.nombre} descarta {len(indices)} (stalled: {self.stalled_steps})")
            self._perform_discard_indices(jugador, indices, auto_pass=True)
        else:
            if not self.mazo:
                # Bloqueo: mazo vacío y mano vacía
                self._diario(f"\n⚠️ PARTIDA BLOQUEADA - [{jugador.nombre}] no puede jugar ni descartar (mazo vacío).\n")
                self.blocked = True
                self.autoplay = False
                self.status_msg = 'Partida bloqueada (mazo vacío, sin jugadas).'
                return
            # Pasa turno sin acción
            self._diario(f"[{jugador.nombre}] Jugada {self.jugada_idx}: no puede jugar; pasa turno.")
            self.siguiente_turno()
    
    # comprobar_victoria está en GameEngine (engine.py)
    
    def handle_click(self, pos: Tuple[int, int]):
        x, y = pos
        # Toggle de barra inferior
        if hasattr(self, 'bottom_bar_toggle_rect') and self.bottom_bar_toggle_rect and self.bottom_bar_toggle_rect.collidepoint(pos):
            self.bottom_bar_collapsed = not self.bottom_bar_collapsed
            return
        
        # Botones de la barra inferior (solo si está expandida)
        if not self.bottom_bar_collapsed:
            # Botón: Nueva Partida
            if hasattr(self, 'btn_nueva_rect') and self.btn_nueva_rect and self.btn_nueva_rect.collidepoint(pos):
                self.iniciar_partida()
                # resetear UI/estados
                self.selected_hand_idx = None
                self.discard_selection.clear()
                self.post_discard_waiting = False
                self.carta_arrastrando = None
                self.status_msg = ''
                return
            # Toggle sonido
            if hasattr(self, 'btn_sound_rect') and self.btn_sound_rect and self.btn_sound_rect.collidepoint(pos):
                self.sound_enabled = not self.sound_enabled
                return
            # Manejo de diario
            if hasattr(self, 'diario_icon_rect') and self.diario_icon_rect and self.diario_icon_rect.collidepoint(pos):
                self.diario_open = not self.diario_open
                return
            # Manejo de ayuda
            if hasattr(self, 'ayuda_icon_rect') and self.ayuda_icon_rect and self.ayuda_icon_rect.collidepoint(pos):
                self.ayuda_open = not self.ayuda_open
                return
        
        # Botón: Cerrar Diario
        if hasattr(self, 'diario_close_rect') and self.diario_open and self.diario_close_rect.collidepoint(pos):
            self.diario_open = False
            return
        
        # Botón: Cerrar Ayuda
        if hasattr(self, 'ayuda_close_rect') and self.ayuda_open and self.ayuda_close_rect.collidepoint(pos):
            self.ayuda_open = False
            return
        # No permitir interacciones si el juego terminó
        if self.game_over:
            return
        colors = ['corazon', 'cerebro', 'huesos', 'estomago']
        for color in colors:
            # Determinar fila destino según carta seleccionada (virus => IA fila 1; resto fila 0)
            target_row = 0
            if self.selected_hand_idx is not None and self.turno == 0:
                try:
                    carta_sel_tmp = self.jugadores[0].mano[self.selected_hand_idx]
                    if carta_sel_tmp.tipo == 'virus':
                        target_row = 1
                except Exception:
                    pass
            slot_x, slot_y = self._slot_center_for_player(target_row, color)
            if (slot_x - 55 <= x <= slot_x + 55 and slot_y - 75 <= y <= slot_y + 75):
                if self.jugadores[self.turno].nombre == 'TÚ':
                    # Drag activo
                    if self.carta_arrastrando:
                        carta = self.carta_arrastrando[0]
                        jugable, _ = self.es_jugable(carta, self.jugadores[self.turno])
                        if jugable:
                            if self.jugar_carta(self.jugadores[self.turno], carta):
                                self.jugadores[self.turno].mano.remove(carta)
                                self.descarte.append(carta)
                                self.carta_arrastrando = None
                                self.siguiente_turno()
                                return
                    # Selección por click
                    if self.selected_hand_idx is not None and self.turno == 0:
                        try:
                            carta = self.jugadores[0].mano[self.selected_hand_idx]
                        except Exception:
                            carta = None
                        if carta is not None:
                            start = self._hand_card_center(self.selected_hand_idx)
                            end = (slot_x, slot_y)
                            # Tratamiento LADRÓN: commit dirigido al color del slot de la IA
                            if carta.tipo == 'tratamiento' and carta.color == 'ladrón' and target_row == 1:
                                def on_done():
                                    if self._jugar_tratamiento(self.jugadores[0], carta, color):
                                        try:
                                            self.jugadores[0].mano.remove(carta)
                                        except Exception:
                                            pass
                                        self.descarte.append(carta)
                                        self.selected_hand_idx = None
                                        self.carta_arrastrando = None
                                        self.status_msg = ''
                                        self.siguiente_turno()
                                self._start_fly_animation(carta, start, end, on_done)
                                return
                            # Resto de cartas: validar y jugar
                            jugable, msg = self.es_jugable(carta, self.jugadores[0])
                            if jugable:
                                self._start_fly_animation(carta, start, end, lambda: self._commit_play(self.jugadores[0], carta))
                                return
                            self.status_msg = msg or 'Movimiento inválido'
                            return
                return
        
        jugador = self.jugadores[self.turno]
        if jugador.nombre == 'TÚ':
            # Código de botón "Pasar Turno" eliminado - ya no se usa
            
            # Ya no bloqueamos acciones tras descartar: el turno avanza automáticamente
            
            # Arrastrar carta de la mano (coordenadas centradas como en render_mano)
            gap = 140  # Espaciado entre cartas (ajustado para cartas más pequeñas)
            count = max(1, len(jugador.mano))
            total_w = (count - 1) * gap
            card_width, card_height = CARD_WIDTH, CARD_HEIGHT
            y_pos = WINDOW_HEIGHT - card_height // 2 - 90  # Ajustado para dejar espacio para la barra inferior
            start_x = WINDOW_WIDTH // 2 - total_w // 2
            for i, carta in enumerate(jugador.mano):
                card_x = start_x + i * gap; card_y = y_pos
                if (card_x - card_width//2 <= x <= card_x + card_width//2 and card_y - card_height//2 <= y <= card_y + card_height//2):
                    # Click con SHIFT: seleccionar para descartar múltiple
                    try:
                        mods = pygame.key.get_mods()
                    except Exception:
                        mods = 0
                    if mods & (pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_META):
                        # Cmd/Ctrl + click: añadir/quitar de selección múltiple
                        if i in self.discard_selection:
                            self.discard_selection.remove(i)
                        else:
                            self.discard_selection.append(i)
                        self.discard_selection.sort()
                        self.selected_hand_idx = i
                        self.status_msg = f'✓ {len(self.discard_selection)} cartas seleccionadas (click en una y arrastra a DESCARTE)'
                    else:
                        # Click sin modificador
                        # Si hay cartas en discard_selection y hago click en una de ellas, iniciar drag múltiple
                        if self.discard_selection and i in self.discard_selection:
                            # DRAG MÚLTIPLE: arrastrar todas las seleccionadas
                            self.cartas_multi_drag = self.discard_selection.copy()
                            self.carta_arrastrando = (carta, x - card_x, y - card_y)
                            self.is_dragging = True
                            self.status_msg = f'Arrastrando {len(self.cartas_multi_drag)} cartas a DESCARTE'
                        else:
                            # DRAG SIMPLE: limpiar selección anterior y arrastrar solo esta carta
                            self.discard_selection.clear()
                            self.cartas_multi_drag.clear()
                            self.selected_hand_idx = i
                            self.status_msg = 'Selecciona un slot compatible para jugar'
                            # iniciar drag & drop PARA TODAS LAS CARTAS (incluido tratamientos)
                            self.carta_arrastrando = (carta, x - card_x, y - card_y)
                            self.is_dragging = True
                            
                            # Si es INTERVENCIÓN, mostrar instrucciones específicas
                            if carta.tipo == 'intervencion' or carta.tipo == 'tratamiento':
                                ok, msg = self.es_jugable(carta, jugador)
                                if ok:
                                    if carta.color == 'ladrón' or carta.color == 'migracion':
                                        self.status_msg = 'MIGRACIÓN: Arrastra al aspecto del rival que quieres robar (o pulsa D para descartar)'
                                    elif carta.color == 'trasplante' or carta.color == 'refactoring':
                                        self.status_msg = 'REFACTORING: Arrastra al aspecto del rival que quieres intercambiar (o pulsa ENTER para intercambio automático)'
                                    else:
                                        # ACTIVO_ACTIVO, CODE_FREEZE, ROLLBACK se pueden arrastrar o usar con Enter
                                        nombre = carta.nombre if carta.nombre else carta.color.upper()
                                        self.status_msg = f'{nombre}: Arrastra para jugar, ENTER para jugar o D para descartar'
                                else:
                                    self.status_msg = f'No puedes jugar {carta.color.upper()}: {msg} (pulsa D para descartar)'
                    return

            # Click en Descarte para descartar varias (autopasar turno)
            if getattr(self, 'disc_rect', None) and self.disc_rect.collidepoint(pos):
                if self.discard_selection:
                    idxs = sorted(self.discard_selection, reverse=True)
                    self._perform_discard_indices(self.jugadores[0], idxs, auto_pass=True)
                    return
                elif self.selected_hand_idx is not None and 0 <= self.selected_hand_idx < len(self.jugadores[0].mano):
                    self._perform_discard_indices(self.jugadores[0], [self.selected_hand_idx], auto_pass=True)
                    return
    
    def handle_mouse_up(self, pos):
        # No permitir acciones si el juego terminó
        if self.game_over:
            self.carta_arrastrando = None
            self.is_dragging = False
            return
        if not self.carta_arrastrando:
            return
        carta, off_x, off_y = self.carta_arrastrando
        jugador = self.jugadores[self.turno]
        if jugador.nombre != 'TÚ':
            self.carta_arrastrando = None
            self.is_dragging = False
            return
        
        # Limpiar estados de arrastre SIEMPRE al soltar
        self.carta_arrastrando = None
        self.is_dragging = False
        # Limpiar también multi-drag si no es un descarte múltiple
        # (el descarte múltiple lo limpiará por sí mismo)
        
        # PRIORIDAD 1: Verificar si suelta sobre la zona de DESCARTE
        drop_rect = getattr(self, 'disc_rect', None)
        if drop_rect is None:
            # fallback por si aún no se dibujó el rectángulo este frame
            center_y = 450
            # Usar las mismas dimensiones estándar de cartas
            drop_w = CARD_WIDTH
            drop_h = CARD_HEIGHT
            drop_rect = pygame.Rect(WINDOW_WIDTH//2 + 110, center_y - drop_h//2, drop_w, drop_h)
        
        # Zona de descarte AMPLIADA pero razonable (80px extra, no 200px)
        discard_zone = drop_rect.inflate(80, 80)
        mouse_now = pygame.mouse.get_pos()
        
        # Si el mouse está cerca de la zona de descarte, DESCARTAR
        if discard_zone.collidepoint(pos) or discard_zone.collidepoint(mouse_now):
            # Si hay DRAG MÚLTIPLE activo, descartar todas las cartas seleccionadas
            if self.cartas_multi_drag:
                self._perform_discard_indices(jugador, self.cartas_multi_drag, auto_pass=True)
                self.cartas_multi_drag.clear()
                self.discard_selection.clear()
            else:
                # Drag simple de una sola carta
                self._discard_card(jugador, carta)
            return
        
        # PRIORIDAD 2: si suelta sobre un slot válido, animar y jugar
        target_color, target_pos = self._resolver_drop_target(pos, jugador, carta)
        if target_color is None or target_pos is None:
            # CASO ESPECIAL: Tratamientos sin target específico (guante, trasplante, contagio, error)
            # Si los sueltas fuera de la zona de descarte, se juegan automáticamente
            if carta.tipo == 'tratamiento' and carta.color in ('guante', 'trasplante', 'contagio', 'error'):
                jugable, _ = self.es_jugable(carta, jugador)
                if jugable:
                    # Usar _commit_play para mantener el flujo consistente
                    self._commit_play(jugador, carta)
                    return
            # No hay slot válido y no está en zona de descarte => cancelar
            return
        
        jugable, msg_error = self.es_jugable(carta, jugador)
        if not jugable:
            # Mostrar mensaje de error cuando no se puede jugar la carta
            self.status_msg = msg_error if msg_error else f'No puedes jugar {carta.tipo}:{carta.color}'
            self.last_action_detail = msg_error if msg_error else 'Jugada inválida'
            return
        start = pos
        end = target_pos
        
        # CASO ESPECIAL: LADRÓN necesita saber el color objetivo
        if carta.tipo == 'tratamiento' and carta.color == 'ladrón':
            def on_done_ladron():
                if self._jugar_tratamiento(jugador, carta, target_color):
                    # Robo exitoso
                    if carta in jugador.mano:
                        jugador.mano.remove(carta)
                    self.descarte.append(carta)
                    # Limpiar TODOS los estados de UI
                    self.selected_hand_idx = None
                    self.carta_arrastrando = None
                    self.cartas_multi_drag.clear()
                    self.discard_selection.clear()
                    self.is_dragging = False
                    self.status_msg = ''
                    self._trace(f"[PLAY] {jugador.nombre} juega {carta.tipo}:{carta.color} -> {target_color}")
                    # Diario jugada
                    try:
                        detalle = f" ⇒ {self.last_action_detail}" if self.last_action_detail else ''
                        self._diario(f"[{jugador.nombre}] Jugada {self.jugada_idx} [JUEGO]: juega {carta.tipo}:{carta.color}{detalle}.")
                    except Exception:
                        pass
                    # Victoria
                    # Comprobar victoria (puede usar motor MTG si está activo)
                    winner = self.comprobar_victoria()
                    if winner:
                        try:
                            self._diario(f"\n🏆 ¡VICTORIA DE [{winner}]! Alcanza 4 aspectos saludables en {self.jugada_idx} jugadas.\n")
                        except Exception:
                            pass
                        self.game_over = True
                        self.winner = winner
                        self.autoplay = False
                        self.status_msg = f"Victoria de {winner}!"
                        return
                    self.siguiente_turno()
                    self.last_action_detail = ''
                else:
                    # Robo fallido: mostrar mensaje y cancelar
                    self.status_msg = self.last_action_detail if self.last_action_detail else f'No puedes robar {target_color.upper()}'
                    # La carta vuelve a la mano (no se descarta)
                    self.selected_hand_idx = None
                    self.carta_arrastrando = None
                    self.cartas_multi_drag.clear()
                    self.discard_selection.clear()
                    self.is_dragging = False
            self._start_fly_animation(carta, start, end, on_done_ladron)
        else:
            self._start_fly_animation(carta, start, end, lambda: self._commit_play(jugador, carta))
    
    def handle_mouse_motion(self, pos):
        if self.headless:
            return
        jugador = self.jugadores[self.turno]
        gap = 140
        count = max(1, len(jugador.mano))
        total_w = (count - 1) * gap
        card_width, card_height = CARD_WIDTH, CARD_HEIGHT
        y_pos = WINDOW_HEIGHT - card_height // 2 - 90  # Ajustado para dejar espacio para la barra inferior
        start_x = WINDOW_WIDTH // 2 - total_w // 2
        self.hover_hand_idx = None
        for i, _carta in enumerate(jugador.mano):
            x = start_x + i * gap
            if (x - card_width//2 <= pos[0] <= x + card_width//2 and y_pos - card_height//2 <= pos[1] <= y_pos + card_height//2):
                self.hover_hand_idx = i
                break
        # Ayuda contextual
        self.hover_help_text = ''
        self.hover_help_pos = None
        try:
            if self.hover_hand_idx is not None:
                c = jugador.mano[self.hover_hand_idx]
                self.hover_help_text = self._card_help(c)
                # posicionar tooltip encima de la carta
                x = start_x + self.hover_hand_idx * gap
                self.hover_help_pos = (x, y_pos - 120)
            elif self.selected_hand_idx is not None and self.turno == 0:
                c = self.jugadores[0].mano[self.selected_hand_idx]
                self.hover_help_text = self._card_help(c)
                x, y = self._hand_card_center(self.selected_hand_idx)
                self.hover_help_pos = (x, y - 120)
        except Exception:
            self.hover_help_text = ''
            self.hover_help_pos = None
        # Cambiar cursor si hay slot compatible
        if self.turno == 0 and self.selected_hand_idx is not None:
            hover_color = self._hover_slot_color(pos)
            if hover_color is not None and self._slot_is_compatible(hover_color):
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                except Exception:
                    pass
                return
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

    def _card_help(self, carta: Carta) -> str:
        t = carta.tipo
        c = carta.color
        # Aspectos
        if t == 'aspecto' or t == 'organo':
            nombre = ASPECTO_MAP.get(c, {}).get('label', c.upper())
            return f"Aspecto {nombre}: colócalo en tu zona. Ganas con 4 aspectos saludables."
        # Ataques y Problemas
        if t == 'ataque' or t == 'problema' or t == 'virus':
            nombre = ASPECTO_MAP.get(c, {}).get('label', c.upper())
            nombre_carta = carta.nombre if carta.nombre else (f"Ataque {nombre}" if t == 'ataque' else f"Problema {nombre}")
            return f"{nombre_carta}: ataca aspecto {nombre} del rival. Vulnera; si ya está vulnerable, lo destruye."
        # Protecciones
        if t == 'proteccion' or t == 'medicina':
            nombre = ASPECTO_MAP.get(c, {}).get('label', c.upper())
            nombre_carta = carta.nombre if carta.nombre else f"Protección {nombre}"
            return f"{nombre_carta}: defiende tu {nombre}. Cura vulnerabilidad; 2 protecciones = fortalecido."
        # Intervenciones
        if t == 'intervencion' or t == 'tratamiento':
            subt = c
            help_map = {
                'ladrón': 'Roba un aspecto del rival que no tengas.',
                'migracion': 'Roba un aspecto del rival que no tengas.',
                'trasplante': 'Intercambia un aspecto entre jugadores.',
                'refactoring': 'Intercambia un aspecto entre jugadores.',
                'contagio': 'Propaga tu vulnerabilidad a ese aspecto del rival.',
                'activo_activo': 'Propaga tu vulnerabilidad a ese aspecto del rival (si tu sistema está mal, el remoto también).',
                'guante': 'Escudo: anula el siguiente ataque o intervención contra ti.',
                'code_freeze': 'Escudo: anula el siguiente ataque o intervención contra ti.',
                'error': 'Rollback: elimina 1 protección de un aspecto rival.',
                'rollback': 'Rollback: elimina 1 protección de un aspecto rival.',
            }
            nombre_intervencion = carta.nombre if carta.nombre else subt.upper()
            return f"{nombre_intervencion}: {help_map.get(subt, 'Efecto no especificado')}"
        return f"{t}:{c}"
    
    def render(self):
        if self.headless:
            return
        assert self.screen is not None
        # Fondo de tapiz
        self._ensure_felt_background()
        self.screen.blit(self.bg_surface, (0, 0))  # type: ignore
        # Actualizaciones de animación
        self._tick_tweens()
        self._tick_particles()
        self.render_zones()
        self.render_panel_ayuda()
        self.render_aspectos()
        self.render_mano()
        self.render_mazos()
        self.render_ia_hand()
        # Carta(s) arrastrando DESPUÉS de los mazos para que la zona de descarte sea visible
        if self.carta_arrastrando and not self.fly_anim:
            carta, _, _ = self.carta_arrastrando
            mouse_pos = pygame.mouse.get_pos()
            jugador_humano = self.jugadores[0]
            jugable, _ = self.es_jugable(carta, jugador_humano) if self.turno == 0 else (False, '')
            
            # Si hay drag múltiple, dibujar efecto de "fan" con todas las cartas
            if self.cartas_multi_drag and len(self.cartas_multi_drag) > 1:
                # Dibujar las cartas en forma de abanico detrás de la principal
                for offset_idx, card_idx in enumerate(self.cartas_multi_drag):
                    if 0 <= card_idx < len(jugador_humano.mano):
                        c = jugador_humano.mano[card_idx]
                        # Offset en X e Y para crear efecto de "stack"
                        offset_x = (offset_idx - len(self.cartas_multi_drag) // 2) * 15
                        offset_y = offset_idx * 8
                        self.draw_card_style_transparent(mouse_pos[0] + offset_x, mouse_pos[1] + offset_y, c, False, alpha=150)
                # Mostrar número de cartas
                count_surf = self.font_large.render(str(len(self.cartas_multi_drag)), True, (255, 255, 255))
                count_bg = pygame.Surface((count_surf.get_width() + 20, count_surf.get_height() + 10), pygame.SRCALPHA)
                pygame.draw.circle(count_bg, (255, 0, 0, 220), (count_bg.get_width()//2, count_bg.get_height()//2), count_surf.get_height()//2 + 10)
                count_bg.blit(count_surf, (10, 5))
                self.screen.blit(count_bg, (mouse_pos[0] + 60, mouse_pos[1] - 70))
            else:
                # Drag simple: dibujar solo una carta
                self.draw_card_style_transparent(mouse_pos[0], mouse_pos[1], carta, jugable, alpha=180)
        self.render_hud()
        self.render_status()
        self.render_turn_arrow()
        self.render_bottom_bar()
        # capa animación
        if self.fly_anim:
            carta = self.fly_anim['card']
            x = int(self.fly_anim['x'])
            y = int(self.fly_anim['y'])
            angle = self.fly_anim.get('angle', 0)
            jugable, _ = self.es_jugable(carta, self.jugadores[self.turno])
            
            # Renderizar carta animada con efecto de escala durante el vuelo
            progress = self.fly_anim['t'] / self.fly_anim['steps']
            # Efecto de "pop" al inicio y al final
            scale = 1.0 + 0.1 * math.sin(progress * math.pi)  # Escala de 1.0 a 1.1 y vuelta
            self.draw_card_style(x, y, carta, jugable)
            
            # Efecto de brillo durante el vuelo
            if self.fly_anim['t'] < self.fly_anim['steps']:
                glow_alpha = int(100 * (1 - abs(self.fly_anim['t'] / self.fly_anim['steps'] - 0.5) * 2))
                glow_surf = pygame.Surface((CARD_WIDTH + 10, CARD_HEIGHT + 10), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*COLOR_GOLD[:3], glow_alpha), 
                               (0, 0, CARD_WIDTH + 10, CARD_HEIGHT + 10), 
                               border_radius=CARD_BORDER_RADIUS + 5)
                self.screen.blit(glow_surf, (x - CARD_WIDTH//2 - 5, y - CARD_HEIGHT//2 - 5))
        # panel de diario por encima del tablero
        self.render_diario_panel()
        self.render_tooltip()
        # Partículas encima de todo
        for p in self.particles:
            alpha = max(40, int(255 * (p['life'] / 30.0)))
            s = max(1, int(p['size']))
            surf = pygame.Surface((s, s), pygame.SRCALPHA)
            surf.fill((*p['color'], alpha))
            self.screen.blit(surf, (int(p['x']), int(p['y'])))
        pygame.display.flip()
    
    def render_tooltip(self) -> None:
        if not self.hover_help_text or self.hover_help_pos is None or self.headless:
            return
        assert self.screen is not None
        txt = self.font_small.render(self.hover_help_text, True, COLOR_WHITE)
        bg = txt.get_rect()
        cx, cy = self.hover_help_pos
        # Clamp dentro de ventana
        cx = max(80, min(WINDOW_WIDTH - 80, cx))
        cy = max(40, min(WINDOW_HEIGHT - 40, cy))
        bg.center = (cx, cy)
        bg.inflate_ip(18, 10)
        # Overlay con alfa y radio para evitar cajas negras
        tooltip_panel = pygame.Surface((bg.width, bg.height), pygame.SRCALPHA)
        pygame.draw.rect(tooltip_panel, (15, 15, 15, 200), (0, 0, bg.width, bg.height), border_radius=8)
        pygame.draw.rect(tooltip_panel, (160, 160, 160, 220), (0, 0, bg.width, bg.height), 1, border_radius=8)
        self.screen.blit(tooltip_panel, bg.topleft)
        self.screen.blit(txt, (bg.centerx - txt.get_width()//2, bg.centery - txt.get_height()//2))

    def render_diario_panel(self) -> None:
        assert self.screen is not None
        
        # El icono del diario ahora está en la barra inferior
        # Si el diario está cerrado, no renderizar el panel pero limpiar close_rect
        if not self.diario_open:
            self.diario_close_rect = None
            return
        
        # Panel del diario (solo si está abierto)
        panel_w = 280
        panel_x = WINDOW_WIDTH - panel_w - 10
        panel_y = 20
        panel_h = WINDOW_HEIGHT - 100
        # fondo con transparencia y radio
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (30, 32, 36, 220), (0, 0, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(panel_surf, (*COLOR_GOLD, 230), (0, 0, panel_w, panel_h), 2, border_radius=8)
        self.screen.blit(panel_surf, (panel_x, panel_y))
        
        # Botón X para cerrar (esquina superior derecha del panel)
        mouse_pos = pygame.mouse.get_pos()
        close_btn_size = 25
        close_btn_x = panel_x + panel_w - close_btn_size - 5
        close_btn_y = panel_y + 5
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        hover_close = close_btn_rect.collidepoint(mouse_pos)
        close_color = COLOR_RED if hover_close else COLOR_WHITE
        close_surf = pygame.Surface((close_btn_size, close_btn_size), pygame.SRCALPHA)
        pygame.draw.rect(close_surf, (60, 60, 60, 220), (0, 0, close_btn_size, close_btn_size), border_radius=4)
        pygame.draw.rect(close_surf, (*close_color, 230), (0, 0, close_btn_size, close_btn_size), 2, border_radius=4)
        self.screen.blit(close_surf, (close_btn_x, close_btn_y))
        # Dibujar X
        close_text = self.font_small.render('×', True, close_color)
        close_text_x = close_btn_x + close_btn_size // 2 - close_text.get_width() // 2
        close_text_y = close_btn_y + close_btn_size // 2 - close_text.get_height() // 2
        self.screen.blit(close_text, (close_text_x, close_text_y))
        
        # Guardar rectángulo para detección de clicks
        self.diario_close_rect = close_btn_rect
        
        title = self.font_medium.render('DIARIO', True, COLOR_WHITE)
        self.screen.blit(title, (panel_x + panel_w//2 - title.get_width()//2, panel_y + 6))
        # área de texto
        text_margin = 8
        content_x = panel_x + text_margin
        # deja espacio suficiente bajo el título para evitar solapes visuales
        content_y = panel_y + title.get_height() + 20
        content_w = panel_w - 2 * text_margin
        content_h = panel_h - (content_y - panel_y) - 10
        # preparar líneas envueltas
        wrapped: List[Tuple[str, Tuple[int, int, int]]] = []
        for entry in self.diario_lines:
            if isinstance(entry, tuple):
                text, col = entry
            else:
                text, col = str(entry), COLOR_WHITE
            for seg in self._wrap_text(text, self.font_tiny, content_w):
                wrapped.append((seg, col))
        # calcular cuántas caben
        line_h = self.font_tiny.get_height() + 2
        max_lines = max(1, content_h // line_h)
        start = max(0, len(wrapped) - max_lines - self.diario_scroll)
        end = start + max_lines
        visible = wrapped[start:end]
        # dibujar
        y = content_y
        if not wrapped:
            placeholder = self.font_tiny.render('(sin eventos)', True, (180, 180, 180))
            self.screen.blit(placeholder, (content_x, y))
        else:
            for line, col in visible:
                surf = self.font_tiny.render(line, True, col)
                self.screen.blit(surf, (content_x, y))
                y += line_h

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        words = text.split(' ')
        lines: List[str] = []
        current = ''
        for w in words:
            test = w if not current else current + ' ' + w
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines
    
    def render_panel_ayuda(self):
        """Renderiza el panel de ayuda con el mismo comportamiento que el diario."""
        assert self.screen is not None
        
        # El icono de ayuda ahora está en la barra inferior
        # Si la ayuda está cerrada, no renderizar el panel pero limpiar close_rect
        if not self.ayuda_open:
            self.ayuda_close_rect = None
            return
        
        # Panel de ayuda (solo si está abierto)
        panel_x, panel_y = 20, 60
        panel_w, panel_h = 180, 680
        
        # Fondo del panel (overlay SRCALPHA)
        panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_bg, (45, 24, 16, 255), (0, 0, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(panel_bg, (139, 69, 19, 255), (0, 0, panel_w, panel_h), 3, border_radius=8)
        self.screen.blit(panel_bg, (panel_x, panel_y))
        
        # Botón X para cerrar (arriba a la derecha del panel)
        mouse_pos = pygame.mouse.get_pos()
        close_btn_size = 28
        close_btn_x = panel_x + panel_w - close_btn_size - 5
        close_btn_y = panel_y + 5
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        
        # Hover en botón X
        hover_close = close_btn_rect.collidepoint(mouse_pos)
        close_bg = (200, 50, 50) if hover_close else (150, 40, 40)
        close_surf = pygame.Surface((close_btn_rect.width, close_btn_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(close_surf, (*close_bg, 255) if len(close_bg)==3 else close_bg, (0,0,close_btn_rect.width, close_btn_rect.height), border_radius=4)
        pygame.draw.rect(close_surf, (*COLOR_WHITE, 255), (0,0,close_btn_rect.width, close_btn_rect.height), 2, border_radius=4)
        self.screen.blit(close_surf, close_btn_rect.topleft)
        
        # Símbolo X
        close_text = self.font_medium.render('×', True, COLOR_WHITE)
        close_text_x = close_btn_x + close_btn_size // 2 - close_text.get_width() // 2
        close_text_y = close_btn_y + close_btn_size // 2 - close_text.get_height() // 2
        self.screen.blit(close_text, (close_text_x, close_text_y))
        
        # Guardar rectángulo para detección de clicks
        self.ayuda_close_rect = close_btn_rect
        
        # Título
        title = self.font_medium.render('AYUDA', True, COLOR_GOLD)
        self.screen.blit(title, (panel_x + panel_w//2 - title.get_width()//2, panel_y + 10))
        
        # Contenido de ayuda
        jugador_actual = self.jugadores[self.turno]
        modo_actual = "AUTO" if self.autoplay else "MANUAL"
        ayuda = [
            f'Turno: {jugador_actual.nombre}',
            f'Aspectos saludables: {jugador_actual.aspectos_saludables()}/4',
            '',
            'Tu turno:',
            '1. Click en carta',
            '2. Colócala',
            '',
            'ASPECTO: Coloca',
            'ATAQUE: Vulnera',
            'PROTECCIÓN: Protege',
            '',
            'OBJETIVO: 4 aspectos SALUDABLES',
            '',
            f'Modo: {modo_actual}',
            'Presiona A para',
            'activar/desactivar',
            'el modo automático'
        ]
        content_start_y = panel_y + 40
        for i, linea in enumerate(ayuda):
            text = self.font_tiny.render(linea, True, COLOR_WHITE)
            self.screen.blit(text, (panel_x + 10, content_start_y + i * 18))
    
    def render_aspectos(self):
        """Renderiza los aspectos en el tablero, posicionados dentro de las zonas definidas."""
        assert self.screen is not None
        # Fila superior: aspectos del Jugador 2 (IA) - dentro de zona superior
        self.render_organos_row(player_index=1, y=180)
        # Fila inferior: aspectos del Jugador 1 (humano) - dentro de zona inferior
        self.render_organos_row(player_index=0, y=480)

    def _draw_slot_placeholder(self, x: int, y: int, w: int, h: int, color_key: str) -> None:
        """Dibuja un placeholder transparente con forma de carta (esquinas redondeadas) para slots vacíos."""
        assert self.screen is not None
        # Usar ASPECTO_MAP directamente, con fallback a COLOR_MAP para compatibilidad
        info = ASPECTO_MAP.get(color_key, None)
        if info is None:
            # Mapeo de nombres antiguos a nuevos para compatibilidad
            legacy_map = {
                'corazon': 'seguridad',
                'cerebro': 'documentacion',
                'huesos': 'gobierno',
                'estomago': 'performance'
            }
            color_key_new = legacy_map.get(color_key, 'multicolor')
            info = ASPECTO_MAP.get(color_key_new, ASPECTO_MAP['multicolor'])
        
        # Crear superficie transparente con forma de carta
        placeholder_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Calcular radio dinámico para este placeholder
        placeholder_radius = get_card_border_radius(w, h)
        
        # Fondo semi-transparente gris muy sutil
        bg_color = (100, 100, 100, 30)  # Muy transparente
        pygame.draw.rect(placeholder_surf, bg_color, (0, 0, w, h), 0, border_radius=placeholder_radius)
        
        # Borde tenue semi-transparente
        border_color = (160, 160, 160, 100)
        pygame.draw.rect(placeholder_surf, border_color, (0, 0, w, h), 2, border_radius=placeholder_radius)
        
        # Aplicar máscara de esquinas redondeadas
        placeholder_surf = self._apply_rounded_clip(placeholder_surf)
        
        # Dibujar icono y etiqueta en gris suave sobre la superficie
        icon = self.font_large.render(info['icon'], True, (180, 180, 180))
        placeholder_surf.blit(icon, (w//2 - icon.get_width()//2, h//2 - 40))
        label = self.font_small.render(info['label'], True, (180, 180, 180))
        placeholder_surf.blit(label, (w//2 - label.get_width()//2, h//2 + 10))
        
        # Blitear la superficie completa en la posición correcta
        self.screen.blit(placeholder_surf, (x - w//2, y - h//2))

    def render_organos_row(self, player_index: int, y: int) -> None:
        """Dibuja los 4 slots de aspectos centrados horizontalmente en la fila y indicada.
        Con estilo similar a doudizhu: áreas claramente definidas con bordes."""
        assert self.screen is not None
        jugador = self.jugadores[player_index]
        colors_order = ASPECTOS  # ['seguridad', 'documentacion', 'gobierno', 'performance']
        gap = 140  # Espaciado entre placeholders (CARD_WIDTH=120 + 20px de margen para evitar solapamiento)
        total_w = gap * 3
        # Centrar dentro de la zona del jugador (usar las mismas dimensiones que render_zones)
        zone_margin_left = 280
        zone_margin_right = 360
        zone_width = WINDOW_WIDTH - zone_margin_left - zone_margin_right
        zone_center_x = zone_margin_left + zone_width // 2
        start_x = zone_center_x - total_w // 2
        xs = [start_x + i * gap for i in range(4)]
        for x, color in zip(xs, colors_order):
            w, h = CARD_WIDTH, CARD_HEIGHT  # Mismo tamaño que todas las cartas
            border_color = COLOR_WHITE
            compatible = False
            if self.selected_hand_idx is not None and self.turno == 0:
                try:
                    carta_sel = self.jugadores[0].mano[self.selected_hand_idx]
                    if carta_sel.tipo == 'aspecto' and player_index == 0:
                        if (carta_sel.color == 'multicolor' and color not in self.jugadores[0].aspectos) or (carta_sel.color == color and color not in self.jugadores[0].aspectos):
                            border_color = COLOR_GOLD; compatible = True
                    elif carta_sel.tipo == 'proteccion' and player_index == 0:
                        if (carta_sel.color == 'multicolor' and color in self.jugadores[0].aspectos) or (carta_sel.color == color and color in self.jugadores[0].aspectos):
                            border_color = COLOR_GOLD; compatible = True
                    elif carta_sel.tipo in ('ataque', 'problema') and player_index == 1:
                        if (carta_sel.color == 'multicolor' and color in self.jugadores[1].aspectos) or (carta_sel.color == color and color in self.jugadores[1].aspectos):
                            border_color = COLOR_GOLD; compatible = True
                except Exception:
                    pass
            
            # Solo dibujar borde si hay una carta en el slot o si es compatible
            # Para slots vacíos, el placeholder ya incluye el borde
            if color in jugador.aspectos or compatible:
                border_px = 3 if border_color == COLOR_GOLD else 2
                border_rgba = (*border_color, 255) if len(border_color) == 3 else border_color
                blit_rounded_border(self.screen, x - w//2, y - h//2, w, h, border_rgba, border_px)
            
            # Overlay de guía para slots compatibles (encendido)
            if compatible:
                pulse = (pygame.time.get_ticks() // 200) % 10
                alpha = 40 + pulse * 8
                blit_rounded_panel(self.screen, x - w//2, y - h//2, w, h,
                                   bg_rgba=(255, 215, 0, alpha), radius=get_card_border_radius(w, h))
            if color in jugador.aspectos:
                asp = jugador.aspectos[color]
                info = COLOR_MAP[color]
                # base y estados según esquema
                # PRIORIDAD: Vulnerable > Inmunizado > Protegido > Sano
                protecciones = asp.get('protecciones', 0)
                vulnerable = asp.get('vulnerable', False)
                if protecciones >= 2:
                    bg_color = COLOR_SILVER
                    estado = 'FORTALECIDO'
                elif vulnerable:
                    # Si está vulnerable, siempre mostrar VULNERABLE
                    bg_color = COLOR_RED_INTENSE
                    estado = 'VULNERABLE'
                elif protecciones >= 1:
                    bg_color = COLOR_BLUE_BRIGHT
                    estado = 'PROTEGIDO'
                else:
                    bg_color = COLOR_TEAL
                    estado = 'SALUDABLE'
                # Calcular radio dinámico para este slot
                slot_radius = get_card_border_radius(w, h)
                # Intentar usar imagen de asset para el estado
                # La máscara ya está aplicada en _get_slot_surface
                surf = self._get_slot_surface(color, estado, (w, h))
                if surf is not None:
                    # Crear composición con borde integrado (sin dibujar directamente sobre screen)
                    slot_composite = pygame.Surface((w, h), pygame.SRCALPHA)
                    slot_composite.blit(surf, (0, 0))
                    # Añadir borde interior suave (sin borde negro exterior)
                    inner_border_rect = pygame.Rect(1, 1, w - 2, h - 2)
                    pygame.draw.rect(slot_composite, COLOR_GOLD, inner_border_rect, 1, border_radius=max(1, slot_radius - 1))
                    rect = slot_composite.get_rect(center=(x, y))
                    self.screen.blit(slot_composite, rect)
                else:
                    # Fallback programático: crear superficie con forma de carta
                    card_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                    pygame.draw.rect(card_surf, bg_color, (0, 0, w, h), 0, border_radius=slot_radius)
                    # Solo borde interior suave (sin borde negro exterior)
                    inner_border = pygame.Rect(1, 1, w - 2, h - 2)
                    pygame.draw.rect(card_surf, COLOR_GOLD, inner_border, 1, border_radius=max(1, slot_radius - 1))
                    # Dibujar icono y texto en la superficie
                    text = self.font_large.render(info['icon'], True, COLOR_WHITE)
                    card_surf.blit(text, (w//2 - text.get_width()//2, h//2 - 40))
                    text = self.font_small.render(info['label'], True, COLOR_WHITE)
                    card_surf.blit(text, (w//2 - text.get_width()//2, h//2 + 10))
                    text = self.font_tiny.render(estado, True, COLOR_WHITE)
                    card_surf.blit(text, (w//2 - text.get_width()//2, h//2 + 50))
                    # Aplicar máscara de esquinas redondeadas
                    card_surf = self._apply_rounded_clip(card_surf)
                    self.screen.blit(card_surf, (x - w//2, y - h//2))
                fx = self.fx_active.get(color)
                if fx:
                    t = fx.get('t', 0); dur = fx.get('dur', 30)
                    ratio = max(0.0, 1.0 - (t / float(dur)))
                    if fx.get('type') in ('infect', 'destroy'):
                        col = (255, int(80 * ratio), int(80 * ratio))
                    elif fx.get('type') in ('vaccinate', 'cure'):
                        col = (80, 160, 255)
                    elif fx.get('type') == 'immunize':
                        col = (120, 255, 120)
                    else:
                        col = (255, 215, 0)
                    # Overlay redondeado con alfa usando helper
                    ov_w, ov_h = w + 6, h + 6
                    fx_radius = max(1, get_card_border_radius(w, h) + 3)
                    blit_rounded_border(self.screen, x - w//2 - 3, y - h//2 - 3, ov_w, ov_h,
                                       (*col, 255), 3, radius=fx_radius)
            else:
                # Slot vacío: mostrar placeholder con nombre del órgano
                self._draw_slot_placeholder(x, y, w, h, color)
    def render_organos_side(self, player_index: int):
        assert self.screen is not None
        jugador = self.jugadores[player_index]
        # coordenadas centradas por fila dentro de la zona del jugador
        gap = 140  # Espaciado entre placeholders (CARD_WIDTH=120 + 20px de margen para evitar solapamiento)
        total_w = gap * 3
        # Centrar dentro de la zona del jugador (usar las mismas dimensiones que render_zones)
        zone_margin_left = 280
        zone_margin_right = 360
        zone_width = WINDOW_WIDTH - zone_margin_left - zone_margin_right
        zone_center_x = zone_margin_left + zone_width // 2
        start_x = zone_center_x - total_w // 2
        xs = [start_x + i * gap for i in range(4)]
        colors_order = ASPECTOS  # ['seguridad', 'documentacion', 'gobierno', 'performance']
        y = 450
        for x, color in zip(xs, colors_order):
            w, h = CARD_WIDTH, CARD_HEIGHT  # Mismo tamaño que todas las cartas
            # highlight de slot si carta seleccionada es compatible y es tu zona (y_offset=0)
            border_color = COLOR_WHITE
            if player_index == 0 and self.selected_hand_idx is not None and self.turno == 0:
                try:
                    carta_sel = self.jugadores[0].mano[self.selected_hand_idx]
                    if carta_sel.tipo == 'aspecto':
                        if (carta_sel.color == 'multicolor' and color not in self.jugadores[0].aspectos) or (carta_sel.color == color and color not in self.jugadores[0].aspectos):
                            border_color = COLOR_GOLD
                    elif carta_sel.tipo in ('ataque', 'problema', 'proteccion'):
                        if (carta_sel.color == 'multicolor' and color in self.jugadores[0].aspectos) or (carta_sel.color == color and color in self.jugadores[0].aspectos):
                            border_color = COLOR_GOLD
                except Exception:
                    pass
            # Solo dibujar borde si hay una carta en el slot o si es compatible
            # Para slots vacíos, el placeholder ya incluye el borde
            if color in jugador.aspectos or border_color == COLOR_GOLD:
                border_px = 3 if border_color == COLOR_GOLD else 2
                border_rgba = (*border_color, 255) if len(border_color) == 3 else border_color
                blit_rounded_border(self.screen, x - w//2, y - h//2, w, h, border_rgba, border_px)
            if color in jugador.aspectos:
                asp = jugador.aspectos[color]
                info = COLOR_MAP[color]
                # PRIORIDAD: Vulnerable > Fortalecido > Protegido > Saludable
                protecciones = asp.get('protecciones', 0)
                vulnerable = asp.get('vulnerable', False)
                if protecciones >= 2:
                    bg_color = COLOR_SILVER
                    estado = 'FORTALECIDO'
                elif vulnerable:
                    # Si está vulnerable, siempre mostrar VULNERABLE
                    bg_color = COLOR_RED_INTENSE
                    estado = 'VULNERABLE'
                elif protecciones >= 1:
                    bg_color = COLOR_BLUE_BRIGHT
                    estado = 'PROTEGIDO'
                else:
                    bg_color = COLOR_TEAL
                    estado = 'SALUDABLE'
                # Calcular radio dinámico para este slot
                slot_radius = get_card_border_radius(w, h)
                # Intentar usar imagen de asset para el estado
                # La máscara ya está aplicada en _get_slot_surface
                surf = self._get_slot_surface(color, estado, (w, h))
                if surf is not None:
                    # Crear composición con borde integrado (sin dibujar directamente sobre screen)
                    slot_composite = pygame.Surface((w, h), pygame.SRCALPHA)
                    slot_composite.blit(surf, (0, 0))
                    # Añadir borde interior suave (sin borde negro exterior)
                    inner_border_rect = pygame.Rect(1, 1, w - 2, h - 2)
                    pygame.draw.rect(slot_composite, COLOR_GOLD, inner_border_rect, 1, border_radius=max(1, slot_radius - 1))
                    rect = slot_composite.get_rect(center=(x, y))
                    self.screen.blit(slot_composite, rect)
                else:
                    # Fallback programático: crear superficie con forma de carta
                    card_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                    pygame.draw.rect(card_surf, bg_color, (0, 0, w, h), 0, border_radius=slot_radius)
                    # Solo borde interior suave (sin borde negro exterior)
                    inner_border = pygame.Rect(1, 1, w - 2, h - 2)
                    pygame.draw.rect(card_surf, COLOR_GOLD, inner_border, 1, border_radius=max(1, slot_radius - 1))
                    # Dibujar icono y texto en la superficie
                    text = self.font_large.render(info['icon'], True, COLOR_WHITE)
                    card_surf.blit(text, (w//2 - text.get_width()//2, h//2 - 40))
                    text = self.font_small.render(info['label'], True, COLOR_WHITE)
                    card_surf.blit(text, (w//2 - text.get_width()//2, h//2 + 10))
                    text = self.font_tiny.render(estado, True, COLOR_WHITE)
                    card_surf.blit(text, (w//2 - text.get_width()//2, h//2 + 50))
                    # Aplicar máscara de esquinas redondeadas
                    card_surf = self._apply_rounded_clip(card_surf)
                    self.screen.blit(card_surf, (x - w//2, y - h//2))
                # overlay de efectos
                fx = self.fx_active.get(color)
                if fx:
                    t = fx.get('t', 0); dur = fx.get('dur', 30)
                    ratio = max(0.0, 1.0 - (t / float(dur)))
                    if fx.get('type') in ('infect', 'destroy'):
                        col = (255, int(80 * ratio), int(80 * ratio))
                    elif fx.get('type') in ('vaccinate', 'cure'):
                        col = (80, 160, 255)
                    elif fx.get('type') == 'immunize':
                        col = (120, 255, 120)
                    else:
                        col = (255, 215, 0)
                    # Overlay redondeado con alfa usando helper
                    ov_w, ov_h = w + 6, h + 6
                    fx_radius = max(1, get_card_border_radius(w, h) + 3)
                    blit_rounded_border(self.screen, x - w//2 - 3, y - h//2 - 3, ov_w, ov_h,
                                       (*col, 255), 3, radius=fx_radius)
            else:
                # Slot vacío en vista lateral: placeholder con nombre
                self._draw_slot_placeholder(x, y, w, h, color)

    def _generate_card_back(self, width: int, height: int) -> pygame.Surface:
        """Genera el dorso de la carta completamente desde código.
        NO usa assets PNG, todo se genera programáticamente para evitar fondos negros."""
        # Crear superficie con SRCALPHA para transparencia total
        back_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        back_surf.fill((0, 0, 0, 0))  # Inicializar completamente transparente
        
        # Calcular radio dinámico
        card_radius = get_card_border_radius(width, height)
        
        # Fondo 100% transparente (la carta "flota" sin recuadro)
        # Si prefieres el color del tapete, cambia a: base_color_rgba = (*COLOR_BOARD, 255)
        base_color_rgba = (0, 0, 0, 0)  # Transparente total
        # No dibujar fondo - la superficie ya está transparente
        # El logo/texto se dibuja directamente sobre el fondo transparente
        
        # Logo o texto centrado (si hay logo disponible, usarlo; sino texto)
        if self.card_back is not None:
            # Intentar cargar y usar el logo si existe
            try:
                logo_size = min(width - 40, height - 40, 80)  # Tamaño máximo del logo
                logo_scaled = self._scale_image_preserving_ratio(self.card_back, (logo_size, logo_size))
                logo_scaled = logo_scaled.convert_alpha()
                
                # LIMPIAR el logo: eliminar cualquier fondo sólido (negro, blanco, o cualquier color uniforme en los bordes)
                # Muestrear los bordes para detectar el color de fondo
                logo_w, logo_h = logo_scaled.get_size()
                border_samples = []
                sample_size = min(10, logo_w // 4, logo_h // 4)
                for x in range(0, logo_w, max(1, logo_w // sample_size)):
                    border_samples.append(logo_scaled.get_at((x, 0)))
                    border_samples.append(logo_scaled.get_at((x, logo_h-1)))
                for y in range(0, logo_h, max(1, logo_h // sample_size)):
                    border_samples.append(logo_scaled.get_at((0, y)))
                    border_samples.append(logo_scaled.get_at((logo_w-1, y)))
                
                # Encontrar el color más común en los bordes (probablemente el fondo)
                if border_samples:
                    most_common_bg = Counter([p[:3] for p in border_samples if p[3] > 200]).most_common(1)
                    if most_common_bg:
                        bg_color = most_common_bg[0][0]
                        threshold = 30
                    else:
                        bg_color = (0, 0, 0)
                        threshold = 40
                else:
                    bg_color = (0, 0, 0)
                    threshold = 40
                
                # Limpiar el logo: hacer transparente cualquier píxel similar al fondo
                logo_cleaned = pygame.Surface((logo_w, logo_h), pygame.SRCALPHA)
                logo_cleaned.fill((0, 0, 0, 0))
                for px in range(logo_w):
                    for py in range(logo_h):
                        try:
                            pixel = logo_scaled.get_at((px, py))
                            r, g, b, a = pixel
                            # Si es similar al fondo (dentro del threshold), hacerlo transparente
                            if a > 200 and abs(r - bg_color[0]) <= threshold and \
                               abs(g - bg_color[1]) <= threshold and \
                               abs(b - bg_color[2]) <= threshold:
                                logo_cleaned.set_at((px, py), (0, 0, 0, 0))
                            else:
                                logo_cleaned.set_at((px, py), pixel)
                        except:
                            logo_cleaned.set_at((px, py), (0, 0, 0, 0))
                
                # Centrar el logo limpio
                logo_x = (width - logo_cleaned.get_width()) // 2
                logo_y = (height - logo_cleaned.get_height()) // 2
                back_surf.blit(logo_cleaned, (logo_x, logo_y))
            except Exception:
                # Si falla, usar texto
                if hasattr(self, 'font_small'):
                    text = self.font_small.render('API KOMBAT', True, (100, 120, 140))
                    text_rect = text.get_rect(center=(width//2, height//2))
                    back_surf.blit(text, text_rect)
        else:
            # Sin logo: usar texto
            if hasattr(self, 'font_small'):
                text = self.font_small.render('API KOMBAT', True, (100, 120, 140))
                text_rect = text.get_rect(center=(width//2, height//2))
                back_surf.blit(text, text_rect)
        
        # APLICAR RECORTE REDONDEADO (elimina cualquier pixel fuera del radio)
        # Esto garantiza que las esquinas sean completamente transparentes
        back_surf = apply_rounded_clip(back_surf)
        
        return back_surf

    def render_card(self, x: int, y: int, carta: Optional[Carta] = None, 
                    face_down: bool = False, transparent: bool = False, 
                    alpha: int = 255, jugable: bool = False, 
                    show_badge: bool = False, border_color: Optional[Tuple[int, int, int]] = None,
                    with_shadow: bool = False) -> pygame.Rect:
        """Renderiza una carta COMPLETAMENTE LIMPIA sin artefactos negros.
        TODAS las superficies se crean con SRCALPHA y se recortan antes del blit."""
        """Función unificada para renderizar cualquier carta en cualquier contexto.
        
        Args:
            x, y: Posición central de la carta
            carta: Objeto Carta a renderizar. Si None, renderiza el dorso
            face_down: Si True, muestra el dorso (ignora carta)
            transparent: Si True, aplica transparencia (alpha)
            alpha: Nivel de transparencia (0-255)
            jugable: Si la carta es jugable (para badge)
            show_badge: Si mostrar badge de jugable/no jugable
            border_color: Color del borde (None = COLOR_GOLD por defecto)
        
        Returns:
            Rectángulo de la carta renderizada
        """
        assert self.screen is not None
        card_width, card_height = CARD_WIDTH, CARD_HEIGHT
        border = border_color or COLOR_GOLD
        
        # Calcular radio dinámico para esta carta
        card_radius = get_card_border_radius(card_width, card_height)
        
        # Crear rectángulo centrado
        card_rect = pygame.Rect(x - card_width//2, y - card_height//2, card_width, card_height)
        
        # Determinar qué renderizar: dorso o carta
        if face_down or carta is None:
            # Generar dorso completamente desde código (NO usa assets PNG)
            back_surf = self._generate_card_back(card_width, card_height)
            
            # === SOMBRA EXTERIOR SUAVE DEL DORSO ===
            if with_shadow and alpha > 0:
                shadow_offset = 4
                shadow_blur = 2
                shadow_surf = pygame.Surface((card_width + shadow_offset * 2, card_height + shadow_offset * 2), pygame.SRCALPHA)
                shadow_surf.fill((0, 0, 0, 0))  # Inicializar transparente
                # Sombra principal con desenfoque suave
                shadow_rect = pygame.Rect(shadow_offset, shadow_offset, card_width, card_height)
                shadow_alpha = 65 if not transparent else max(0, int(alpha * 0.25))
                # Dibujar la sombra solo dentro del área redondeada
                shadow_card = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
                shadow_card.fill((0, 0, 0, shadow_alpha))
                shadow_card = self._apply_rounded_clip(shadow_card)
                shadow_surf.blit(shadow_card, (shadow_offset, shadow_offset))
                self.screen.blit(shadow_surf, (card_rect.x - shadow_offset, card_rect.y - shadow_offset))
            
            # Aplicar transparencia si es necesario
            if transparent:
                back_surf.set_alpha(alpha)
            
            # Blitear dorso directamente (ya viene limpio y recortado de _generate_card_back)
            self.screen.blit(back_surf, card_rect)
            
            return card_rect
        
        # Renderizar carta frontal
        surf = self._get_card_surface(carta, (card_width, card_height))
        if surf is not None:
            # Usar imagen de asset (la máscara ya está aplicada en _get_card_surface)
            # Renderizar en superficie temporal para composición completa
            card_composite = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
            card_composite.fill((0, 0, 0, 0))  # INICIALIZAR COMPLETAMENTE TRANSPARENTE
            card_composite.blit(surf, (0, 0))
            
            # NO dibujar bordes con pygame.draw.rect - deja artefactos negros
            # APLICAR RECORTE REDONDEADO AL COMPOSITE FINAL (CRÍTICO: elimina bordes negros)
            card_composite = self._apply_rounded_clip(card_composite)
            
            # Aplicar transparencia si es necesario
            if transparent:
                card_composite.set_alpha(alpha)
            
            # Blitear composición completa usando helper limpio
            blit_card_clean(self.screen, card_composite, card_rect.x, card_rect.y)
            
            return card_rect
        
        # Fallback: renderizado programático mejorado estilo doudizhu
        # Crear superficie para la carta con efectos visuales
        card_surf = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
        card_surf.fill((0, 0, 0, 0))  # INICIALIZAR COMPLETAMENTE TRANSPARENTE
        
        # Determinar color base según tipo
        if carta.tipo == 'aspecto':
            base_color = COLOR_TEAL
            highlight_color = (0, 200, 130)  # Más brillante para gradiente
        elif carta.tipo == 'virus':
            base_color = COLOR_RED_INTENSE
            highlight_color = (255, 60, 60)
        elif carta.tipo == 'medicina':
            base_color = COLOR_GREEN
            highlight_color = (80, 240, 140)
        else:
            base_color = COLOR_YELLOW
            highlight_color = (255, 240, 100)
        
        # === SOMBRA EXTERIOR SUAVE ===
        if with_shadow and alpha > 0:
            shadow_offset = 4
            shadow_blur = 2
            shadow_surf = pygame.Surface((card_width + shadow_offset * 2, card_height + shadow_offset * 2), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 0))  # Inicializar transparente
            # Sombra principal con desenfoque suave
            shadow_rect = pygame.Rect(shadow_offset, shadow_offset, card_width, card_height)
            shadow_alpha = 65 if not transparent else max(0, int(alpha * 0.25))
            # Dibujar la sombra solo dentro del área redondeada
            shadow_card = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
            shadow_card.fill((0, 0, 0, shadow_alpha))
            shadow_card = self._apply_rounded_clip(shadow_card)
            shadow_surf.blit(shadow_card, (shadow_offset, shadow_offset))
            self.screen.blit(shadow_surf, (card_rect.x - shadow_offset, card_rect.y - shadow_offset))
        
        # === FONDO CON GRADIENTE SUTIL ===
        # Dibujar fondo directamente en card_surf con transparencia (sin capas intermedias)
        # card_surf ya tiene SRCALPHA y está inicializado como transparente
        pygame.draw.rect(card_surf, (*base_color, 255), (0, 0, card_width, card_height), 
                         0, border_radius=card_radius)
        # Highlight superior (efecto de luz)
        highlight_rect = pygame.Rect(0, 0, card_width, card_height // 3)
        highlight_surf = pygame.Surface((card_width, card_height // 3), pygame.SRCALPHA)
        highlight_surf.fill((*highlight_color, 60))
        card_surf.blit(highlight_surf, (0, 0))
        
        # === BORDES FINOS Y ELEGANTES (sin usar pygame.draw.rect que deja bordes negros) ===
        # NO dibujar borde aquí - se puede añadir después del recorte si es necesario
        # pygame.draw.rect con border_radius deja artefactos negros en las esquinas
        
        # === CONTENIDO DE LA CARTA ===
        if carta.tipo == 'tratamiento':
            # Fondo especial para tratamientos
            treatment_bg = pygame.Rect(4, 4, card_width - 8, 30)
            treatment_bg_surf = pygame.Surface((card_width - 8, 30), pygame.SRCALPHA)
            treatment_bg_surf.fill((0, 0, 0, 120))
            card_surf.blit(treatment_bg_surf, (4, 4))
            
            titulo = self.font_small.render('TRATAMIENTO', True, COLOR_WHITE)
            card_surf.blit(titulo, (card_width//2 - titulo.get_width()//2, 8))
            
            subtipo_txt = carta.color.upper()
            subtipo = self.font_medium.render(subtipo_txt, True, COLOR_WHITE)
            card_surf.blit(subtipo, (card_width//2 - subtipo.get_width()//2, card_height//2 - 10))
        else:
            # Icono grande centrado
            info = COLOR_MAP.get(carta.color, COLOR_MAP['multicolor'])
            icon = self.font_large.render(info['icon'], True, COLOR_WHITE)
            # Sombra del icono (renderizado en superficie temporal con alpha)
            icon_shadow_surf = pygame.Surface((icon.get_width() + 4, icon.get_height() + 4), pygame.SRCALPHA)
            icon_shadow = self.font_large.render(info['icon'], True, (0, 0, 0))
            icon_shadow_surf.set_alpha(150)
            icon_shadow_surf.blit(icon_shadow, (2, 2))
            card_surf.blit(icon_shadow_surf, (card_width//2 - icon.get_width()//2 - 2, card_height//2 - icon.get_height()//2 - 22))
            card_surf.blit(icon, (card_width//2 - icon.get_width()//2, card_height//2 - icon.get_height()//2 - 20))
            
            # Tipo de carta
            tipo = self.font_small.render(carta.tipo.upper(), True, COLOR_WHITE)
            # Sombra del texto
            tipo_shadow_surf = pygame.Surface((tipo.get_width() + 2, tipo.get_height() + 2), pygame.SRCALPHA)
            tipo_shadow = self.font_small.render(carta.tipo.upper(), True, (0, 0, 0))
            tipo_shadow_surf.set_alpha(150)
            tipo_shadow_surf.blit(tipo_shadow, (1, 1))
            card_surf.blit(tipo_shadow_surf, (card_width//2 - tipo.get_width()//2 - 1, card_height//2 + 24))
            card_surf.blit(tipo, (card_width//2 - tipo.get_width()//2, card_height//2 + 25))
        
        # === APLICAR RECORTE REDONDEADO (igual que assets) ===
        card_surf = self._apply_rounded_clip(card_surf)
        
        # === APLICAR TRANSPARENCIA SI ES NECESARIO ===
        if transparent:
            card_surf.set_alpha(alpha)
        
        # Blitear carta completa usando helper limpio
        blit_card_clean(self.screen, card_surf, card_rect.x, card_rect.y)
        
        return card_rect
    
    def draw_card_style(self, x, y, carta, jugable=True):
        """Wrapper para compatibilidad: usa render_card unificado"""
        return self.render_card(x, y, carta, face_down=False, jugable=jugable, show_badge=False, with_shadow=False)
    
    def draw_card_style_transparent(self, x, y, carta, jugable=True, alpha=180):
        """Wrapper para compatibilidad: usa render_card unificado con transparencia"""
        return self.render_card(x, y, carta, face_down=False, transparent=True, alpha=alpha, 
                               jugable=jugable, show_badge=False, with_shadow=False)

    # ==== Assets ====
    def _load_assets(self) -> None:
        # Crear carpetas si no existen
        try:
            os.makedirs(self.cards_dir, exist_ok=True)
            os.makedirs(self.sfx_dir, exist_ok=True)
        except Exception:
            pass
        # Intentar cargar theme.json (opcional)
        theme_path = os.path.join(self.assets_dir, 'theme.json')
        if os.path.isfile(theme_path):
            try:
                with open(theme_path, 'r', encoding='utf-8') as f:
                    self.theme = json.load(f)
            except Exception:
                self.theme = {}

        # Cargar imágenes disponibles por convención (temática API)
        mapping = []
        # Aspectos
        for color in ASPECTOS + ['multicolor']:
            mapping.append(('aspecto', color, f"aspecto_{color}.png"))
            # Compatibilidad: también buscar nombres antiguos
            color_legacy = {'seguridad': 'corazon', 'documentacion': 'cerebro', 
                          'gobierno': 'huesos', 'performance': 'estomago'}.get(color, color)
            if color != 'multicolor':
                mapping.append(('aspecto', color, f"organo_{color_legacy}.png"))
        
        # Ataques y Problemas
        # Seguridad: nombres específicos
        for nombre_ataque in ATAQUES_SEGURIDAD:
            # Normalizar nombre para archivo (sin espacios, sin caracteres especiales)
            nombre_file = nombre_ataque.lower().replace(' ', '_').replace('/', '_')
            mapping.append(('ataque', 'seguridad', f"ataque_seguridad_{nombre_file}.png"))
            mapping.append(('ataque', 'seguridad', f"ataque_{nombre_file}.png"))
            # Fallback genérico
            mapping.append(('ataque', 'seguridad', f"ataque_seguridad.png"))
        # Problemas para otros aspectos
        for color in ['documentacion', 'gobierno', 'performance']:
            mapping.append(('problema', color, f"problema_{color}.png"))
        # Wildcard
        mapping.append(('ataque', 'multicolor', f"ataque_multicolor.png"))
        mapping.append(('problema', 'multicolor', f"problema_multicolor.png"))
        # Compatibilidad: nombres antiguos
        for color_legacy in ['corazon', 'cerebro', 'huesos', 'estomago', 'multicolor']:
            mapping.append(('ataque', color_legacy, f"virus_{color_legacy}.png"))
            mapping.append(('problema', color_legacy, f"virus_{color_legacy}.png"))
        
        # Protecciones
        # Seguridad: nombres específicos
        for nombre_proteccion in PROTECCIONES_SEGURIDAD:
            # Normalizar nombre para archivo
            nombre_file = nombre_proteccion.lower().replace(' ', '_').replace('/', '_')
            mapping.append(('proteccion', 'seguridad', f"proteccion_seguridad_{nombre_file}.png"))
            mapping.append(('proteccion', 'seguridad', f"proteccion_{nombre_file}.png"))
            # Fallback genérico
            mapping.append(('proteccion', 'seguridad', f"proteccion_seguridad.png"))
        # Protecciones para otros aspectos
        for color in ['documentacion', 'gobierno', 'performance']:
            mapping.append(('proteccion', color, f"proteccion_{color}.png"))
        # Wildcard
        mapping.append(('proteccion', 'multicolor', f"proteccion_multicolor.png"))
        # Compatibilidad: nombres antiguos
        for color_legacy in ['corazon', 'cerebro', 'huesos', 'estomago', 'multicolor']:
            mapping.append(('proteccion', color_legacy, f"medicina_{color_legacy}.png"))
        
        # Intervenciones
        intervenciones_map = {
            'refactoring': 'refactoring',
            'migracion': 'migracion',
            'activo_activo': 'activo_activo',
            'code_freeze': 'code_freeze',
            'rollback': 'rollback',
            # Compatibilidad
            'trasplante': 'refactoring',
            'ladrón': 'migracion',
            'contagio': 'activo_activo',
            'guante': 'code_freeze',
            'error': 'rollback'
        }
        for subtipo, nombre_file in intervenciones_map.items():
            mapping.append(('intervencion', subtipo, f"intervencion_{nombre_file}.png"))
            # Fallback genérico
            mapping.append(('intervencion', subtipo, f"tratamiento_{subtipo}.png"))
        
        # Cargar imágenes (sin duplicados)
        loaded_keys = set()
        for tipo, color, filename in mapping:
            key = f"{tipo}:{color}"
            if key in loaded_keys:
                continue  # Ya cargada esta combinación
            path = os.path.join(self.cards_dir, filename)
            if os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.card_images[key] = img
                    loaded_keys.add(key)
                    print(f"[DEBUG] ✓ Cargada: {filename} -> {key}")
                except Exception as e:
                    print(f"[DEBUG] ✗ Error cargando {filename}: {e}")
        # Cargar imágenes de jugadores (genéricas)
        players_dir = os.path.join(self.assets_dir, 'players')
        # Crear directorio si no existe
        try:
            os.makedirs(players_dir, exist_ok=True)
        except Exception:
            pass
        
        # Cargar imagen de jugador humano
        player_path = os.path.join(players_dir, 'player.png')
        if os.path.isfile(player_path):
            try:
                loaded_img = pygame.image.load(player_path).convert_alpha()
                # NO procesar el fondo del Player 1 - ya está bien, solo hacer circular
                # Convertir a círculo con fondo transparente (sin negro) - tamaño mayor para mejor visibilidad
                self.player_image = self._create_circular_avatar(loaded_img, 100)
                print(f"[DEBUG] ✓ Cargada imagen de jugador: {player_path} ({loaded_img.get_width()}x{loaded_img.get_height()} -> 100x100 circular)")
            except Exception as e:
                print(f"[DEBUG] ✗ Error cargando player.png: {e}")
                self.player_image = None
        else:
            print(f"[DEBUG] ✗ No se encontró: {player_path}")
            self.player_image = None
        
        # Cargar imagen de bot
        bot_path = os.path.join(players_dir, 'bot.png')
        if os.path.isfile(bot_path):
            try:
                # Cargar con convert_alpha para preservar transparencia
                loaded_img = pygame.image.load(bot_path).convert_alpha()
                # PREPROCESAR: Eliminar fondo negro antes de crear el avatar circular
                # Esto elimina cualquier fondo negro que pueda tener la imagen
                cleaned_img = self._remove_black_background(loaded_img)
                # Convertir a círculo con fondo transparente (sin negro)
                self.bot_image = self._create_circular_avatar(cleaned_img, 100)
                print(f"[DEBUG] ✓ Cargada imagen de bot: {bot_path} ({loaded_img.get_width()}x{loaded_img.get_height()} -> 100x100 circular)")
            except Exception as e:
                print(f"[DEBUG] ✗ Error cargando bot.png: {e}")
                self.bot_image = None
        else:
            print(f"[DEBUG] ✗ No se encontró: {bot_path}")
            self.bot_image = None
        
        # Generar avatares programáticamente SOLO si no hay imágenes (tamaño mayor para mejor visibilidad)
        if self.player_image is None:
            self.player_avatar_generated = self._generate_player_avatar(100, is_bot=False)
            print(f"[DEBUG] → Generado avatar programático para jugador humano")
        else:
            self.player_avatar_generated = None
            print(f"[DEBUG] → Usando imagen cargada para jugador humano")
            
        if self.bot_image is None:
            self.bot_avatar_generated = self._generate_player_avatar(100, is_bot=True)
            print(f"[DEBUG] → Generado avatar programático para bot")
        else:
            self.bot_avatar_generated = None
            print(f"[DEBUG] → Usando imagen cargada para bot")
        
        # Cargar dorso de carta
        # Prioridad theme.json
        theme_back = None
        try:
            theme_back = self.theme.get('images', {}).get('cardBack')
        except Exception:
            theme_back = None
        back_candidates = []
        if theme_back:
            back_candidates.append(theme_back)
        back_candidates += [os.path.join(self.cards_dir, n) for n in ['back.png', 'card_back.png', 'dorso.png']]
        for p in back_candidates:
            if os.path.isfile(p):
                try:
                    self.card_back = pygame.image.load(p).convert_alpha()
                except Exception:
                    self.card_back = None
                break

        # Cargar iconos de la barra inferior
        self._load_icons()
        
        # Cargar SFX opcionales (permitir override por theme)
        sfx_names = ['place', 'infect', 'destroy', 'cure', 'vaccinate', 'immunize']
        try:
            pygame.mixer.init()
        except Exception:
            return
        for name in sfx_names:
            theme_p = None
            try:
                theme_p = self.theme.get('sfx', {}).get(name)
            except Exception:
                theme_p = None
            p = theme_p if theme_p else os.path.join(self.sfx_dir, f"{name}.wav")
            if os.path.isfile(p):
                try:
                    self.sounds[name] = pygame.mixer.Sound(p)
                except Exception:
                    self.sounds[name] = None
            else:
                self.sounds[name] = None

    def _load_icons(self) -> None:
        """Carga los iconos de la barra inferior desde assets/icons."""
        icon_size = 32  # Tamaño base de los iconos
        icon_names = {
            'sound_on': 'sound_on.png',
            'sound_off': 'sound_off.png',
            'new_game': 'new_game.png',
            'diary': 'diary.png',
            'help': 'help.png',
            'toggle_up': 'toggle_up.png',
            'toggle_down': 'toggle_down.png',
        }
        
        for attr_name, filename in icon_names.items():
            icon_path = os.path.join(self.icons_dir, filename)
            if os.path.isfile(icon_path):
                try:
                    icon = pygame.image.load(icon_path).convert_alpha()
                    # Escalar al tamaño deseado manteniendo aspect ratio
                    icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                    setattr(self, f'icon_{attr_name}', icon)
                    print(f"[DEBUG] ✓ Cargado icono: {filename}")
                except Exception as e:
                    print(f"[DEBUG] ✗ Error cargando {filename}: {e}")
                    setattr(self, f'icon_{attr_name}', None)
            else:
                print(f"[DEBUG] ✗ No se encontró: {icon_path}")
                setattr(self, f'icon_{attr_name}', None)

    def _create_rounded_surface(self, width: int, height: int, fill_color: Optional[Tuple[int, int, int, int]] = None) -> pygame.Surface:
        """Crea una superficie con esquinas redondeadas PERFECTAS, sin artefactos.
        Método: crea superficie transparente y dibuja solo dentro del área redondeada usando clipping."""
        radius = get_card_border_radius(width, height)
        
        # Crear superficie completamente transparente
        result = pygame.Surface((width, height), pygame.SRCALPHA)
        result.fill((0, 0, 0, 0))
        
        if radius <= 0:
            if fill_color:
                result.fill(fill_color)
            return result
        
        # Crear máscara de forma redondeada usando clipping
        # Dibujar el rectángulo central (sin esquinas)
        if fill_color:
            # Rectángulo central
            if radius < width // 2 and radius < height // 2:
                center_rect = pygame.Rect(radius, 0, width - 2 * radius, height)
                result.fill(fill_color, center_rect)
                center_rect = pygame.Rect(0, radius, width, height - 2 * radius)
                result.fill(fill_color, center_rect)
            
            # Dibujar círculos en las esquinas para forma redondeada perfecta
            # Esquina superior izquierda
            center_x, center_y = radius, radius
            for y in range(radius + 1):
                for x in range(radius + 1):
                    dx = x - center_x
                    dy = y - center_y
                    if dx*dx + dy*dy <= radius*radius:
                        result.set_at((x, y), fill_color)
            
            # Esquina superior derecha
            center_x = width - radius
            center_y = radius
            for y in range(radius + 1):
                for x in range(width - radius - 1, width):
                    dx = x - center_x
                    dy = y - center_y
                    if dx*dx + dy*dy <= radius*radius:
                        result.set_at((x, y), fill_color)
            
            # Esquina inferior izquierda
            center_x = radius
            center_y = height - radius
            for y in range(height - radius - 1, height):
                for x in range(radius + 1):
                    dx = x - center_x
                    dy = y - center_y
                    if dx*dx + dy*dy <= radius*radius:
                        result.set_at((x, y), fill_color)
            
            # Esquina inferior derecha
            center_x = width - radius
            center_y = height - radius
            for y in range(height - radius - 1, height):
                for x in range(width - radius - 1, width):
                    dx = x - center_x
                    dy = y - center_y
                    if dx*dx + dy*dy <= radius*radius:
                        result.set_at((x, y), fill_color)
        
        return result
    
    def _apply_rounded_clip(self, surface: pygame.Surface) -> pygame.Surface:
        """Wrapper que usa la función global apply_rounded_clip."""
        return apply_rounded_clip(surface)
    
    def _get_card_surface(self, carta: Carta, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        # Intentar buscar por tipo:color primero
        key = f"{carta.tipo}:{carta.color}"
        surf = self.card_images.get(key)
        
        # Si no se encuentra y es una carta con nombre específico (ataques/protecciones de seguridad),
        # intentar buscar por nombre normalizado
        if surf is None and carta.nombre:
            # Normalizar nombre para búsqueda
            nombre_normalizado = carta.nombre.lower().replace(' ', '_').replace('/', '_')
            # Intentar varias variantes de clave
            posibles_claves = [
                f"{carta.tipo}:{carta.color}:{nombre_normalizado}",
                f"{carta.tipo}_{nombre_normalizado}",
                f"{nombre_normalizado}",
            ]
            for clave_alt in posibles_claves:
                if clave_alt in self.card_images:
                    surf = self.card_images[clave_alt]
                    break
        
        # Fallback: si es ataque/problema de seguridad, usar genérico
        if surf is None and carta.tipo in ['ataque', 'problema'] and carta.color == 'seguridad':
            key_fallback = f"ataque:seguridad"
            surf = self.card_images.get(key_fallback)
        
        # Fallback: si es protección de seguridad, usar genérico
        if surf is None and carta.tipo == 'proteccion' and carta.color == 'seguridad':
            key_fallback = f"proteccion:seguridad"
            surf = self.card_images.get(key_fallback)
        
        # Compatibilidad: buscar nombres antiguos
        if surf is None:
            # Mapeo de tipos nuevos a antiguos
            tipo_legacy_map = {
                'aspecto': 'organo',
                'ataque': 'virus',
                'problema': 'virus',
                'proteccion': 'medicina',
                'intervencion': 'tratamiento'
            }
            tipo_legacy = tipo_legacy_map.get(carta.tipo, carta.tipo)
            # Mapeo de colores nuevos a antiguos
            color_legacy_map = {
                'seguridad': 'corazon',
                'documentacion': 'cerebro',
                'gobierno': 'huesos',
                'performance': 'estomago'
            }
            color_legacy = color_legacy_map.get(carta.color, carta.color)
            key_legacy = f"{tipo_legacy}:{color_legacy}"
            surf = self.card_images.get(key_legacy)
        
        if surf is None:
            return None
        
        w, h = size
        if surf.get_width() != w or surf.get_height() != h:
            # Escalar manteniendo aspect ratio correcto (280×380 = 1.357)
            surf = self._scale_image_preserving_ratio(surf, (w, h))
        
        # Asegurar formato con alpha antes de recortar
        if surf is not None:
            surf = surf.convert_alpha()
        
        # Aplicar recorte redondeado a TODAS las cartas con assets
        # BLEND_RGBA_MIN eliminará automáticamente cualquier fondo negro
        surf = self._apply_rounded_clip(surf)
        return surf
    
    def _aggressive_remove_background(self, img: pygame.Surface) -> pygame.Surface:
        """Elimina el fondo de forma muy agresiva usando múltiples técnicas."""
        result = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        w, h = img.get_size()
        
        # Obtener muestra grande del borde (más confiable)
        sample_size = min(50, w // 4, h // 4)  # Muestra de hasta 50 píxeles o 25% del tamaño
        border_samples = []
        
        # Muestrear bordes superior e inferior
        for x in range(0, w, max(1, w // sample_size)):
            border_samples.append(img.get_at((x, 0)))
            border_samples.append(img.get_at((x, h-1)))
        # Muestrear bordes laterales
        for y in range(0, h, max(1, h // sample_size)):
            border_samples.append(img.get_at((0, y)))
            border_samples.append(img.get_at((w-1, y)))
        
        if len(border_samples) > 0:
            # Agrupar colores similares (threshold de 30)
            color_groups = {}
            for pixel in border_samples:
                rgb = pixel[:3]
                # Agrupar por rangos de color
                key = (rgb[0] // 30 * 30, rgb[1] // 30 * 30, rgb[2] // 30 * 30)
                if key not in color_groups:
                    color_groups[key] = []
                color_groups[key].append(rgb)
            
            # Encontrar el grupo de color más común (probablemente el fondo)
            most_common_key = max(color_groups.items(), key=lambda x: len(x[1]))[0]
            bg_color = most_common_key
            threshold = 50  # Threshold muy amplio
            
            # Recorrer TODOS los píxeles
            for x in range(w):
                for y in range(h):
                    try:
                        pixel_color = img.get_at((x, y))
                        pixel_rgb = pixel_color[:3]
                        pixel_alpha = pixel_color[3] if len(pixel_color) > 3 else 255
                        
                        # Si el píxel es similar al fondo O es muy transparente, hacerlo completamente transparente
                        color_match = abs(pixel_rgb[0] - bg_color[0]) <= threshold and \
                                    abs(pixel_rgb[1] - bg_color[1]) <= threshold and \
                                    abs(pixel_rgb[2] - bg_color[2]) <= threshold
                        
                        if color_match or pixel_alpha < 128:  # También eliminar píxeles semi-transparentes
                            result.set_at((x, y), (0, 0, 0, 0))
                        else:
                            # Mantener el píxel pero asegurar que tenga alpha completo
                            result.set_at((x, y), (*pixel_rgb, 255))
                    except:
                        result.set_at((x, y), (0, 0, 0, 0))
        else:
            result.blit(img, (0, 0))
        
        return result
    
    def _remove_black_background(self, img: pygame.Surface) -> pygame.Surface:
        """Elimina específicamente el fondo negro de una imagen, haciendo transparentes los píxeles negros o muy oscuros."""
        result = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        w, h = img.get_size()
        
        # Threshold para detectar negro/oscuro (RGB < 30)
        black_threshold = 30
        
        for x in range(w):
            for y in range(h):
                try:
                    pixel = img.get_at((x, y))
                    r, g, b, a = pixel
                    
                    # Si el píxel es negro o muy oscuro (RGB < threshold), hacerlo transparente
                    if r < black_threshold and g < black_threshold and b < black_threshold:
                        result.set_at((x, y), (0, 0, 0, 0))
                    else:
                        # Mantener el píxel original
                        result.set_at((x, y), pixel)
                except:
                    result.set_at((x, y), (0, 0, 0, 0))
        
        return result
    
    def _remove_background_if_needed(self, img: pygame.Surface) -> pygame.Surface:
        """Elimina el fondo de la imagen de manera agresiva usando múltiples métodos."""
        result = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        w, h = img.get_size()
        
        # Método 1: Detectar color de fondo en los bordes (más confiable que esquinas)
        border_pixels = []
        # Muestra de píxeles del borde (todos los lados)
        for x in range(w):
            border_pixels.append(img.get_at((x, 0)))  # Borde superior
            border_pixels.append(img.get_at((x, h-1)))  # Borde inferior
        for y in range(h):
            border_pixels.append(img.get_at((0, y)))  # Borde izquierdo
            border_pixels.append(img.get_at((w-1, y)))  # Borde derecho
        
        # Encontrar el color más común en los bordes (probablemente el fondo)
        color_counts = {}
        for pixel in border_pixels:
            rgb = pixel[:3]  # Solo RGB, ignorar alpha
            # Agrupar colores similares (threshold de 20)
            key = (rgb[0] // 20 * 20, rgb[1] // 20 * 20, rgb[2] // 20 * 20)
            color_counts[key] = color_counts.get(key, 0) + 1
        
        if color_counts:
            # El color más común en los bordes es probablemente el fondo
            bg_color = max(color_counts.items(), key=lambda x: x[1])[0]
            threshold = 40  # Threshold más amplio para detectar variaciones del fondo
            
            # Recorrer todos los píxeles y hacer transparentes los que coinciden con el fondo
            for x in range(w):
                for y in range(h):
                    try:
                        pixel_color = img.get_at((x, y))
                        pixel_rgb = pixel_color[:3]
                        
                        # Si el píxel es similar al color de fondo, hacerlo transparente
                        if abs(pixel_rgb[0] - bg_color[0]) <= threshold and \
                           abs(pixel_rgb[1] - bg_color[1]) <= threshold and \
                           abs(pixel_rgb[2] - bg_color[2]) <= threshold:
                            # Hacer transparente
                            result.set_at((x, y), (0, 0, 0, 0))
                        else:
                            # Copiar el píxel original
                            result.set_at((x, y), pixel_color)
                    except:
                        pass
        else:
            # Si no se pudo detectar, simplemente copiar la imagen
            result.blit(img, (0, 0))
        
        return result
    
    def _create_circular_avatar_strict(self, img: pygame.Surface, size: int) -> pygame.Surface:
        """Crea avatar circular perfecto con fondo 100% transparente usando método correcto."""
        return self._create_circular_avatar(img, size)
    
    def _create_circular_avatar(self, img: pygame.Surface, size: int) -> pygame.Surface:
        """Crea avatar circular con efectos visuales profesionales - VERSIÓN SIMPLIFICADA."""
        # Crear superficie con transparencia TOTAL garantizada
        avatar = pygame.Surface((size, size), pygame.SRCALPHA)
        avatar.fill((0, 0, 0, 0))  # Transparencia total inicial
        
        center = size // 2
        border_outer_radius = int(size * 0.48)
        border_inner_radius = int(size * 0.44)
        image_radius = int(size * 0.46)
        
        # === PASO 1: BORDE METÁLICO PLATEADO ===
        border_width = border_outer_radius - border_inner_radius
        num_rings = 20
        for i in range(num_rings):
            progress = i / num_rings
            base = 155
            r = int(base + progress * (255 - base))
            g = int(base + progress * (255 - base))
            b = int(base + progress * (255 - base))
            radius = border_outer_radius - int(i * (border_width / num_rings))
            thickness = max(1, int((border_width / num_rings)) + 1)
            pygame.draw.circle(avatar, (r, g, b, 255), (center, center), radius, thickness)
        
        # Highlight superior
        for angle_deg in range(-75, 76, 1):
            angle = math.radians(angle_deg - 90)
            intensity = math.exp(-(angle_deg**2) / 900.0)
            alpha = int(230 * intensity)
            if alpha > 15:
                x1 = center + int(border_inner_radius * math.cos(angle))
                y1 = center + int(border_inner_radius * math.sin(angle))
                x2 = center + int(border_outer_radius * math.cos(angle))
                y2 = center + int(border_outer_radius * math.sin(angle))
                pygame.draw.line(avatar, (255, 255, 255, alpha), (x1, y1), (x2, y2), 3)
        
        # Borde externo
        pygame.draw.circle(avatar, (170, 180, 190, 255), (center, center), border_outer_radius, 4)
        pygame.draw.circle(avatar, (230, 235, 240, 255), (center, center), border_outer_radius - 1, 2)
        pygame.draw.circle(avatar, (255, 255, 255, 220), (center, center), border_outer_radius - 2, 1)
        
        # === PASO 2: IMAGEN DEL JUGADOR ===
        img_w, img_h = img.get_width(), img.get_height()
        max_diameter = image_radius * 2
        zoom_factor = 1.13
        target_diameter = int(max_diameter * zoom_factor)
        img_max_dimension = max(img_w, img_h)
        scale = target_diameter / img_max_dimension
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        if new_w > max_diameter:
            scale = max_diameter / new_w
            new_w = int(new_w * scale)
            new_h = int(new_h * scale)
        if new_h > max_diameter:
            scale = max_diameter / new_h
            new_w = int(new_w * scale)
            new_h = int(new_h * scale)
        
        try:
            scaled_img = pygame.transform.smoothscale(img, (new_w, new_h))
        except Exception:
            scaled_img = pygame.transform.scale(img, (new_w, new_h))
        
        x_offset = center - new_w // 2
        y_offset = center - new_h // 2
        
        # Copiar imagen dentro del círculo - INTERIOR OPACO
        for x in range(size):
            for y in range(size):
                dx = x - center
                dy = y - center
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= image_radius:
                    img_x = x - x_offset
                    img_y = y - y_offset
                    if 0 <= img_x < new_w and 0 <= img_y < new_h:
                        try:
                            pixel = scaled_img.get_at((img_x, img_y))
                            r, g, b, a = pixel
                            # Copiar TODOS los píxeles con alpha > 20, asegurando opacidad dentro del círculo
                            if a > 20:
                                # Asegurar que el píxel sea opaco (alpha = 255) dentro del círculo
                                avatar.set_at((x, y), (r, g, b, 255))
                            else:
                                # Si el píxel es transparente, usar un fondo opaco (puede ser negro u otro color)
                                # Para mantener la imagen visible, usar el color del píxel si existe, o negro opaco
                                avatar.set_at((x, y), (r, g, b, 255))
                        except:
                            # Si hay error, poner un píxel opaco (negro) para que el interior no sea transparente
                            avatar.set_at((x, y), (0, 0, 0, 255))
                    else:
                        # Si está dentro del círculo pero fuera de la imagen, poner fondo opaco
                        avatar.set_at((x, y), (0, 0, 0, 255))
        
        # === PASO 3: SOMBRA INTERIOR ===
        for i in range(4):
            alpha = int(30 - i * 7)
            if alpha > 0:
                radius = image_radius - i
                pygame.draw.circle(avatar, (0, 0, 0, alpha), (center, center), radius, 1)
        
        # === PASO 4: LIMPIEZA FINAL - GARANTIZAR TRANSPARENCIA TOTAL FUERA DEL BORDE ===
        # Crear superficie final completamente limpia con SRCALPHA
        final = pygame.Surface((size, size), pygame.SRCALPHA)
        # CRÍTICO: Llenar COMPLETAMENTE con transparencia total antes de copiar nada
        final.fill((0, 0, 0, 0))
        
        # PASO 4A: Copiar solo lo que está dentro del borde exterior
        for x in range(size):
            for y in range(size):
                dist = math.sqrt((x - center)**2 + (y - center)**2)
                
                # Si está fuera del borde exterior, NO copiar nada (ya está transparente)
                if dist > border_outer_radius:
                    continue  # No hacer nada, ya es transparente
                
                pixel = avatar.get_at((x, y))
                r, g, b, a = pixel
                
                # Solo copiar si tiene alpha > 0
                if a > 0:
                    # Si está DENTRO del círculo de imagen, copiar TODO y asegurar OPACIDAD
                    if dist <= image_radius:
                        # Asegurar que el píxel sea completamente opaco dentro del círculo
                        final.set_at((x, y), (r, g, b, 255))
                    # Si está FUERA del círculo de imagen pero dentro del borde
                    elif dist > image_radius:
                        # Eliminar negro puro (0,0,0) - esto es fondo residual
                        if r == 0 and g == 0 and b == 0:
                            continue  # No copiar negro puro fuera de la imagen
                        # Si está en el borde metálico, copiar (es plateado, no negro)
                        elif dist >= border_inner_radius and dist <= border_outer_radius:
                            final.set_at((x, y), pixel)
                        # Entre image_radius y border_inner: eliminar negro puro
                        elif r > 0 or g > 0 or b > 0:
                            final.set_at((x, y), pixel)
        
        # PASO 5: VERIFICACIÓN FINAL ABSOLUTA - Forzar transparencia fuera del borde
        # Esto es una garantía adicional para asegurar que NO haya píxeles fuera del borde
        for x in range(size):
            for y in range(size):
                dist = math.sqrt((x - center)**2 + (y - center)**2)
                if dist > border_outer_radius:
                    # Forzar transparencia absoluta fuera del borde
                    pixel_check = final.get_at((x, y))
                    if pixel_check[3] > 0:  # Si tiene alpha > 0, forzar a transparente
                        final.set_at((x, y), (0, 0, 0, 0))
        
        # PASO 6: VERIFICACIÓN FINAL EXTRA - Eliminar cualquier píxel negro fuera del círculo
        # Esto asegura que no quede ningún rastro de fondo negro
        for x in range(size):
            for y in range(size):
                dist = math.sqrt((x - center)**2 + (y - center)**2)
                if dist > image_radius:
                    pixel_check = final.get_at((x, y))
                    r, g, b, a = pixel_check
                    # Si es negro puro (0,0,0) y está fuera del círculo de imagen, eliminarlo
                    if a > 0 and r == 0 and g == 0 and b == 0:
                        # Verificar si está en el borde metálico (que no es negro)
                        if dist < border_inner_radius or dist > border_outer_radius:
                            # Fuera del borde metálico: eliminar negro
                            final.set_at((x, y), (0, 0, 0, 0))
        
        return final
    
    def _scale_image_preserving_ratio(self, img: pygame.Surface, target_size: Tuple[int, int]) -> pygame.Surface:
        """Escala una imagen manteniendo el aspect ratio correcto de cartas (280×380 = 1.357).
        Si la imagen original tiene un ratio diferente, se ajusta para que encaje correctamente."""
        target_w, target_h = target_size
        target_ratio = target_w / target_h  # Debería ser ~1.357 (280/380)
        
        img_w, img_h = img.get_width(), img.get_height()
        img_ratio = img_w / img_h
        
        # Si el ratio de la imagen es diferente, escalamos para que encaje en el tamaño objetivo
        # manteniendo el aspecto de carta (vertical rectangular)
        if abs(img_ratio - target_ratio) > 0.01:  # Si hay diferencia significativa
            # Calcular el tamaño que mantiene el ratio objetivo pero encaja en el target
            if img_ratio > target_ratio:
                # Imagen más ancha: ajustamos altura
                new_h = int(target_w / target_ratio)
                new_w = target_w
            else:
                # Imagen más alta: ajustamos ancho
                new_w = int(target_h * target_ratio)
                new_h = target_h
            try:
                scaled = pygame.transform.smoothscale(img, (new_w, new_h))
            except Exception:
                scaled = pygame.transform.scale(img, (new_w, new_h))
            # Si hay diferencia, crear surface del tamaño exacto y centrar
            if new_w != target_w or new_h != target_h:
                final = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
                x_offset = (target_w - new_w) // 2
                y_offset = (target_h - new_h) // 2
                final.blit(scaled, (x_offset, y_offset))
                return final
            return scaled
        else:
            # Ratio correcto, escalar normalmente
            try:
                return pygame.transform.smoothscale(img, (target_w, target_h))
            except Exception:
                return pygame.transform.scale(img, (target_w, target_h))

    def _get_slot_surface(self, color: str, state: str, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        """Devuelve surface del órgano en tablero según estado usando assets existentes.
        Regla: sano->organo_color, vacunado/inmunizado->medicina_color, infecto->virus_color.
        Cacheado por (color,state,size)."""
        key = (color, state, size)
        if key in self.slot_image_cache:
            # Si ya está en caché, asegurarse de que tenga la máscara aplicada
            cached = self.slot_image_cache[key]
            if cached is not None:
                # Aplicar recorte si no está aplicado (por compatibilidad con caché antigua)
                return self._apply_rounded_clip(cached)
            return cached
        # 1) Intentar theme.json explícito
        try:
            state_key = {'SANO': 'sano', 'VACUNADO': 'vacunado', 'INMUNIZADO': 'inmunizado', 'INFECTO': 'infecto'}[state]
        except Exception:
            state_key = None
        if state_key:
            try:
                path = self.theme.get('images', {}).get('organs', {}).get(color, {}).get(state_key)
            except Exception:
                path = None
            if path and os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    w, h = size
                    try:
                        scaled = pygame.transform.smoothscale(img, (w, h))
                    except Exception:
                        scaled = pygame.transform.scale(img, (w, h))
                    # Aplicar recorte redondeado antes de guardar en caché
                    scaled = self._apply_rounded_clip(scaled)
                    self.slot_image_cache[key] = scaled
                    return scaled
                except Exception:
                    pass
        # 2) Fallback por convención
        # IMPORTANTE: En el área central solo deben aparecer aspectos, no protecciones ni ataques
        # Los estados (PROTEGIDO, FORTALECIDO, VULNERABLE, SALUDABLE) se muestran visualmente con colores/overlays
        # pero la carta base siempre es un aspecto
        tipo_src = 'aspecto'  # Siempre usar aspecto como base, independientemente del estado
        if tipo_src is None:
            self.slot_image_cache[key] = None
            return None
        surf = self.card_images.get(f"{tipo_src}:{color}")
        if surf is None:
            self.slot_image_cache[key] = None
            return None
        w, h = size
        try:
            scaled = pygame.transform.smoothscale(surf, (w, h))
        except Exception:
            scaled = pygame.transform.scale(surf, (w, h))
        # Aplicar recorte redondeado antes de guardar en caché (usar _apply_rounded_clip, NO _apply_rounded_mask)
        scaled = self._apply_rounded_clip(scaled)
        self.slot_image_cache[key] = scaled
        return scaled

    def render_mano(self):
        assert self.screen is not None
        # Mano del jugador humano en la parte inferior centrada
        jugador_humano = self.jugadores[0]
        gap = 140  # Espaciado ajustado para cartas más pequeñas
        count = max(1, len(jugador_humano.mano))
        total_w = (count - 1) * gap
        # Posición ajustada para las cartas
        card_width, card_height = CARD_WIDTH, CARD_HEIGHT
        y_pos = WINDOW_HEIGHT - card_height // 2 - 90  # Ajustado para dejar espacio para la barra inferior
        start_x = WINDOW_WIDTH // 2 - total_w // 2
        for i, carta in enumerate(jugador_humano.mano):
            if self.carta_arrastrando and self.carta_arrastrando[0] == carta:
                continue
            x = start_x + i * gap
            # Solo marcamos como jugable si es el turno del jugador humano
            jugable, _ = self.es_jugable(carta, jugador_humano) if self.turno == 0 else (False, '')
            highlight = (self.hover_hand_idx == i and not self.carta_arrastrando)
            sel = (self.selected_hand_idx == i)
            self.draw_card_style(x, y_pos, carta, jugable or highlight or sel)
            # Resaltar si está seleccionada para descartar con efecto pulsante dorado
            if i in self.discard_selection:
                # Efecto de pulso usando pygame.time.get_ticks()
                pulse = abs((pygame.time.get_ticks() // 150) % 10 - 5) + 5
                border_color = (255, 215, 0) if (pygame.time.get_ticks() // 300) % 2 == 0 else (255, 165, 0)
                # Dibujar highlight como overlay con SRCALPHA
                ov = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
                radius = get_card_border_radius(CARD_WIDTH, CARD_HEIGHT)
                pygame.draw.rect(ov, (*border_color, 255), (0, 0, CARD_WIDTH, CARD_HEIGHT), pulse, border_radius=radius)
                self.screen.blit(ov, (x - CARD_WIDTH//2, y_pos - CARD_HEIGHT//2))
        # Etiqueta
        label = self.font_medium.render('Mano Jugador 1', True, COLOR_WHITE)
        lx = WINDOW_WIDTH // 2 - label.get_width() // 2 - 24
        ly = y_pos + 22
        self._draw_person_icon(lx, ly + 6, 20)
        self.screen.blit(label, (lx + 28, ly))

    def render_mazos(self):
        """Renderiza mazos y descarte en la zona central del tablero."""
        assert self.screen is not None
        # Baraja movida a la zona izquierda (donde hay espacio disponible)
        # Centrada verticalmente pero fuera del área de cartas del jugador
        # La mano del jugador está alrededor de y=810 (WINDOW_HEIGHT - 90)
        # Centrar verticalmente en el área disponible (entre zonas de jugadores)
        deck_y = 380  # Un poco más arriba que el centro, fuera de la zona de cartas del jugador
        # Baraja: usar el mismo tamaño estándar de cartas (sin escalado adicional)
        deck_w = CARD_WIDTH  # Mismo tamaño que todas las cartas
        deck_h = CARD_HEIGHT
        # Posición mucho más a la izquierda, cerca del borde izquierdo
        deck_x = 50  # 300 píxeles más a la izquierda que antes (x=150 - 300 = -150, pero limitado a 50)
        self.deck_rect = pygame.Rect(deck_x, deck_y - deck_h//2, deck_w, deck_h)
        # Descarte permanece en la zona central
        center_y = 330
        self.disc_rect = pygame.Rect(WINDOW_WIDTH//2 + 110, center_y - deck_h//2, deck_w, deck_h)
        
        # === RENDERIZADO DEL MAZO (BARAJА) ===
        # Mostrar cartas apiladas boca abajo igual que el descarte
        if len(self.mazo) == 0:
            # Vacío: mostrar fondo sutil (transparente)
            deck_radius = CARD_BORDER_RADIUS
            # No dibujar nada, dejar transparente
        else:
            # Hay cartas: mostrar apiladas boca abajo usando render_card unificado
            # Limitar visualmente a las últimas 5 cartas para no sobrecargar
            cards_to_show = min(5, len(self.mazo))
            offset_x = 3  # Offset horizontal para efecto de apilado
            offset_y = 2  # Offset vertical para efecto de apilado
            
            # Mostrar cartas desde la más antigua (abajo) hasta la más reciente (arriba)
            start_idx = max(0, len(self.mazo) - cards_to_show)
            for i in range(start_idx, len(self.mazo)):
                card_idx = i - start_idx
                card_x = self.deck_rect.centerx + card_idx * offset_x
                card_y = self.deck_rect.centery + card_idx * offset_y
                # Usar render_card unificado para el dorso sin sombra
                self.render_card(card_x, card_y, face_down=True, with_shadow=False)
        
        # Borde del mazo (ELIMINADO - solo confundía)
        # pygame.draw.rect(self.screen, COLOR_GOLD, self.deck_rect, 2, border_radius=CARD_BORDER_RADIUS)
        
        # === RENDERIZADO DEL DESCARTE ===
        # Si está vacío, no mostrar nada (transparente)
        # Si hay cartas, mostrar cartas apiladas boca abajo
        if len(self.descarte) == 0:
            # Vacío: solo mostrar zona de drop si se está arrastrando
            if self.is_dragging or self.carta_arrastrando:
                drop_zone = self.disc_rect.inflate(80, 80)
                drop_radius = get_card_border_radius(drop_zone.width, drop_zone.height)
                blit_rounded_panel(self.screen, drop_zone.x, drop_zone.y, drop_zone.width, drop_zone.height,
                                   bg_rgba=(255, 215, 0, 40), border_rgba=(255, 215, 0, 100), border_px=3, radius=drop_radius)
                blit_rounded_border(self.screen, self.disc_rect.x, self.disc_rect.y, self.disc_rect.width, self.disc_rect.height,
                                   (255, 215, 0, 120), 2, radius=CARD_BORDER_RADIUS)
        else:
            # Hay cartas: mostrar apiladas boca abajo
            # Limitar visualmente a las últimas 5 cartas para no sobrecargar
            cards_to_show = min(5, len(self.descarte))
            offset_x = 3  # Offset horizontal para efecto de apilado
            offset_y = 2  # Offset vertical para efecto de apilado
            
            # Mostrar cartas desde la más antigua (abajo) hasta la más reciente (arriba)
            start_idx = max(0, len(self.descarte) - cards_to_show)
            for i in range(start_idx, len(self.descarte)):
                card_idx = i - start_idx
                card_x = self.disc_rect.centerx + card_idx * offset_x
                card_y = self.disc_rect.centery + card_idx * offset_y
                # Usar render_card unificado para el dorso sin sombra
                self.render_card(card_x, card_y, face_down=True, with_shadow=False)
            
            # Highlight cuando se está arrastrando hacia el descarte
            if self.is_dragging or self.carta_arrastrando:
                drop_zone = self.disc_rect.inflate(80, 80)
                drop_radius = get_card_border_radius(drop_zone.width, drop_zone.height)
                blit_rounded_panel(self.screen, drop_zone.x, drop_zone.y, drop_zone.width, drop_zone.height,
                                   bg_rgba=(255, 215, 0, 40), border_rgba=(255, 215, 0, 100), border_px=3, radius=drop_radius)
        
        # Etiquetas - debajo de las cartas, con fondo oscuro para que se vea el texto blanco
        label_text = self.font_orbitron.render('Baraja', True, COLOR_WHITE)
        num_text = self.font_orbitron.render(str(len(self.mazo)), True, COLOR_WHITE)
        separation = 25
        text_start_y = self.deck_rect.centery + deck_h//2 + separation
        text_height = label_text.get_height() + num_text.get_height() + 15
        text_bg_x = self.deck_rect.x
        text_bg_y = text_start_y - 5
        text_bg_rect = pygame.Rect(text_bg_x, text_bg_y, deck_w, text_height + 10)
        blit_rounded_panel(self.screen, text_bg_rect.x, text_bg_rect.y, text_bg_rect.width, text_bg_rect.height,
                          bg_rgba=(20, 30, 40, 255), radius=5)
        
        # Dibujar texto "Baraja" sobre el fondo oscuro (centrado en el ancho de la baraja)
        self.screen.blit(label_text, (self.deck_rect.centerx - label_text.get_width()//2, text_start_y))
        # Dibujar número de cartas justo debajo
        self.screen.blit(num_text, (self.deck_rect.centerx - num_text.get_width()//2, text_start_y + label_text.get_height() + 15))
        
        # Etiqueta descarte solo si hay cartas
        if len(self.descarte) > 0:
            txt2 = self.font_medium.render('Descarte', True, COLOR_WHITE)
            self.screen.blit(txt2, (self.disc_rect.centerx - txt2.get_width()//2, self.disc_rect.centery - 10))
            num2 = self.font_small.render(str(len(self.descarte)), True, COLOR_WHITE)
            self.screen.blit(num2, (self.disc_rect.centerx - num2.get_width()//2, self.disc_rect.centery + 12))
        # Indicador de turno centrado debajo
        turn_txt = self.font_medium.render(f'Turno: {self.jugadores[self.turno].nombre}', True, (255, 255, 255))
        trect = turn_txt.get_rect()
        trect.center = (WINDOW_WIDTH//2, center_y + 90)
        temp_rect = trect.inflate(24, 12)
        blit_rounded_panel(self.screen, temp_rect.x, temp_rect.y, temp_rect.width, temp_rect.height,
                          bg_rgba=(220, 80, 80, 220), border_rgba=(*COLOR_GOLD, 230), border_px=2, radius=8)
        self.screen.blit(turn_txt, trect)

    def render_ia_hand(self):
        """Dibuja la mano de la IA como dorsos genéricos usando las dimensiones estándar de cartas."""
        assert self.screen is not None
        ia = self.jugadores[1]
        backs = min(8, len(ia.mano))
        # Usar dimensiones estándar de cartas (mismo tamaño que todas)
        back_w = CARD_WIDTH  # Mismo tamaño que todas las cartas
        back_h = CARD_HEIGHT
        gap = int(back_w * 0.5)  # Espaciado proporcional
        # Mano Jugador 2 (IA) centrada arriba
        start_x = WINDOW_WIDTH // 2 - (backs * gap) // 2
        y = 130
        for i in range(backs):
            card_x = start_x + i * gap
            card_y = y
            # Usar render_card unificado para mostrar el dorso
            self.render_card(card_x, card_y, face_down=True, with_shadow=False)
        # Icono robot y texto
        icon_x = start_x + backs * 18 + 10
        self._draw_robot_icon(icon_x, y - 14, 18)
        label = self.font_small.render(f'Mano Jugador 2 (oculta): {len(ia.mano)}', True, COLOR_WHITE)
        self.screen.blit(label, (icon_x + 24, y - 18))

    def _generate_player_avatar(self, size: int, is_bot: bool = False) -> pygame.Surface:
        """Genera un avatar programático circular con borde metálico y fondo transparente."""
        avatar = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        border_width = 3  # Ancho del borde metálico
        radius = size // 2 - border_width  # Radio del círculo interno
        
        if is_bot:
            # Avatar para bot: fondo azul con gradiente
            pygame.draw.circle(avatar, (100, 150, 200), (center, center), radius)
            pygame.draw.circle(avatar, (120, 170, 220), (center, center), radius - 5)
            
            # Icono de robot simple y claro
            head_y = center - 4
            # Cabeza blanca del robot
            head_w, head_h = int(size * 0.18), int(size * 0.16)
            head_rect = pygame.Rect(center - head_w//2, head_y - head_h//2, head_w, head_h)
            pygame.draw.rect(avatar, COLOR_WHITE, head_rect, border_radius=4)
            pygame.draw.rect(avatar, (80, 120, 160), head_rect, 2, border_radius=4)
            # Ojos azules brillantes
            eye_size = int(size * 0.04)
            pygame.draw.circle(avatar, (0, 180, 255), (center - 5, head_y), eye_size)
            pygame.draw.circle(avatar, (0, 180, 255), (center + 5, head_y), eye_size)
            pygame.draw.circle(avatar, COLOR_WHITE, (center - 5, head_y - 1), 1)
            pygame.draw.circle(avatar, COLOR_WHITE, (center + 5, head_y - 1), 1)
            # Antenas amarillas
            pygame.draw.circle(avatar, (255, 220, 0), (center - 6, head_y - 8), 2)
            pygame.draw.circle(avatar, (255, 220, 0), (center + 6, head_y - 8), 2)
        else:
            # Avatar para jugador humano: fondo verde con gradiente
            pygame.draw.circle(avatar, (100, 180, 120), (center, center), radius)
            pygame.draw.circle(avatar, (120, 200, 140), (center, center), radius - 5)
            
            # Icono de usuario simple y claro
            head_radius = int(size * 0.12)
            head_y = center - 4
            # Cabeza beige clara
            pygame.draw.circle(avatar, (240, 220, 200), (center, head_y), head_radius)
            pygame.draw.circle(avatar, (180, 160, 140), (center, head_y), head_radius, 2)
            # Highlight en la cabeza
            pygame.draw.circle(avatar, (255, 240, 230), (center - 3, head_y - 3), 4)
            # Cuerpo blanco simple
            body_top = head_y + head_radius
            body_bottom = center + 8
            body_width = int(size * 0.14)
            body_points = [
                (center - body_width//2, body_top),
                (center - body_width//2 + 2, body_bottom),
                (center - 3, body_bottom),
                (center + 3, body_bottom),
                (center + body_width//2 - 2, body_bottom),
                (center + body_width//2, body_top),
            ]
            pygame.draw.polygon(avatar, COLOR_WHITE, body_points)
            pygame.draw.polygon(avatar, (80, 140, 100), body_points, 2)
        
        # Dibujar borde metálico plateado (igual que en _create_circular_avatar)
        # Borde exterior más oscuro
        pygame.draw.circle(avatar, (180, 180, 190, 255), (center, center), size // 2 - 1, border_width)
        # Borde interior más brillante para efecto metálico
        pygame.draw.circle(avatar, (220, 220, 230, 255), (center, center), size // 2 - 2, 1)
        # Highlight superior para efecto 3D
        highlight_radius = size // 2 - border_width - 2
        highlight_y = center - highlight_radius // 3
        pygame.draw.circle(avatar, (240, 240, 250, 180), (center, highlight_y), highlight_radius // 4)
        
        return avatar

    # ==== Iconos simples (vectoriales) ====
    def _draw_robot_icon(self, x: int, y: int, size: int) -> None:
        """Dibuja un robot minimalista (cabeza y antenas). x,y esquina superior izquierda."""
        assert self.screen is not None
        s = size
        # cabeza
        head = pygame.Rect(x, y, s, s)
        # Reducir cajas opacas: contenedor con alfa y radio
        head_panel = pygame.Surface((head.width, head.height), pygame.SRCALPHA)
        pygame.draw.rect(head_panel, (120, 120, 130, 220), (0, 0, head.width, head.height), border_radius=6)
        pygame.draw.rect(head_panel, (*COLOR_WHITE, 230), (0, 0, head.width, head.height), 2, border_radius=6)
        self.screen.blit(head_panel, head.topleft)
        # ojos (overlay)
        eye_w = int(s * 0.15); eye_h = int(s * 0.15)
        eye1 = pygame.Surface((eye_w, eye_h), pygame.SRCALPHA)
        pygame.draw.rect(eye1, (0, 0, 0, 255), (0, 0, eye_w, eye_h), border_radius=3)
        self.screen.blit(eye1, (x + int(s*0.25), y + int(s*0.35)))
        eye2 = pygame.Surface((eye_w, eye_h), pygame.SRCALPHA)
        pygame.draw.rect(eye2, (0, 0, 0, 255), (0, 0, eye_w, eye_h), border_radius=3)
        self.screen.blit(eye2, (x + int(s*0.60), y + int(s*0.35)))
        # antena
        pygame.draw.line(self.screen, COLOR_WHITE, (x + s*0.5, y - s*0.25), (x + s*0.5, y), 2)
        pygame.draw.circle(self.screen, (255, 80, 80), (int(x + s*0.5), int(y - s*0.28)), int(s*0.08))

    def _draw_person_icon(self, x: int, y: int, size: int) -> None:
        """Dibuja una silueta de persona (cabeza + torso). x,y esquina superior izquierda."""
        assert self.screen is not None
        s = size
        # cabeza
        pygame.draw.circle(self.screen, (220, 220, 220), (x + s//2, y + s//3), s//3)
        pygame.draw.circle(self.screen, COLOR_WHITE, (x + s//2, y + s//3), s//3, 2)
        # torso
        torso = pygame.Rect(x + s*0.15, y + s*0.55, s*0.7, s*0.45)
        torso_panel = pygame.Surface((int(torso.width), int(torso.height)), pygame.SRCALPHA)
        pygame.draw.rect(torso_panel, (180, 180, 180, 255), (0,0,int(torso.width),int(torso.height)), border_radius=6)
        pygame.draw.rect(torso_panel, (*COLOR_WHITE, 255), (0,0,int(torso.width),int(torso.height)), 2, border_radius=6)
        self.screen.blit(torso_panel, torso.topleft)

    def _draw_shield_icon(self, x: int, y: int, size: int) -> None:
        """Dibuja un escudo brillante con efecto pulsante para indicar protección activa."""
        assert self.screen is not None
        s = size
        # Centro del escudo
        center_x = int(x + s // 2)
        center_y = int(y + s // 2)
        
        # Efecto pulsante usando tiempo
        t = pygame.time.get_ticks() / 300.0
        pulse = 0.85 + 0.15 * math.sin(t)
        radius = int((s // 2) * pulse)
        
        # Resplandor exterior (aura dorada)
        for i in range(3, 0, -1):
            alpha = 40 * i
            glow_surf = pygame.Surface((s + i*8, s + i*8), pygame.SRCALPHA)
            glow_radius = radius + i * 3
            pygame.draw.circle(glow_surf, (255, 215, 0, alpha), 
                             (glow_surf.get_width()//2, glow_surf.get_height()//2), glow_radius)
            self.screen.blit(glow_surf, (x - i*4, y - i*4))
        
        # Escudo principal (forma de escudo clásico)
        # Crear los puntos del escudo
        shield_points = [
            (center_x, center_y - radius),  # arriba
            (center_x + radius * 0.7, center_y - radius * 0.5),  # arriba derecha
            (center_x + radius * 0.7, center_y + radius * 0.3),  # medio derecha
            (center_x, center_y + radius),  # punta inferior
            (center_x - radius * 0.7, center_y + radius * 0.3),  # medio izquierda
            (center_x - radius * 0.7, center_y - radius * 0.5),  # arriba izquierda
        ]
        
        # Relleno del escudo con gradiente simulado (azul brillante a cyan)
        pygame.draw.polygon(self.screen, (80, 180, 255), shield_points)
        
        # Borde brillante dorado
        pygame.draw.polygon(self.screen, COLOR_GOLD, shield_points, 3)
        
        # Cruz/símbolo de protección en el centro
        cross_size = radius * 0.4
        # Vertical
        pygame.draw.line(self.screen, COLOR_WHITE, 
                        (center_x, center_y - cross_size), 
                        (center_x, center_y + cross_size), 3)
        # Horizontal
        pygame.draw.line(self.screen, COLOR_WHITE, 
                        (center_x - cross_size, center_y), 
                        (center_x + cross_size, center_y), 3)
        
        # Brillo superior (highlight)
        highlight_y = center_y - radius * 0.5
        pygame.draw.circle(self.screen, (200, 230, 255, 100), 
                          (center_x, int(highlight_y)), int(radius * 0.3))

    def render_hud(self):
        """Renderiza el HUD. Los textos de Turno y Órganos sanos ahora solo aparecen en el panel de ayuda."""
        assert self.screen is not None
        # Los textos de "Turno" y "Órganos sanos" ahora solo se muestran en el panel de ayuda
        # El mensaje de victoria se muestra en render_status() (centrado)
        
        # INDICADOR VISUAL DE AUTOPLAY (solo se muestra cuando está activo)
        # En modo manual, no se muestra nada (la info está en el panel de ayuda)
        if self.autoplay:
            autoplay_x = 20
            autoplay_y = 10
            autoplay_w = 200
            autoplay_h = 40
            # AUTOPLAY ON: Verde brillante con efecto pulsante
            t = pygame.time.get_ticks() / 300.0
            pulse = 0.9 + 0.1 * abs(math.sin(t))
            auto_color = (int(50 * pulse), int(200 * pulse), int(50 * pulse))
            auto_panel = pygame.Surface((autoplay_w, autoplay_h), pygame.SRCALPHA)
            pygame.draw.rect(auto_panel, (*auto_color, 220), (0,0,autoplay_w,autoplay_h), border_radius=8)
            pygame.draw.rect(auto_panel, (*COLOR_GREEN, 255), (0,0,autoplay_w,autoplay_h), 3, border_radius=8)
            self.screen.blit(auto_panel, (autoplay_x, autoplay_y))
            auto_text = self.font_medium.render('AUTOPLAY: ON', True, COLOR_WHITE)
            self.screen.blit(auto_text, (autoplay_x + autoplay_w//2 - auto_text.get_width()//2, autoplay_y + 10))
        
        # Los botones de sonido y nueva partida ahora están en la barra inferior

        # avanzar efectos temporales
        to_del = []
        for k, fx in self.fx_active.items():
            fx['t'] = fx.get('t', 0) + 1
            if fx['t'] >= fx.get('dur', 30):
                to_del.append(k)
        for k in to_del:
            del self.fx_active[k]

    def render_bottom_bar(self) -> None:
        """Renderiza la barra inferior collapsable con botones de iconos."""
        assert self.screen is not None
        mouse_pos = pygame.mouse.get_pos()
        
        # Limpiar tooltip por defecto
        self.hover_help_text = ''
        self.hover_help_pos = None
        
        # Dimensiones de la barra
        bar_height_expanded = 70
        bar_height_collapsed = 30
        bar_height = bar_height_collapsed if self.bottom_bar_collapsed else bar_height_expanded
        bar_y = WINDOW_HEIGHT - bar_height
        bar_x = 0
        bar_width = WINDOW_WIDTH
        
        # Fondo de la barra
        bar_color = (40, 40, 50, 200)
        bar_surf = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
        bar_surf.fill(bar_color)
        self.screen.blit(bar_surf, (bar_x, bar_y))
        
        # Borde superior
        pygame.draw.line(self.screen, COLOR_GOLD, (bar_x, bar_y), (bar_x + bar_width, bar_y), 2)
        
        # Si está colapsada, hacer toda la barra clickeable para expandir
        if self.bottom_bar_collapsed:
            # Hacer toda la barra clickeable (más fácil de usar)
            toggle_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            hover_toggle = toggle_rect.collidepoint(mouse_pos)
            toggle_color = COLOR_GOLD if hover_toggle else COLOR_WHITE
            
            # Botón toggle visual más grande y visible (centrado)
            toggle_size = 30
            toggle_x = bar_x + bar_width // 2 - toggle_size // 2
            toggle_y = bar_y + (bar_height - toggle_size) // 2
            toggle_visual = pygame.Rect(toggle_x, toggle_y, toggle_size, toggle_size)
            
            # Fondo del botón con efecto hover
            bg_color = (80, 80, 90) if hover_toggle else (60, 60, 70)
            tv_panel = pygame.Surface((toggle_visual.width, toggle_visual.height), pygame.SRCALPHA)
            pygame.draw.rect(tv_panel, (*bg_color, 255) if len(bg_color)==3 else bg_color, (0,0,toggle_visual.width,toggle_visual.height), border_radius=5)
            pygame.draw.rect(tv_panel, (*toggle_color, 255), (0,0,toggle_visual.width,toggle_visual.height), 3, border_radius=5)
            self.screen.blit(tv_panel, toggle_visual.topleft)
            
            # Icono de flecha hacia arriba (usar icono si está disponible)
            if self.icon_toggle_up is not None:
                # Escalar icono si es necesario
                icon_size = min(toggle_size - 4, self.icon_toggle_up.get_width())
                if icon_size != self.icon_toggle_up.get_width():
                    icon = pygame.transform.smoothscale(self.icon_toggle_up, (icon_size, icon_size))
                else:
                    icon = self.icon_toggle_up
                icon_x = toggle_x + toggle_size // 2 - icon.get_width() // 2
                icon_y = toggle_y + toggle_size // 2 - icon.get_height() // 2
                self.screen.blit(icon, (icon_x, icon_y))
            else:
                # Usar texto más grande
                arrow = self.font_medium.render('▲', True, toggle_color)
                arrow_x = toggle_x + toggle_size // 2 - arrow.get_width() // 2
                arrow_y = toggle_y + toggle_size // 2 - arrow.get_height() // 2
                self.screen.blit(arrow, (arrow_x, arrow_y))
            
            # Área clickeable: toda la barra
            self.bottom_bar_toggle_rect = toggle_rect
            
            # Tooltip para toggle colapsado
            if hover_toggle:
                self.hover_help_text = 'Click para expandir barra'
                self.hover_help_pos = (toggle_x + toggle_size // 2, toggle_y - 15)
            return
        
        # Barra expandida: mostrar botones
        # Botón toggle para colapsar (extremo izquierdo)
        toggle_size = 25
        toggle_x = bar_x + 10
        toggle_y = bar_y + (bar_height_expanded - toggle_size) // 2
        toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_size, toggle_size)
        hover_toggle = toggle_rect.collidepoint(mouse_pos)
        toggle_color = COLOR_GOLD if hover_toggle else COLOR_WHITE
        toggle_panel = pygame.Surface((toggle_rect.width, toggle_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(toggle_panel, (60, 60, 70, 255), (0,0,toggle_rect.width,toggle_rect.height), border_radius=3)
        pygame.draw.rect(toggle_panel, (*toggle_color, 255), (0,0,toggle_rect.width,toggle_rect.height), 2, border_radius=3)
        self.screen.blit(toggle_panel, toggle_rect.topleft)
        # Icono de flecha hacia abajo (usar icono si está disponible)
        if self.icon_toggle_down is not None:
            icon_x = toggle_x + toggle_size // 2 - self.icon_toggle_down.get_width() // 2
            icon_y = toggle_y + toggle_size // 2 - self.icon_toggle_down.get_height() // 2
            self.screen.blit(self.icon_toggle_down, (icon_x, icon_y))
        else:
            arrow = self.font_small.render('▼', True, toggle_color)
            arrow_x = toggle_x + toggle_size // 2 - arrow.get_width() // 2
            arrow_y = toggle_y + toggle_size // 2 - arrow.get_height() // 2
            self.screen.blit(arrow, (arrow_x, arrow_y))
        self.bottom_bar_toggle_rect = toggle_rect
        # Tooltip para toggle expandido
        if hover_toggle:
            self.hover_help_text = 'Colapsar barra'
            self.hover_help_pos = (toggle_x + toggle_size // 2, toggle_y - 10)
        
        # Botones con iconos (sin texto)
        button_size = 50
        button_spacing = 15
        start_x = toggle_x + toggle_size + 20
        
        # 1. Botón Sonido
        snd_x = start_x
        snd_y = bar_y + (bar_height_expanded - button_size) // 2
        snd_rect = pygame.Rect(snd_x, snd_y, button_size, button_size)
        hover_snd = snd_rect.collidepoint(mouse_pos)
        snd_color = (60, 130, 60) if self.sound_enabled else (120, 60, 60)
        snd_color = (90, 170, 90) if hover_snd and self.sound_enabled else ((150, 90, 90) if hover_snd else snd_color)
        snd_panel = pygame.Surface((snd_rect.width, snd_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(snd_panel, (*snd_color, 255) if len(snd_color)==3 else snd_color, (0,0,snd_rect.width,snd_rect.height), border_radius=5)
        pygame.draw.rect(snd_panel, (*COLOR_GOLD, 255), (0,0,snd_rect.width,snd_rect.height), 2, border_radius=5)
        self.screen.blit(snd_panel, snd_rect.topleft)
        # Icono de sonido (usar icono si está disponible)
        sound_icon = self.icon_sound_on if self.sound_enabled else self.icon_sound_off
        if sound_icon is not None:
            icon_x = snd_x + button_size // 2 - sound_icon.get_width() // 2
            icon_y = snd_y + button_size // 2 - sound_icon.get_height() // 2
            self.screen.blit(sound_icon, (icon_x, icon_y))
        else:
            snd_icon = '🔊' if self.sound_enabled else '🔇'
            icon_text = self.font_large.render(snd_icon, True, COLOR_WHITE)
            icon_x = snd_x + button_size // 2 - icon_text.get_width() // 2
            icon_y = snd_y + button_size // 2 - icon_text.get_height() // 2
            self.screen.blit(icon_text, (icon_x, icon_y))
        self.btn_sound_rect = snd_rect
        # Tooltip para sonido
        if hover_snd:
            snd_text = 'Sonido: ON' if self.sound_enabled else 'Sonido: OFF'
            self.hover_help_text = snd_text
            self.hover_help_pos = (snd_x + button_size // 2, snd_y - 10)
        
        # 2. Botón Nueva Partida
        nueva_x = snd_x + button_size + button_spacing
        nueva_y = snd_y
        nueva_rect = pygame.Rect(nueva_x, nueva_y, button_size, button_size)
        hover_nueva = nueva_rect.collidepoint(mouse_pos)
        nueva_color = COLOR_ORANGE if hover_nueva else (150, 100, 50)
        nueva_panel = pygame.Surface((nueva_rect.width, nueva_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(nueva_panel, (*nueva_color, 255) if len(nueva_color)==3 else nueva_color, (0,0,nueva_rect.width,nueva_rect.height), border_radius=5)
        pygame.draw.rect(nueva_panel, (*COLOR_GOLD, 255), (0,0,nueva_rect.width,nueva_rect.height), 2, border_radius=5)
        self.screen.blit(nueva_panel, nueva_rect.topleft)
        # Icono de nueva partida (usar icono si está disponible)
        if self.icon_new_game is not None:
            icon_x = nueva_x + button_size // 2 - self.icon_new_game.get_width() // 2
            icon_y = nueva_y + button_size // 2 - self.icon_new_game.get_height() // 2
            self.screen.blit(self.icon_new_game, (icon_x, icon_y))
        else:
            nueva_icon = self.font_large.render('🔄', True, COLOR_WHITE)
            icon_x = nueva_x + button_size // 2 - nueva_icon.get_width() // 2
            icon_y = nueva_y + button_size // 2 - nueva_icon.get_height() // 2
            self.screen.blit(nueva_icon, (icon_x, icon_y))
        self.btn_nueva_rect = nueva_rect
        # Tooltip para nueva partida
        if hover_nueva:
            self.hover_help_text = 'Nueva Partida'
            self.hover_help_pos = (nueva_x + button_size // 2, nueva_y - 10)
        
        # 3. Botón Diario
        diario_x = nueva_x + button_size + button_spacing
        diario_y = snd_y
        diario_rect = pygame.Rect(diario_x, diario_y, button_size, button_size)
        hover_diario = diario_rect.collidepoint(mouse_pos)
        diario_color = COLOR_GOLD if hover_diario else (60, 60, 80)
        if self.diario_open:
            diario_color = COLOR_GOLD
        diario_panel = pygame.Surface((diario_rect.width, diario_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(diario_panel, (*diario_color, 255) if len(diario_color)==3 else diario_color, (0,0,diario_rect.width,diario_rect.height), border_radius=5)
        border_col = COLOR_WHITE if hover_diario or self.diario_open else COLOR_GOLD
        pygame.draw.rect(diario_panel, (*border_col, 255), (0,0,diario_rect.width,diario_rect.height), 2, border_radius=5)
        self.screen.blit(diario_panel, diario_rect.topleft)
        # Icono de diario (usar icono si está disponible)
        if self.icon_diary is not None:
            icon_x = diario_x + button_size // 2 - self.icon_diary.get_width() // 2
            icon_y = diario_y + button_size // 2 - self.icon_diary.get_height() // 2
            self.screen.blit(self.icon_diary, (icon_x, icon_y))
        else:
            diario_icon = self.font_large.render('📖', True, COLOR_WHITE)
            icon_x = diario_x + button_size // 2 - diario_icon.get_width() // 2
            icon_y = diario_y + button_size // 2 - diario_icon.get_height() // 2
            self.screen.blit(diario_icon, (icon_x, icon_y))
        self.diario_icon_rect = diario_rect
        # Tooltip para diario
        if hover_diario:
            self.hover_help_text = 'Diario' + (' (abierto)' if self.diario_open else '')
            self.hover_help_pos = (diario_x + button_size // 2, diario_y - 10)
        
        # 4. Botón Ayuda
        ayuda_x = diario_x + button_size + button_spacing
        ayuda_y = snd_y
        ayuda_rect = pygame.Rect(ayuda_x, ayuda_y, button_size, button_size)
        hover_ayuda = ayuda_rect.collidepoint(mouse_pos)
        ayuda_color = COLOR_GOLD if hover_ayuda else (60, 60, 80)
        if self.ayuda_open:
            ayuda_color = COLOR_GOLD
        ayuda_panel = pygame.Surface((ayuda_rect.width, ayuda_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(ayuda_panel, (*ayuda_color, 255) if len(ayuda_color)==3 else ayuda_color, (0,0,ayuda_rect.width,ayuda_rect.height), border_radius=5)
        border_col2 = COLOR_WHITE if hover_ayuda or self.ayuda_open else COLOR_GOLD
        pygame.draw.rect(ayuda_panel, (*border_col2, 255), (0,0,ayuda_rect.width,ayuda_rect.height), 2, border_radius=5)
        self.screen.blit(ayuda_panel, ayuda_rect.topleft)
        # Icono de ayuda (usar icono si está disponible)
        if self.icon_help is not None:
            icon_x = ayuda_x + button_size // 2 - self.icon_help.get_width() // 2
            icon_y = ayuda_y + button_size // 2 - self.icon_help.get_height() // 2
            self.screen.blit(self.icon_help, (icon_x, icon_y))
        else:
            ayuda_icon = self.font_large.render('❓', True, COLOR_WHITE)
            icon_x = ayuda_x + button_size // 2 - ayuda_icon.get_width() // 2
            icon_y = ayuda_y + button_size // 2 - ayuda_icon.get_height() // 2
            self.screen.blit(ayuda_icon, (icon_x, icon_y))
        self.ayuda_icon_rect = ayuda_rect
        # Tooltip para ayuda
        if hover_ayuda:
            self.hover_help_text = 'Ayuda' + (' (abierto)' if self.ayuda_open else '')
            self.hover_help_pos = (ayuda_x + button_size // 2, ayuda_y - 10)

    def render_turn_arrow(self) -> None:
        assert self.screen is not None
        color = COLOR_GOLD
        if self.turno == 0:
            # Flecha hacia abajo, apuntando a la mano del jugador 1
            y = WINDOW_HEIGHT - 130
            x = WINDOW_WIDTH // 2
            points = [(x, y), (x - 14, y - 22), (x + 14, y - 22)]
            pygame.draw.polygon(self.screen, color, points)
        else:
            # Flecha hacia arriba, apuntando a mano IA
            y = 120
            x = WINDOW_WIDTH // 2
            points = [(x, y), (x - 14, y + 22), (x + 14, y + 22)]
            pygame.draw.polygon(self.screen, color, points)

    def render_zones(self) -> None:
        """Renderiza el tablero con áreas definidas estilo doudizhu: bordes, sombras y efectos visuales."""
        assert self.screen is not None
        
        # Áreas principales del tablero (más estructuradas)
        # Zona IA (arriba) - área de juego del oponente (recortada por ambos lados)
        zone_margin_left = 280  # Aumentado de 220 a 280 (60px más de margen izquierdo)
        zone_margin_right = 360  # Margen derecho aumentado (120px más que antes)
        zone_width = WINDOW_WIDTH - zone_margin_left - zone_margin_right  # Ancho reducido
        top_rect = pygame.Rect(zone_margin_left, 80, zone_width, 220)
        # Zona Jugador (abajo) - área de juego del jugador (recortada por ambos lados)
        bottom_rect = pygame.Rect(zone_margin_left, 360, zone_width, 280)
        # Zona central (mazos y descarte)
        center_rect = pygame.Rect(220, 300, WINDOW_WIDTH - 240, 60)

        # === ZONA IA (ARRIBA) ===
        # Fondo con bordes tipo "mesa de juego" (overlay)
        top_panel = pygame.Surface((top_rect.w, top_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(top_panel, (25, 35, 45, 255), (0,0,top_rect.w, top_rect.h), border_radius=8)
        pygame.draw.rect(top_panel, (60, 80, 100, 255), (0,0,top_rect.w, top_rect.h), 2, border_radius=8)
        # Sombra interna
        inner_top = pygame.Surface((top_rect.w, top_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(inner_top, (15, 25, 35, 255), (2,2, top_rect.w-4, top_rect.h-4), border_radius=6)
        top_panel.blit(inner_top, (0,0))
        self.screen.blit(top_panel, top_rect.topleft)
        
        # Overlay semitransparente para efecto de profundidad
        top_surf = pygame.Surface((top_rect.w, top_rect.h), pygame.SRCALPHA)
        top_surf.fill((40, 60, 70, 50))
        self.screen.blit(top_surf, top_rect.topleft)

        # === ZONA JUGADOR (ABAJO) ===
        # Fondo con bordes (overlay)
        bottom_panel = pygame.Surface((bottom_rect.w, bottom_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(bottom_panel, (30, 50, 40, 255), (0,0,bottom_rect.w, bottom_rect.h), border_radius=8)
        pygame.draw.rect(bottom_panel, (70, 120, 90, 255), (0,0,bottom_rect.w, bottom_rect.h), 2, border_radius=8)
        # Sombra interna
        inner_bottom = pygame.Surface((bottom_rect.w, bottom_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(inner_bottom, (20, 40, 30, 255), (2,2,bottom_rect.w-4,bottom_rect.h-4), border_radius=6)
        bottom_panel.blit(inner_bottom, (0,0))
        self.screen.blit(bottom_panel, bottom_rect.topleft)
        
        # Overlay semitransparente
        bottom_surf = pygame.Surface((bottom_rect.w, bottom_rect.h), pygame.SRCALPHA)
        bottom_surf.fill((120, 160, 120, 30))
        self.screen.blit(bottom_surf, bottom_rect.topleft)

        # === ZONA CENTRAL (MAZOS) ===
        # Área central eliminada - ya no se dibuja el recuadro verde
        # center_surf = pygame.Surface((center_rect.w, center_rect.h), pygame.SRCALPHA)
        # center_surf.fill((40, 60, 50, 60))
        # self.screen.blit(center_surf, center_rect.topleft)
        # pygame.draw.rect(self.screen, (60, 90, 70), center_rect, 1, border_radius=4)

        # === INDICADOR DE TURNO ===
        # Resaltar zona activa con efecto pulsante (ELIMINADO - solo confundía)
        # if self.turno == 0:
        #     t = pygame.time.get_ticks() / 200.0
        #     alpha = 80 + int(50 * (0.5 + 0.5 * math.sin(t)))
        #     highlight_surf = pygame.Surface((bottom_rect.w, bottom_rect.h), pygame.SRCALPHA)
        #     highlight_surf.fill((255, 215, 0, alpha))
        #     self.screen.blit(highlight_surf, bottom_rect.topleft)
        #     # Borde dorado pulsante
        #     border_alpha = 150 + int(50 * (0.5 + 0.5 * math.sin(t)))
        #     border_surf = pygame.Surface((bottom_rect.w + 4, bottom_rect.h + 4), pygame.SRCALPHA)
        #     pygame.draw.rect(border_surf, (*COLOR_GOLD[:3], border_alpha), 
        #                    (0, 0, bottom_rect.w + 4, bottom_rect.h + 4), 3, border_radius=10)
        #     self.screen.blit(border_surf, (bottom_rect.x - 2, bottom_rect.y - 2))
        if self.turno == 1:
            t = pygame.time.get_ticks() / 200.0
            alpha = 60 + int(40 * (0.5 + 0.5 * math.sin(t)))
            highlight_surf = pygame.Surface((top_rect.w, top_rect.h), pygame.SRCALPHA)
            highlight_surf.fill((100, 150, 200, alpha))
            self.screen.blit(highlight_surf, top_rect.topleft)

        # === RÓTULOS Y AVATARES DE JUGADORES ===
        avatar_size = 100  # Tamaño aumentado para mejor visibilidad
        
        # Player 2 (arriba) - siempre es bot en el juego actual
        player2_is_bot = (self.jugadores[1].nombre == 'IA' or self.jugadores[1].nombre == 'BOT')
        
        # Determinar qué imagen usar (prioridad: imagen cargada > generada)
        if player2_is_bot:
            player2_img = self.bot_image if self.bot_image is not None else self.bot_avatar_generated
        else:
            player2_img = self.player_image if self.player_image is not None else self.player_avatar_generated
        
        # Renderizar Player 2 (arriba)
        player2_x = top_rect.x + 10
        player2_y = top_rect.y - 50
        avatar_center_x = player2_x + avatar_size//2
        avatar_center_y = player2_y + avatar_size//2
        
        if player2_img is not None:
            # La imagen ya incluye el borde metálico y está escalada a 100x100 en _load_assets
            # El fondo alrededor del círculo es completamente transparente
            # Blit con preservación de transparencia usando BLEND_ALPHA_SDL2 para mejor manejo
            # Verificar que la superficie tenga SRCALPHA
            if player2_img.get_flags() & pygame.SRCALPHA:
                # Blit con preservación explícita de transparencia
                self.screen.blit(player2_img, (player2_x, player2_y), special_flags=pygame.BLEND_ALPHA_SDL2)
            else:
                # Fallback: blit normal
                self.screen.blit(player2_img, (player2_x, player2_y))
        
        # Texto "Player 2" debajo del avatar (con fuente Orbitron) - centrado bajo el avatar
        label_text = self.font_orbitron.render('Player 2', True, COLOR_WHITE)
        self.screen.blit(label_text, (avatar_center_x - label_text.get_width()//2, player2_y + avatar_size + 5))
        
        # Player 1 (abajo) - siempre es humano en el juego actual
        player1_is_bot = (self.jugadores[0].nombre == 'IA' or self.jugadores[0].nombre == 'BOT')
        
        # Determinar qué imagen usar (prioridad: imagen cargada > generada)
        if player1_is_bot:
            player1_img = self.bot_image if self.bot_image is not None else self.bot_avatar_generated
        else:
            player1_img = self.player_image if self.player_image is not None else self.player_avatar_generated
        
        # Renderizar Player 1 (abajo)
        player1_x = bottom_rect.x + 10
        player1_y = bottom_rect.y - 50
        avatar1_center_x = player1_x + avatar_size//2
        avatar1_center_y = player1_y + avatar_size//2
        
        if player1_img is not None:
            # La imagen ya incluye el borde metálico y está escalada a 100x100 en _load_assets
            # El fondo alrededor del círculo es completamente transparente
            self.screen.blit(player1_img, (player1_x, player1_y))
        
        # Texto "Player 1" debajo del avatar (con fuente Orbitron) - centrado bajo el avatar
        label_text = self.font_orbitron.render('Player 1', True, COLOR_WHITE)
        self.screen.blit(label_text, (avatar1_center_x - label_text.get_width()//2, player1_y + avatar_size + 5))
        
        # === INDICADOR DE ESCUDO (GUANTE) ===
        # IA (jugador 1)
        if self.jugadores[1].treatment_shield:
            shield_x = top_rect.x + 200
            shield_y = top_rect.y - 40
            self._draw_shield_icon(shield_x, shield_y, 32)
            # Texto "Protegido"
            shield_text = self.font_small.render('Protegido', True, COLOR_GOLD)
            self.screen.blit(shield_text, (shield_x + 35, shield_y + 5))
        # JUGADOR (jugador 0)
        if self.jugadores[0].treatment_shield:
            shield_x = bottom_rect.x + 200
            shield_y = bottom_rect.y - 40
            self._draw_shield_icon(shield_x, shield_y, 32)
            # Texto "Protegido"
            shield_text = self.font_small.render('Protegido', True, COLOR_GOLD)
            self.screen.blit(shield_text, (shield_x + 35, shield_y + 5))

    # === Fondo tipo tapiz de póker ===
    def _ensure_felt_background(self) -> None:
        if self.bg_surface is not None:
            return
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        base = (16, 92, 58)
        surf.fill(base)
        rng = random.Random(42)
        # Motas
        for _ in range(4500):
            x = rng.randrange(0, WINDOW_WIDTH)
            y = rng.randrange(0, WINDOW_HEIGHT)
            shade = rng.randrange(-18, 18)
            color = (max(0, min(255, base[0] + shade)), max(0, min(255, base[1] + shade)), max(0, min(255, base[2] + shade)))
            surf.set_at((x, y), color)
        # Líneas diagonales suaves
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for i in range(-WINDOW_HEIGHT, WINDOW_WIDTH, 12):
            pygame.draw.line(overlay, (255, 255, 255, 6), (i, 0), (i + WINDOW_HEIGHT, WINDOW_HEIGHT), 1)
        surf.blit(overlay, (0, 0))
        self.bg_surface = surf

    # ==== Helpers anim/drop ====
    def _slot_center_for_player(self, player_index: int, color: str) -> Tuple[int, int]:
        # Mapeo de nombres antiguos a nuevos para compatibilidad
        legacy_to_new = {
            'corazon': 'seguridad',
            'cerebro': 'documentacion',
            'huesos': 'gobierno',
            'estomago': 'performance'
        }
        # Convertir color a nuevo formato si es necesario
        color_key = legacy_to_new.get(color, color)
        # Usar el mismo orden que ASPECTOS
        colors_order = ASPECTOS  # ['seguridad', 'documentacion', 'gobierno', 'performance']
        gap = 140  # Espaciado entre placeholders (CARD_WIDTH=120 + 20px de margen para evitar solapamiento)
        total_w = gap * 3
        # Centrar dentro de la zona del jugador (usar las mismas dimensiones que render_zones)
        zone_margin_left = 280
        zone_margin_right = 360
        zone_width = WINDOW_WIDTH - zone_margin_left - zone_margin_right
        zone_center_x = zone_margin_left + zone_width // 2
        start_x = zone_center_x - total_w // 2
        idx = colors_order.index(color_key) if color_key in colors_order else 0
        x = start_x + idx * gap
        # Posiciones ajustadas a las nuevas zonas del tablero
        y = 180 if player_index == 1 else 480
        return (x, y)

    # _resolver_destino_color está en GameEngine (engine.py)

    def _resolver_drop_target(self, pos: Tuple[int, int], jugador: Jugador, carta: Carta):
        x, y = pos
        # fila destino según tipo de carta: virus, LADRÓN y TRASPLANTE => oponente; medicina/órgano => propio
        target_index = 0
        if jugador is self.jugadores[0]:
            if carta.tipo == 'virus' or (carta.tipo == 'tratamiento' and carta.color in ('ladrón', 'trasplante')):
                target_index = 1
        target_owner = self._opponent_of(jugador) if target_index == 1 else jugador
        for color in ['corazon', 'cerebro', 'huesos', 'estomago']:
            cx, cy = self._slot_center_for_player(target_index, color)
            # Área más grande para LADRÓN y TRASPLANTE (más fácil de usar)
            is_ladron_or_trasplante = (carta.tipo == 'tratamiento' and carta.color in ('ladrón', 'trasplante'))
            margen_x = 70 if is_ladron_or_trasplante else 55
            margen_y = 90 if is_ladron_or_trasplante else 75
            if (cx - margen_x <= x <= cx + margen_x and cy - margen_y <= y <= cy + margen_y):
                # CASO ESPECIAL: LADRÓN - validar directamente sin depender de _resolver_destino_color
                if carta.tipo == 'tratamiento' and carta.color == 'ladrón':
                    # Para LADRÓN: solo validar si el oponente tiene ese órgano y tú no
                    if color in target_owner.aspectos and color not in jugador.aspectos:
                        return (color, (cx, cy))
                    # Si el órgano no existe en el oponente o ya lo tienes, no es válido
                    return (None, None)
                # CASO ESPECIAL: TRASPLANTE - puedes seleccionar cualquier órgano del oponente
                if carta.tipo == 'tratamiento' and carta.color == 'trasplante':
                    # Para TRASPLANTE: validar si el oponente tiene ese órgano
                    if color in target_owner.aspectos:
                        return (color, (cx, cy))
                    # Si el órgano no existe en el oponente, no es válido
                    return (None, None)
                
                # Para otras cartas, usar la lógica normal
                destino = self._resolver_destino_color(target_owner, carta)
                if destino is None:
                    return (None, None)
                if carta.color == 'multicolor':
                    if carta.tipo == 'aspecto' and color not in target_owner.aspectos:
                        return (color, (cx, cy))
                    if carta.tipo in ('ataque', 'problema', 'proteccion') and color in target_owner.aspectos:
                        return (color, (cx, cy))
                    if carta.tipo == 'tratamiento' and color in target_owner.aspectos and color not in jugador.aspectos:
                        return (color, (cx, cy))
                    return (None, None)
                else:
                    return (carta.color, (cx, cy)) if color == carta.color else (None, None)
        # Si no soltó exactamente sobre ningún slot, devolver None
        # (esto permite que handle_mouse_up verifique si es descarte)
        return (None, None)

    def _hover_slot_color(self, pos: Tuple[int, int]) -> Optional[str]:
        x, y = pos
        # detectar sobre qué fila está el ratón (propia abajo o rival arriba)
        for idx in (0, 1):
            for color in ['corazon', 'cerebro', 'huesos', 'estomago']:
                cx, cy = self._slot_center_for_player(idx, color)
                if (cx - 55 <= x <= cx + 55 and cy - 75 <= y <= cy + 75):
                    return color
        return None

    def _slot_is_compatible(self, color: str) -> bool:
        try:
            carta = self.jugadores[0].mano[self.selected_hand_idx]  # type: ignore
        except Exception:
            return False
        if carta.tipo == 'aspecto':
            if (carta.color == 'multicolor' and color not in self.jugadores[0].aspectos) or (carta.color == color and color not in self.jugadores[0].aspectos):
                return True
        elif carta.tipo in ('ataque', 'problema', 'proteccion'):
            if carta.tipo == 'proteccion':
                owner = self.jugadores[0]
            else:
                owner = self.jugadores[1]  # ataque/problema sobre rival
            if (carta.color == 'multicolor' and color in owner.aspectos) or (carta.color == color and color in owner.aspectos):
                return True
        elif carta.tipo == 'tratamiento' and carta.color == 'ladrón':
            # compatible si la IA tiene ese aspecto y el jugador no
            if color in self.jugadores[1].aspectos and color not in self.jugadores[0].aspectos:
                return True
        return False

    def _calcular_destino_carta(self, jugador: Jugador, carta: Carta) -> Tuple[int, int]:
        """Calcula la posición de destino para una carta según su tipo."""
        # Para órganos y medicinas/virus que afectan órganos propios
        if carta.tipo == 'aspecto':
            # Va al slot del jugador
            player_idx = 0 if jugador.nombre == 'TÚ' else 1
            x, y = self._slot_center_for_player(player_idx, carta.color)
            return (x, y)
        elif carta.tipo in ('medicina', 'virus'):
            # Medicina/virus: determinar si es para el jugador o el oponente
            objetivo = self._opponent_of(jugador)
            # Asumimos que ataca/defiende el color de la carta
            player_idx = 1 if jugador.nombre == 'TÚ' else 0  # Oponente
            if carta.tipo == 'proteccion' and carta.color in jugador.aspectos:
                # Medicina propia
                player_idx = 0 if jugador.nombre == 'TÚ' else 1
            x, y = self._slot_center_for_player(player_idx, carta.color)
            return (x, y)
        else:
            # Tratamientos: va al centro de la pantalla
            return (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
    
    def _start_fly_animation(self, carta: Carta, start: Tuple[int, int], end: Tuple[int, int], on_done):
        """Inicia animación de vuelo de carta con efectos visuales mejorados"""
        steps = 20  # Más frames para animación más suave
        self.fly_anim = {
            'card': carta, 
            'x': float(start[0]), 
            'y': float(start[1]), 
            'sx': start[0], 
            'sy': start[1], 
            'ex': end[0], 
            'ey': end[1], 
            't': 0, 
            'steps': steps, 
            'angle': 0.0,
            'on_done': on_done
        }
        # Emitir partículas desde el punto de inicio
        self._emit_particles(start[0], start[1], COLOR_GOLD, count=8)

    def _hand_card_center(self, index: int) -> Tuple[int, int]:
        # mano inferior centrada
        gap = 140
        count = max(1, len(self.jugadores[0].mano))
        total_w = (count - 1) * gap
        card_width, card_height = CARD_WIDTH, CARD_HEIGHT
        y_pos = WINDOW_HEIGHT - card_height // 2 - 90  # Ajustado para dejar espacio para la barra inferior
        start_x = WINDOW_WIDTH // 2 - total_w // 2
        return (start_x + index * gap, y_pos)

    def _tick_fly_animation(self):
        if not self.fly_anim:
            return
        t = self.fly_anim['t'] + 1
        steps = self.fly_anim['steps']
        
        # TIMEOUT: Si la animación lleva demasiados frames (>60 = 1 segundo), forzar finalización
        if t > 60:
            self._trace("[WARNING] Animación atascada, forzando finalización")
            on_done = self.fly_anim.get('on_done')
            self.fly_anim = None
            if on_done:
                try:
                    on_done()
                except Exception as e:
                    self._trace(f"[ERROR] Error en on_done: {e}")
            return
        
        sx, sy, ex, ey = self.fly_anim['sx'], self.fly_anim['sy'], self.fly_anim['ex'], self.fly_anim['ey']
        ratio = min(1.0, t / steps)
        # Usar easing mejorado con pequeño rebote al final
        ratio = self._ease_out_back(ratio)
        # Agregar rotación sutil durante el vuelo
        angle_offset = math.sin(ratio * math.pi) * 5  # Rotación de hasta 5 grados
        self.fly_anim['x'] = sx + (ex - sx) * ratio
        self.fly_anim['y'] = sy + (ey - sy) * ratio
        self.fly_anim['angle'] = angle_offset  # Guardar ángulo para rotación visual
        self.fly_anim['t'] = t
        if t >= steps:
            on_done = self.fly_anim['on_done']
            self.fly_anim = None
            try:
                on_done()
            except Exception as e:
                self._trace(f"[ERROR] Error en on_done de animación: {e}")
            return
        # schedule next tick
        # handled in main loop via render() + clock

    def _start_or_queue_fly(self, carta: Carta, start: Tuple[int, int], end: Tuple[int, int], on_done) -> None:
        if self.fly_anim is None:
            self._start_fly_animation(carta, start, end, on_done)
        else:
            self._draw_queue.append((carta, start, end))

    def _animate_draw_sequence(self, jugador: Jugador, count: int, on_all_done=None) -> None:
        if count <= 0:
            if on_all_done:
                try:
                    on_all_done()
                except Exception:
                    pass
            return
        # Construir destino para las últimas 'count' cartas de la mano
        last_indexes = list(range(len(jugador.mano) - count, len(jugador.mano)))
        starts: List[Tuple[int, int]] = []
        if hasattr(self, 'deck_rect') and self.deck_rect:
            s = (self.deck_rect.centerx, self.deck_rect.centery)
        else:
            s = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        for _ in last_indexes:
            starts.append(s)

        # Encadenar animaciones
        def make_on_done(idx: int):
            def _on_done():
                next_idx = idx + 1
                if next_idx < len(last_indexes):
                    card = jugador.mano[last_indexes[next_idx]]
                    self._start_fly_animation(card, starts[next_idx], self._hand_card_center(last_indexes[next_idx]), make_on_done(next_idx))
                else:
                    # Ejecutar animaciones pendientes si las hubiera
                    if self._draw_queue:
                        c, st, en = self._draw_queue.pop(0)
                        self._start_fly_animation(c, st, en, lambda: None)
                    if on_all_done:
                        try:
                            on_all_done()
                        except Exception:
                            pass
            return _on_done

        first_idx = last_indexes[0]
        first_card = jugador.mano[first_idx]
        self._start_fly_animation(first_card, starts[0], self._hand_card_center(first_idx), make_on_done(0))

    def _commit_play(self, jugador: Jugador, carta: Carta):
        """Confirma la jugada de una carta con efectos visuales"""
        resultado = self.jugar_carta(jugador, carta)
        if not resultado:
            # La jugada falló - descartar la carta para evitar loop infinito
            if carta in jugador.mano:
                jugador.mano.remove(carta)
            self.descarte.append(carta)
            # Efecto visual de fallo
            self._emit_particles(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, COLOR_RED, count=15)
            self.siguiente_turno()
            return
        
        # Efecto visual de éxito: partículas doradas en el destino
        if carta.tipo == 'aspecto':
            # Aspecto colocado: efecto en el slot
            if carta.color in jugador.aspectos:
                cx, cy = self._slot_center_for_player(0 if jugador is self.jugadores[0] else 1, carta.color)
                self._emit_particles(cx, cy, COLOR_GREEN, count=20)
        elif carta.tipo in ('ataque', 'problema'):
            # Ataque/Problema: efecto rojo en el objetivo
            target_idx = 1 if jugador is self.jugadores[0] else 0
            if carta.color in self.jugadores[target_idx].aspectos:
                cx, cy = self._slot_center_for_player(target_idx, carta.color)
                self._emit_particles(cx, cy, COLOR_RED_INTENSE, count=20)
        elif carta.tipo == 'proteccion':
            # Protección: efecto azul
            if carta.color in jugador.aspectos:
                cx, cy = self._slot_center_for_player(0 if jugador is self.jugadores[0] else 1, carta.color)
                self._emit_particles(cx, cy, COLOR_BLUE_BRIGHT, count=15)
        
        # La jugada fue exitosa
        if carta in jugador.mano:
            jugador.mano.remove(carta)
        self.descarte.append(carta)
        # limpiar TODOS los estados de selección/drag para evitar bloquear el flujo
        self.selected_hand_idx = None
        self.carta_arrastrando = None
        self.cartas_multi_drag.clear()
        self.discard_selection.clear()
        self.is_dragging = False
        self.status_msg = ''
        self._trace(f"[PLAY] {jugador.nombre} juega {carta.tipo}:{carta.color}")
        # Diario jugada
        try:
            tag = 'ATAQUE' if carta.tipo == 'virus' else ('DEFENSA' if carta.tipo == 'medicina' else 'JUEGO')
            detalle = f" ⇒ {self.last_action_detail}" if self.last_action_detail else ''
            self._diario(f"[{jugador.nombre}] Jugada {self.jugada_idx} [{tag}]: {carta.tipo}:{carta.color}{detalle}")
        except Exception:
            pass
        self.stalled_steps = 0
        # Victoria
        winner = self.comprobar_victoria()
        if winner:
            try:
                self._diario(f"\n🏆 ¡VICTORIA DE [{winner}]! Alcanza 4 órganos sanos en {self.jugada_idx} jugadas.\n")
            except Exception:
                pass
            self.game_over = True
            self.winner = winner
            self.autoplay = False
            self.status_msg = f"Victoria de {winner}!"
            return
        self.siguiente_turno()
        self.last_action_detail = ''
    
    def _discard_card(self, jugador: Jugador, carta: Carta) -> None:
        # descartado de 1 carta => robar 1 y PASAR automáticamente
        if carta in jugador.mano:
            idx = jugador.mano.index(carta)
            self._perform_discard_indices(jugador, [idx], auto_pass=True)

    def _perform_discard_indices(self, jugador: Jugador, indices: List[int], auto_pass: bool = False) -> None:
        # Descartar múltiples índices (orden descendente) y robar la misma cantidad
        if not indices:
            return
        # Guardar índices a reemplazar y descartar en orden descendente para pop seguro
        indices = sorted([i for i in indices if 0 <= i < len(jugador.mano)], reverse=True)
        num = 0
        descartadas: List[Carta] = []
        for i in indices:
            try:
                carta = jugador.mano.pop(i)
                self.descarte.append(carta)
                num += 1
                descartadas.append(carta)
            except Exception:
                pass
        # Robar la misma cantidad e INSERTAR en las mismas posiciones originales (mantener orden visual)
        drawn = 0
        recibidas: List[Carta] = []
        # Insertar de nuevo en orden ASCENDENTE para respetar índices originales tras los pops
        indices_insert = sorted(indices)
        for idx in indices_insert:
            if not self.mazo:
                self._recycle_discard()
            if self.mazo:
                c = self.mazo.pop()
                # Limitar índice por si la mano quedó más corta
                safe_idx = max(0, min(idx, len(jugador.mano)))
                jugador.mano.insert(safe_idx, c)
                drawn += 1
                recibidas.append(c)
        # limpiar selección/estados y pasar turno automáticamente tras robar
        self.discard_selection.clear()
        self.selected_hand_idx = None
        self.carta_arrastrando = None
        self.status_msg = f'Descartaste {num}.'
        # Diario
        try:
            desc_nombres = ', '.join([f"{c.tipo}:{c.color}" for c in descartadas]) if descartadas else '—'
            recv_nombres = ', '.join([f"{c.tipo}:{c.color}" for c in recibidas]) if recibidas else '—'
            linea = f"[{jugador.nombre}] Jugada {self.jugada_idx} [DESCARTE]: descarta {num} y recibe {drawn}"
            self._diario(linea)
        except Exception:
            pass
        # animación de robo: solo las realmente robadas
        if drawn > 0:
            self._animate_draw_sequence(jugador, drawn, on_all_done=lambda: self.siguiente_turno())
        else:
            self.siguiente_turno()
    
    def _trigger_fx(self, color: str, fx_type: str) -> None:
        # 30 frames ~ 0.5s
        self.fx_active[color] = {'type': fx_type, 't': 0, 'dur': 30}
        # Emite partículas en centro de la zona correspondiente
        try:
            # localizar slot del jugador humano (fila inferior) por color
            x0, y0 = self._slot_center_for_player(0, color)
            x1, y1 = self._slot_center_for_player(1, color)
            col = COLOR_GOLD if fx_type == 'place' else (COLOR_BLUE_BRIGHT if fx_type in ('vaccinate', 'cure') else (COLOR_SILVER if fx_type == 'immunize' else COLOR_RED_INTENSE))
            self._emit_particles(x0, y0, col, 14)
            self._emit_particles(x1, y1, col, 8)
        except Exception:
            pass

    def _play_sfx(self, name: str) -> None:
        if not getattr(self, 'sound_enabled', True):
            return
        snd = self.sounds.get(name)
        try:
            if snd:
                snd.play()
        except Exception:
            pass

    # _recycle_discard está en GameEngine (engine.py)

    # ==== Estado UX ====
    def render_status(self) -> None:
        assert self.screen is not None
        y_cursor = 56
        # Mensaje de victoria (grande y prominente)
        if self.game_over and self.winner:
            victoria_text = f"🏆 ¡VICTORIA DE {self.winner}!"
            txt = self.font_large.render(victoria_text, True, COLOR_GOLD)
            bg = txt.get_rect()
            bg.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 100)
            bg.inflate_ip(40, 20)
            # Fondo semitransparente oscuro
            blit_rounded_panel(self.screen, bg.x, bg.y, bg.width, bg.height,
                              bg_rgba=(0, 0, 0, 200), border_rgba=(*COLOR_GOLD, 255), border_px=4, radius=8)
            self.screen.blit(txt, (bg.centerx - txt.get_width()//2, bg.centery - txt.get_height()//2))
            # Mensaje secundario
            msg2 = f"Alcanza 4 aspectos saludables en {self.jugada_idx} jugadas"
            txt2 = self.font_medium.render(msg2, True, COLOR_WHITE)
            bg2 = txt2.get_rect()
            bg2.center = (WINDOW_WIDTH // 2, bg.bottom + 30)
            bg2.inflate_ip(30, 15)
            blit_rounded_panel(self.screen, bg2.x, bg2.y, bg2.width, bg2.height,
                              bg_rgba=(0, 0, 0, 180), border_rgba=(*COLOR_WHITE, 255), border_px=2, radius=8)
            self.screen.blit(txt2, (bg2.centerx - txt2.get_width()//2, bg2.centery - txt2.get_height()//2))
            # No mostrar status_msg cuando hay victoria (ya se muestra el mensaje grande arriba)
            return
        if self.status_msg:
            txt = self.font_medium.render(self.status_msg, True, COLOR_WHITE)
            bg = txt.get_rect()
            bg.center = (WINDOW_WIDTH // 2, y_cursor)
            bg.inflate_ip(24, 12)
            # Overlay con alfa y bordes redondeados
            blit_rounded_panel(self.screen, bg.x, bg.y, bg.width, bg.height,
                              bg_rgba=(0, 0, 0, 180), border_rgba=(*COLOR_GOLD, 220), border_px=2, radius=8)
            self.screen.blit(txt, (bg.centerx - txt.get_width()//2, bg.centery - txt.get_height()//2))
            y_cursor += bg.height + 6
        if self.hover_help_text:
            txt2 = self.font_small.render(self.hover_help_text, True, COLOR_WHITE)
            bg2 = txt2.get_rect()
            bg2.center = (WINDOW_WIDTH // 2, y_cursor)
            bg2.inflate_ip(18, 10)
            blit_rounded_panel(self.screen, bg2.x, bg2.y, bg2.width, bg2.height,
                              bg_rgba=(20, 20, 20, 180), border_rgba=(160, 160, 160, 220), border_px=1, radius=8)
            self.screen.blit(txt2, (bg2.centerx - txt2.get_width()//2, bg2.centery - txt2.get_height()//2))
    def run(self):
        autorun = ('--autorun' in sys.argv) or (os.getenv('AUTORUN', '').lower() in ('1', 'true', 'yes'))
        if autorun:
            self.nivel_ia = 'facil'
            self.autoplay = True
        else:
            self.nivel_ia = 'medio'  # Nivel por defecto sin menú
        running = True
        self.iniciar_partida()
        if self.headless:
            return
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    # scroll del diario: solo si está abierto
                    if self.diario_open:
                        self.diario_scroll = max(0, self.diario_scroll - event.y)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.selected_hand_idx is not None:
                        self.selected_hand_idx = None
                        self.status_msg = ''
                    else:
                        running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    self.sound_enabled = not self.sound_enabled
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_d:
                    # Descarta carta seleccionada
                    if self.turno == 0 and self.selected_hand_idx is not None:
                        try:
                            carta = self.jugadores[0].mano[self.selected_hand_idx]
                            self._discard_card(self.jugadores[0], carta)
                        except Exception:
                            pass
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    # ENTER: Jugar tratamiento seleccionado (excepto LADRÓN que necesita target)
                    if self.turno == 0 and self.selected_hand_idx is not None:
                        try:
                            carta = self.jugadores[0].mano[self.selected_hand_idx]
                            if carta.tipo == 'tratamiento' and carta.color != 'ladrón':
                                ok, msg = self.es_jugable(carta, self.jugadores[0])
                                if ok:
                                    # Usar _commit_play para consistencia con drag & drop
                                    self._commit_play(self.jugadores[0], carta)
                                else:
                                    self.status_msg = msg
                        except Exception:
                            pass  # Silenciar errores en producción
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                    self.autoplay = not self.autoplay
                    # El indicador visual en pantalla muestra el estado
            # animaciones
            if self.fly_anim:
                self._tick_fly_animation()
            
            # No permitir jugadas si el juego terminó
            if self.game_over:
                # Solo permitir renderizado, no acciones
                self.render()
                self.clock.tick(FPS)
                continue
            
            # Auto-play: IA siempre juega automáticamente, jugador humano solo si autoplay está ON
            jugador_actual = self.jugadores[self.turno]
            debe_jugar_auto = (jugador_actual.nombre == 'IA') or self.autoplay
            
            if debe_jugar_auto:
                if self.fly_anim:
                    # Si hay animación activa, verificar si está tomando demasiado tiempo
                    if self.fly_anim.get('t', 0) > 45:  # Más de 45 frames (0.75s) es sospechoso
                        # Forzar finalización de animación lenta
                        on_done = self.fly_anim.get('on_done')
                        self.fly_anim = None
                        if on_done:
                            try:
                                on_done()
                            except Exception:
                                pass
                else:
                    # No hay animación, ejecutar autoplay
                    now = pygame.time.get_ticks()
                    if now - self.last_auto_ms > 200:  # Reducido de 350ms a 200ms para más fluidez
                        self._auto_play_current_turn()
                        self.last_auto_ms = now
            self.render()
            self.clock.tick(FPS)
        pygame.quit(); sys.exit()

def self_test() -> bool:
    """Pequeña batería de pruebas de reglas sin abrir ventana."""
    g = VirusGame(headless=True)
    g.iniciar_partida()
    # Forzar manos previsibles
    # Añade un órgano corazón al jugador 0
    j = g.jugadores[0]
    j.mano = [Carta('organo', 'corazon', 'Órgano corazon')]
    assert g.jugar_carta(j, j.mano[0]) is True
    j.mano.clear(); g.descarte.clear()
    # Infectar y destruir con virus doble
    j.mano = [Carta('virus', 'corazon', 'Virus corazon')]
    assert g.jugar_carta(j, j.mano[0]) is True
    j.mano = [Carta('virus', 'corazon', 'Virus corazon')]
    assert g.jugar_carta(j, j.mano[0]) is True
    assert 'corazon' not in j.organos
    # Colocar 4 aspectos saludables => victoria
    for c in ['corazon', 'cerebro', 'huesos', 'estomago']:
        j.mano = [Carta('organo', c, f'Órgano {c}')]
        assert g.jugar_carta(j, j.mano[0]) is True
        j.mano.clear()
    assert g.comprobar_victoria() == 'TÚ'
    return True


if __name__ == '__main__':
    game = VirusGame()
    game.run()


