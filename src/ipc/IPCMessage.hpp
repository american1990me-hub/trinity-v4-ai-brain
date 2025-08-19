#pragma once

#include <string>

// Enum describing the type of the IPC message.
enum class IPCMessageType {
    None = 0,
    Text,
    Binary,
};

// Basic IPC message used by the core system. Each message stores the
// sender of the message, the type and the textual payload. The payload is
// intentionally kept as a string so that higher level layers can encode any
// arbitrary data (JSON, binary encoded etc.) if desired.
struct IPCMessage {
    int senderPid{0};        // process id of the sender
    IPCMessageType type{IPCMessageType::None};
    std::string payload;     // contents of the message
};

