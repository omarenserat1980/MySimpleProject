import unittest
from brain_v12.brain.stratum_v1_field_normalization import (
    decode_hash32_hex,
    decode_merkle_branch_hex,
    stratum_u32_to_header_bytes,
)


class StratumV1FieldNormalizationTests(unittest.TestCase):
    def test_u32_fields_are_converted_to_header_little_endian(self):
        self.assertEqual(stratum_u32_to_header_bytes('20000000', field='version'), bytes.fromhex('00000020'))
        self.assertEqual(stratum_u32_to_header_bytes('495fab29', field='ntime'), bytes.fromhex('29ab5f49'))
        self.assertEqual(stratum_u32_to_header_bytes('1d00ffff', field='nbits'), bytes.fromhex('ffff001d'))
        self.assertEqual(stratum_u32_to_header_bytes('12345678', field='nonce'), bytes.fromhex('78563412'))

    def test_hash_order_must_be_explicit(self):
        value = '00' + '11' * 30 + '22'
        self.assertEqual(decode_hash32_hex(value, reverse_bytes=False), bytes.fromhex(value))
        self.assertEqual(decode_hash32_hex(value, reverse_bytes=True), bytes.fromhex(value)[::-1])

    def test_merkle_branch_is_decoded_without_implicit_reversal(self):
        value = ''.join(f'{i:02x}' for i in range(32))
        self.assertEqual(decode_merkle_branch_hex(value), bytes(range(32)))

    def test_rejects_wrong_width_non_hex_and_unsupported_field(self):
        for call in (
            lambda: stratum_u32_to_header_bytes('123', field='ntime'),
            lambda: stratum_u32_to_header_bytes('zz000000', field='ntime'),
            lambda: stratum_u32_to_header_bytes('00000000', field='prevhash'),
            lambda: decode_hash32_hex('00', reverse_bytes=False),
            lambda: decode_merkle_branch_hex('gg' * 32),
        ):
            with self.assertRaises(ValueError):
                call()

if __name__ == '__main__':
    unittest.main()
