#pragma once

#include <array>
#include <functional>
#include <string_view>

namespace brain6 {

enum class ExecutionMode { TestSimulation, RealExecution };

struct SimulatorPointer {
    std::string_view id;
    std::string_view simulator_entry;
    std::string_view real_executor_entry;
};

struct PointerResolution {
    const SimulatorPointer* pointer = nullptr;
    std::string_view selected_entry;
    std::string_view status;
    ExecutionMode mode = ExecutionMode::TestSimulation;

    explicit operator bool() const noexcept { return pointer != nullptr; }
};

// Empty real_executor_entry is intentional until a real adapter is explicitly
// registered and independently verified. It must never fall back to simulation.
inline constexpr std::array<SimulatorPointer, 3> simulator_pointers{{
    {"termux-brain", "brain_v12/brain/termux_emulator.py", "brain_v12/tools/brain_runtime_bootstrap.sh"},
    {"desktop-commander-brain", "brain_v12/brain/desktop_commander_emulator.py", ""},
    {"powershell-brain", "brain_v12/brain/powershell_emulator.py", ""},
}};

inline PointerResolution resolve_simulator_pointer(
    std::string_view id,
    ExecutionMode mode,
    const std::function<bool(std::string_view)>& exists,
    bool real_executor_independently_verified = false) {
    for (const auto& candidate : simulator_pointers) {
        if (candidate.id != id) continue;
        if (mode == ExecutionMode::TestSimulation) {
            if (candidate.simulator_entry.empty() || !exists(candidate.simulator_entry))
                return {nullptr, {}, "SIMULATOR_TARGET_MISSING", mode};
            return {&candidate, candidate.simulator_entry, "SIMULATOR_POINTER_RESOLVED", mode};
        }
        if (!real_executor_independently_verified)
            return {nullptr, {}, "REAL_EXECUTOR_NOT_VERIFIED", mode};
        if (candidate.real_executor_entry.empty())
            return {nullptr, {}, "REAL_EXECUTOR_NOT_CONFIGURED", mode};
        if (!exists(candidate.real_executor_entry))
            return {nullptr, {}, "REAL_EXECUTOR_TARGET_MISSING", mode};
        return {&candidate, candidate.real_executor_entry, "REAL_EXECUTOR_POINTER_RESOLVED", mode};
    }
    return {nullptr, {}, "SIMULATOR_ID_UNKNOWN", mode};
}

}  // namespace brain6
