#include "Syscall.hpp"

#include <stdexcept>

namespace core {

SyscallDispatcher::SyscallDispatcher() {
    handlers_[Syscall::ProcessCreate] = [this](const auto& args) { return _syscall_process_create(args); };
    handlers_[Syscall::ProcessExit] = [this](const auto& args) { return _syscall_process_exit(args); };
    handlers_[Syscall::IPCSend] = [this](const auto& args) { return _syscall_ipc_send(args); };
    handlers_[Syscall::IPCReceive] = [this](const auto& args) { return _syscall_ipc_receive(args); };
}

SyscallResult SyscallDispatcher::invoke_syscall(Syscall call, const std::vector<std::string>& args) {
    std::lock_guard<std::mutex> lock(dispatcher_mutex_);
    auto it = handlers_.find(call);
    if (it == handlers_.end()) {
        return {false, -1, "unknown syscall", std::nullopt};
    }
    return it->second(args);
}

SyscallResult SyscallDispatcher::_syscall_process_create(const std::vector<std::string>& /*args*/) {
    std::lock_guard<std::mutex> lock(process_mutex_);
    int pid = next_pid_++;
    processes_.emplace(pid, ProcessInfo{pid});
    return {true, pid, "process created", std::nullopt};
}

SyscallResult SyscallDispatcher::_syscall_process_exit(const std::vector<std::string>& args) {
    if (args.empty()) {
        return {false, -1, "missing pid", std::nullopt};
    }
    int pid = std::stoi(args[0]);
    std::lock_guard<std::mutex> lock(process_mutex_);
    auto it = processes_.find(pid);
    if (it == processes_.end()) {
        return {false, -1, "process not found", std::nullopt};
    }
    processes_.erase(it);
    return {true, 0, "process exited", std::nullopt};
}

SyscallResult SyscallDispatcher::_syscall_ipc_send(const std::vector<std::string>& args) {
    if (args.size() < 3) {
        return {false, -1, "missing arguments", std::nullopt};
    }
    int target_pid = std::stoi(args[0]);
    ipc::IPCMessageType type = static_cast<ipc::IPCMessageType>(std::stoi(args[1]));
    std::string data = args[2];

    {
        std::lock_guard<std::mutex> lock(process_mutex_);
        if (processes_.find(target_pid) == processes_.end()) {
            return {false, -1, "target process not found", std::nullopt};
        }
    }

    {
        std::lock_guard<std::mutex> lock(message_mutex_);
        message_queues_[target_pid].push_back({type, data});
    }
    return {true, 0, "message sent", std::nullopt};
}

SyscallResult SyscallDispatcher::_syscall_ipc_receive(const std::vector<std::string>& args) {
    if (args.empty()) {
        return {false, -1, "missing pid", std::nullopt};
    }
    int pid = std::stoi(args[0]);
    std::lock_guard<std::mutex> lock(message_mutex_);
    auto q_it = message_queues_.find(pid);
    if (q_it == message_queues_.end() || q_it->second.empty()) {
        return {false, -1, "no message", std::nullopt};
    }
    ipc::IPCMessage msg = q_it->second.front();
    q_it->second.pop_front();
    return {true, 0, "message received", msg};
}

} // namespace core

