#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace osiris {

// OSIRIS sürümü
inline constexpr const char* kVersion = "0.1.0";

// Plugin durumları
enum class PluginState {
    Loaded,
    Running,
    Stopped,
    Failed
};

// Plugin arayüzü — her veri kaynağı bir plugin'tir (bkz. doküman §12)
class Plugin {
public:
    virtual ~Plugin() = default;

    virtual std::string id() const = 0;
    virtual std::string name() const = 0;
    virtual std::string version() const = 0;
    virtual std::string network_type() const = 0;

    virtual bool load() = 0;
    virtual bool start() = 0;
    virtual bool stop() = 0;
    virtual bool health_check() = 0;

    PluginState state() const { return state_; }

protected:
    PluginState state_ = PluginState::Loaded;
};

// Zamanlanmış görev (bkz. doküman §5.1)
struct Task {
    std::string id;
    std::string plugin_id;
    std::string schedule;   // Cron ifadesi
    int priority = 5;
    bool enabled = true;
    std::uint64_t last_run_at = 0;
};

// Core Engine — merkezi koordinatör
class Core {
public:
    Core();
    ~Core();

    // Plugin yaşam döngüsü
    bool register_plugin(std::unique_ptr<Plugin> plugin);
    bool start_plugin(const std::string& id);
    bool stop_plugin(const std::string& id);

    // Görev yönetimi
    void schedule_task(const Task& task);
    void run_scheduler();

    // REST API sunucusu (iç ve dış arayüzler için)
    void start_api_server(int port);

    // Log ve izleme
    void set_log_level(int level);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace osiris
