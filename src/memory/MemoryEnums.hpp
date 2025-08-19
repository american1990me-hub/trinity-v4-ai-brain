#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace trinity {

// Permissions for a region of memory. These can be combined as bit flags.
enum class MemoryPermission : std::uint8_t {
    NONE  = 0,
    READ  = 1 << 0,
    WRITE = 1 << 1,
    EXEC  = 1 << 2
};

// High level classification of memory usage.
enum class MemoryType {
    CODE = 0,
    DATA = 1,
    STACK = 2,
    HEAP = 3,
    SHARED = 4,
    OTHER = 5
};

// Continuous region of memory with associated metadata.
struct MemoryRegion {
    std::uintptr_t start = 0;      // Starting address
    std::uintptr_t end = 0;        // End address (exclusive)
    MemoryPermission permission = MemoryPermission::NONE;
    MemoryType type = MemoryType::OTHER;
};

// Logical grouping of memory regions such as a module or allocation.
struct MemorySegment {
    std::string name;                    // Identifier for the segment
    std::vector<MemoryRegion> regions;   // Regions belonging to this segment
};

} // namespace trinity

