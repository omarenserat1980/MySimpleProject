import hashlib
import unittest

from brain_v12.business.cl_000003_master_release_gate import REQUIRED, decide
from brain_v12.business.cl_000003_publication_guard import require_master_release


class ThousandDeepReleaseLoopTests(unittest.TestCase):
    """Execute 1000 adversarial release iterations, not 1000 static assertions."""

    def valid(self, i):
        return {
            "film_id": f"CL3-FILM-{i:04d}",
            "film_version": f"v{i % 17 + 1}",
            "production_run": f"RUN-{i:04d}",
            **{
                k: {
                    "passed": True,
                    "evidence_ref": f"evidence/{i}/{k}",
                    "evidence_sha256": hashlib.sha256(
                        f"{i}:{k}".encode()
                    ).hexdigest(),
                }
                for k in REQUIRED
            },
        }

    def mutate(self, evidence, i):
        attack = i % 10
        if attack == 0:
            evidence.pop("film_id", None)
        elif attack == 1:
            evidence.pop("film_version", None)
        elif attack == 2:
            evidence.pop("production_run", None)
        elif attack == 3:
            evidence["cinematic"]["passed"] = False
        elif attack == 4:
            evidence["rights"].pop("evidence_ref", None)
        elif attack == 5:
            evidence["legal_policy"].pop("evidence_sha256", None)
        elif attack == 6:
            evidence["technical"]["evidence_sha256"] = "x"
        elif attack == 7:
            evidence["status"] = "MASTER_RELEASE_PASS"
            evidence["publish_authorized"] = True
            evidence["cinematic"]["passed"] = False
        elif attack == 8:
            evidence["film_id"] = " "
        elif attack == 9:
            evidence["legal_policy"]["passed"] = False
        return evidence

    def test_1000_real_adversarial_iterations(self):
        iterations = 1000
        blocked = 0
        unexpected_authorizations = []

        for i in range(iterations):
            evidence = self.mutate(self.valid(i), i)
            decision = decide(evidence)
            publication = require_master_release(evidence)

            # Every iteration is deliberately corrupted, so publication must fail.
            if decision["publish_authorized"] or publication["authorized"]:
                unexpected_authorizations.append({
                    "iteration": i,
                    "decision": decision,
                    "publication": publication,
                })
            else:
                blocked += 1

        self.assertEqual(blocked, iterations)
        self.assertEqual(unexpected_authorizations, [])


if __name__ == "__main__":
    unittest.main()
