# GX Interface Validator

[![CI](https://github.com/d4tr3s14/gx-interface-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/d4tr3s14/gx-interface-validator/actions/workflows/ci.yml)
[![Allure Report](https://img.shields.io/badge/Allure-report-fa4d56?logo=allure)](https://d4tr3s14.github.io/gx-interface-validator/)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-3776ab?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Validación declarativa de **interfaces de archivos planos de ancho fijo**
(_fixed-width flat files_) usando **Great Expectations 1.x**, una capa **BDD con
Gherkin (pytest-bdd)** y reportería en **Allure**.

> Proyecto de portafolio. Reconstrucción **100% anonimizada** y con datos
> sintéticos de un validador de interfaces que diseñé para un cliente del sector
> financiero. No contiene datos, nombres, credenciales ni estructuras reales del
> cliente.

---

## 🎯 Qué resuelve

Los sistemas core suelen intercambiar información mediante **archivos de ancho
fijo** con tres tipos de registro: una cabecera (_header_), un detalle (_body_)
y un pie/totales (_trailer/footer_). Antes de procesar uno de estos archivos hay
que verificar que **cumple su contrato**: columnas, dominios de valores,
formatos, unicidad, completitud y reglas de negocio (p. ej. que los totales del
footer cuadren con el detalle).

Este proyecto permite que un **QA automatizador** defina esas reglas de forma
declarativa y las ejecute **sin ninguna interfaz gráfica**, integrándose en
pipelines de CI y produciendo reportes para dos públicos distintos.

## 👥 Dos públicos, dos reportes

| Público | Reporte | Para qué |
|---------|---------|----------|
| **QA automatizador** | **Allure** (`pytest`) | Depurar, ver cada expectativa verde/rojo con el valor y la línea exactos del error, trazabilidad en CI |
| **Product Owner / responsable de la interfaz** | **Informe HTML/PDF** (de cara al usuario) | Evidencia legible: estado de certificación (APROBADO/RECHAZADO), validaciones por categoría, clasificación de errores y detalle |

Ambos parten del **mismo motor y del mismo JSON consolidado**, así que siempre
cuentan la misma verdad. De hecho, el reporte Allure **embebe el informe
ejecutivo HTML** como adjunto, y cada expectativa fallida incluye un detalle
"¿Dónde está el error?" con el valor encontrado y la línea afectada.

## 🧩 Enfoque: dos capas que se complementan

Great Expectations y Gherkin son, ambos, lenguajes declarativos. Para no
duplicarlos, el proyecto usa una arquitectura de **dos capas**:

| Capa | Herramienta | Quién la escribe | Qué expresa |
|------|-------------|------------------|-------------|
| **Negocio / contrato** | Gherkin (`features/*.feature`) | QA / analista | Escenarios legibles: "la sección X cumple su contrato", "los totales del footer cuadran con el body" |
| **Reglas de datos** | Suites GE (`expectations/*.json`) | QA automatizador | El detalle por columna: dominios, formatos, nulos, unicidad… |

Así el Gherkin queda **limpio y legible** (no un `Then` por cada columna) y el
grueso de las reglas vive como datos versionables.

## 🏗️ Arquitectura

```
            archivo .FC (ancho fijo)
                     │
       ┌─────────────▼─────────────┐
       │  parser/  (layout YAML)   │  → DataFrames: header / body / footer
       └─────────────┬─────────────┘
                     │
       ┌─────────────▼─────────────┐   built-in de GE
       │  engine/  Great Exp. 1.x  │ + reglas semánticas → GE (regex)
       │                           │ + expectations personalizadas
       └─────────────┬─────────────┘ + reglas cross-section (negocio)
                     │
       ┌─────────────▼─────────────┐
       │  consolidator/            │  → UN SOLO JSON por interfaz
       └─────────────┬─────────────┘
                     │
       ┌─────────────▼─────────────┐
       │  features/ (pytest-bdd)   │  → reporte Allure (verde / rojo)
       │  reporting/ (Allure)      │
       └───────────────────────────┘
```

### Decisiones de diseño destacadas

- **Un único JSON por interfaz.** El sistema original generaba 3 archivos
  (header/body/footer); aquí se consolidan en uno solo con un `summary` global
  y el detalle por sección (ver `consolidator/merge.py`).
- **Reglas semánticas traducidas a GE.** Un QA puede escribir
  `expect_column_values_to_be_numeric` y el motor lo traduce a una expectation
  nativa de GE basada en regex (`engine/translators.py`). Vocabulario de negocio,
  ejecución real sobre GE.
- **Expectations personalizadas enchufables.** Lo que GE no trae de fábrica
  (p. ej. "sin filas duplicadas") se registra en `engine/custom_rules.py`.
- **Reglas cross-section.** Validaciones que cruzan secciones (footer vs. body)
  en `engine/cross_section.py`, expuestas como escenario de negocio en Gherkin.
- **Sin UI, sin base de datos.** Pensado para CLI y CI.

## 🚀 Uso

### Requisitos
- Python 3.10 – 3.12
- [Allure CLI](https://allurereport.org/docs/install/) (opcional, para ver el reporte HTML)

### Instalación

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows
# source .venv/bin/activate          # Linux/macOS
pip install -e ".[test]"
```

### Generar datos de ejemplo (sintéticos)

```bash
python scripts/generate_sample_data.py
```

### Validar una interfaz por CLI

```bash
# Solo validación + JSON consolidado
validate-interface --file data/sample/SAMPLE01_F20250404.FC

# Validación + informe de usuario (HTML)
validate-interface --file data/sample/SAMPLE01_F20250402.FC \
    --report html --system RIESGO \
    --responsible "Equipo QA Datos" --project "Iniciativa Mejoras a Interfaces"

# Segunda interfaz de ejemplo (otra estructura y reglas)
validate-interface --file data/sample/SAMPLE02_F20250404.FC --layout sample02 --report html
```

El informe HTML es autocontenido (se abre en cualquier navegador). Para PDF use
`--report pdf` (o `both`): se genera el **mismo documento** mediante un backend
automático — **WeasyPrint** si está disponible (ideal en Linux/CI) o, si no,
**Chromium headless** (Edge/Chrome ya instalado). El PDF trae exactamente la
misma información que el HTML.

```bash
validate-interface --file data/sample/SAMPLE01_F20250402.FC --report both --system RIESGO
# -> output/Informe_SAMPLE01_20250402.html  y  .pdf
```

El **detalle de expectativas fallidas** muestra *dónde* está el error: el valor
exacto encontrado, la(s) línea(s) afectada(s) y, para reglas de negocio, el valor
declarado vs. el calculado.

Salida:

```
Interfaz : SAMPLE01  (SAMPLE01_F20250404.FC)
Fecha    : 20250404
Resultado: OK  -  44/44 expectativas (100.0%)
  [OK ] header         11/11
  [OK ] body           19/19
  [OK ] footer         11/11
  [OK ] cross_section  3/3
JSON     : output/resultado.SAMPLE01.20250404.json
```

Código de salida: `0` (todo OK), `1` (alguna expectativa falló), `2` (error).

### Ejecutar las pruebas BDD y ver el reporte Allure

```bash
pytest                                  # genera resultados en allure-results/
allure serve allure-results             # abre el reporte en el navegador
```

## ➕ Cómo añadir una interfaz nueva (flujo del QA automatizador)

1. **Layout (FD):** crea `src/interface_validator/layouts/<nombre>.yml` con las
   posiciones fijas de cada columna por sección.
2. **Suites de expectativas:** crea `expectations/<nombre>_header.json`,
   `<nombre>_body.json` y `<nombre>_footer.json`.
3. **(Opcional) Escenarios Gherkin:** añade un `.feature` describiendo el
   contrato a nivel de negocio.
4. **Ejecuta:** `validate-interface --file <ruta> --layout <nombre>`.

No se toca código Python salvo que necesites una expectation personalizada nueva.

## 📁 Estructura

```
src/interface_validator/
  layouts/        layouts (FD) en YAML
  parser/         lector de ancho fijo → DataFrames
  engine/         motor GE 1.x + traductores + reglas custom + cross-section
  consolidator/   une las secciones en un único JSON
  reporting/      Allure + informe HTML/PDF de usuario + taxonomía
  cli.py          CLI sin UI
expectations/     suites de expectativas (JSON declarativo) — SAMPLE01 y SAMPLE02
features/         Gherkin (.feature) + step definitions (pytest-bdd)
tests/            tests unitarios
scripts/          generador de datos sintéticos
data/sample/      interfaces .FC sintéticas (versionadas como ejemplo)
examples/         informes HTML/PDF y JSON consolidado de muestra
```

> 💡 En [`examples/`](examples/) hay informes HTML/PDF y JSON ya generados (datos
> ficticios) para revisar el resultado sin ejecutar nada.

### Interfaces de ejemplo incluidas

| Interfaz | Descripción | Marcadores | Demuestra |
|----------|-------------|------------|-----------|
| `SAMPLE01` | Movimientos contables | `HDR` / `TLR` | reglas de débito/crédito vs. body |
| `SAMPLE02` | Saldos diarios de clientes | `HDR` / `EOF` | otra estructura y reglas, **sin tocar código** |

## 📝 Licencia

MIT — ver [LICENSE](LICENSE).
