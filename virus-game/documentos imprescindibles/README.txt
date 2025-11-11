================================================================================
                    DOCUMENTOS IMPRESCINDIBLES - API KOMBAT
================================================================================

Esta carpeta contiene todos los documentos esenciales para entender y
reproducir el juego en otros proyectos.

ARCHIVOS INCLUIDOS:
================================================================================

1. REGLAS_DEL_JUEGO.txt
   - Reglas completas del juego
   - Objetivo, componentes, tipos de cartas, efectos, flujo del juego
   - Condiciones de victoria y restricciones
   - Formato: Texto plano

2. cartas_completas.csv
   - Resumen de todas las cartas del juego
   - Columnas: tipo, color, nombre, cantidad, descripcion
   - Formato: CSV (valores separados por comas)

3. cartas_detalladas.csv
   - Lista detallada de todas las cartas (una fila por carta individual)
   - Columnas: tipo, color, nombre, cantidad, archivo_sugerido, icono, label
   - Total: 89 cartas (filas)
   - Formato: CSV (valores separados por comas)

4. CARTAS_ESPECIFICAS.md
   - Documentación sobre cartas específicas del juego
   - Formato: Markdown

5. DESGLOSE_CARTAS_API.md
   - Desglose detallado de las cartas con temática de API
   - Formato: Markdown

6. LISTA_COMPLETA_CARTAS_API.md
   - Lista completa de todas las cartas con temática de API
   - Formato: Markdown

7. MAPEO_TEMATICA_API_FINAL.md
   - Mapeo final de la temática de API aplicada a las cartas
   - Formato: Markdown

USO PARA OTROS PROYECTOS:
================================================================================

Para recrear el juego en otro proyecto:

1. Lee REGLAS_DEL_JUEGO.txt para entender todas las reglas
2. Usa cartas_completas.csv o cartas_detalladas.csv para generar el mazo
3. Consulta los documentos .md para detalles específicos de implementación
4. El código fuente del engine está en engine.py (fuera de esta carpeta)

================================================================================

