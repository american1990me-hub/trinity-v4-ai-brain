#ifndef TRINITY_MEMORY_ENUMS_HPP
#define TRINITY_MEMORY_ENUMS_HPP

#include <string>
#include <unordered_map>
#include <cstdint>

namespace trinity {

// Memory access permissions
enum class MemoryPermission : std::uint8_t {
    NONE = 0,
    READ = 1,
    WRITE = 2,
    READ_WRITE = 3,
    EXECUTE = 4,
    READ_EXECUTE = 5,
    WRITE_EXECUTE = 6,
    READ_WRITE_EXECUTE = 7
};

// Memory types
enum class MemoryType {
    NORMAL,
    SHARED,
    LOCKED,
    HUGE,
    DEVICE
};

struct MemoryRegion {
    std::string id;
    std::uint64_t start{0};
    std::uint64_t size{0};
    int owner_pid{0};
    MemoryType memory_type{MemoryType::NORMAL};
    MemoryPermission permissions{MemoryPermission::READ_WRITE};
    std::string name;
    std::unordered_map<std::string, std::string> metadata;
    bool is_mapped{true};
    double created_at{0};
    double last_accessed{0};
};

struct MemorySegment {
    std::uint64_t start{0};
    std::uint64_t size{0};
    MemoryPermission permissions{MemoryPermission::READ_WRITE};
    std::string segment_type; // e.g., code, data, stack
};

} // namespace trinity

#endif // TRINITY_MEMORY_ENUMS_HPP
