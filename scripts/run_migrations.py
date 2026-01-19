#!/usr/bin/env python3
"""
Database migration runner for V3.
Applies SQL migrations in order to the questions.db database.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


def get_applied_migrations(conn: sqlite3.Connection) -> set:
    """Get set of already applied migration filenames."""
    cursor = conn.cursor()

    # Create migrations tracking table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    cursor.execute("SELECT filename FROM _migrations")
    return {row[0] for row in cursor.fetchall()}


def apply_migration(conn: sqlite3.Connection, migration_path: Path) -> bool:
    """Apply a single migration file."""
    filename = migration_path.name
    print(f"  Applying {filename}...", end=" ")

    try:
        with open(migration_path, "r") as f:
            sql = f.read()

        cursor = conn.cursor()
        cursor.executescript(sql)

        # Record the migration
        cursor.execute(
            "INSERT INTO _migrations (filename) VALUES (?)",
            (filename,)
        )
        conn.commit()

        print("OK")
        return True

    except Exception as e:
        print(f"FAILED: {e}")
        conn.rollback()
        return False


def run_migrations(db_path: str, migrations_dir: str) -> None:
    """Run all pending migrations."""
    db_path = Path(db_path)
    migrations_dir = Path(migrations_dir)

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    if not migrations_dir.exists():
        print(f"Error: Migrations directory not found at {migrations_dir}")
        return

    # Get all .sql files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found.")
        return

    print(f"Found {len(migration_files)} migration file(s)")
    print(f"Database: {db_path}")
    print()

    conn = sqlite3.connect(db_path)
    applied = get_applied_migrations(conn)

    pending = [f for f in migration_files if f.name not in applied]

    if not pending:
        print("All migrations already applied.")
        conn.close()
        return

    print(f"Pending migrations: {len(pending)}")
    print()

    success_count = 0
    for migration_path in pending:
        if apply_migration(conn, migration_path):
            success_count += 1
        else:
            print(f"\nStopping due to failed migration.")
            break

    conn.close()

    print()
    print(f"Applied {success_count}/{len(pending)} migrations.")


if __name__ == "__main__":
    # Default paths relative to project root
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "databases" / "questions.db"
    migrations_dir = project_root / "scripts" / "migrations"

    print("=" * 50)
    print("V3 Database Migration Runner")
    print("=" * 50)
    print()

    run_migrations(str(db_path), str(migrations_dir))
