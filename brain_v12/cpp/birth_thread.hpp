#pragma once

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <thread>

namespace brain::family {

// Emits virtual birth-cycle events on a dedicated worker thread.
// The callback runs on that worker thread and must be safe for that execution context.
class BirthThread {
public:
    using CycleHandler = std::function<void(std::uint64_t)>;

    explicit BirthThread(CycleHandler handler,
                         std::chrono::milliseconds interval = std::chrono::seconds(90));
    ~BirthThread();

    BirthThread(const BirthThread&) = delete;
    BirthThread& operator=(const BirthThread&) = delete;

    bool start();
    void stop();
    bool running() const;

private:
    void run();

    CycleHandler handler_;
    std::chrono::milliseconds interval_;
    mutable std::mutex mutex_;
    std::condition_variable wake_;
    std::thread worker_;
    bool stopping_ = false;
    bool running_ = false;
    std::uint64_t cycle_ = 0;
};

}  // namespace brain::family
