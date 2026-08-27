#include "osiris/logger.hpp"

#include <chrono>
#include <ctime>
#include <iostream>
#include <mutex>

namespace osiris {

namespace {
std::mutex g_log_mutex;

std::string level_name(LogLevel level) {
    switch (level) {
        case LogLevel::Debug: return "DEBUG";
        case LogLevel::Info:  return "INFO";
        case LogLevel::Warn:  return "WARN";
        case LogLevel::Error: return "ERROR";
    }
    return "?";
}

std::string timestamp() {
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&t, &tm);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tm);
    return buf;
}
}  // namespace

Logger& Logger::instance() {
    static Logger logger;
    return logger;
}

void Logger::set_level(LogLevel level) {
    level_ = level;
}

void Logger::debug(const std::string& msg) { log(LogLevel::Debug, msg); }
void Logger::info(const std::string& msg)  { log(LogLevel::Info, msg); }
void Logger::warn(const std::string& msg)  { log(LogLevel::Warn, msg); }
void Logger::error(const std::string& msg) { log(LogLevel::Error, msg); }

void Logger::log(LogLevel level, const std::string& msg) {
    if (static_cast<int>(level) < static_cast<int>(level_)) {
        return;
    }
    std::lock_guard<std::mutex> lock(g_log_mutex);
    std::cout << "[" << timestamp() << "] [" << level_name(level) << "] " << msg << std::endl;
}

}  // namespace osiris
