#pragma once

#include <condition_variable>
#include <deque>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <unordered_map>

#include "process/ProcessState.hpp"

namespace trinity {

/**
 * Basic representation of a process in the system. Each process contains an
 * identifier, its current state and the task to execute when scheduled.
 */
struct Process {
    int pid{0};
    int priority{0};
    ProcessState state{ProcessState::NEW};
    std::string name;
    std::function<void()> task; // Work the process should perform
};

/**
 * CoreSystem provides a tiny cooperative scheduler. Processes can be added to
 * a ready queue and will be executed sequentially by a background thread.
 */
class CoreSystem {
public:
    CoreSystem();
    ~CoreSystem();

    /** Initialize system resources. */
    void initialize();

    /** Start the scheduler thread. */
    void start();

    /** Stop the scheduler thread and wait for completion. */
    void stop();

    /**
     * Add a new process to the ready queue.
     * @param task     Work the process should perform
     * @param priority Larger values run sooner
     * @param name     Human readable name for diagnostics
     */
    void addProcess(std::function<void()> task, int priority = 0, std::string name = "");

    /** Query the state of a process by PID. */
    std::optional<ProcessState> getProcessState(int pid) const;

private:
    /** Scheduler loop executed on a dedicated thread. */
    void schedulerLoop();

    std::deque<Process> readyQueue_;   ///< Queue of processes awaiting execution.
    std::thread schedulerThread_;      ///< Thread running the scheduler.
    mutable std::mutex queueMutex_;    ///< Protects access to the ready queue.
    std::condition_variable cv_;       ///< Notifies scheduler of new work.
    bool running_{false};              ///< Indicates if the scheduler is active.
    int nextPid_{1};                   ///< Simple PID generator.
    std::unordered_map<int, ProcessState> processStates_; ///< Tracks state by PID.
};

} // namespace trinity

