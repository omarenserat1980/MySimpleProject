from platform_foundation.provider_policy import (
    BrainProviderPolicy,
    ProviderDecision,
    ProviderDescriptor,
    ProviderRole,
)


def test_brain_local_is_primary_authority():
    policy = BrainProviderPolicy()
    result = policy.select([
        ProviderDescriptor("render", ProviderRole.OPTIONAL_AUXILIARY, paid=False, available=True),
        ProviderDescriptor("brain-local", ProviderRole.PRIMARY, paid=False, available=True),
    ])
    assert result.decision == ProviderDecision.ALLOWED
    assert result.provider_id == "brain-local"


def test_render_is_optional_and_never_authoritative():
    policy = BrainProviderPolicy()
    status = policy.auxiliary_status(
        ProviderDescriptor("render", ProviderRole.OPTIONAL_AUXILIARY, paid=False, available=True)
    )
    assert status["authoritative"] is False
    assert status["required_for_brain_autonomy"] is False


def test_external_provider_cannot_replace_missing_local_authority():
    policy = BrainProviderPolicy()
    result = policy.select([
        ProviderDescriptor("render", ProviderRole.OPTIONAL_AUXILIARY, paid=False, available=True),
    ])
    assert result.decision == ProviderDecision.BLOCKED
    assert result.provider_id is None


def test_github_verification_is_not_runtime_authority():
    policy = BrainProviderPolicy()
    status = policy.verification_status(
        ProviderDescriptor("github-actions", ProviderRole.VERIFICATION_ONLY, available=False)
    )
    assert status["authoritative"] is False
    assert status["required_for_brain_autonomy"] is False
