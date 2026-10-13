#include "birth_thread.hpp"

#include <utility>

namespace brain::family {

BirthThread::BirthThread(CycleHandler handler, std::chrono::milliseconds interval)
    : handler_(std::move(handler)), interval_(interval) {
    if (interval_ <= std::chrono::milliseconds::zero()) {
        interval_ = std::chrono::seconds(90);
    }
}

BirthThread::~BirthThread() {
    stop();
}

bool BirthThread::start() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (worker_.joinable() || !handler_) return false;
    stopping_ = false;
    running_ = true;
    worker_ = std::thread(&BirthThread::run, this);
    return true;
}

void BirthThread::stop() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        stopping_ = true;
    }
    wake_.notify_all();
    if (worker_.joinable()) worker_.join();
    std::lock_guard<std::mutex> lock(mutex_);
    running_ = false;
}

bool BirthThread::running() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return running_;
}

void BirthThread::run() {
    std::unique_lock<std::mutex> lock(mutex_);
    while (!wake_.wait_for(lock, interval_, [this] { return stopping_; })) {
        const auto next_cycle = ++cycle_;
        lock.unlock();
        try {
            handler_(next_cycle);
        } catch (...) {
            lock.lock();
            stopping_ = true;
            running_ = false;
            return;
        }
        lock.lock();
    }
    running_ = false;
}

}  // namespace brain::family
