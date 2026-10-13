#pragma once

#include "birth_thread.hpp"
#include "family_memory_store.hpp"

#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace brain::family {

struct ConsentingPair {
    std::string pair_id;
    std::string parent_a;
    std::string parent_b;
    bool parent_a_consents = false;
    bool parent_b_consents = false;
};

// In-process worker harness: restores child memory before starting the timed thread,
// then records one virtual child per mutually consenting pair per cycle.
class FamilyCloudWorker {
public:
    explicit FamilyCloudWorker(std::string memory_path,
        std::chrono::milliseconds interval = std::chrono::seconds(90));
    ~FamilyCloudWorker();

    FamilyCloudWorker(const FamilyCloudWorker&) = delete;
    FamilyCloudWorker& operator=(const FamilyCloudWorker&) = delete;

    bool register_pair(const ConsentingPair& pair, std::string* error = nullptr);
    bool start(std::string* error = nullptr);
    void stop();
    bool running() const;
    std::vector<ChildMemory> memories() const;

private:
    void on_cycle(std::uint64_t local_cycle);

    FamilyMemoryStore memory_;
    std::chrono::milliseconds interval_;
    mutable std::mutex mutex_;
    std::vector<ConsentingPair> pairs_;
    std::unique_ptr<BirthThread> birth_thread_;
    std::uint64_t cycle_offset_ = 0;
    bool started_ = false;
};

}  // namespace brain::family
