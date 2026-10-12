"""Functional SECDED ECC word model; not a DDR PHY or hardware ECC engine."""
from __future__ import annotations


_DATA_POSITIONS = tuple(position for position in range(1, 72)
                        if position & (position - 1))
_PARITY_POSITIONS = (1, 2, 4, 8, 16, 32, 64)
_WORD_MASK = (1 << 64) - 1


class VirtualECCMemoryController:
    """Sparse 64-bit words with Hamming SECDED encode/decode and deterministic bit faults.

    Bit positions 1..71 contain 64 data bits and seven Hamming parity bits. A separate
    overall parity bit detects two-bit corruption. The model corrects any single-bit error
    in the encoded word and reports (does not correct) detected double-bit errors.
    """
    def __init__(self):
        self._words: dict[int, tuple[int, int]] = {}
        self.stats = {"writes": 0, "reads": 0, "corrected_single_bit_errors": 0,
                      "detected_double_bit_errors": 0, "parity_bit_errors": 0}

    @staticmethod
    def _encode(data: int) -> tuple[int, int]:
        if not isinstance(data, int) or not 0 <= data <= _WORD_MASK:
            raise ValueError("ECC_WORD_OUT_OF_RANGE")
        codeword = 0
        for bit_index, position in enumerate(_DATA_POSITIONS):
            if (data >> bit_index) & 1:
                codeword |= 1 << (position - 1)
        for parity_position in _PARITY_POSITIONS:
            parity = 0
            for position in range(1, 72):
                if position & parity_position:
                    parity ^= (codeword >> (position - 1)) & 1
            if parity:
                codeword |= 1 << (parity_position - 1)
        overall_parity = codeword.bit_count() & 1
        return codeword, overall_parity

    @staticmethod
    def _decode(codeword: int, overall_parity: int) -> tuple[int, int, int]:
        syndrome = 0
        for parity_position in _PARITY_POSITIONS:
            parity = 0
            for position in range(1, 72):
                if position & parity_position:
                    parity ^= (codeword >> (position - 1)) & 1
            if parity:
                syndrome |= parity_position
        overall_mismatch = (codeword.bit_count() & 1) ^ overall_parity
        if syndrome and overall_mismatch:
            if syndrome <= 71:
                codeword ^= 1 << (syndrome - 1)
            else:
                return 0, 0, 1
            corrected = syndrome
        elif syndrome == 0 and overall_mismatch:
            # Only the separate overall-parity bit is wrong; data remains intact.
            corrected = 72
        elif syndrome and not overall_mismatch:
            return 0, syndrome, 2
        else:
            corrected = 0
        data = 0
        for bit_index, position in enumerate(_DATA_POSITIONS):
            data |= ((codeword >> (position - 1)) & 1) << bit_index
        return data, corrected, 0

    def write_word(self, address: int, data: int) -> dict:
        if not isinstance(address, int) or address < 0:
            raise ValueError("ECC_ADDRESS_INVALID")
        self._words[address] = self._encode(data)
        self.stats["writes"] += 1
        return {"ok": True, "address": address, "data": data, "word_bits": 64,
                "check_bits": 8, "scheme": "SECDED", "physical_memory_used": False}

    def read_word(self, address: int) -> dict:
        if not isinstance(address, int) or address < 0:
            raise ValueError("ECC_ADDRESS_INVALID")
        codeword, overall = self._words.get(address, self._encode(0))
        data, correction, error = self._decode(codeword, overall)
        self.stats["reads"] += 1
        if error:
            self.stats["detected_double_bit_errors"] += 1
            return {"ok": False, "status": "ECC_UNCORRECTABLE", "address": address,
                    "syndrome": correction, "data": None, "scheme": "SECDED"}
        if correction:
            self.stats["corrected_single_bit_errors"] += 1
            # The decoded data is repaired and re-encoded for subsequent reads.
            self._words[address] = self._encode(data)
            if correction in _PARITY_POSITIONS or correction == 72:
                self.stats["parity_bit_errors"] += 1
        return {"ok": True, "status": "ECC_CORRECTED" if correction else "OK",
                "address": address, "data": data, "corrected": bool(correction),
                "scheme": "SECDED", "physical_memory_used": False}

    def inject_bit_flip(self, address: int, encoded_bit_index: int) -> dict:
        if not isinstance(address, int) or address < 0 or not 0 <= encoded_bit_index <= 71:
            raise ValueError("ECC_BIT_INDEX_INVALID")
        codeword, overall = self._words.get(address, self._encode(0))
        if encoded_bit_index == 71:
            overall ^= 1
        else:
            codeword ^= 1 << encoded_bit_index
        self._words[address] = (codeword, overall)
        return {"ok": True, "address": address, "encoded_bit_index": encoded_bit_index,
                "deterministic": True}

    def snapshot(self) -> dict:
        return {"schema_version": 1,
                "words": {str(address): {"codeword": codeword, "overall_parity": overall}
                          for address, (codeword, overall) in sorted(self._words.items())},
                "stats": dict(self.stats), "scheme": "SECDED"}

    def restore(self, snapshot: dict) -> None:
        if snapshot.get("schema_version") != 1 or snapshot.get("scheme") != "SECDED":
            raise ValueError("ECC_SNAPSHOT_VERSION_INVALID")
        restored = {}
        for raw_address, value in (snapshot.get("words") or {}).items():
            address = int(raw_address)
            if address < 0 or not isinstance(value, dict):
                raise ValueError("ECC_SNAPSHOT_INVALID")
            codeword, overall = int(value["codeword"]), int(value["overall_parity"])
            if codeword < 0 or codeword >= (1 << 71) or overall not in {0, 1}:
                raise ValueError("ECC_SNAPSHOT_INVALID")
            restored[address] = (codeword, overall)
        self._words = restored
        self.stats = {key: int(value) for key, value in (snapshot.get("stats") or {}).items()}
        for key in ("writes", "reads", "corrected_single_bit_errors", "detected_double_bit_errors", "parity_bit_errors"):
            self.stats.setdefault(key, 0)

    def status(self) -> dict:
        return {"scheme": "SECDED", "logical_words": len(self._words), "word_bits": 64,
                "check_bits_per_word": 8, "stats": dict(self.stats),
                "fidelity": "functional_single_error_correction_double_error_detection",
                "physical_ecc_engine_used": False, "dram_phy_modeled": False}
