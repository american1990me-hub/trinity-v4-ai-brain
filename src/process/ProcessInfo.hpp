#pragma once

#include <string>

#include "ProcessEnums.hpp"

namespace trinity {

// Basic information about a process.
struct ProcessInfo {
    int pid = 0;                 // Process identifier
    int parent_pid = 0;          // Parent process identifier
    std::string name;            // Human-readable name
    ProcessState state = ProcessState::NEW;
    ProcessPriority priority = ProcessPriority::NORMAL;
    SchedulingPolicy policy = SchedulingPolicy::FIFO;
};

} // namespace trinity

