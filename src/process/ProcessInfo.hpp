#ifndef TRINITY_PROCESS_INFO_HPP
#define TRINITY_PROCESS_INFO_HPP

#include <string>
#include <vector>
#include <unordered_set>
#include <unordered_map>
#include <chrono>

#include "ProcessEnums.hpp"

namespace trinity {

struct ProcessInfo {
    int process_id;
    int parent_id;
    std::string name;
    ProcessState state;
    ProcessPriority priority;
    SchedulingPolicy policy;
    std::vector<int> cpu_affinity;
    double creation_time; // seconds since epoch
    double start_time{0};
    double runtime{0};
    double deadline{0};
    double time_slice{0.01};
    double weight{1.0};
    double quantum_used{0};
    double last_run{0};
    int context_switches{0};
    std::size_t memory_usage{0};
    std::unordered_set<int> file_descriptors;
    std::unordered_map<std::string, std::string> metadata;
};

struct ProcessContext {
    std::unordered_map<std::string, int> registers;
    int stack_pointer{0};
    int program_counter{0};
    std::vector<int> stack;
    std::unordered_map<std::string, std::pair<int, int>> memory_segments;
};

} // namespace trinity

#endif // TRINITY_PROCESS_INFO_HPP
