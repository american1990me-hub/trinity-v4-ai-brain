#pragma once

#include <string>

namespace ipc {

enum class IPCMessageType {
    Text,
    Binary,
};

struct IPCMessage {
    IPCMessageType type;
    std::string data;
};

} // namespace ipc

