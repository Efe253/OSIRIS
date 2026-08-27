#include "osiris/core.hpp"

#include <algorithm>
#include <map>
#include <mutex>
#include <thread>

#include "osiris/logger.hpp"

namespace osiris {

struct Core::Impl {
    std::map<std::string, std::unique_ptr<Plugin>> plugins;
    std::vector<Task> tasks;
    std::mutex mutex;
    bool running = false;
};

Core::Core() : impl_(std::make_unique<Impl>()) {
    Logger::instance().info("OSIRIS Core v" + std::string(kVersion) + " başlatıldı");
}

Core::~Core() {
    if (impl_->running) {
        stop_plugin("");
    }
}

bool Core::register_plugin(std::unique_ptr<Plugin> plugin) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    const auto id = plugin->id();
    if (impl_->plugins.contains(id)) {
        Logger::instance().warn("Plugin zaten kayıtlı: " + id);
        return false;
    }
    if (!plugin->load()) {
        Logger::instance().error("Plugin yüklenemedi: " + id);
        return false;
    }
    impl_->plugins[id] = std::move(plugin);
    Logger::instance().info("Plugin kaydedildi: " + id);
    return true;
}

bool Core::start_plugin(const std::string& id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->plugins.find(id);
    if (it == impl_->plugins.end()) {
        Logger::instance().warn("Plugin bulunamadı: " + id);
        return false;
    }
    return it->second->start();
}

bool Core::stop_plugin(const std::string& id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (id.empty()) {
        for (auto& [_, plugin] : impl_->plugins) {
            plugin->stop();
        }
        return true;
    }
    auto it = impl_->plugins.find(id);
    if (it == impl_->plugins.end()) {
        return false;
    }
    return it->second->stop();
}

void Core::schedule_task(const Task& task) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->tasks.push_back(task);
    Logger::instance().info("Görev zamanlandı: " + task.id);
}

void Core::run_scheduler() {
    impl_->running = true;
    Logger::instance().info("Zamanlayıcı başlatıldı");
    // Faz 1: temel zamanlayıcı döngüsü. Cron ayrıştırma Faz 2'de eklenecek.
    while (impl_->running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}

void Core::start_api_server(int port) {
    Logger::instance().info("REST API sunucusu port " + std::to_string(port) + " üzerinde başlatılıyor");
    // Faz 1: API sunucusu iskeleti. Tam uygulama osiris-api (Python) modülünde.
}

void Core::set_log_level(int level) {
    Logger::instance().set_level(static_cast<LogLevel>(level));
}

}  // namespace osiris
