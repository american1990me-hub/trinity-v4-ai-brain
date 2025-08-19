#pragma once

#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

class CoreSystem {
public:
    CoreSystem();
    ~CoreSystem();

    void initialize();
    void start();
    void stop();

private:
    void _scheduler_loop();
    void _detect_capabilities();
    void _init_memory();

    std::unordered_map<int, std::string> m_process_table;
    std::unordered_map<int, std::function<void()>> m_syscall_registry;
    std::unordered_map<int, std::deque<std::string>> m_ipc_queues;
    std::deque<int> m_ready_queue;

    std::vector<std::uint8_t> m_kernel_memory;
    std::vector<std::uint8_t> m_shared_memory;

    std::size_t m_kernel_mem_size;
    std::size_t m_shared_mem_size;

    std::thread m_scheduler_thread;
    std::mutex m_mutex;
    bool m_running;
};

