#include "core/CoreSystem.h"
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    bool debug = false;
    std::string config;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--debug") {
            debug = true;
        } else if (arg == "--config" && i + 1 < argc) {
            config = argv[++i];
        } else if (arg == "--help") {
            std::cout << "Usage: " << argv[0]
                      << " [--config <file>] [--debug]" << std::endl;
            return 0;
        }
    }

    CoreSystem system;
    return system.run();
}
