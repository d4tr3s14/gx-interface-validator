# 📘 Guía detallada (para todos los niveles)

Esta guía explica **paso a paso** cómo ejecutar, entender y editar el proyecto
**gx-interface-validator**, desde tu computador hasta lo que ocurre en GitHub
cuando se ejecuta el CI. Pensada para que **alguien junior** pueda hacerlo sin
complicaciones.

> Orden sugerido: **1)** ¿Qué es? → **2)** Glosario → **3)** Frameworks →
> **4)** Requisitos → **5)** Clonar → **6)** Ejecución local → **7)** Reportes →
> **8)** Cómo editar → **9)** Qué hace el CI.

---

## 1. ¿Qué es este proyecto?

Es un validador de **interfaces de archivos planos de ancho fijo**
(*fixed-width*). En la banca y sistemas legados, muchos sistemas intercambian
datos con archivos de texto donde **cada campo ocupa una posición fija** (sin
comas). Antes de procesar uno de esos archivos hay que verificar que **cumple su
contrato**: que tenga las columnas correctas, sin nulos, con los formatos y
valores esperados, y que los totales cuadren.

Este proyecto hace esa validación de forma **declarativa** usando **Great
Expectations**, la describe en lenguaje de negocio con **BDD (Gherkin)**, y
genera **dos reportes**: uno técnico (**Allure**) y uno ejecutivo (**HTML/PDF**)
para los responsables de la interfaz.

```
archivo .FC ─► parser (layout) ─► Great Expectations ─► 1 JSON ─► Allure + Informe HTML/PDF
```

---

## 2. Glosario (términos clave)

| Término | Qué significa, en simple |
|---------|--------------------------|
| **Interfaz** | Un archivo de datos que un sistema le envía a otro. |
| **Ancho fijo** (*fixed-width*) | Formato donde cada campo ocupa posiciones de carácter fijas (ej. caracteres 1–3 = código). |
| **Header / Body / Footer** | Cabecera (1 línea), detalle (N líneas) y pie/totales (1 línea) del archivo. |
| **Layout / FD** (*File Definition*) | El "mapa" que dice qué columna va en qué posición. Aquí vive en un `.yml`. |
| **Great Expectations (GE)** | Librería que valida datos con "expectativas" (reglas declarativas). |
| **Expectativa** (*expectation*) | Una regla sobre los datos, ej. "esta columna no debe tener nulos". |
| **Suite** | Un conjunto de expectativas (aquí, una por sección: header/body/footer). |
| **Categorías** | Las reglas se agrupan en: **Completitud, Dominio, Formato, Unicidad, Negocio**. |
| **Regla cross-section** | Validación que cruza secciones, ej. "el total del footer = suma del body". |
| **JSON consolidado** | Un único archivo de resultados por interfaz (header+body+footer juntos). |
| **BDD / Gherkin** | Escribir pruebas en lenguaje natural (`Dado / Cuando / Entonces`). |
| **pytest-bdd** | La librería que conecta el Gherkin con el código Python. |
| **Allure** | Reporte interactivo de pruebas para el QA/ingeniero. |
| **Informe ejecutivo** | Reporte HTML/PDF legible para un Product Owner (estado APROBADO/RECHAZADO). |
| **CI** (*Integración Continua*) | Automatización que valida el proyecto en cada cambio en GitHub. |
| **gh-pages** | Rama especial de GitHub donde se publica el reporte Allure como sitio web. |
| **Artefacto** | Archivo que el CI genera y deja para descargar. |

---

## 3. Frameworks y lenguajes (para qué sirve cada uno)

| Herramienta | Lenguaje | ¿Para qué sirve **en este proyecto**? |
|-------------|----------|----------------------------------------|
| **Python** | — | Lenguaje base de todo el proyecto. |
| **Great Expectations** | Python | El **motor de validación**: ejecuta las expectativas sobre los datos. |
| **pandas** | Python | Carga las secciones del archivo como tablas (DataFrames) en memoria. |
| **PyYAML** | Python | Lee los **layouts** (`.yml`) que describen las posiciones de las columnas. |
| **pytest** | Python | El **ejecutor** de pruebas. |
| **pytest-bdd** | Python | Conecta los escenarios **Gherkin** con las funciones Python (steps). |
| **Jinja2** | Python | Plantilla del **informe HTML** de cara al usuario. |
| **allure-pytest** | Python | Genera los resultados para el dashboard **Allure**. |
| **WeasyPrint / Chromium** | — | Convierte el informe HTML a **PDF** (uno u otro, lo que esté disponible). |
| **GitHub Actions** | YAML | El **CI**: corre las pruebas y publica el reporte automáticamente. |

---

## 4. Requisitos previos

1. **Python 3.10, 3.11 o 3.12** → https://www.python.org/downloads/ (verifica `python --version`).
2. **Git** → https://git-scm.com/
3. *(Opcional, para ver el dashboard)* **Allure CLI** → `npm install -g allure-commandline`.

---

## 5. Clonar el proyecto

```bash
git clone https://github.com/d4tr3s14/gx-interface-validator.git
cd gx-interface-validator
```

---

## 6. Ejecución LOCAL paso a paso

### Paso 1 — Entorno virtual e instalación
Un *entorno virtual* (`.venv`) aísla las librerías del proyecto.
```bash
python -m venv .venv
```
Actívalo:
- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **Windows (Git Bash):** `source .venv/Scripts/activate`
- **Linux / macOS:** `source .venv/bin/activate`

