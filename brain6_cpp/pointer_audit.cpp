#include "simulator_pointer_registry.hpp"
#include <filesystem>
#include <iostream>
int main(int argc, char** argv) {
    const std::filesystem::path root = argc > 1 ? argv[1] : ".";
    const auto r = brain6::audit_simulator_pointers(root);
    for (const auto& id : r.active_simulator_ids) std::cout << "ACTIVE simulator " << id << "\n";
    for (const auto& id : r.active_real_executor_ids) std::cout << "ACTIVE real_executor " << id << "\n";
    for (const auto& f : r.inactive_pointers)
        std::cout << "INACTIVE " << f.pointer_kind << " " << f.id
                  << " status=" << f.status << " target=" << f.target << "\n";
    std::cout << "SUMMARY active_simulators=" << r.active_simulator_ids.size()
              << " active_real_executors=" << r.active_real_executor_ids.size()
              << " inactive_pointers=" << r.inactive_pointers.size() << "\n";
    return r.clean() ? 0 : 1;
}
