from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .errors import ManifestError


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    files: dict[str, Path]

    def checksum(self, dialect: str) -> str:
        return hashlib.sha256(self.files[dialect].read_bytes()).hexdigest()


def load_manifest(root: Path) -> list[Migration]:
    path = root / "manifest.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload["migrations"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Invalid migration manifest: {path}") from exc
    migrations = []
    previous = ""
    for entry in entries:
        version = str(entry.get("version", ""))
        if not version or version <= previous:
            raise ManifestError("Migration versions must be unique and strictly increasing")
        files = {dialect: root / relative for dialect, relative in entry.get("files", {}).items()}
        if set(files) != {"sqlite", "postgresql", "dws"} or not all(file.is_file() for file in files.values()):
            raise ManifestError(f"Migration {version} must provide sqlite, postgresql, and dws files")
        migrations.append(Migration(version, str(entry.get("name") or version), files))
        previous = version
    return migrations
