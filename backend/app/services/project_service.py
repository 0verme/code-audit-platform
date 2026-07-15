from app.db.runtime_store import list_projects


def get_projects() -> list[dict]:
    return [dict(row) for row in list_projects()]
