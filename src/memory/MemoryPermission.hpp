#pragma once
#include <cstdint>

namespace trinity {

enum class MemoryPermission : std::uint8_t {
    NONE   = 0,
    READ   = 1 << 0,
    WRITE  = 1 << 1,
    EXEC   = 1 << 2
};

inline MemoryPermission operator|(MemoryPermission lhs, MemoryPermission rhs) {
    return static_cast<MemoryPermission>(static_cast<std::uint8_t>(lhs) |
                                         static_cast<std::uint8_t>(rhs));
}

inline MemoryPermission operator&(MemoryPermission lhs, MemoryPermission rhs) {
    return static_cast<MemoryPermission>(static_cast<std::uint8_t>(lhs) &
                                         static_cast<std::uint8_t>(rhs));
}

inline MemoryPermission operator~(MemoryPermission perm) {
    return static_cast<MemoryPermission>(~static_cast<std::uint8_t>(perm));
}

inline MemoryPermission& operator|=(MemoryPermission& lhs, MemoryPermission rhs) {
    lhs = lhs | rhs;
    return lhs;
}

inline MemoryPermission& operator&=(MemoryPermission& lhs, MemoryPermission rhs) {
    lhs = lhs & rhs;
    return lhs;
}

inline bool has_permission(MemoryPermission value, MemoryPermission perm) {
    return static_cast<std::uint8_t>(value & perm) != 0;
}

}
