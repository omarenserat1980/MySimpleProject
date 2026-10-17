import unittest

from component_dossier import build_dossier


class ComponentDossierTests(unittest.TestCase):
    def test_lists_all_major_component_functions(self):
        report = build_dossier()
        refs = {item["ref"] for item in report["components"]}
        self.assertTrue({"U1", "U2", "U3", "U5", "U8", "U9", "J1", "J2", "PCB1"} <= refs)

    def test_never_claims_assembly_ready_without_parts(self):
        report = build_dossier()
        self.assertFalse(report["ready_for_assembly"])
        self.assertEqual(report["identified_exact_part_count"], 0)
        self.assertEqual(report["status"], "BLOCKED_PART_IDENTIFICATION")

    def test_manufacturer_label_is_not_physical_manufacturing_evidence(self):
        report = build_dossier()
        self.assertEqual(report["project_manufacturer_label"], "BRAIN AI")
        self.assertFalse(report["physical_manufacturing_verified"])
        self.assertFalse(report["legal_company_registration_verified"])
        self.assertTrue(all(p["physical_manufacturing_verified"] is False for p in report["components"]))

    def test_every_component_has_required_fields_and_missing_fields(self):
        for part in build_dossier()["components"]:
            self.assertTrue(part["required_fields"])
            self.assertEqual(part["missing_fields"], part["required_fields"])


if __name__ == "__main__":
    unittest.main()
