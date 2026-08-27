#pragma once

#include <string>
#include <memory>
#include <vector>

namespace osiris {

// Basit seviyeli logger (bkz. doküman §5.1 — log ve izleme altyapısı)
enum class LogLevel {
    Debug = 0,
    Info = 1,
    Warn = 2,
    Error = 3
};

class Logger {
public:
    static Logger& instance();

    void set_level(LogLevel level);
    void debug(const std::string& msg);
    void info(const std::string& msg);
    void warn(const std::string& msg);
    void error(const std::string& msg);

private:
    Logger() = default;
    void log(LogLevel level, const std::string& msg);

    LogLevel level_ = LogLevel::Info;
};

}  // namespace osiris
