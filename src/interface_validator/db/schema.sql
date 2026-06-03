-- ============================================================================
-- Esquema de la base de datos de resultados de validación (PostgreSQL).
-- Modelo estrella: dimensiones (project, user, interface) + puente N:M +
-- tres niveles de hechos (run -> section -> expectation).
-- ============================================================================

-- --- Dimensiones (catálogo gestionado para project y user) ------------------
CREATE TABLE IF NOT EXISTS dim_project (
    project_id   SERIAL PRIMARY KEY,
    project_key  TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    owner        TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_user (
    user_id      SERIAL PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE,
    display_name TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- La interfaz se da de alta automáticamente (se conoce por su layout).
CREATE TABLE IF NOT EXISTS dim_interface (
    interface_id SERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    layout       TEXT,
    description  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Puente N:M: qué interfaces se han usado en qué proyectos ---------------
CREATE TABLE IF NOT EXISTS bridge_project_interface (
    project_id   INT NOT NULL REFERENCES dim_project(project_id),
    interface_id INT NOT NULL REFERENCES dim_interface(interface_id),
    first_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, interface_id)
);

-- --- Hecho 1: la ejecución (run) --------------------------------------------
CREATE TABLE IF NOT EXISTS fact_run (
    run_id          BIGSERIAL PRIMARY KEY,
    interface_id    INT NOT NULL REFERENCES dim_interface(interface_id),
    project_id      INT NOT NULL REFERENCES dim_project(project_id),
    user_id         INT NOT NULL REFERENCES dim_user(user_id),
    file_name       TEXT,
    interface_date  TEXT,
    environment     TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_ms     INT,
    success         BOOLEAN NOT NULL,
    total_expectations INT NOT NULL,
    successful      INT NOT NULL,
    failed          INT NOT NULL,
    success_percent REAL NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_fact_run_project   ON fact_run(project_id);
CREATE INDEX IF NOT EXISTS ix_fact_run_interface ON fact_run(interface_id);
CREATE INDEX IF NOT EXISTS ix_fact_run_user      ON fact_run(user_id);

-- --- Hecho 2: resultado por sección (header/body/footer/cross_section) ------
CREATE TABLE IF NOT EXISTS fact_section (
    section_id      BIGSERIAL PRIMARY KEY,
    run_id          BIGINT NOT NULL REFERENCES fact_run(run_id) ON DELETE CASCADE,
    section         TEXT NOT NULL,
    suite_name      TEXT,
    success         BOOLEAN NOT NULL,
    evaluated       INT NOT NULL,
    successful      INT NOT NULL,
    unsuccessful    INT NOT NULL,
    success_percent REAL NOT NULL,
    row_count       INT
);
CREATE INDEX IF NOT EXISTS ix_fact_section_run ON fact_section(run_id);

-- --- Hecho 3: resultado por expectativa (incluye el dato exacto que falló) ---
CREATE TABLE IF NOT EXISTS fact_expectation (
    expectation_id   BIGSERIAL PRIMARY KEY,
    section_id       BIGINT NOT NULL REFERENCES fact_section(section_id) ON DELETE CASCADE,
    expectation_type TEXT NOT NULL,
    category         TEXT,
    column_name      TEXT,
    success          BOOLEAN NOT NULL,
    expected_text    TEXT,
    found_examples   TEXT,
    affected_lines   TEXT,
    unexpected_count INT,
    kwargs           JSONB,
    result           JSONB
);
CREATE INDEX IF NOT EXISTS ix_fact_expectation_section ON fact_expectation(section_id);

-- --- Vista de conveniencia: resumen de ejecuciones por proyecto -------------
CREATE OR REPLACE VIEW vw_run_summary AS
SELECT r.run_id,
       p.project_key,
       p.name        AS project_name,
       i.name        AS interface,
       u.username,
       r.interface_date,
       r.started_at,
       r.duration_ms,
       r.success,
       r.success_percent,
       r.total_expectations,
       r.failed
FROM fact_run r
JOIN dim_project   p ON p.project_id   = r.project_id
JOIN dim_interface i ON i.interface_id = r.interface_id
JOIN dim_user      u ON u.user_id      = r.user_id;
