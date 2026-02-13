"""
Unified import service factory.

Returns the appropriate database service (SQLite or Supabase)
based on the target parameter. Used by all import scripts.

Usage:
    from dashboard.backend.services.import_service import get_import_db
    db = get_import_db('supabase')  # or 'sqlite'
"""

import os
from pathlib import Path


def get_import_db(target: str = None):
    """Return the appropriate database service for imports.

    Args:
        target: 'sqlite' or 'supabase'. If None, reads from
                IMPORT_TARGET env var (default: 'supabase').

    Returns:
        DatabaseService or SupabaseDatabaseService instance.
    """
    if target is None:
        target = os.environ.get('IMPORT_TARGET', 'supabase')

    if target == 'supabase':
        from dashboard.backend.services.supabase_db import SupabaseDatabaseService
        return SupabaseDatabaseService()
    else:
        from dashboard.backend.services.database import DatabaseService
        db_path = Path(__file__).parent.parent.parent / "data" / "questions.db"
        return DatabaseService(db_path)
