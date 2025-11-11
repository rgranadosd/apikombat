#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Engine - game logic without rendering dependencies.
Keeps gameplay separate from the pygame-based presentation layer.
"""

import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import os


class Carta:
    def __init__(self, tipo: str, color: str, nombre: str):
        self.tipo = tipo
        self.color = color
        self.nombre = nombre
    
    def __repr__(self):
        return f"Carta({self.tipo}, {self.color})"


class Jugador:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.mano: List[Carta] = []
        self.aspectos: Dict[str, Dict] = {}  # Formerly: organs
        self.treatment_shield: bool = False  # Formerly: code_freeze_shield
    
    def aspectos_saludables(self) -> int:
        """Return the number of healthy (non-vulnerable) aspects."""
        return sum(1 for a in self.aspectos.values() if not a.get('vulnerable', False))
    
    # Backward compatibility: keep legacy organs property
    @property
    def organos(self) -> Dict[str, Dict]:
        return self.aspectos
    
    def organos_sanos(self) -> int:
        return self.aspectos_saludables()


# API aspects (formerly COLORS)
ASPECTOS = ['seguridad', 'documentacion', 'gobierno', 'performance']

# Aspect mapping (legacy COLOR_MAP)
ASPECTO_MAP = {
    'seguridad': {'color': (255, 100, 100), 'icon': '🔒', 'label': 'SECURITY'},
    'documentacion': {'color': (52, 152, 219), 'icon': '📚', 'label': 'DOCUMENTATION'},
    'gobierno': {'color': (155, 89, 182), 'icon': '🏛️', 'label': 'GOVERNANCE'},
    'performance': {'color': (46, 204, 113), 'icon': '⚡', 'label': 'PERFORMANCE'},
    'multicolor': {'color': (155, 89, 182), 'icon': '🌈', 'label': 'WILDCARD'}
}

# Security hack names
HACKS_SEGURIDAD = ['DoS', 'Brute Force', 'OWASP', 'Bad Design']

# Documentation hack names
HACKS_DOCUMENTACION = ['Integration Delay', 'Knowledge Silos', 'Onboarding Friction', 'Disabled AI agents']

# Governance hack names
HACKS_GOBIERNO = ['Low Reusability', 'Shadow APIs', 'Broken Ownership', 'Data Leakage Risk']

# Performance hack names
HACKS_PERFORMANCE = ['Tooling Fragmentation', 'Inefficient API Gateways', 'Poor Developer Experience (DX)', 'Reactive Scaling']

# Security shield names
SHIELDS_SEGURIDAD = ['Automatic audits', 'ApiGateway', 'Identity Server', 'Rate Limiting']

# Documentation shield names
SHIELDS_DOCUMENTACION = ['OpenAPI + JSON Schema + Samples', 'AI Documentation', 'Dev Portal', 'Api Team']

# Governance shield names
SHIELDS_GOBIERNO = ['DevOps', 'Deployment Control', 'API Scoring', 'API Catalog']

# Performance shield names
SHIELDS_PERFORMANCE = ['Unified Stack', 'Testing End2End', 'Time to First Successful Call (TTFSC)', 'Cloud Control Plane']

# Compatibility: keep legacy names for older code
ATAQUES_SEGURIDAD = HACKS_SEGURIDAD
PROTECCIONES_SEGURIDAD = SHIELDS_SEGURIDAD

# Compatibility: keep COLORS alias for legacy code (will be removed gradually)
COLORS = ASPECTOS
COLOR_MAP = ASPECTO_MAP

STEAL_SUBTYPES = {'ladron', 'ladr\u00f3n', 'migration', 'migracion', 'steal'}
SWAP_SUBTYPES = {'transplant', 'trasplante', 'refactoring'}
MIRROR_SUBTYPES = {'mirroring', 'contagio', 'activo_activo'}
FREEZE_SUBTYPES = {'code_freeze', 'guante'}
ROLLBACK_SUBTYPES = {'rollback', 'error'}


class GameEngine:
    """Game engine containing all game logic without rendering."""
    
    def __init__(self, trace_enabled: bool = False, diario_path: Optional[str] = None):
        self.jugadores = [Jugador('YOU'), Jugador('AI')]
        self.turno = 0
        self.mazo: List[Carta] = []
        self.descarte: List[Carta] = []
        self.nivel_ia = 'facil'
        
        # Game state
        self.jugada_idx: int = 1
        self.stalled_steps: int = 0
        self.blocked: bool = False
        self.game_over: bool = False
        self.winner: Optional[str] = None
        
        # Logging
        self.trace_enabled: bool = trace_enabled
        self.trace_file_path = os.path.join(os.path.dirname(__file__), 'assets', 'trace.log')
        self.diario_path = diario_path or os.path.join(os.path.dirname(__file__), 'assets', 'diario.txt')
        
        # Clear diary file when the engine starts
        try:
            with open(self.diario_path, 'w', encoding='utf-8') as f:
                f.write('')  # Empty file
        except Exception:
            pass
        
        # UI state kept for compatibility, not used by the engine
        self.last_action_detail: str = ''
    
    def _opponent_of(self, jugador: Jugador) -> Jugador:
        """Return the opponent of the provided player."""
        return self.jugadores[1] if jugador == self.jugadores[0] else self.jugadores[0]
    
    def crear_mazo(self) -> List[Carta]:
        """Create and shuffle the complete deck according to the configured list."""
        cartas = []
        
        # Fundamentals (10 cards total)
        # Security, Documentation, Governance, Performance (2 copies each)
        for c in ASPECTOS:
            for _ in range(2):
                cartas.append(Carta('fundamental', c, ASPECTO_MAP[c]['label']))
        # All (Wildcard) - 2 copies
        for _ in range(2):
            cartas.append(Carta('fundamental', 'multicolor', 'All'))
        
        # Hack Security (9 cards)
        for nombre_hack in HACKS_SEGURIDAD:
            for _ in range(2):
                cartas.append(Carta('hack', 'seguridad', nombre_hack))
        cartas.append(Carta('hack', 'seguridad', 'WildCard'))  # 1 copy
        
        # Hack Documentation (9 cards)
        for nombre_hack in HACKS_DOCUMENTACION:
            for _ in range(2):
                cartas.append(Carta('hack', 'documentacion', nombre_hack))
        cartas.append(Carta('hack', 'documentacion', 'WildCard'))  # 1 copy
        
        # Hack Governance (9 cards)
        for nombre_hack in HACKS_GOBIERNO:
            for _ in range(2):
                cartas.append(Carta('hack', 'gobierno', nombre_hack))
        cartas.append(Carta('hack', 'gobierno', 'Wildcard'))  # 1 copy
        
        # Hack Performance (9 cards)
        for nombre_hack in HACKS_PERFORMANCE:
            for _ in range(2):
                cartas.append(Carta('hack', 'performance', nombre_hack))
        cartas.append(Carta('hack', 'performance', 'WildCard'))  # 1 copy
        
        # Shield Security (9 cards)
        for nombre_shield in SHIELDS_SEGURIDAD:
            for _ in range(2):
                cartas.append(Carta('shield', 'seguridad', nombre_shield))
        cartas.append(Carta('shield', 'seguridad', 'Wildcard'))  # 1 copy
        
        # Shield Documentation (9 cards)
        for nombre_shield in SHIELDS_DOCUMENTACION:
            for _ in range(2):
                cartas.append(Carta('shield', 'documentacion', nombre_shield))
        cartas.append(Carta('shield', 'documentacion', 'Wildcard'))  # 1 copy
        
        # Shield Governance (9 cards)
        for nombre_shield in SHIELDS_GOBIERNO:
            for _ in range(2):
                cartas.append(Carta('shield', 'gobierno', nombre_shield))
        cartas.append(Carta('shield', 'gobierno', 'Wildcard'))  # 1 copy
        
        # Shield Performance (9 cards)
        for nombre_shield in SHIELDS_PERFORMANCE:
            for _ in range(2):
                cartas.append(Carta('shield', 'performance', nombre_shield))
        cartas.append(Carta('shield', 'performance', 'Wildcard'))  # 1 copy
        
        # Management (8 cards)
        for _ in range(2):
            cartas.append(Carta('management', 'refactoring', 'Refactoring'))
        for _ in range(2):
            cartas.append(Carta('management', 'migration', 'Migration'))
        for _ in range(2):
            cartas.append(Carta('management', 'mirroring', 'Mirroring'))
        cartas.append(Carta('management', 'code_freeze', 'Code Freeze'))  # 1 copy
        cartas.append(Carta('management', 'rollback', 'Rollback'))  # 1 copy
        
        random.shuffle(cartas)
        random.shuffle(cartas)
        return cartas
    
    def repartir(self):
        """Deal three cards to each player."""
        for jugador in self.jugadores:
            jugador.mano = []
            jugador.aspectos = {}  # Formerly: organs
        for _ in range(3):
            for jugador in self.jugadores:
                if not self.mazo:
                    self._recycle_discard()
                if self.mazo:
                    jugador.mano.append(self.mazo.pop())
    
    def iniciar_partida(self):
        """Start a new match."""
        self.mazo = self.crear_mazo()
        self.repartir()
        self.descarte = []
        self.turno = 0
        self._trace('[GAME] New match started')
        self.jugada_idx = 1
        self.stalled_steps = 0
        self.blocked = False
        self.game_over = False
        self.winner = None
        # Reset treatment shields (code freeze) when starting a new match
        for jugador in self.jugadores:
            jugador.treatment_shield = False
        try:
            self._diario(f"\n=== Match started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        except Exception:
            pass
    
    def jugar_carta(self, jugador: Jugador, carta: Carta) -> bool:
        """Attempt to play a card. Returns True if the play succeeds."""
        # Management cards (legacy interventions/treatments)
        if carta.tipo == 'management':
            return self._jugar_intervencion(jugador, carta)
        # Compatibility: keep legacy intervention/treatment types for old code
        if carta.tipo == 'intervencion' or carta.tipo == 'tratamiento':
            return self._jugar_intervencion(jugador, carta)
        # Fundamentals (legacy aspects/organs)
        if carta.tipo == 'fundamental' or carta.tipo == 'aspecto' or carta.tipo == 'organo':
            # Verificar límite de aspectos
            if len(jugador.aspectos) >= 4:
                self.last_action_detail = "ERROR: You already have 4 aspects (maximum allowed)"
                return False
            # Resolver color específico si es multicolor
            color_final = carta.color
            if carta.color == 'multicolor':
                color_resuelto = self._resolver_destino_color(jugador, carta)
                if color_resuelto is None:
                    self.last_action_detail = "ERROR: You already have every available aspect (4/4)"
                    return False  # No hay slot disponible
                color_final = color_resuelto
            # Verificar que no exista ya ese aspecto
            if color_final in jugador.aspectos:
                asp_existente = jugador.aspectos[color_final]
                estado = "vulnerable" if asp_existente.get('vulnerable', False) else "saludable"
                protecciones = asp_existente.get('protecciones', 0)
                estado_prot = f", {protecciones} protection(s)" if protecciones > 0 else ""
                self.last_action_detail = f"ERROR: You already have {ASPECTO_MAP[color_final]['label']} ({estado}{estado_prot})"
                return False
            jugador.aspectos[color_final] = {'vulnerable': False, 'protecciones': 0}
            self.last_action_detail = f"place aspect {ASPECTO_MAP[color_final]['label']}"
            return True
        # Hacks (legacy attacks/problems/viruses)
        if carta.tipo == 'hack' or carta.tipo == 'ataque' or carta.tipo == 'problema' or carta.tipo == 'virus':
            objetivo = self._opponent_of(jugador)
            # Verificar si el objetivo tiene escudo (code freeze) activo
            if objetivo.treatment_shield:
                objetivo.treatment_shield = False
                self.last_action_detail = f"ATTACK blocked - {objetivo.nombre}'s CODE FREEZE cancels the attack"
                # Log in the diary that the shield was consumed
                try:
                    self._diario(f"    [INFO] 🛡️ Code Freeze for [{objetivo.nombre}] consumed - an attack was blocked.")
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
                self.last_action_detail = f"ATTACK {objetivo.nombre}: blocked - {ASPECTO_MAP[color_final]['label']} protected"
                return False
            if asp.get('vulnerable', False):
                del objetivo.aspectos[color_final]
                self.last_action_detail = f"ATTACK {objetivo.nombre}: destroys {ASPECTO_MAP[color_final]['label']} (was already vulnerable)"
            else:
                asp['vulnerable'] = True
                self.last_action_detail = f"ATTACK {objetivo.nombre}: exposes {ASPECTO_MAP[color_final]['label']}"
            return True
        # Shields (legacy protections/medicine)
        if carta.tipo == 'shield' or carta.tipo == 'proteccion' or carta.tipo == 'medicina':
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
                self.last_action_detail = f"DEFEND: heals vulnerability in {ASPECTO_MAP[color_final]['label']}"
            pre = asp.get('protecciones', 0)
            asp['protecciones'] = min(2, asp.get('protecciones', 0) + 1)
            if asp['protecciones'] >= 2 and pre < 2:
                self.last_action_detail = f"DEFEND: fortifies {ASPECTO_MAP[color_final]['label']}"
            elif asp['protecciones'] >= 1 and pre < 1:
                self.last_action_detail = f"DEFEND: protects {ASPECTO_MAP[color_final]['label']}"
            elif not self.last_action_detail:
                self.last_action_detail = f"DEFEND: strengthens protection on {ASPECTO_MAP[color_final]['label']}"
            return True
        return False
    
    def _jugar_intervencion(self, jugador: Jugador, carta: Carta, target_color: Optional[str] = None) -> bool:
        """Play an intervention (legacy treatment)."""
        return self._jugar_tratamiento(jugador, carta, target_color)
    
    def _jugar_tratamiento(self, jugador: Jugador, carta: Carta, target_color: Optional[str] = None) -> bool:
        """Legacy compatibility layer that delegates to _jugar_intervencion."""
        objetivo = self._opponent_of(jugador)
        # If the opponent has an active shield and this treatment would affect them, consume it and cancel
        def consumes_shield_if_affects(target: Jugador) -> bool:
            if target.treatment_shield:
                target.treatment_shield = False
                self.last_action_detail = f"TREATMENT cancelled by CODE FREEZE from {target.nombre}"
                # Log in the diary that the shield was consumed
                try:
                    self._diario(f"    [INFO] 🛡️ Shield for [{target.nombre}] consumed - blocked a treatment.")
                except Exception:
                    pass
                return True
            return False

        subtipo = carta.color
        subtipo_norm = subtipo.lower().replace("\u00f3", "o")
        # Compatibility: support legacy subtype names
        if subtipo_norm in STEAL_SUBTYPES:
            if consumes_shield_if_affects(objetivo):
                return True
            # If the user specified a target color, validate it
            if target_color is not None:
                if target_color not in objetivo.aspectos:
                    # Opponent lacks that aspect
                    self.last_action_detail = f"ERROR: {objetivo.nombre} does not have aspect {ASPECTO_MAP[target_color]['label']}"
                    try:
                        self._diario(f"    [ERROR] Steal failed: {objetivo.nombre} lacks {ASPECTO_MAP[target_color]['label']}")
                    except Exception:
                        pass
                    return False
                if target_color in jugador.aspectos:
                    # You already own that aspect, so you cannot steal it
                    self.last_action_detail = f"ERROR: You already own {ASPECTO_MAP[target_color]['label']}; cannot steal it"
                    try:
                        self._diario(f"    [ERROR] Steal failed: already own {ASPECTO_MAP[target_color]['label']}, you can only steal missing aspects")
                    except Exception:
                        pass
                    return False
                if target_color in objetivo.aspectos and target_color not in jugador.aspectos:
                    # Copy the complete aspect state (not just the reference)
                    jugador.aspectos[target_color] = {
                        'vulnerable': objetivo.aspectos[target_color].get('vulnerable', False),
                        'protecciones': objetivo.aspectos[target_color].get('protecciones', 0)
                    }
                    del objetivo.aspectos[target_color]
                    self.last_action_detail = f"steals aspect {ASPECTO_MAP[target_color]['label']} from {objetivo.nombre}"
                    return True
                return False
            # Otherwise, steal the first aspect you do not own
            for color, data in list(objetivo.aspectos.items()):
                if color not in jugador.aspectos:
                    # Copy the complete aspect state (not just the reference)
                    jugador.aspectos[color] = {
                        'vulnerable': data.get('vulnerable', False),
                        'protecciones': data.get('protecciones', 0)
                    }
                    del objetivo.aspectos[color]
                    self.last_action_detail = f"steals aspect {ASPECTO_MAP[color]['label']} from {objetivo.nombre}"
                    return True
            return False
        if subtipo_norm in SWAP_SUBTYPES:
            if consumes_shield_if_affects(objetivo):
                return True
            if not jugador.aspectos or not objetivo.aspectos:
                return False
            # If a target_color was provided, swap that specific opponent aspect
            if target_color is not None:
                # Ensure the opponent actually has that aspect
                if target_color not in objetivo.aspectos:
                    self.last_action_detail = f"ERROR: {objetivo.nombre} does not have {ASPECTO_MAP[target_color]['label']}"
                    return False
                # Look for a different aspect you can swap
                color_tuyo = None
                for c in jugador.aspectos.keys():
                    if c != target_color:  # Avoid swapping the same aspect
                        color_tuyo = c
                        break
                if color_tuyo is None:
                    # If you only own aspects of the same color, fall back to the first one
                    color_tuyo = next(iter(jugador.aspectos.keys()))
                # If the swap targets the same aspect (same color) do nothing
                if color_tuyo == target_color:
                    self.last_action_detail = f"REFACTORING no effect: both pick {ASPECTO_MAP[target_color]['label']}"
                    return True
                # Perform the swap
                temp = jugador.aspectos[color_tuyo].copy()
                jugador.aspectos[target_color] = objetivo.aspectos[target_color].copy()
                del objetivo.aspectos[target_color]
                objetivo.aspectos[color_tuyo] = temp
                del jugador.aspectos[color_tuyo]
                self.last_action_detail = f"swaps {ASPECTO_MAP[color_tuyo]['label']} ↔ {ASPECTO_MAP[target_color]['label']} with {objetivo.nombre}"
                return True
            # Without target_color: perform a simple swap (legacy behavior)
            color_a = next(iter(jugador.aspectos.keys()))
            color_b = next(iter(objetivo.aspectos.keys()))
            # If both aspects are the same, do nothing to avoid double removal
            if color_a == color_b:
                self.last_action_detail = f"REFACTORING no effect: both hold {ASPECTO_MAP[color_a]['label']}"
                return True
            if color_b in jugador.aspectos and color_a in objetivo.aspectos:
                # Avoid duplicates without an actual change
                pass
            temp = jugador.aspectos[color_a].copy()
            jugador.aspectos[color_b] = objetivo.aspectos[color_b].copy()
            del objetivo.aspectos[color_b]
            objetivo.aspectos[color_a] = temp
            del jugador.aspectos[color_a]
            self.last_action_detail = f"swaps {ASPECTO_MAP[color_a]['label']} ↔ {ASPECTO_MAP[color_b]['label']} with {objetivo.nombre}"
            return True
        if subtipo_norm in MIRROR_SUBTYPES:
            if consumes_shield_if_affects(objetivo):
                return True
            # Try to expose an opponent aspect that exists and is not fortified
            for color, asp_mio in jugador.aspectos.items():
                if asp_mio.get('vulnerable', False) and color in objetivo.aspectos:
                    asp_rival = objetivo.aspectos[color]
                    if asp_rival.get('protecciones', 0) < 2 and not asp_rival.get('vulnerable', False):
                        asp_rival['vulnerable'] = True
                        self.last_action_detail = f"Mirroring: exposes {ASPECTO_MAP[color]['label']} of {objetivo.nombre}"
                        return True
            return False
        if subtipo_norm in FREEZE_SUBTYPES:
            jugador.treatment_shield = True
            self.last_action_detail = "activates CODE FREEZE: cancels the next attack or intervention against you"
            return True
        if subtipo_norm in ROLLBACK_SUBTYPES:
            # Remove one protection from the opponent if available
            for color, asp in objetivo.aspectos.items():
                if asp.get('protecciones', 0) > 0:
                    asp['protecciones'] -= 1
                    self.last_action_detail = f"Rollback: reduces protection on {ASPECTO_MAP[color]['label']} of {objetivo.nombre}"
                    return True
            return False
        return False
    
    def es_jugable(self, carta: Carta, jugador: Jugador) -> Tuple[bool, str]:
        """Determine whether the given player can play the card. Returns (bool, message)."""
        # Management cards (legacy interventions/treatments)
        if carta.tipo == 'management' or carta.tipo == 'intervencion' or carta.tipo == 'tratamiento':
            subt = carta.color.lower().replace("\u00f3", "o")
            rival = self._opponent_of(jugador)
            if subt in STEAL_SUBTYPES:
                for color in rival.aspectos.keys():
                    if color not in jugador.aspectos:
                        return True, ''
                return False, 'The opponent has no aspects you can steal'
            if subt in SWAP_SUBTYPES:
                if jugador.aspectos and rival.aspectos:
                    return True, ''
                return False, 'Both players must hold at least one aspect'
            if subt in MIRROR_SUBTYPES:
                tiene_vulnerable = False
                aspectos_vulnerables = []
                aspectos_compatibles = []
                for color, asp in jugador.aspectos.items():
                    if asp.get('vulnerable', False):
                        tiene_vulnerable = True
                        aspectos_vulnerables.append(color)
                        if color in rival.aspectos:
                            asp_rival = rival.aspectos[color]
                            if asp_rival.get('protecciones', 0) >= 2:
                                aspectos_compatibles.append(f"{ASPECTO_MAP[color]['label']} (fortified)")
                                continue
                            if asp_rival.get('vulnerable', False):
                                aspectos_compatibles.append(f"{ASPECTO_MAP[color]['label']} (already vulnerable)")
                                continue
                        return True, ''
                if not tiene_vulnerable:
                    return False, 'You must have at least one vulnerable aspect'
                if aspectos_compatibles:
                    aspectos_str = ", ".join([ASPECTO_MAP[o]['label'] for o in aspectos_vulnerables])
                    return False, f'Vulnerable aspects: {aspectos_str}. Opponent lacks compatible aspects: {", ".join(aspectos_compatibles)}'
                aspectos_str = ", ".join([ASPECTO_MAP[o]['label'] for o in aspectos_vulnerables])
                return False, f'You have {aspectos_str} vulnerable, but the opponent lacks those aspects. Mirroring requires matching aspects.'
            if subt in FREEZE_SUBTYPES:
                return True, ''
            if subt in ROLLBACK_SUBTYPES:
                for asp in rival.aspectos.values():
                    if asp.get('protecciones', 0) > 0:
                        return True, ''
                return False, 'The opponent has no protections to remove'
            return False, 'Unknown intervention'
        # Fundamentals (legacy aspects/organs)
        if carta.tipo == 'fundamental' or carta.tipo == 'aspecto' or carta.tipo == 'organo':
            if carta.color == 'multicolor':
                # Multicolor aspect: you can place it if there is at least one free slot
                if len(jugador.aspectos) < 4:
                    return True, ''
                return False, 'You already have 4 aspects'
            if carta.color in jugador.aspectos:
                return False, f'You already have aspect {ASPECTO_MAP[carta.color]["label"]}'
            return True, ''
        # Hacks (hack) - legacy attack/problem/virus
        if carta.tipo == 'hack' or carta.tipo == 'ataque' or carta.tipo == 'problema' or carta.tipo == 'virus':
            objetivo = self._opponent_of(jugador)
            if carta.color == 'multicolor':
                # Multicolor attack/problem: you can target any opponent aspect
                for color, asp in objetivo.aspectos.items():
                    if asp.get('protecciones', 0) < 1:
                        return True, ''
                if objetivo.aspectos:
                    return False, 'All opponent aspects are protected'
                return False, 'The opponent has no aspects'
            if carta.color not in objetivo.aspectos:
                return False, f'The opponent does not have aspect {ASPECTO_MAP[carta.color]["label"]}'
            asp = objetivo.aspectos[carta.color]
            if asp.get('protecciones', 0) >= 1:
                return False, f'Aspect {ASPECTO_MAP[carta.color]["label"]} protected'
            return True, ''
        # Shields (shield) - legacy protection/medicine
        if carta.tipo == 'shield' or carta.tipo == 'proteccion' or carta.tipo == 'medicina':
            if carta.color == 'multicolor':
                # Multicolor protection: you can defend any aspect you control
                if jugador.aspectos:
                    return True, ''
                return False, 'You have no aspects'
            if carta.color not in jugador.aspectos:
                return False, f'You do not have aspect {ASPECTO_MAP[carta.color]["label"]}'
            return True, ''
        return True, ''
    
    def siguiente_turno(self):
        """Advance to the next turn and draw cards if needed."""
        prev = self.jugadores[self.turno]
        
        # Draw cards for the current player (before changing turn)
        while len(prev.mano) < 3:
            if not self.mazo:
                self._recycle_discard()
                if not self.mazo:
                    break
            prev.mano.append(self.mazo.pop())
        
        # Now change turn
        self.turno = (self.turno + 1) % len(self.jugadores)
        jugador = self.jugadores[self.turno]
        
        # Log end of turn
        try:
            self._diario(f"   [{prev.nombre}] → End of play {self.jugada_idx}. Turn for [{jugador.nombre}]")
        except Exception:
            pass
        self.jugada_idx += 1
        self._trace(f"[TURN] Now playing: {jugador.nombre}")
    
    def descartar_indices(self, jugador: Jugador, indices: List[int]) -> Tuple[int, int]:
        """Discard multiple indices and draw the same amount.
        Returns (discarded, drawn).
        """
        if not indices:
            return (0, 0)
        # Store indices in descending order for safe pops
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
        # Draw the same amount and insert at the original positions (preserve order)
        drawn = 0
        recibidas: List[Carta] = []
        indices_insert = sorted(indices)
        for idx in indices_insert:
            if not self.mazo:
                self._recycle_discard()
            if self.mazo:
                c = self.mazo.pop()
                safe_idx = max(0, min(idx, len(jugador.mano)))
                jugador.mano.insert(safe_idx, c)
                drawn += 1
                recibidas.append(c)
        
        # Diary
        try:
            desc_nombres = ', '.join([f"{c.tipo}:{c.color}" for c in descartadas]) if descartadas else '—'
            recv_nombres = ', '.join([f"{c.tipo}:{c.color}" for c in recibidas]) if recibidas else '—'
            linea = f"[{jugador.nombre}] Turn {self.jugada_idx} [DISCARD]: discards {num} and draws {drawn}"
            self._diario(linea)
        except Exception:
            pass
        
        return (num, drawn)
    
    def comprobar_victoria(self) -> Optional[str]:
        """Check if there is a winner. Returns the winner name or None."""
        for jugador in self.jugadores:
            if jugador.aspectos_saludables() >= 4:
                return jugador.nombre
        return None
    
    def _recycle_discard(self) -> None:
        """If the deck is empty, recycle the discard pile back into the deck."""
        if self.mazo:
            return
        if not self.descarte:
            return
        try:
            random.shuffle(self.descarte)
        except Exception:
            pass
        self.mazo.extend(self.descarte)
        self.descarte.clear()
        # Neutral diary entry
        self._diario('[INFO] Discard pile recycled back into the deck (shuffled).')
    
    def _resolver_destino_color(self, jugador: Jugador, carta: Carta) -> Optional[str]:
        """Resolve the destination color for a multicolor card."""
        if carta.tipo in ('aspecto', 'organo', 'fundamental'):
            if carta.color == 'multicolor':
                for c in ['seguridad', 'documentacion', 'gobierno', 'performance']:
                    if c not in jugador.aspectos:
                        return c
                return None
            return carta.color
        if carta.tipo in ('virus', 'medicina', 'ataque', 'problema', 'proteccion'):
            if carta.color == 'multicolor':
                for c in ['seguridad', 'documentacion', 'gobierno', 'performance']:
                    if c in jugador.aspectos:
                        return c
                return None
            return carta.color
        return None
    
    def _trace(self, message: str) -> None:
        """Write a message to the trace log (if enabled)."""
        if not self.trace_enabled:
            return
        try:
            print(message)
            with open(self.trace_file_path, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception:
            pass
    
    def _diario(self, message: str) -> None:
        """Append a message to the diary file."""
        try:
            with open(self.diario_path, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception:
            pass

