cmake_minimum_required(VERSION 3.20)
project(osiris-core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Bağımlılıklar
find_package(Threads REQUIRED)
find_package(OpenSSL REQUIRED)

# libcurl (HTTP/HTTPS, proxy desteği)
find_package(CURL REQUIRED)

# nlohmann/json (JSON işleme)
find_package(nlohmann_json QUIET)
if(NOT nlohmann_json_FOUND)
    message(STATUS "nlohmann_json bulunamadı, FetchContent ile indirilecek")
    include(FetchContent)
    FetchContent_Declare(nlohmann_json
        URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz)
    FetchContent_MakeAvailable(nlohmann_json)
endif()

# Kaynaklar
set(OSIRIS_CORE_SOURCES
    src/main.cpp
    src/core.cpp
    src/plugin.cpp
    src/task.cpp
    src/logger.cpp
)

add_executable(osiris-core ${OSIRIS_CORE_SOURCES})

target_include_directories(osiris-core PRIVATE include)

target_link_libraries(osiris-core PRIVATE
    Threads::Threads
    OpenSSL::SSL
    OpenSSL::Crypto
    CURL::libcurl
    nlohmann_json::nlohmann_json
)

target_compile_options(osiris-core PRIVATE -Wall -Wextra -Wpedantic)

install(TARGETS osiris-core RUNTIME DESTINATION bin)
