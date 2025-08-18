#pragma once

namespace trinity {

/**
 * Enumeration of possible states a process can be in.
 */
enum class ProcessState {
    NEW,      ///< Process has been created but not yet scheduled.
    READY,    ///< Process is ready to run.
    RUNNING,  ///< Process is currently executing.
    WAITING,  ///< Process is waiting on I/O or another event.
    TERMINATED ///< Process has finished execution.
};

} // namespace trinity

