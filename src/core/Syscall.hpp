#pragma once

#include <functional>
#include <unordered_map>
#include <vector>
#include <string>
#include <mutex>
#include <deque>
#include <optional>

#include "../ipc/IPCMessage.hpp"

namespace core {

enum class Syscall : int {
    ProcessCreate = 0,
    ProcessExit,
    IPCSend,
    IPCReceive,
};

struct SyscallResult {
    bool success;
    int value;
    std::string message;
    std::optional<ipc::IPCMessage> ipc_message;
};

class SyscallDispatcher {
public:
    using Handler = std::function<SyscallResult(const std::vector<std::string>&)>;

    SyscallDispatcher();
    SyscallResult invoke_syscall(Syscall call, const std::vector<std::string>& args);

private:
    SyscallResult _syscall_process_create(const std::vector<std::string>& args);
    SyscallResult _syscall_process_exit(const std::vector<std::string>& args);
    SyscallResult _syscall_ipc_send(const std::vector<std::string>& args);
    SyscallResult _syscall_ipc_receive(const std::vector<std::string>& args);

    struct ProcessInfo {
        int pid;
    };

    std::unordered_map<Syscall, Handler> handlers_;
    std::mutex dispatcher_mutex_;

    std::unordered_map<int, ProcessInfo> processes_;
    int next_pid_ = 1;
    std::mutex process_mutex_;

    std::unordered_map<int, std::deque<ipc::IPCMessage>> message_queues_;
    std::mutex message_mutex_;
};

} // namespace core

