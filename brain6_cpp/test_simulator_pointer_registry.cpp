#include "simulator_pointer_registry.hpp"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string_view>

int main() {
    using brain6::ExecutionMode;
    auto exists = [](std::string_view p) {
        return p == "brain_v12/brain/termux_emulator.py" ||
               p == "brain_v12/brain/desktop_commander_emulator.py" ||
               p == "brain_v12/brain/powershell_emulator.py" ||
               p == "brain_v12/tools/brain_runtime_bootstrap.sh";
    };
    auto sim = brain6::resolve_simulator_pointer("termux-brain", ExecutionMode::TestSimulation, exists);
    assert(sim && sim.selected_entry == "brain_v12/brain/termux_emulator.py");
    auto no_proof = brain6::resolve_simulator_pointer("termux-brain", ExecutionMode::RealExecution, exists);
    assert(!no_proof && no_proof.status == "REAL_EXECUTOR_NOT_VERIFIED");
    auto no_adapter = brain6::resolve_simulator_pointer("powershell-brain", ExecutionMode::RealExecution, exists, true);
    assert(!no_adapter && no_adapter.status == "REAL_EXECUTOR_NOT_CONFIGURED");
    auto unknown = brain6::resolve_simulator_pointer("unknown", ExecutionMode::TestSimulation, exists);
    assert(!unknown && unknown.status == "SIMULATOR_ID_UNKNOWN");

    const auto root = std::filesystem::temp_directory_path() / "brain-pointer-audit-test";
    std::filesystem::remove_all(root);
    std::filesystem::create_directories(root / "brain_v12/brain");
    std::filesystem::create_directories(root / "brain_v12/tools");
    for (const auto* p : {"brain_v12/brain/termux_emulator.py",
                          "brain_v12/brain/desktop_commander_emulator.py",
                          "brain_v12/brain/powershell_emulator.py",
                          "brain_v12/tools/brain_runtime_bootstrap.sh"})
        std::ofstream(root / p) << "test fixture\n";
    auto report = brain6::audit_simulator_pointers(root);
    assert(report.active_simulator_ids.size() == 3);
    assert(report.active_real_executor_ids.empty());
    assert(report.inactive_pointers.size() == 3);
    std::filesystem::remove(root / "brain_v12/brain/powershell_emulator.py");
    report = brain6::audit_simulator_pointers(root);
    assert(report.active_simulator_ids.size() == 2);
    bool missing = false;
    for (const auto& f : report.inactive_pointers)
        if (f.id == "powershell-brain" && f.pointer_kind == "simulator" &&
            f.status == "SIMULATOR_TARGET_MISSING") missing = true;
    assert(missing);
    std::filesystem::remove_all(root);
    return 0;
}
