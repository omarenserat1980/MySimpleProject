#include "simulator_pointer_registry.hpp"

#include <filesystem>
#include <iostream>

int main(int argc, char** argv) {
    const std::filesystem::path root = argc > 1 ? argv[1] : ".";
    const auto report = brain6::audit_simulator_pointers(root);

    for (const auto& id : report.active_simulator_ids)
        std::cout << "ACTIVE simulator " << id << "\n";
    for (const auto& id : report.active_real_executor_ids)
        std::cout << "ACTIVE real_executor " << id << "\n";
    for (const auto& item : report.inactive_pointers)
        std::cout << "INACTIVE " << item.pointer_kind << " " << item.id
                  << " status=" << item.status << " target=" << item.target << "\n";

    std::cout << "SUMMARY active_simulators=" << report.active_simulator_ids.size()
              << " active_real_executors=" << report.active_real_executor_ids.size()
              << " inactive_pointers=" << report.inactive_pointers.size() << "\n";
    // Inactive pointers are reported and excluded, not deleted from source.
    return report.inactive_pointers.empty() ? 0 : 1;
}
