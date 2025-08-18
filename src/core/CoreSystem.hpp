#pragma once

#include <string>

class CoreSystem {
public:
    bool initialize(const std::string &configPath, bool debug);
    void run();
};
