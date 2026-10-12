from economics.source_identity import (
    normalize_source_url,
    same_source,
    source_fingerprint,
)


def test_normalization_removes_fragment_and_trailing_slash():
    assert normalize_source_url(
        "HTTPS://Example.COM/job/123/#details"
    ) == "https://example.com/job/123"


def test_source_fingerprint_is_stable():
    assert source_fingerprint(
        "https://example.com/job/123/"
    ) == source_fingerprint("https://EXAMPLE.com/job/123")


def test_different_sources_do_not_collide():
    assert not same_source(
        "https://example.com/job/123",
        "https://example.com/job/124",
    )


def test_invalid_source_fails_closed():
    try:
        source_fingerprint("not-a-url")
        assert False
    except ValueError:
        assert True
