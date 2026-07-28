from __future__ import annotations

from .path_export import safe_remove_prefix
from .report_helpers import build_source_file


def resolve_source_file(context, path, *, section: str, kind: str):
    """Build one source descriptor through the runtime override or shared fallback."""

    if not path:
        return None
    if callable(context.reports.build_source_file):
        return context.reports.build_source_file(path, section=section, kind=kind)
    return build_source_file(
        path,
        section=section,
        kind=kind,
        download_url=context.services.download_url,
        relative_path=safe_remove_prefix,
    )
