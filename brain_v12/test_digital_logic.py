import unittest

from brain_v12.virtual_hardware.digital_logic import DigitalClock, MiniCalculator


class DigitalClockTests(unittest.TestCase):
    def test_clock_advances_and_wraps(self):
        clock = DigitalClock(width_bits=3, ticks=6)
        self.assertEqual(clock.pulse(1)["ticks"], 7)
        status = clock.pulse(1)
        self.assertEqual(status["ticks"], 0)
        self.assertEqual(status["mode"], "SIMULATED_LOGICAL_TICKS")

    def test_disabled_clock_does_not_advance_and_reset_works(self):
        clock = DigitalClock(width_bits=8, ticks=12, enabled=False)
        self.assertEqual(clock.pulse(10)["ticks"], 12)
        self.assertEqual(clock.reset()["ticks"], 0)

    def test_clock_rejects_invalid_width_ticks_and_pulses(self):
        with self.assertRaisesRegex(ValueError, "CLOCK_WIDTH"):
            DigitalClock(width_bits=0)
        with self.assertRaisesRegex(ValueError, "CLOCK_TICKS"):
            DigitalClock(width_bits=3, ticks=8)
        with self.assertRaisesRegex(ValueError, "CLOCK_PULSE"):
            DigitalClock().pulse(-1)


class MiniCalculatorTests(unittest.TestCase):
    def test_unsigned_arithmetic_and_overflow(self):
        calc = MiniCalculator(width_bits=8)
        self.assertEqual(calc.calculate("ADD", 7, 5)["value"], 12)
        overflow = calc.calculate("ADD", 255, 1)
        self.assertEqual(overflow["value"], 0)
        self.assertTrue(overflow["overflow"])

    def test_signed_wraparound_and_division_truncates_toward_zero(self):
        calc = MiniCalculator(width_bits=8, signed=True)
        result = calc.calculate("ADD", 127, 1)
        self.assertEqual(result["value"], -128)
        self.assertTrue(result["overflow"])
        self.assertEqual(calc.calculate("DIV", -7, 2)["value"], -3)

    def test_calculator_rejects_zero_division_bad_ops_and_bad_operands(self):
        calc = MiniCalculator()
        with self.assertRaisesRegex(ZeroDivisionError, "DIVIDE_BY_ZERO"):
            calc.calculate("DIV", 4, 0)
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_OPERATION"):
            calc.calculate("POW", 2, 3)
        with self.assertRaisesRegex(ValueError, "OPERAND_OUT_OF_RANGE"):
            calc.calculate("ADD", 256, 1)
        with self.assertRaisesRegex(TypeError, "OPERANDS_MUST_BE_INTEGERS"):
            calc.calculate("ADD", True, 1)


if __name__ == "__main__":
    unittest.main()
