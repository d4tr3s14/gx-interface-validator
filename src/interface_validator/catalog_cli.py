"""
CLI de administración del catálogo (proyectos y usuarios gestionados).

Como la validación/comparación solo aceptan proyectos y usuarios que existan en
el catálogo, este comando permite darlos de alta sin escribir SQL:

    iv-catalog add-project --key RIESGO --name "Mejoras a Interfaces" --owner "Equipo Riesgo"
    iv-catalog add-user --username dleiva --display-name "D. Leiva"
    iv-catalog list-projects
    iv-catalog list-users
"""
from __future__ import annotations

import argparse
import sys

from .db import repository as repo
from .db.connection import get_connection


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iv-catalog",
        description="Administra el catálogo de proyectos y usuarios (PostgreSQL).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_proj = sub.add_parser("add-project", help="Da de alta (o actualiza) un proyecto.")
    p_proj.add_argument("--key", required=True, help="Clave única del proyecto (project_key).")
    p_proj.add_argument("--name", required=True, help="Nombre del proyecto.")
    p_proj.add_argument("--owner", default=None, help="Responsable / dueño (opcional).")

    p_user = sub.add_parser("add-user", help="Da de alta (o actualiza) un usuario.")
    p_user.add_argument("--username", required=True, help="Nombre de usuario único.")
    p_user.add_argument("--display-name", default=None, help="Nombre visible (opcional).")

    sub.add_parser("list-projects", help="Lista los proyectos del catálogo.")
    sub.add_parser("list-users", help="Lista los usuarios del catálogo.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        conn = get_connection()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] No se pudo conectar a la base de datos: {exc}", file=sys.stderr)
        return 2

    try:
        if args.command == "add-project":
            project_id = repo.add_project(conn, args.key, args.name, args.owner)
            conn.commit()
            print(f"Proyecto guardado: '{args.key}' — {args.name} (project_id={project_id})")

        elif args.command == "add-user":
            user_id = repo.add_user(conn, args.username, args.display_name)
            conn.commit()
            print(f"Usuario guardado: '{args.username}' (user_id={user_id})")

        elif args.command == "list-projects":
            rows = repo.list_projects(conn)
            print(f"Proyectos ({len(rows)}):")
            for key, name, owner in rows:
                print(f"  {key:<14} {name}{f'  [{owner}]' if owner else ''}")

        elif args.command == "list-users":
            rows = repo.list_users(conn)
            print(f"Usuarios ({len(rows)}):")
            for username, display in rows:
                print(f"  {username:<16} {display or ''}")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
