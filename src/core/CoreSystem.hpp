#ifndef TRINITY_CORE_SYSTEM_HPP
#define TRINITY_CORE_SYSTEM_HPP

#include <unordered_map>
#include <deque>
#include <thread>
#include <mutex>
#include <atomic>
#include <string>
#include <cstdint>
#include <vector>

#include "process/ProcessInfo.hpp"
#include "memory/MemoryEnums.hpp"

namespace trinity {

class CoreSystem {
public:
    CoreSystem();
    bool initialize();
    bool start();
    bool stop();

    // basic API for demonstration
    int createProcess(const std::string& name);
    std::string allocateMemory(int pid, std::uint64_t size);

    const ProcessInfo* getProcess(int pid) const;

private:
    void schedulerLoop();

    // state flags
    bool initialized_{false};
    std::atomic<bool> running_{false};
    std::atomic<bool> stop_requested_{false};

    // process management
    std::unordered_map<int, ProcessInfo> processes_;
    std::unordered_map<int, std::vector<std::string>> process_memory_;
    std::deque<int> ready_queue_;
    std::mutex proc_mutex_;
    int next_pid_{2};

    // memory management
    std::unordered_map<std::string, MemoryRegion> memory_regions_;
    std::mutex mem_mutex_;
    std::uint64_t next_mem_start_{0x20000000};
    int region_counter_{0};

    // scheduler thread
    std::thread scheduler_thread_;

    void initMemory();
    void initProcessMemory(int pid);
};

} // namespace trinity

#endif // TRINITY_CORE_SYSTEM_HPP
