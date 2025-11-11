# Guía de preparación del ZIP para API Scoring

Este documento describe cómo debe estructurarse el paquete `.zip` que se sube al validador web de **API Scoring**. Sigue estas reglas para evitar errores `422 Unprocessable Entity` y garantizar que todas las verificaciones (Diseño, Seguridad y Documentación) puedan ejecutarse.

---

## 1. Principios generales

- El archivo debe estar comprimido en formato **ZIP** estándar (sin contraseña).
- El contenido del ZIP se descomprime en un directorio temporal; por tanto, todas las rutas deben ser relativas a la carpeta raíz del ZIP.
- Los contratos soportados actualmente son OpenAPI/REST (`.yaml`, `.yml`, `.json`) y los materiales adicionales (README u otros Markdown) deben codificarse en UTF‑8.
- Evita incluir ficheros binarios innecesarios. Solo se necesitan contratos, documentación y archivos de configuración relevantes.

---

## 2. Modalidad principal: `metadata.yml`

La forma más completa consiste en añadir un fichero `metadata.yml` en la raíz del ZIP con el listado de APIs a evaluar.

### 2.1. Ubicación

```
my-bundle.zip
├── metadata.yml          # requerido en esta modalidad
└── myApis/
    └── ...
```

### 2.2. Formato del `metadata.yml`

```yaml
apis:
  - name: "REST Sample"
    api-spec-type: rest           # valores admitidos: rest | event | grpc | graphql
    definition-path: myApis/rest  # carpeta relativa dentro del ZIP
    definition-file: contract/openapi-rest.yml
```

- `name`: Identificador legible para la API (aparece en los reportes).
- `api-spec-type`: Tipo de contrato. Determina qué linters se ejecutan.
- `definition-path`: Directorio relativo que contiene la definición.
- `definition-file`: Ruta del archivo dentro de `definition-path`.

Puedes declarar varias APIs dentro del mismo ZIP: cada entrada del array `apis` se procesa y puntúa de manera independiente.

---

## 3. Modalidad alternativa: exportaciones WSO2

Cuando el ZIP procede de una exportación directa de **WSO2 API Manager**, el motor detecta automáticamente la estructura. En este caso no es obligatorio incluir `metadata.yml`.

### 3.1. Estructura mínima esperada

```
PizzaShackAPI-1.0.0.zip
├── api.yaml                       # o api.yml / api.json
└── Definitions/
    └── swagger.yaml               # también se aceptan swagger.yml|json u openapi.yaml|yml|json
```

También se admiten exportaciones donde el archivo `api.yaml` reside dentro de `Meta-information/api.yaml`. El parser buscará en los siguientes caminos:

- `api.yaml`, `api.yml`, `api.json`
- `Meta-information/api.yaml`, `Meta-information/api.yml`, `Meta-information/api.json`

Para la definición (`definition-file`) se evalúan estos nombres dentro de `Definitions/`:

- `swagger.yaml`, `swagger.yml`, `swagger.json`
- `openapi.yaml`, `openapi.yml`, `openapi.json`

### 3.2. Recomendaciones

- Mantén el nombre de la carpeta principal con el identificador de la API; ese nombre se usa como fallback para rellenar campos cuando falta metadata.
- No elimines ni renombres `Meta-information` o `Definitions`; el detector se basa en esas carpetas.

---

## 4. Documentación opcional (módulo Documentation)

Si deseas puntuar el módulo de Documentación, añade un `README.md` (u otros archivos `.md`) en el ZIP. Markdownlint comprobará que exista una sección `# About`. Ejemplo:

```
README.md
└── Contenido…
    └── # About
```

> Si no se incluye documentación en Markdown, el módulo seguirá apareciendo, pero con puntuación reducida o sin datos.

---

## 5. Buenas prácticas

- **Nombres coherentes**: Usa nombres de carpetas y archivos consistentes con el contenido (`contract/openapi.yaml`, `schemas/…`).
- **Codificación UTF‑8**: Evita caracteres especiales sin declarar; algunos linters son sensibles a codificaciones distintas.
- **Validación previa**: Si es posible, valida los contratos con Spectral o herramientas similares antes de comprimir.
- **Tamaño razonable**: El ZIP debe ser ligero. El backend rechaza archivos excesivamente grandes para proteger la plataforma.

---

## 6. Ejemplo completo

```
bundle.zip
├── metadata.yml
├── README.md
├── myApis/
│   └── rest/
│       └── contract/
│           └── openapi-rest.yml
└── myApis/
    └── asyncapi/
        └── asyncapi.yml
```

En este caso, `metadata.yml` referencia las dos APIs (`rest` y `event`). El `README.md` proporciona la documentación para que el módulo de Documentación pueda ejecutarse.

---

### Resumen

1. **Con `metadata.yml`**: especifica todas las APIs a validar y sus rutas.
2. **Con exportaciones WSO2**: asegúrate de mantener `api.yaml` y `Definitions/swagger.yaml` (o equivalentes) en las ubicaciones estándar.
3. **Documentación Markdown**: añade un `README.md` con sección `About` si deseas una evaluación completa.

Cumpliendo estas pautas, el analizador web aceptará el ZIP y generará los informes con el radar de puntuaciones y los listados de issues.

