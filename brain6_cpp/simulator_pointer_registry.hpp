#pragma once

#include <array>
#include <filesystem>
#include <functional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

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

struct PointerFinding {
    std::string id;
    std::string pointer_kind;
    std::string target;
    std::string status;
};

struct PointerAuditReport {
    std::vector<std::string> active_simulator_ids;
    std::vector<std::string> active_real_executor_ids;
    std::vector<PointerFinding> inactive_pointers;

    bool clean() const noexcept { return inactive_pointers.empty(); }
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

// Audit is deliberately non-destructive: bad pointers are excluded from the
// active lists and reported, but simulator source files and registry entries
// are not deleted. A real executor is active only with both a real target file
// and an explicit independently-verified identity supplied by the caller.
inline PointerAuditReport audit_simulator_pointers(
    const std::filesystem::path& repository_root,
    const std::unordered_set<std::string>& independently_verified_real_ids = {}) {
    PointerAuditReport report;
    std::unordered_set<std::string> seen_ids;
    std::unordered_set<std::string> seen_simulator_targets;

    for (const auto& candidate : simulator_pointers) {
        const std::string id(candidate.id);
        const std::string simulator_target(candidate.simulator_entry);
        if (!seen_ids.insert(id).second) {
            report.inactive_pointers.push_back(
                {id, "simulator", simulator_target, "DUPLICATE_SIMULATOR_ID"});
            continue;
        }

        if (simulator_target.empty()) {
            report.inactive_pointers.push_back(
                {id, "simulator", simulator_target, "SIMULATOR_TARGET_NOT_CONFIGURED"});
        } else if (!std::filesystem::is_regular_file(repository_root / simulator_target)) {
            report.inactive_pointers.push_back(
                {id, "simulator", simulator_target, "SIMULATOR_TARGET_MISSING"});
        } else if (!seen_simulator_targets.insert(simulator_target).second) {
            report.inactive_pointers.push_back(
                {id, "simulator", simulator_target, "DUPLICATE_SIMULATOR_TARGET"});
        } else {
            report.active_simulator_ids.push_back(id);
        }

        const std::string real_target(candidate.real_executor_entry);
        if (real_target.empty()) {
            report.inactive_pointers.push_back(
                {id, "real_executor", real_target, "REAL_EXECUTOR_NOT_CONFIGURED"});
        } else if (!std::filesystem::is_regular_file(repository_root / real_target)) {
            report.inactive_pointers.push_back(
                {id, "real_executor", real_target, "REAL_EXECUTOR_TARGET_MISSING"});
        } else if (independently_verified_real_ids.find(id) == independently_verified_real_ids.end()) {
            report.inactive_pointers.push_back(
                {id, "real_executor", real_target, "REAL_EXECUTOR_NOT_INDEPENDENTLY_VERIFIED"});
        } else {
            report.active_real_executor_ids.push_back(id);
        }
    }
    return report;
}

}  // namespace brain6
