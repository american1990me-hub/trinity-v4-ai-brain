#include "CoreSystem.hpp"

#include <chrono>
#include <sstream>

namespace trinity {

CoreSystem::CoreSystem() = default;

bool CoreSystem::initialize() {
    if (initialized_) {
        return true;
    }
    initMemory();
    double now = std::chrono::duration<double>(
                    std::chrono::system_clock::now().time_since_epoch()).count();
    ProcessInfo kernel{0,0,"kernel",ProcessState::RUNNING,
                       ProcessPriority::SYSTEM,SchedulingPolicy::FIFO,{},now};
    ProcessInfo init{1,0,"init",ProcessState::READY,
                     ProcessPriority::SYSTEM,SchedulingPolicy::FIFO,{},now};
    {
        std::lock_guard<std::mutex> lock(proc_mutex_);
        processes_[0] = kernel;
        processes_[1] = init;
        ready_queue_.push_back(1);
    }
    initialized_ = true;
    return true;
}

bool CoreSystem::start() {
    if (!initialized_ && !initialize()) {
        return false;
    }
    if (running_) {
        return true;
    }
    stop_requested_ = false;
    scheduler_thread_ = std::thread(&CoreSystem::schedulerLoop, this);
    running_ = true;
    return true;
}

bool CoreSystem::stop() {
    if (!running_) {
        return true;
    }
    stop_requested_ = true;
    if (scheduler_thread_.joinable()) {
        scheduler_thread_.join();
    }
    running_ = false;
    return true;
}

void CoreSystem::schedulerLoop() {
    using namespace std::chrono_literals;
    while (!stop_requested_) {
        // Scheduler placeholder
        std::this_thread::sleep_for(1ms);
    }
}

int CoreSystem::createProcess(const std::string& name) {
    int pid;
    double now = std::chrono::duration<double>(
                    std::chrono::system_clock::now().time_since_epoch()).count();
    {
        std::lock_guard<std::mutex> lock(proc_mutex_);
        pid = next_pid_++;
        ProcessInfo proc{pid,0,name,ProcessState::READY,
                         ProcessPriority::NORMAL,SchedulingPolicy::ROUND_ROBIN,{},now};
        processes_[pid] = proc;
        ready_queue_.push_back(pid);
    }
    initProcessMemory(pid);
    return pid;
}

std::string CoreSystem::allocateMemory(int pid, std::uint64_t size) {
    std::lock_guard<std::mutex> lock(mem_mutex_);
    std::ostringstream oss;
    oss << "region_" << region_counter_++;
    std::string id = oss.str();
    MemoryRegion region{id, next_mem_start_, size, pid,
                        MemoryType::NORMAL, MemoryPermission::READ_WRITE};
    memory_regions_[id] = region;
    process_memory_[pid].push_back(id);
    next_mem_start_ += size;
    {
        std::lock_guard<std::mutex> plock(proc_mutex_);
        processes_[pid].memory_usage += size;
    }
    return id;
}

const ProcessInfo* CoreSystem::getProcess(int pid) const {
    auto it = processes_.find(pid);
    if (it == processes_.end()) {
        return nullptr;
    }
    return &it->second;
}

void CoreSystem::initMemory() {
    MemoryRegion kernel{"kernel_main",0x1000,64*1024*1024,0,
                         MemoryType::LOCKED,MemoryPermission::READ_WRITE_EXECUTE};
    MemoryRegion shared{"system_shared",0x10000000,32*1024*1024,0,
                         MemoryType::SHARED,MemoryPermission::READ_WRITE};
    std::lock_guard<std::mutex> lock(mem_mutex_);
    memory_regions_[kernel.id] = kernel;
    memory_regions_[shared.id] = shared;
    process_memory_[0] = {kernel.id, shared.id};
}

void CoreSystem::initProcessMemory(int pid) {
    std::lock_guard<std::mutex> lock(mem_mutex_);
    std::string code_id = "code_" + std::to_string(pid);
    MemoryRegion code{code_id, next_mem_start_, 1*1024*1024, pid,
                      MemoryType::NORMAL, MemoryPermission::READ_EXECUTE};
    next_mem_start_ += code.size;
    std::string data_id = "data_" + std::to_string(pid);
    MemoryRegion data{data_id, next_mem_start_, 4*1024*1024, pid,
                      MemoryType::NORMAL, MemoryPermission::READ_WRITE};
    next_mem_start_ += data.size;
    std::string stack_id = "stack_" + std::to_string(pid);
    MemoryRegion stack{stack_id, next_mem_start_, 2*1024*1024, pid,
                       MemoryType::NORMAL, MemoryPermission::READ_WRITE};
    next_mem_start_ += stack.size;
    memory_regions_[code.id] = code;
    memory_regions_[data.id] = data;
    memory_regions_[stack.id] = stack;
    process_memory_[pid] = {code.id, data.id, stack.id};
    {
        std::lock_guard<std::mutex> plock(proc_mutex_);
        processes_[pid].memory_usage = code.size + data.size + stack.size;
    }
}

} // namespace trinity
