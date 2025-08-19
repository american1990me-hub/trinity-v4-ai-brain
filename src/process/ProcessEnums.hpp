#pragma once

namespace trinity {

// Represents the lifecycle state of a process in the system.
enum class ProcessState {
    NEW = 0,       // Process has been created but not yet scheduled
    READY = 1,     // Ready to run and waiting for CPU time
    RUNNING = 2,   // Currently executing on the CPU
    BLOCKED = 3,   // Waiting on I/O or another resource
    TERMINATED = 4 // Finished execution
};

// Priority hint for the scheduler when deciding which process to run.
enum class ProcessPriority {
    LOW = 0,
    NORMAL = 1,
    HIGH = 2,
    CRITICAL = 3
};

// Scheduling policy the operating system uses for this process.
enum class SchedulingPolicy {
    FIFO = 0,        // First-in first-out
    ROUND_ROBIN = 1, // Time-sliced round robin
    PRIORITY = 2     // Priority based scheduling
};

} // namespace trinity

