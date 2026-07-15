from __future__ import annotations

import shutil

from app.db.connection import connect
from app.db.profiles import get_active_profile


def get_health() -> tuple[dict, int]:
    profile = get_active_profile()
    database = {"profile": profile.name, "type": profile.type, "connected": False}
    payload = {"status": "ok", "database": database, "svn": {"cliAvailable": bool(shutil.which("svn"))}}
    try:
        with connect(profile) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        database["connected"] = True
        return payload, 200
    except Exception:
        payload["status"] = "degraded"
        return payload, 503
