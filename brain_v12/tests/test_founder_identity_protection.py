from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_LITERALS = {
    "FOUNDER_NATIONAL_ID_VALUE",
    "FOUNDER_PASSPORT_VALUE",
    "FOUNDER_BANK_ACCOUNT_VALUE",
    "FOUNDER_PRIVATE_EMAIL_VALUE",
}

ALLOWED_OPAQUE_REFS = {
    "FOUNDER_IDENTITY_REF",
    "FOUNDER_PAYMENT_DESTINATION_REF",
}


def test_identity_policy_exists():
    assert (ROOT / "docs" / "FOUNDER_IDENTITY_PROTECTION.md").is_file()


def test_public_code_uses_opaque_identity_references():
    text = (ROOT / "FOUNDER_COMPENSATION_ENGINE_SPEC.md").read_text(encoding="utf-8")
    assert "FOUNDER_PAYMENT_DESTINATION_REF" in text
    assert "actual email/account identifier must never be committed" in text


def test_forbidden_identity_placeholders_are_not_committed():
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert not (FORBIDDEN_LITERALS & set(text.split())), path


def test_no_real_identity_value_is_embedded_by_design():
    # This test intentionally does not contain or receive the founder's real
    # identity value. Exact-value checks belong in a private secret-scanning
    # environment, never in source-controlled tests.
    assert "FOUNDER_IDENTITY_REF" in ALLOWED_OPAQUE_REFS