Instala el proyecto (el `-e ".[test]"` instala el código + las dependencias de pruebas):
```bash
pip install -e ".[test]"
```

### Paso 2 — Generar datos de ejemplo (sintéticos)
```bash
python scripts/generate_sample_data.py
```
Esto crea archivos `.FC` ficticios en `data/sample/` (interfaces SAMPLE01 y SAMPLE02).

### Paso 3 — Validar una interfaz (CLI, sin pruebas)
```bash
validate-interface --file data/sample/SAMPLE01_F20250404.FC --report both --system DEMO
```
Verás en consola un resumen (APROBADO/RECHAZADO, expectativas OK) y se generará:
- el **JSON consolidado** en `output/`,
- el **informe HTML y PDF** en `output/` (ábrelos en el navegador).

Prueba también la interfaz "con errores" para ver un RECHAZADO:
```bash
validate-interface --file data/sample/SAMPLE01_F20250402.FC --report both --system DEMO
```

### Paso 4 — Ejecutar las pruebas BDD + Allure
```bash
pytest                          # genera resultados en allure-results/
allure serve allure-results     # abre el dashboard (si tienes Allure CLI)
```

> ¿No tienes Allure CLI? Igual puedes abrir los **informes HTML** de `output/` o
> los de ejemplo en [`examples/`](../examples/).

---

## 7. Los dos reportes (clave del proyecto)

| Público | Reporte | Cómo se genera |
|---------|---------|----------------|
| **QA / ingeniero** | **Allure** | `pytest` → `allure serve allure-results` |
| **Product Owner / usuario** | **Informe HTML/PDF** | `validate-interface --report both` (queda en `output/`) |

Ambos parten del **mismo JSON consolidado**, así que cuentan la misma verdad. El
informe ejecutivo muestra el detalle del error: el valor exacto encontrado y la
línea afectada.

---

## 8. Cómo EDITAR el proyecto (recetas para junior)

### a) Agregar una interfaz nueva (¡sin tocar código Python!)
1. Crea su **layout**: `src/interface_validator/layouts/<nombre>.yml` con las
   posiciones de cada columna por sección (copia `sample01.yml` como base).
2. Crea sus **suites de expectativas**: `expectations/<nombre>_header.json`,
   `<nombre>_body.json`, `<nombre>_footer.json`.
3. Ejecuta: `validate-interface --file <ruta.FC> --layout <nombre> --report both`.

### b) Agregar una expectativa a una interfaz existente
Edita la suite JSON correspondiente (`expectations/sample01_body.json`) y añade
una entrada, por ejemplo:
```json
{ "expectation_type": "expect_column_values_to_not_be_null", "kwargs": { "column": "AMOUNT_LOCAL" } }
```

### c) Agregar una regla de negocio (cross-section)
Se declaran en el `business_rules` del layout `.yml` (ej. "total del footer =
suma del body").

### d) Cambiar textos/metadatos del informe ejecutivo
Pásalos por la CLI: `--system`, `--responsible`, `--project`, `--environment`.

---

## 9. ¿Qué hace el CI en GitHub? (paso a paso)

El CI vive en `.github/workflows/ci.yml` y corre en cada `push`/`pull request`:

1. **Matriz de Python** — instala y prueba en **3.10, 3.11 y 3.12** (para
   asegurar compatibilidad).
2. **Install + generate data** — instala el proyecto y genera los datos sintéticos.
3. **pytest** — corre todas las pruebas BDD; deja resultados en `allure-results/`.
4. **Upload Allure results** — guarda esos resultados como artefacto.
5. **Job `report` (solo en push a main)** — fusiona los resultados, **genera el
   reporte Allure** y lo **publica en GitHub Pages** (rama `gh-pages`); además
   genera y sube los **informes HTML/PDF de muestra** como artefacto descargable.

### ¿Dónde veo el resultado?
- GitHub → pestaña **Actions** → el run (✅ verde / ❌ rojo).
- Reporte Allure en vivo: **https://d4tr3s14.github.io/gx-interface-validator/**
  (requiere tener GitHub Pages activado en *Settings → Pages → rama `gh-pages`*).

---

## 10. Problemas comunes

| Problema | Solución |
|----------|----------|
| `validate-interface: command not found` | Activa el `.venv` y ejecuta `pip install -e ".[test]"`. |
| No se generan datos | Corre `python scripts/generate_sample_data.py`. |
| El PDF no se genera | Es opcional; si no hay WeasyPrint ni navegador, igual tendrás el HTML. |
| `allure: command not found` | Instala el CLI: `npm install -g allure-commandline` (o abre el HTML). |
| El badge de Allure da 404 | Falta activar GitHub Pages (rama `gh-pages`). |

---

## 11. Mapa de archivos

```
src/interface_validator/
  layouts/        layouts (FD) en YAML — el "mapa" de posiciones
  parser/         lee el archivo de ancho fijo → tablas (DataFrames)
  engine/         motor Great Expectations + reglas custom + cross-section
  consolidator/   une las secciones en un único JSON
  reporting/      Allure + informe HTML/PDF + taxonomía
  cli.py          comando `validate-interface`
expectations/     suites de expectativas (JSON) — SAMPLE01 y SAMPLE02
features/         escenarios BDD (Gherkin) + steps (pytest-bdd)
tests/            pruebas unitarias
scripts/          generador de datos sintéticos
examples/         informes HTML/PDF y JSON de muestra
.github/workflows/ci.yml   el pipeline de CI
```

---

¿Dudas? Empieza por la **sección 6** (validar una interfaz por CLI), que es lo
más rápido para ver resultados.
