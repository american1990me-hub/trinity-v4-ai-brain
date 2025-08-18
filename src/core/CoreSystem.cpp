#include "CoreSystem.hpp"
#include <iostream>

bool CoreSystem::initialize(const std::string &configPath, bool debug) {
    std::cout << "Initializing CoreSystem with config: " << configPath
              << " debug: " << std::boolalpha << debug << std::endl;
    return true;
}

void CoreSystem::run() {
    std::cout << "CoreSystem running..." << std::endl;
}
