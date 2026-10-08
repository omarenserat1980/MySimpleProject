import unittest

from brain_v12.brain.execution_policy import (
    WINDOWS_CLOUD_NATIVE,
    WINDOWS_NATIVE_EXECUTOR,
    WINDOWS_REAL_BOOT,
)
from brain_v12.brain.executor_router import (
    assert_single_flight,
    route_windows,
)


class ExecutorRouterTests(unittest.TestCase):
    def test_real_boot_requires_qemu_cloud_route(self):
        route = route_windows(
            WINDOWS_REAL_BOOT,
            {"executor": "windows-real-boot-qemu"},
        )
        self.assertEqual(route.executor, "windows-real-boot-qemu")
        self.assertTrue(route.single_flight)

    def test_real_boot_rejects_native_substitution(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_BOOT_REQUIRES_QEMU_CLOUD"
        ):
            route_windows(
                WINDOWS_REAL_BOOT,
                {"executor": "windows-server-2025-cloud"},
            )

    def test_native_windows_is_separate(self):
        route = route_windows(WINDOWS_NATIVE_EXECUTOR)
        self.assertEqual(route.mode, WINDOWS_NATIVE_EXECUTOR)

    def test_cloud_native_is_separate(self):
        route = route_windows(WINDOWS_CLOUD_NATIVE)
        self.assertEqual(route.mode, WINDOWS_CLOUD_NATIVE)

    def test_single_flight_blocks_second_consequential_run(self):
        route = route_windows(
            WINDOWS_REAL_BOOT,
            {"executor": "windows-real-boot-qemu"},
        )
        with self.assertRaisesRegex(RuntimeError, "EXECUTOR_SINGLE_FLIGHT_BUSY"):
            assert_single_flight(route, 1)

    def test_zero_active_runs_is_allowed(self):
        route = route_windows(
            WINDOWS_REAL_BOOT,
            {"executor": "windows-real-boot-qemu"},
        )
        assert_single_flight(route, 0)


if __name__ == "__main__":
    unittest.main()
