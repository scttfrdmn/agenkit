cmake_minimum_required(VERSION 3.16)
project(agenkit VERSION 0.29.2 LANGUAGES CXX)

# C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(AGENKIT_BUILD_EXAMPLES "Build examples" ON)
option(AGENKIT_BUILD_TESTS "Build tests" ON)
option(AGENKIT_BUILD_INTEGRATION_TESTS "Build integration tests" OFF)
option(AGENKIT_BUILD_BENCHMARKS "Build benchmarks" ON)
option(AGENKIT_BUILD_SHARED "Build shared library" ON)
option(AGENKIT_HAS_AWS_SDK "Build with AWS SDK support for Bedrock adapter" OFF)

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

# Optional: AWS SDK for Bedrock adapter
if(AGENKIT_HAS_AWS_SDK)
    find_package(AWSSDK REQUIRED COMPONENTS bedrock-runtime)
    add_definitions(-DAGENKIT_HAS_AWS_SDK)
    message(STATUS "AWS SDK found - Bedrock adapter enabled")
else()
    message(STATUS "AWS SDK not found - Bedrock adapter will be stubbed")
endif()

# Library target
add_library(agenkit
    src/core/message.cpp
    src/core/errors.cpp
    src/adapters/echo_agent.cpp
    src/adapters/claude_agent.cpp
    src/adapters/ollama_agent.cpp
    src/adapters/openai_agent.cpp
    src/adapters/litellm_agent.cpp
    src/adapters/gemini_agent.cpp
    src/adapters/bedrock_agent.cpp
    src/transports/http_agent.cpp
    src/transports/http_server.cpp
    src/patterns/reflection.cpp
    src/patterns/react.cpp
    src/patterns/agents_as_tools.cpp
    src/patterns/orchestration.cpp
    src/patterns/reasoning_with_tools.cpp
    src/patterns/conversational.cpp
    src/patterns/task.cpp
    src/patterns/multiagent.cpp
    src/patterns/planning.cpp
    src/patterns/autonomous.cpp
    src/patterns/memory.cpp
    src/patterns/sequential.cpp
    src/patterns/parallel.cpp
    src/patterns/supervisor.cpp
    src/patterns/router.cpp
    src/patterns/collaborative.cpp
    src/patterns/human_in_loop.cpp
    src/patterns/fallback.cpp
    src/evaluation/metrics.cpp
    src/evaluation/recorder.cpp
    src/evaluation/regression.cpp
    src/evaluation/quality_metrics.cpp
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

# Link AWS SDK if available
if(AGENKIT_HAS_AWS_SDK)
    target_link_libraries(agenkit
        PRIVATE
            ${AWSSDK_LINK_LIBRARIES}
    )
endif()

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
message(STATUS "Build Integration Tests: ${AGENKIT_BUILD_INTEGRATION_TESTS}")
message(STATUS "Build Benchmarks: ${AGENKIT_BUILD_BENCHMARKS}")
message(STATUS "AWS SDK Support: ${AGENKIT_HAS_AWS_SDK}")
