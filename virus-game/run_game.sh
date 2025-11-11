#!/bin/bash
# Script para ejecutar el juego Virus (versión Tkinter)

set -e

echo "Iniciando Virus (Pygame)"

# Directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Entorno virtual opcional
VENV_DIR="venv"
REQUIREMENTS="requirements.txt"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# Instalar dependencias solo si hay líneas no vacías ni comentadas
if grep -vE '^\s*(#|$)' "$REQUIREMENTS" >/dev/null 2>&1; then
    echo "Instalando dependencias..."
    pip install -r "$REQUIREMENTS" -q || true
fi

echo "Ejecutando juego Pygame..."

# Parseo simple de argumentos: autorun=true o --autorun
AUTORUN_FLAG="false"
for arg in "$@"; do
  case "$arg" in
    autorun=true|--autorun)
      AUTORUN_FLAG="true"
      ;;
  esac
done

if [ "$AUTORUN_FLAG" = "true" ]; then
  AUTORUN=true python3 virus_game.py --autorun
else
  python3 virus_game.py
fi

deactivate
echo "Finalizado"
