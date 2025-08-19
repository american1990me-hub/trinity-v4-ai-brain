#include <cstddef>
#include <memory>

#include "memory/MemoryRegion.hpp"

namespace trinity {

class CoreSystem {
public:
    CoreSystem() = default;

    void _init_process_memory(std::size_t capacity) {
        region = std::make_unique<MemoryRegion>(capacity);
    }

    void* _syscall_memory_allocate(std::size_t size,
                                   MemoryPermission perm,
                                   MemoryType type) {
        if (!region) {
            return nullptr;
        }
        return region->allocate(size, perm, type).address;
    }

    void _syscall_memory_free(void* addr) {
        if (region) {
            region->free(addr);
        }
    }

private:
    std::unique_ptr<MemoryRegion> region;
};

} // namespace trinity
