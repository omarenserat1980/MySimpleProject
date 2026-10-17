#pragma once

#include "birth_thread.hpp"
#include "family_memory_store.hpp"

#include <chrono>
#include <cstdint>
#include <functional>
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

// In-process worker harness. The eligibility callback must verify current family
// policy (adult status, marriage, and prohibited-kinship rules) before a cycle
// may record a virtual descendant.
class FamilyCloudWorker {
public:
    using EligibilityCheck = std::function<bool(const ConsentingPair&)>;

    FamilyCloudWorker(std::string memory_path, EligibilityCheck eligibility_check,
        std::chrono::milliseconds interval = std::chrono::seconds(90));
    ~FamilyCloudWorker();

    FamilyCloudWorker(const FamilyCloudWorker&) = delete;
    FamilyCloudWorker& operator=(const FamilyCloudWorker&) = delete;

    bool register_pair(const ConsentingPair& pair, std::string* error = nullptr);
    bool start(std::string* error = nullptr);
    void stop();
    bool running() const;
    std::vector<ChildMemory> memories() const;
    std::string last_error() const;

private:
    void on_cycle(std::uint64_t local_cycle);

    FamilyMemoryStore memory_;
    EligibilityCheck eligibility_check_;
    std::chrono::milliseconds interval_;
    mutable std::mutex mutex_;
    std::vector<ConsentingPair> pairs_;
    std::unique_ptr<BirthThread> birth_thread_;
    std::uint64_t cycle_offset_ = 0;
    bool started_ = false;
    std::string last_error_;
};

}  // namespace brain::family
