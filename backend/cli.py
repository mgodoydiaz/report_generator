"""CLI para tareas administrativas del backend."""

import argparse
import getpass
import re
import sys

from backend.database import SessionLocal
from backend.models import Organization, User
from backend.auth import hash_password


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    return slug


def create_superadmin(_args):
    name = input("Nombre: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Contraseña: ")

    if not name or not email or not password:
        print("Error: todos los campos son obligatorios.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Error: ya existe un usuario con el email '{email}'.")
            sys.exit(1)

        org = db.query(Organization).filter(Organization.slug == "system").first()
        if not org:
            org = Organization(name="System", slug="system")
            db.add(org)
            db.flush()

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            is_superadmin=True,
            role="admin",
            org_id=org.id,
        )
        db.add(user)
        db.commit()
        print(f"Superadmin '{name}' creado exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"Error al crear superadmin: {e}")
        sys.exit(1)
    finally:
        db.close()


def create_org(args):
    name = args.name.strip()
    if not name:
        print("Error: el nombre de la organización es obligatorio.")
        sys.exit(1)

    slug = slugify(name)

    db = SessionLocal()
    try:
        existing = db.query(Organization).filter(Organization.slug == slug).first()
        if existing:
            print(f"Error: ya existe una organización con el slug '{slug}'.")
            sys.exit(1)

        org = Organization(name=name, slug=slug)
        db.add(org)
        db.commit()
        print(f"Organización '{name}' (slug: {slug}) creada exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"Error al crear organización: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="CLI de administración del backend")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("create-superadmin", help="Crear un usuario superadmin")

    org_parser = subparsers.add_parser("create-org", help="Crear una organización")
    org_parser.add_argument("--name", required=True, help="Nombre de la organización")

    args = parser.parse_args()

    if args.command == "create-superadmin":
        create_superadmin(args)
    elif args.command == "create-org":
        create_org(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
