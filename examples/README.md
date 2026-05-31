# Ejemplos de salida

Muestras generadas por el validador (datos 100% ficticios) para ver el resultado
sin tener que ejecutar nada. Se regeneran con:

```bash
validate-interface --file data/sample/SAMPLE01_F20250402.FC --report both --system RIESGO
```

| Archivo | Caso | Estado |
|---------|------|--------|
| `Informe_SAMPLE01_20250402.*` | Movimientos contables con errores inyectados | **RECHAZADO** |
| `Informe_SAMPLE01_20250404.*` | Movimientos contables correctos | **APROBADO** |
| `Informe_SAMPLE02_20250404.*` | Saldos diarios de clientes (2ª interfaz) | **APROBADO** |

- `Informe_*.html` / `Informe_*.pdf` → informe de cara al usuario (Product Owner).
  El de SAMPLE01 rechazado muestra el detalle del error: valor encontrado y línea.
- `resultado.*.json` → el **único JSON consolidado por interfaz** (header + body +
  footer + reglas de negocio), que alimenta tanto el informe como Allure.

> El reporte Allure no se versiona (se genera con `pytest`).
