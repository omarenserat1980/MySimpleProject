from brain_v12.taiwan_open_source.catalog import catalog
from brain_v12.taiwan_open_source.license_checker import classify_license_text, is_safe_for_adapter

def test_catalog_has_projects():
    assert len(catalog()) >= 5

def test_mit_is_adapter_allowed():
    assert is_safe_for_adapter("MIT")

def test_unknown_is_rejected():
    assert not is_safe_for_adapter("UNKNOWN")

def test_license_detection():
    assert classify_license_text("MIT License\nPermission is hereby granted") == "MIT"
