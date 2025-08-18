#include "core/CoreSystem.hpp"
#include <iostream>
#include <string>

int main(int argc, char **argv) {
    std::string configPath;
    bool debug = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if ((arg == "-c" || arg == "--config") && i + 1 < argc) {
            configPath = argv[++i];
        } else if (arg == "--debug") {
            debug = true;
        } else if (arg == "-h" || arg == "--help") {
            std::cout << "Usage: " << argv[0]
                      << " [--config <path>] [--debug]" << std::endl;
            return 0;
        }
    }

    CoreSystem core;
    if (!core.initialize(configPath, debug)) {
        std::cerr << "Failed to initialize CoreSystem" << std::endl;
        return 1;
    }
    core.run();
    return 0;
}
