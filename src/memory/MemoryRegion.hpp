#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

#include "MemoryPermission.hpp"
#include "MemoryType.hpp"

namespace trinity {

struct MemorySegment {
    void* address{nullptr};
    std::size_t size{0};
    MemoryPermission permission{MemoryPermission::NONE};
    MemoryType type{MemoryType::UNKNOWN};
};

class MemoryRegion {
public:
    explicit MemoryRegion(std::size_t capacity = 0)
        : m_base(nullptr), m_capacity(capacity), m_used(0) {
        if (m_capacity) {
            m_base = new std::uint8_t[m_capacity];
        }
    }

    ~MemoryRegion() { delete[] m_base; }

    MemoryRegion(MemoryRegion&& other) noexcept
        : m_base(other.m_base), m_capacity(other.m_capacity), m_used(other.m_used),
          m_segments(std::move(other.m_segments)) {
        other.m_base = nullptr;
        other.m_capacity = other.m_used = 0;
    }

    MemoryRegion& operator=(MemoryRegion&& other) noexcept {
        if (this != &other) {
            delete[] m_base;
            m_base = other.m_base;
            m_capacity = other.m_capacity;
            m_used = other.m_used;
            m_segments = std::move(other.m_segments);
            other.m_base = nullptr;
            other.m_capacity = other.m_used = 0;
        }
        return *this;
    }

    MemoryRegion(const MemoryRegion&) = delete;
    MemoryRegion& operator=(const MemoryRegion&) = delete;

    MemorySegment allocate(std::size_t size,
                           MemoryPermission perm = MemoryPermission::READ | MemoryPermission::WRITE,
                           MemoryType type = MemoryType::HEAP) {
        if (!m_base || size == 0 || m_used + size > m_capacity) {
            return {};
        }
        void* addr = m_base + m_used;
        m_used += size;
        MemorySegment seg{addr, size, perm, type};
        m_segments.push_back(seg);
        return seg;
    }

    bool free(void* address) {
        auto it = std::find_if(m_segments.begin(), m_segments.end(),
                               [address](const MemorySegment& seg) { return seg.address == address; });
        if (it == m_segments.end()) {
            return false;
        }
        if (std::next(it) == m_segments.end()) {
            m_used -= it->size; // reclaim only if last segment
        }
        m_segments.erase(it);
        return true;
    }

    std::size_t capacity() const { return m_capacity; }
    std::size_t used() const { return m_used; }
    const std::vector<MemorySegment>& segments() const { return m_segments; }

private:
    std::uint8_t* m_base;
    std::size_t m_capacity;
    std::size_t m_used;
    std::vector<MemorySegment> m_segments;
};

} // namespace trinity
