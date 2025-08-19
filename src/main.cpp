#include <iostream>
#include <string>

#include "core/CoreSystem.hpp"

int main(int argc, char** argv) {
    trinity::CoreSystem core;
    if (!core.initialize()) {
        std::cerr << "Failed to initialize CoreSystem" << std::endl;
        return 1;
    }
    if (!core.start()) {
        std::cerr << "Failed to start CoreSystem" << std::endl;
        return 1;
    }
    std::cout << "Trinity CoreSystem started" << std::endl;
    int pid = core.createProcess("test_process");
    std::cout << "Created process with pid " << pid << std::endl;
    std::string region = core.allocateMemory(pid, 1024 * 1024);
    std::cout << "Allocated memory region " << region << std::endl;
    const trinity::ProcessInfo* info = core.getProcess(pid);
    if (info) {
        std::cout << "Process memory usage: " << info->memory_usage << std::endl;
    }
    core.stop();
    return 0;
}
