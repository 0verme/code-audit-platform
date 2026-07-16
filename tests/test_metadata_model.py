import types

from app.modules.metadata.services.metadata_model import get_metadata_model, table_name


def test_profile_metadata_mapping_overrides_valid_identifiers():
    profile = types.SimpleNamespace(config={"metadata": {"schema": "audit", "tables": {"jobs": "jobs_v2"}}})
    assert table_name("jobs", profile) == "audit.jobs_v2"


def test_invalid_metadata_identifier_uses_safe_default_mapping():
    profile = types.SimpleNamespace(config={"metadata": {"schema": "dwp; drop table users"}})
    assert get_metadata_model(profile)["schema"] == "dwp"
