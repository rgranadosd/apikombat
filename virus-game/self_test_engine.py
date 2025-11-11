#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self Test del motor (engine) con trazas detalladas:
- Inicializa partida con semilla determinista
- Imprime mazo, manos iniciales, y por turno: juega/descarta/roba
- Muestra estado de aspectos tras cada acción
- Finaliza cuando hay ganador o tras N turnos
- Opcional: guarda log en assets/trace.log además de imprimir

Uso:
    python3 self_test_engine.py                    # Por defecto (seed=42, max_turns=20, sin log)
    python3 self_test_engine.py --seed 123        # Cambiar semilla
    python3 self_test_engine.py --max-turns 30     # Cambiar límite de turnos
    python3 self_test_engine.py --log              # Guardar log en archivo
    python3 self_test_engine.py --seed 100 --max-turns 50 --log  # Combinar opciones
"""
from __future__ import annotations
import os
import random
import argparse
from typing import Optional, Callable
from engine import GameEngine, Carta, Jugador


class Logger:
	def __init__(self, to_file: bool = False, file_path: Optional[str] = None):
		self.to_file = to_file
		self.file_path = file_path or os.path.join(os.path.dirname(__file__), 'assets', 'trace.log')
		if self.to_file:
			try:
				os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
				with open(self.file_path, 'w', encoding='utf-8') as f:
					f.write('')
			except Exception:
				pass

	def log(self, msg: str) -> None:
		print(msg)
		if self.to_file:
			try:
				with open(self.file_path, 'a', encoding='utf-8') as f:
					f.write(msg + "\n")
			except Exception:
				pass


def format_hand(j: Jugador) -> str:
	return ", ".join([f"{c.tipo}:{c.color}:{c.nombre}" for c in j.mano])


def print_aspectos(prefix: str, j: Jugador, log: Callable[[str], None]) -> None:
	estados = []
	for color, data in j.aspectos.items():
		prot = data.get('protecciones', 0)
		vuln = data.get('vulnerable', False)
		estados.append(f"{color}[{'V' if vuln else 'S'};prot={prot}]")
	log(f"{prefix} aspectos -> {{ " + ", ".join(estados) + " }}")


def try_play_first_playable(ge: GameEngine, j: Jugador, log: Callable[[str], None]) -> bool:
	for idx, c in enumerate(list(j.mano)):
		ok, msg = ge.es_jugable(c, j)
		if ok:
			log(f"  ✓ Juega {c.tipo}:{c.color}:{c.nombre}")
			if ge.jugar_carta(j, c):
				# sacar de la mano la carta jugada
				try:
					j.mano.pop(idx)
				except Exception:
					pass
				return True
			else:
				log("    ! jugar_carta devolvió False")
		else:
			log(f"  · No jugable {c.tipo}:{c.color}:{c.nombre} -> {msg}")
	return False


def ensure_hand_size(ge: GameEngine, j: Jugador, log: Callable[[str], None]) -> None:
	# Descarta si tiene >3; roba hasta 3 si tiene <3
	while len(j.mano) > 3:
		c = j.mano.pop(0)
		ge.descarte.append(c)
		log(f"  ↘ Descarta {c.tipo}:{c.color}:{c.nombre}")
	while len(j.mano) < 3:
		if not ge.mazo:
			ge._recycle_discard()
			if not ge.mazo:
				break
		c = ge.mazo.pop()
		j.mano.append(c)
		log(f"  ↗ Roba {c.tipo}:{c.color}:{c.nombre}")


def run(max_turns: int = 20, seed: int = 42, log_to_file: bool = False) -> None:
	logger = Logger(to_file=log_to_file)
	log = logger.log
	log(f"== SELF TEST ENGINE (seed={seed}, max_turns={max_turns}, log_to_file={log_to_file}) ==")
	random.seed(seed)
	ge = GameEngine(trace_enabled=False)
	ge.iniciar_partida()

	j0, j1 = ge.jugadores
	log(f"Jugadores: {j0.nombre}, {j1.nombre}")
	log(f"Mazo inicial: {len(ge.mazo)} cartas")
	log(f"Mano J0: {format_hand(j0)}")
	log(f"Mano J1: {format_hand(j1)}")

	turn = 0
	while turn < max_turns:
		current = ge.jugadores[ge.turno]
		log(f"\n-- Turno {turn+1} :: {current.nombre} --")
		print_aspectos("  Estado antes - J0", j0, log)
		print_aspectos("  Estado antes - J1", j1, log)
		log(f"  Mano actual: {format_hand(current)}")

		played = try_play_first_playable(ge, current, log)
		if not played:
			log("  (No pudo jugar, descarta/roba)")
			ensure_hand_size(ge, current, log)
		else:
			# tras jugar, rellena hasta 3 si procede
			ensure_hand_size(ge, current, log)

		print_aspectos("  Estado después - J0", j0, log)
		print_aspectos("  Estado después - J1", j1, log)
		log(f"  Mano J0: {len(j0.mano)} | Mano J1: {len(j1.mano)} | Mazo: {len(ge.mazo)} | Descarte: {len(ge.descarte)}")

		winner = ge.comprobar_victoria()
		if winner:
			log(f"\n== Ganador: {winner} ==")
			break

		ge.siguiente_turno()
		turn += 1

	if not ge.comprobar_victoria():
		log("\n== Fin por límite de turnos ==")


if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='Self Test del motor del juego API Card Game',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Ejemplos:
  %(prog)s                           # Por defecto (seed=42, max_turns=20, sin log)
  %(prog)s --seed 123                 # Cambiar semilla
  %(prog)s --max-turns 30             # Cambiar límite de turnos
  %(prog)s --log                      # Guardar log en assets/trace.log
  %(prog)s --seed 100 --max-turns 50 --log  # Combinar opciones
		"""
	)
	parser.add_argument(
		'--seed',
		type=int,
		default=42,
		help='Semilla para random (default: 42)'
	)
	parser.add_argument(
		'--max-turns',
		type=int,
		default=20,
		help='Número máximo de turnos (default: 20)'
	)
	parser.add_argument(
		'--log',
		action='store_true',
		help='Guardar log en assets/trace.log además de imprimir en consola'
	)
	
	args = parser.parse_args()
	run(max_turns=args.max_turns, seed=args.seed, log_to_file=args.log)
