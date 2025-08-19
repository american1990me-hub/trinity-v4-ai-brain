#ifndef TRINITY_PROCESS_ENUMS_HPP
#define TRINITY_PROCESS_ENUMS_HPP

#include <cstdint>

namespace trinity {

// Process states
enum class ProcessState {
    CREATED,
    READY,
    RUNNING,
    BLOCKED,
    SUSPENDED,
    TERMINATED,
    ZOMBIE
};

// Process priority levels
enum class ProcessPriority : std::uint8_t {
    IDLE = 0,
    LOW = 10,
    NORMAL = 20,
    HIGH = 30,
    REAL_TIME = 40,
    SYSTEM = 50
};

// Scheduling policies
enum class SchedulingPolicy {
    ROUND_ROBIN,
    FIFO,
    PRIORITY,
    DEADLINE,
    FAIR
};

} // namespace trinity

#endif // TRINITY_PROCESS_ENUMS_HPP
