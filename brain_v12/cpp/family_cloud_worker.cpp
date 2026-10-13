#include "family_cloud_worker.hpp"

#include <algorithm>
#include <utility>

namespace brain::family {

FamilyCloudWorker::FamilyCloudWorker(std::string memory_path,
                                     std::chrono::milliseconds interval)
    : memory_(std::move(memory_path)), interval_(interval) {}

FamilyCloudWorker::~FamilyCloudWorker() {
    stop();
}

bool FamilyCloudWorker::register_pair(const ConsentingPair& pair, std::string* error) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (started_) {
        if (error) *error = "CANNOT_REGISTER_PAIR_WHILE_RUNNING";
        return false;
    }
    if (pair.pair_id.empty() || pair.parent_a.empty() || pair.parent_b.empty() ||
        pair.parent_a == pair.parent_b) {
        if (error) *error = "PAIR_IDENTITIES_INVALID";
        return false;
    }
    const auto duplicate = std::find_if(pairs_.begin(), pairs_.end(),
        [&pair](const ConsentingPair& existing) { return existing.pair_id == pair.pair_id; });
    if (duplicate != pairs_.end()) {
        if (error) *error = "PAIR_ID_ALREADY_REGISTERED";
        return false;
    }
    pairs_.push_back(pair);
    return true;
}

bool FamilyCloudWorker::start(std::string* error) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (started_) {
            if (error) *error = "WORKER_ALREADY_STARTED";
            return false;
        }
    }
    if (!memory_.restore(error)) return false;
    const auto existing = memory_.children();
    std::uint64_t highest_cycle = 0;
    for (const auto& entry : existing) {
        highest_cycle = std::max(highest_cycle, entry.birth_cycle);
    }
    {
        std::lock_guard<std::mutex> lock(mutex_);
        cycle_offset_ = highest_cycle;
        last_error_.clear();
        birth_thread_ = std::make_unique<BirthThread>(
            [this](std::uint64_t cycle) { on_cycle(cycle); }, interval_);
        started_ = birth_thread_->start();
        if (!started_) {
            birth_thread_.reset();
            if (error) *error = "BIRTH_THREAD_START_FAILED";
            return false;
        }
    }
    return true;
}

void FamilyCloudWorker::stop() {
    BirthThread* thread = nullptr;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (birth_thread_) thread = birth_thread_.get();
    }
    if (thread) thread->stop();
    {
        std::lock_guard<std::mutex> lock(mutex_);
        started_ = false;
        birth_thread_.reset();
    }
}

bool FamilyCloudWorker::running() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return birth_thread_ && birth_thread_->running();
}

std::vector<ChildMemory> FamilyCloudWorker::memories() const {
    return memory_.children();
}

std::string FamilyCloudWorker::last_error() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return last_error_;
}

void FamilyCloudWorker::on_cycle(std::uint64_t local_cycle) {
    std::vector<ConsentingPair> pairs;
    std::uint64_t global_cycle = 0;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        pairs = pairs_;
        global_cycle = cycle_offset_ + local_cycle;
    }
    for (const auto& pair : pairs) {
        if (!pair.parent_a_consents || !pair.parent_b_consents) continue;
        ChildMemory child;
        child.child_id = "sim-child-" + pair.pair_id + "-cycle-" + std::to_string(global_cycle);
        child.name = "Virtual descendant " + pair.pair_id + " #" + std::to_string(global_cycle);
        child.parent_a = pair.parent_a;
        child.parent_b = pair.parent_b;
        child.birth_cycle = global_cycle;
        std::string write_error;
        if (!memory_.remember(child, &write_error)) {
            std::lock_guard<std::mutex> lock(mutex_);
            last_error_ = write_error.empty() ? "CHILD_MEMORY_WRITE_FAILED" : write_error;
        }
    }
}

}  // namespace brain::family
