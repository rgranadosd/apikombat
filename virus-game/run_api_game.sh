#!/bin/bash
# Script para ejecutar API Card Game con pygame_cards

# Obtener el directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== API Card Game ===${NC}"
echo ""

# Verificar si existe entorno virtual
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activando entorno virtual...${NC}"
    source venv/bin/activate
fi

# Verificar si pygame está instalado
if ! python3 -c "import pygame" 2>/dev/null; then
    echo -e "${YELLOW}pygame-ce no encontrado. Instalando...${NC}"
    python3 -m pip install --break-system-packages pygame-ce 2>&1 | grep -E "(Installing|Successfully|already)" || true
fi

# Verificar si sortedcontainers está instalado (para MTG engine)
if ! python3 -c "import sortedcontainers" 2>/dev/null; then
    echo -e "${YELLOW}sortedcontainers no encontrado. Instalando...${NC}"
    python3 -m pip install --break-system-packages sortedcontainers 2>&1 | grep -E "(Installing|Successfully|already)" || true
fi

echo ""
echo -e "${GREEN}Iniciando juego...${NC}"
echo ""

# Limpiar cachés de Python para asegurar que se cargan los últimos cambios
find . -type d -name '__pycache__' -prune -exec rm -rf {} +

# Ejecutar el juego (propaga argumentos pasados al script)
# Por defecto usa motor MTG, para desactivar: USE_MTG_ENGINE=false
python3 virus_game.py "$@"

# Si hay error, mostrar mensaje
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Error al ejecutar el juego.${NC}"
    echo "Verifica que todas las dependencias estén instaladas:"
    echo "  pip install pygame-ce sortedcontainers"
    exit 1
fi

