#include "osiris/core.hpp"

#include <atomic>
#include <csignal>
#include <iostream>

#include "osiris/logger.hpp"

namespace {
std::atomic<osiris::Core*> g_core{nullptr};

void handle_signal(int) {
    if (auto* core = g_core.load()) {
        core->stop_scheduler();
    }
}
}  // namespace

int main(int argc, char* argv[]) {
    osiris::Core core;

    if (argc > 1 && std::string(argv[1]) == "--version") {
        std::cout << "osiris-core " << osiris::kVersion << std::endl;
        return 0;
    }

    g_core.store(&core);
    std::signal(SIGINT, handle_signal);
    std::signal(SIGTERM, handle_signal);
    core.set_log_level(static_cast<int>(osiris::LogLevel::Info));
    core.start_api_server(8000);
    core.run_scheduler();
    g_core.store(nullptr);
    return 0;
}
