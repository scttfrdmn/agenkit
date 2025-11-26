cmake_minimum_required(VERSION 3.16)
project(agenkit VERSION 0.29.2 LANGUAGES CXX)

# C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(AGENKIT_BUILD_EXAMPLES "Build examples" ON)
option(AGENKIT_BUILD_TESTS "Build tests" ON)
option(AGENKIT_BUILD_BENCHMARKS "Build benchmarks" ON)
option(AGENKIT_BUILD_SHARED "Build shared library" ON)

# Dependencies
find_package(nlohmann_json 3.11.0 REQUIRED)
find_package(Threads REQUIRED)

# cpp-httplib (header-only HTTP library)
include(FetchContent)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.14.3
)
FetchContent_MakeAvailable(httplib)

# Library target
add_library(agenkit
    src/core/message.cpp
    src/core/errors.cpp
    src/adapters/echo_agent.cpp
    src/transports/http_agent.cpp
    src/transports/http_server.cpp
)

target_include_directories(agenkit
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(agenkit
    PUBLIC
        nlohmann_json::nlohmann_json
    PRIVATE
        Threads::Threads
        httplib::httplib
)

# Compiler warnings
if(MSVC)
    target_compile_options(agenkit PRIVATE /W4 /WX)
else()
    target_compile_options(agenkit PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# Examples
if(AGENKIT_BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Tests
if(AGENKIT_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Benchmarks
if(AGENKIT_BUILD_BENCHMARKS)
    add_subdirectory(benchmarks)
endif()

# Install rules (placeholder)
# install(TARGETS agenkit
#     EXPORT agenkitTargets
#     LIBRARY DESTINATION lib
#     ARCHIVE DESTINATION lib
#     RUNTIME DESTINATION bin
#     INCLUDES DESTINATION include
# )

# install(DIRECTORY include/
#     DESTINATION include
# )

message(STATUS "Agenkit C++ v${PROJECT_VERSION}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Build Examples: ${AGENKIT_BUILD_EXAMPLES}")
message(STATUS "Build Tests: ${AGENKIT_BUILD_TESTS}")
message(STATUS "Build Benchmarks: ${AGENKIT_BUILD_BENCHMARKS}")
