#include "osiris/core.hpp"

#include <iostream>

#include "osiris/logger.hpp"

int main(int argc, char* argv[]) {
    osiris::Core core;

    if (argc > 1 && std::string(argv[1]) == "--version") {
        std::cout << "osiris-core " << osiris::kVersion << std::endl;
        return 0;
    }

    core.set_log_level(static_cast<int>(osiris::LogLevel::Info));
    core.start_api_server(8000);
    core.run_scheduler();
    return 0;
}
