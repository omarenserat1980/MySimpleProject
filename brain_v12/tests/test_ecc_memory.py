from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.ecc_memory import VirtualECCMemoryController


class VirtualECCMemoryTests(unittest.TestCase):
    def test_clean_word_roundtrip_and_snapshot_restore(self):
        ecc = VirtualECCMemoryController()
        value = 0xFEDCBA9876543210
        ecc.write_word(0x100, value)
        self.assertEqual(ecc.read_word(0x100)["data"], value)
        clone = VirtualECCMemoryController()
        clone.restore(ecc.snapshot())
        self.assertEqual(clone.read_word(0x100)["data"], value)
        self.assertEqual(clone.status()["scheme"], "SECDED")

    def test_single_data_bit_is_corrected_and_repaired(self):
        ecc = VirtualECCMemoryController()
        value = 0x0123456789ABCDEF
        ecc.write_word(7, value)
        ecc.inject_bit_flip(7, 0)  # encoded codeword bit at position 1
        result = ecc.read_word(7)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "ECC_CORRECTED")
        self.assertEqual(result["data"], value)
        self.assertEqual(ecc.read_word(7)["status"], "OK")
        self.assertEqual(ecc.status()["stats"]["corrected_single_bit_errors"], 1)

    def test_single_parity_bit_is_corrected(self):
        ecc = VirtualECCMemoryController()
        ecc.write_word(8, 0xA5A5A5A5A5A5A5A5)
        ecc.inject_bit_flip(8, 0)  # position 1 is a Hamming parity bit
        result = ecc.read_word(8)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], 0xA5A5A5A5A5A5A5A5)
        self.assertEqual(ecc.status()["stats"]["parity_bit_errors"], 1)

    def test_double_bit_error_is_detected_not_silently_corrected(self):
        ecc = VirtualECCMemoryController()
        ecc.write_word(9, 0xDEADBEEF)
        ecc.inject_bit_flip(9, 2)
        ecc.inject_bit_flip(9, 4)
        result = ecc.read_word(9)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "ECC_UNCORRECTABLE")
        self.assertIsNone(result["data"])
        self.assertEqual(ecc.status()["stats"]["detected_double_bit_errors"], 1)

    def test_invalid_addresses_and_words_are_rejected(self):
        ecc = VirtualECCMemoryController()
        with self.assertRaisesRegex(ValueError, "ECC_WORD_OUT_OF_RANGE"):
            ecc.write_word(0, 1 << 64)
        with self.assertRaisesRegex(ValueError, "ECC_ADDRESS_INVALID"):
            ecc.read_word(-1)
        with self.assertRaisesRegex(ValueError, "ECC_BIT_INDEX_INVALID"):
            ecc.inject_bit_flip(0, 72)


if __name__ == "__main__":
    unittest.main()
