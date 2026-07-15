from __future__ import annotations


def asset_issue_to_dict(issue):
    return {
        "issueType": getattr(issue, "issue_type", ""),
        "issueTitle": getattr(issue, "issue_title", ""),
        "issueDesc": getattr(issue, "issue_desc", ""),
        "assetType": getattr(issue, "asset_type", ""),
        "sourceModule": getattr(issue, "source_module", ""),
        "sourceFile": getattr(issue, "source_file", ""),
        "severity": getattr(issue, "severity", ""),
        "suggestion": getattr(issue, "suggestion", ""),
        "portalModule": getattr(issue, "portal_module", ""),
        "actionLabel": getattr(issue, "action_label", ""),
        "schemaName": getattr(issue, "schema_name", ""),
        "tableName": getattr(issue, "table_name", ""),
        "fieldName": getattr(issue, "field_name", ""),
        "rootWord": getattr(issue, "root_word", ""),
        "objectName": ".".join(
            value
            for value in (
                getattr(issue, "schema_name", ""),
                getattr(issue, "table_name", ""),
                getattr(issue, "field_name", ""),
            )
            if value
        )
        or getattr(issue, "root_word", ""),
        "issueKey": getattr(issue, "issue_key", ""),
        "hashKey": getattr(issue, "issue_hash_key", ""),
        "portalUrl": getattr(issue, "portal_url", ""),
        "sourceRule": getattr(issue, "portal_module", "") or getattr(issue, "issue_type", ""),
    }
