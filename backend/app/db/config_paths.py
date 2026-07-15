"""Canonical filesystem locations for backend runtime configuration."""

from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
CONFIG_DIR = BACKEND_DIR / "configs"
DEFAULT_DATABASE_CONFIG = CONFIG_DIR / "database.yaml"
DEFAULT_SVN_CONFIG = CONFIG_DIR / "svn.yaml"
