#include "simulator_pointer_registry.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <string_view>
#include <unordered_set>

int main() {
    using brain6::ExecutionMode;
    auto exists = [](std::string_view path) {
        return path == "brain_v12/brain/termux_emulator.py" ||
               path == "brain_v12/brain/desktop_commander_emulator.py" ||
               path == "brain_v12/brain/powershell_emulator.py" ||
               path == "brain_v12/tools/brain_runtime_bootstrap.sh";
    };

    auto termux = brain6::resolve_simulator_pointer(
        "termux-brain", ExecutionMode::TestSimulation, exists);
    assert(termux && termux.selected_entry == "brain_v12/brain/termux_emulator.py");

    auto powershell = brain6::resolve_simulator_pointer(
        "powershell-brain", ExecutionMode::TestSimulation, exists);
    assert(powershell && powershell.selected_entry == "brain_v12/brain/powershell_emulator.py");

    auto desktop = brain6::resolve_simulator_pointer(
        "desktop-commander-brain", ExecutionMode::TestSimulation, exists);
    assert(desktop && desktop.selected_entry == "brain_v12/brain/desktop_commander_emulator.py");

    auto real_without_proof = brain6::resolve_simulator_pointer(
        "termux-brain", ExecutionMode::RealExecution, exists, false);
    assert(!real_without_proof);
    assert(real_without_proof.status == "REAL_EXECUTOR_NOT_VERIFIED");

    auto real_termux = brain6::resolve_simulator_pointer(
        "termux-brain", ExecutionMode::RealExecution, exists, true);
    assert(real_termux);
    assert(real_termux.selected_entry == "brain_v12/tools/brain_runtime_bootstrap.sh");

    auto real_missing_adapter = brain6::resolve_simulator_pointer(
        "powershell-brain", ExecutionMode::RealExecution, exists, true);
    assert(!real_missing_adapter);
    assert(real_missing_adapter.status == "REAL_EXECUTOR_NOT_CONFIGURED");

    auto unknown = brain6::resolve_simulator_pointer(
        "unknown", ExecutionMode::TestSimulation, exists);
    assert(!unknown && unknown.status == "SIMULATOR_ID_UNKNOWN");

    // Audit removes dead pointers from active lists without deleting useful simulators.
    const auto root = std::filesystem::temp_directory_path() / "brain-pointer-audit-test";
    std::filesystem::remove_all(root);
    std::filesystem::create_directories(root / "brain_v12/brain");
    std::filesystem::create_directories(root / "brain_v12/tools");
    for (const auto* p : {
             "brain_v12/brain/termux_emulator.py",
             "brain_v12/brain/desktop_commander_emulator.py",
             "brain_v12/brain/powershell_emulator.py",
             "brain_v12/tools/brain_runtime_bootstrap.sh"}) {
        std::ofstream(root / p) << "# test fixture\n";
    }

    auto report = brain6::audit_simulator_pointers(root);
    assert(report.active_simulator_ids.size() == 3);
    assert(report.active_real_executor_ids.empty());
    assert(report.inactive_pointers.size() == 3);
    bool found_unconfigured_real = false;
    for (const auto& finding : report.inactive_pointers) {
        if (finding.pointer_kind == "real_executor" &&
            finding.status == "REAL_EXECUTOR_NOT_CONFIGURED")
            found_unconfigured_real = true;
    }
    assert(found_unconfigured_real);

    // Missing simulator target is excluded; the simulator itself is not deleted.
    std::filesystem::remove(root / "brain_v12/brain/powershell_emulator.py");
    report = brain6::audit_simulator_pointers(root);
    assert(report.active_simulator_ids.size() == 2);
    bool found_missing = false;
    for (const auto& finding : report.inactive_pointers) {
        if (finding.id == "powershell-brain" &&
            finding.pointer_kind == "simulator" &&
            finding.status == "SIMULATOR_TARGET_MISSING")
            found_missing = true;
    }
    assert(found_missing);
    std::filesystem::remove_all(root);
    return 0;
}
