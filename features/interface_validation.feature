# language: es
@interfaces @sample01
Característica: Validación de interfaces de ancho fijo con Great Expectations
  Como QA automatizador
  Quiero validar las secciones de una interfaz contra sus suites de expectativas
  Para garantizar que el archivo cumple su contrato antes de procesarlo

  @smoke @valida
  Esquema del escenario: La sección <seccion> de una interfaz válida cumple su contrato
    Dado el archivo de interfaz "SAMPLE01_F20250404.FC"
    Cuando valido la interfaz
    Entonces la sección "<seccion>" cumple todas sus expectativas

    Ejemplos:
      | seccion |
      | header  |
      | body    |
      | footer  |

  @valida @negocio
  Escenario: Los totales del footer de una interfaz válida cuadran con el detalle del body
    Dado el archivo de interfaz "SAMPLE01_F20250404.FC"
    Cuando valido la interfaz
    Entonces las reglas de negocio cross-section se cumplen

  @falla @regresion
  Escenario: Una interfaz con errores es rechazada y reporta sus fallas
    Dado el archivo de interfaz "SAMPLE01_F20250402.FC"
    Cuando valido la interfaz
    Entonces la interfaz se marca como fallida
    Y se reportan expectativas fallidas en las secciones "header, body, cross_section"

  @valida @sample02
  Esquema del escenario: La sección <seccion> de una segunda interfaz (saldos) cumple su contrato
    Dado el archivo de interfaz "SAMPLE02_F20250404.FC"
    Cuando valido la interfaz
    Entonces la sección "<seccion>" cumple todas sus expectativas

    Ejemplos:
      | seccion |
      | header  |
      | body    |
      | footer  |
