# ZIP Preparation Guide for API Scoring

This document explains how to structure the `.zip` package that you upload to the **API Scoring** web validator. Follow these rules to avoid `422 Unprocessable Entity` errors and to ensure that all checks (Design, Security, and Documentation) can run.

---

## 1. General principles

- Compress the bundle using the standard **ZIP** format (no password).
- The ZIP is unpacked into a temporary directory; therefore, every path must be relative to the ZIP root folder.
- Supported contracts are OpenAPI/REST (`.yaml`, `.yml`, `.json`). Additional materials (README or other Markdown files) must be encoded in UTF-8.
- Skip unnecessary binary files. Only include contracts, documentation, and relevant configuration files.

---

## 2. Primary workflow: `metadata.yml`

The most complete option is to add a `metadata.yml` file at the root of the ZIP with the list of APIs to evaluate.

### 2.1. Location

```
my-bundle.zip
├── metadata.yml          # required in this workflow
└── myApis/
    └── ...
```

### 2.2. `metadata.yml` format

```yaml
apis:
  - name: "REST Sample"
    api-spec-type: rest           # allowed values: rest | event | grpc | graphql
    definition-path: myApis/rest  # relative folder inside the ZIP
    definition-file: contract/openapi-rest.yml
```

- `name`: Human-readable identifier for the API (shown in reports).
- `api-spec-type`: Contract type. It determines which linters run.
- `definition-path`: Relative directory containing the definition.
- `definition-file`: Path to the file within `definition-path`.

You can declare multiple APIs in the same ZIP. Each entry in the `apis` array is processed and scored independently.

---

## 3. Alternative workflow: WSO2 exports

When the ZIP comes from a direct **WSO2 API Manager** export, the engine detects the structure automatically. In this case, including `metadata.yml` is optional.

### 3.1. Minimum expected structure

```
PizzaShackAPI-1.0.0.zip
├── api.yaml                       # or api.yml / api.json
└── Definitions/
    └── swagger.yaml               # swagger.yml|json or openapi.yaml|yml|json are also accepted
```

Exports where the `api.yaml` file lives inside `Meta-information/api.yaml` are also accepted. The parser looks in the following paths:

- `api.yaml`, `api.yml`, `api.json`
- `Meta-information/api.yaml`, `Meta-information/api.yml`, `Meta-information/api.json`

For the definition (`definition-file`), these names are evaluated inside `Definitions/`:

- `swagger.yaml`, `swagger.yml`, `swagger.json`
- `openapi.yaml`, `openapi.yml`, `openapi.json`

### 3.2. Recommendations

- Keep the top-level folder name aligned with the API identifier; that value is used as a fallback when metadata is missing.
- Do not delete or rename `Meta-information` or `Definitions`; the detector relies on those folders.

---

## 4. Optional documentation (Documentation module)

If you want to score the Documentation module, add a `README.md` (or other `.md` files) to the ZIP. Markdownlint checks for a `# About` section. Example:

```
README.md
└── Content…
    └── # About
```

> If no Markdown documentation is included, the module still appears but its score will be reduced or missing.

---

## 5. Best practices

- **Consistent names**: Use folder and file names that match their content (`contract/openapi.yaml`, `schemas/...`).
- **UTF-8 encoding**: Avoid undeclared special characters; some linters are sensitive to other encodings.
- **Pre-validation**: If possible, validate the contracts with Spectral or similar tools before compressing.
- **Reasonable size**: Keep the ZIP lean. The backend rejects oversized files to protect the platform.

---

## 6. Full example

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

In this scenario, `metadata.yml` references both APIs (`rest` and `event`). The `README.md` provides the documentation required for the Documentation module to run.

---

### Summary

1. **With `metadata.yml`**: specify every API to validate and its paths.
2. **With WSO2 exports**: keep `api.yaml` and `Definitions/swagger.yaml` (or equivalents) in their standard locations.
3. **Markdown documentation**: add a `README.md` with an `About` section if you need a complete evaluation.

By following these guidelines, the web analyzer will accept the ZIP and produce the radar charts and issue listings in the reports.

