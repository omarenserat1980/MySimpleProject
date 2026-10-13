#include "birth_thread.hpp"

#include <atomic>
#include <cassert>
#include <chrono>
#include <thread>

using brain::family::BirthThread;
using namespace std::chrono_literals;

int main() {
    std::atomic<unsigned> events{0};
    BirthThread births([&events](std::uint64_t cycle) {
        assert(cycle > 0);
        ++events;
    }, 5ms);

    assert(births.start());
    assert(!births.start());
    for (unsigned i = 0; i < 100 && events.load() < 2; ++i) {
        std::this_thread::sleep_for(2ms);
    }
    births.stop();
    assert(!births.running());
    assert(events.load() >= 2);

    const auto final_count = events.load();
    std::this_thread::sleep_for(15ms);
    assert(events.load() == final_count);
    return 0;
}
