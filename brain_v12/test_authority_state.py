import unittest
from brain_v12.brain.authority_state import AuthorityState, derive_authority_state


class AuthorityStateTests(unittest.TestCase):
    def test_configuration_never_claims_autonomy(self):
        state = derive_authority_state(
            runtime_code=True,
            preflight_verified=True,
            runner_online=False,
            task_executed=False,
            task_verified=False,
            autonomy_certified=False,
        )
        self.assertEqual(state, AuthorityState.INTERNAL_RUNNER_PREFLIGHT_VERIFIED)

    def test_autonomy_requires_full_evidence(self):
        state = derive_authority_state(
            runtime_code=True,
            preflight_verified=True,
            runner_online=True,
            task_executed=True,
            task_verified=True,
            autonomy_certified=True,
        )
        self.assertEqual(state, AuthorityState.AUTONOMOUS_WITHIN_AUTHORITY)


if __name__ == "__main__":
    unittest.main()
