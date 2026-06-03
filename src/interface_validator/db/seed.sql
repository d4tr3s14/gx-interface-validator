-- ============================================================================
-- Datos de catálogo de ejemplo (proyectos y usuarios gestionados).
-- La validación SOLO acepta proyectos/usuarios que existan aquí.
-- ============================================================================

INSERT INTO dim_project (project_key, name, owner) VALUES
    ('DEMO',   'Proyecto Demo',                     'Equipo QA'),
    ('RIESGO', 'Iniciativa Mejoras a Interfaces',   'Equipo Riesgo'),
    ('TESORERIA', 'Carga de Saldos Diarios',        'Equipo Tesorería')
ON CONFLICT (project_key) DO NOTHING;

INSERT INTO dim_user (username, display_name) VALUES
    ('dleiva', 'D. Leiva'),
    ('qa_bot', 'QA Automation'),
    ('analista1', 'Analista de Datos')
ON CONFLICT (username) DO NOTHING;
