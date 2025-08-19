#include "core/CoreSystem.hpp"

#include <algorithm>
#include <utility>

namespace trinity {

CoreSystem::CoreSystem() = default;

CoreSystem::~CoreSystem() { stop(); }

void CoreSystem::initialize() {
    // Placeholder for future initialization logic.
}

void CoreSystem::start() {
    running_ = true;
    schedulerThread_ = std::thread(&CoreSystem::schedulerLoop, this);
}

void CoreSystem::stop() {
    {
        std::lock_guard<std::mutex> lock(queueMutex_);
        running_ = false;
    }
    cv_.notify_all();
    if (schedulerThread_.joinable()) {
        schedulerThread_.join();
    }
}

void CoreSystem::addProcess(std::function<void()> task, int priority, std::string name) {
    std::lock_guard<std::mutex> lock(queueMutex_);
    int pid = nextPid_++;
    Process proc{pid, priority, ProcessState::READY, std::move(name), std::move(task)};

    auto it = std::find_if(readyQueue_.begin(), readyQueue_.end(),
                           [priority](const Process& p) { return priority > p.priority; });
    readyQueue_.insert(it, std::move(proc));
    processStates_[pid] = ProcessState::READY;
    cv_.notify_one();
}

std::optional<ProcessState> CoreSystem::getProcessState(int pid) const {
    std::lock_guard<std::mutex> lock(queueMutex_);
    auto it = processStates_.find(pid);
    if (it != processStates_.end()) {
        return it->second;
    }
    return std::nullopt;
}

void CoreSystem::schedulerLoop() {
    while (true) {
        Process proc;
        {
            std::unique_lock<std::mutex> lock(queueMutex_);
            cv_.wait(lock, [this] { return !running_ || !readyQueue_.empty(); });
            if (!running_ && readyQueue_.empty()) {
                break; // No more work and scheduler stopped.
            }
            proc = std::move(readyQueue_.front());
            readyQueue_.pop_front();
            proc.state = ProcessState::RUNNING;
            processStates_[proc.pid] = proc.state;
        }

        if (proc.task) {
            proc.task();
        }

        {
            std::lock_guard<std::mutex> lock(queueMutex_);
            proc.state = ProcessState::TERMINATED;
            processStates_[proc.pid] = proc.state;
        }
    }
}

} // namespace trinity

