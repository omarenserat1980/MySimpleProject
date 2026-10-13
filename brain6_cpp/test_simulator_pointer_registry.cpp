#include "simulator_pointer_registry.hpp"

#include <cassert>
#include <string_view>

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

    // Missing proof must fail closed; it must not silently point to a simulator.
    auto real_without_proof = brain6::resolve_simulator_pointer(
        "termux-brain", ExecutionMode::RealExecution, exists, false);
    assert(!real_without_proof);
    assert(real_without_proof.status == "REAL_EXECUTOR_NOT_VERIFIED");

    auto real_missing_adapter = brain6::resolve_simulator_pointer(
        "powershell-brain", ExecutionMode::RealExecution, exists, true);
    assert(!real_missing_adapter);
    assert(real_missing_adapter.status == "REAL_EXECUTOR_NOT_CONFIGURED");

    auto unknown = brain6::resolve_simulator_pointer(
        "unknown", ExecutionMode::TestSimulation, exists);
    assert(!unknown && unknown.status == "SIMULATOR_ID_UNKNOWN");
    return 0;
}
