#include "family_cloud_worker.hpp"

#include <cassert>
#include <chrono>
#include <cstdio>
#include <thread>

using brain::family::ConsentingPair;
using brain::family::FamilyCloudWorker;
using namespace std::chrono_literals;

int main() {
    const std::string path = "/tmp/brain-family-cloud-worker-test.log";
    std::remove(path.c_str());

    const ConsentingPair consenting{"pair-a", "parent-a", "parent-b", true, true};
    const ConsentingPair not_consented{"pair-b", "parent-c", "parent-d", true, false};
    const ConsentingPair ineligible{"pair-c", "parent-e", "parent-f", true, true};
    const auto eligibility = [](const ConsentingPair& pair) {
        // Test stand-in for the Brain family policy's adult/married/kinship checks.
        return pair.pair_id == "pair-a" || pair.pair_id == "pair-fail";
    };

    {
        FamilyCloudWorker missing_policy(path, {}, 5ms);
        std::string error;
        assert(!missing_policy.start(&error));
        assert(error == "FAMILY_ELIGIBILITY_CHECK_REQUIRED");
    }

    {
        FamilyCloudWorker worker(path, eligibility, 5ms);
        std::string error;
        assert(worker.register_pair(consenting, &error));
        assert(worker.register_pair(not_consented, &error));
        assert(worker.register_pair(ineligible, &error));
        assert(worker.start(&error));
        assert(worker.running());

        for (unsigned i = 0; i < 100 && worker.memories().empty(); ++i) {
            std::this_thread::sleep_for(2ms);
        }
        worker.stop();
        assert(!worker.running());
        const auto memories = worker.memories();
        assert(!memories.empty());
        for (const auto& entry : memories) {
            assert(entry.parent_a == "parent-a");
            assert(entry.parent_b == "parent-b");
        }
    }

    const auto previous_size = [&path, &eligibility]() {
        FamilyCloudWorker worker(path, eligibility, 5ms);
        std::string error;
        assert(worker.register_pair(ConsentingPair{"pair-a", "parent-a", "parent-b", true, true}, &error));
        assert(worker.start(&error));
        for (unsigned i = 0; i < 100 && worker.memories().size() < 2; ++i) {
            std::this_thread::sleep_for(2ms);
        }
        worker.stop();
        return worker.memories();
    }();
    assert(previous_size.size() >= 2);
    assert(previous_size[0].birth_cycle != previous_size[1].birth_cycle);

    const std::string bad_path = "/tmp/brain-family-missing-dir-for-test/memory.log";
    FamilyCloudWorker failing_worker(bad_path, eligibility, 5ms);
    std::string error;
    assert(failing_worker.register_pair(
        ConsentingPair{"pair-fail", "parent-x", "parent-y", true, true}, &error));
    assert(failing_worker.start(&error));
    for (unsigned i = 0; i < 100 && failing_worker.last_error().empty(); ++i) {
        std::this_thread::sleep_for(2ms);
    }
    failing_worker.stop();
    assert(failing_worker.last_error() == "MEMORY_FILE_NOT_WRITABLE");

    std::remove(path.c_str());
    return 0;
}
