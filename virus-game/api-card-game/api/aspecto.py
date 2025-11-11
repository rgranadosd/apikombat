"""
Sistema de Aspectos como Permanentes en el Battlefield
Los aspectos son permanentes que representan los 4 aspectos de API
"""
import sys
import os

# Añadir el directorio del motor MTG al path
mtg_engine_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'mtg-engine')
if mtg_engine_path not in sys.path:
    sys.path.insert(0, mtg_engine_path)

from MTG import permanent
from MTG import gameobject
from MTG import cardtype


class AspectoPermanent(permanent.Permanent):
    """Permanente que representa un aspecto de API."""
    
    def __init__(self, aspecto_type: str, characteristics=None, controller=None, owner=None, zone=None):
        """
        aspecto_type: 'seguridad', 'documentacion', 'gobierno', 'performance'
        """
        # Crear características básicas
        if characteristics is None:
            characteristics = gameobject.Characteristics(
                name=f"Aspecto {aspecto_type}",
                types=[cardtype.CardType.ENCHANTMENT],
                supertype=[],
                color=[],
                mana_cost='',
                text=f'Aspecto de API: {aspecto_type}'
            )
        
        super().__init__(characteristics, controller, owner, zone)
        
        self.aspecto_type = aspecto_type
        self.vulnerable = False  # Estado vulnerable (equivale a "infectado")
        self.protecciones = 0    # Contador de protecciones (0-2)
        self.is_aspecto = True
    
    def is_saludable(self):
        """Retorna True si el aspecto está saludable (no vulnerable)."""
        return not self.vulnerable
    
    def add_proteccion(self):
        """Añade una protección (máximo 2)."""
        self.protecciones = min(2, self.protecciones + 1)
    
    def remove_proteccion(self):
        """Elimina una protección."""
        self.protecciones = max(0, self.protecciones - 1)
    
    def vulnerar(self):
        """Vulnera el aspecto (lo marca como vulnerable)."""
        self.vulnerable = True
    
    def curar(self):
        """Cura el aspecto (quita el estado vulnerable)."""
        self.vulnerable = False
    
    def esta_protegido(self):
        """Retorna True si tiene al menos una protección."""
        return self.protecciones >= 1
    
    def esta_fortalecido(self):
        """Retorna True si tiene 2 protecciones (fortalecido/inmunizado)."""
        return self.protecciones >= 2

