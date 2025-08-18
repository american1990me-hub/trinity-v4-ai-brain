#pragma once

#include <cstdint>

namespace trinity {

/**
 * Enumeration describing available process information fields.
 * These values can be used to query or set attributes on a process.
 */
enum class ProcessInfo : std::uint8_t {
    PID,        ///< Unique process identifier
    PRIORITY,   ///< Scheduling priority
    STATE,      ///< Current state of the process
    NAME        ///< Human readable name
};

} // namespace trinity

