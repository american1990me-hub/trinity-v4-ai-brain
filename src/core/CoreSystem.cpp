#include "CoreSystem.hpp"

#include <chrono>
#include <thread>

CoreSystem::CoreSystem()
    : m_kernel_mem_size(0), m_shared_mem_size(0), m_running(false) {}

CoreSystem::~CoreSystem() {
    stop();
}

void CoreSystem::initialize() {
    std::lock_guard<std::mutex> lock(m_mutex);
    _detect_capabilities();
    _init_memory();
}

void CoreSystem::start() {
    std::lock_guard<std::mutex> lock(m_mutex);
    if (m_running)
        return;
    m_running = true;
    m_scheduler_thread = std::thread(&CoreSystem::_scheduler_loop, this);
}

void CoreSystem::stop() {
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (!m_running)
            return;
        m_running = false;
    }
    if (m_scheduler_thread.joinable())
        m_scheduler_thread.join();
}

void CoreSystem::_scheduler_loop() {
    while (true) {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (!m_running)
                break;
            if (!m_ready_queue.empty()) {
                int pid = m_ready_queue.front();
                m_ready_queue.pop_front();
                // Simulate processing of the PID
                m_ready_queue.push_back(pid);
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void CoreSystem::_detect_capabilities() {
    // Placeholder capabilities detection
    m_kernel_mem_size = 1024;  // 1 KB kernel memory
    m_shared_mem_size = 2048;  // 2 KB shared memory
}

void CoreSystem::_init_memory() {
    m_kernel_memory.assign(m_kernel_mem_size, 0);
    m_shared_memory.assign(m_shared_mem_size, 0);
}

