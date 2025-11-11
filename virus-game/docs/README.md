# Documentos imprescindibles – API Kombat

Esta carpeta recopila todos los archivos esenciales para entender el juego y reutilizarlo en otros proyectos.

## Archivos incluidos

1. **`REGLAS_DEL_JUEGO.txt`**  
   - Reglas completas del juego: objetivo, componentes, tipos de cartas, flujo y condiciones de victoria.  
   - Formato: texto plano.

2. **`cartas_completas.csv`**  
   - Resumen de todas las cartas.  
   - Columnas: `tipo`, `color`, `nombre`, `cantidad`, `descripcion`.

3. **`cartas_detalladas.csv`**  
   - Lista detallada (una fila por carta).  
   - Columnas: `tipo`, `color`, `nombre`, `cantidad`, `archivo_sugerido`, `icono`, `label`.  
   - Total: 89 filas.

4. **`CARTAS_ESPECIFICAS.md`**  
   - Documentación sobre cartas concretas.

5. **`DESGLOSE_CARTAS_API.md`**  
   - Desglose detallado de las cartas con temática API.

6. **`LISTA_COMPLETA_CARTAS_API.md`**  
   - Listado completo de cartas de temática API.

7. **`MAPEO_TEMATICA_API_FINAL.md`**  
   - Mapeo final de la temática API aplicada a cada carta.

## Cómo usar estos archivos en otros proyectos

1. Revisa `REGLAS_DEL_JUEGO.txt` para comprender las mecánicas.  
2. Utiliza `cartas_completas.csv` o `cartas_detalladas.csv` para generar o trasladar el mazo.  
3. Consulta los documentos `.md` para detalles adicionales de diseño e implementación.  
4. El motor del juego se encuentra en `engine.py` (fuera de esta carpeta).

---

> Mantén estos archivos sincronizados con cualquier cambio en la mecánica o en el mazo para asegurar que la documentación siga siendo fiel al juego actual.

