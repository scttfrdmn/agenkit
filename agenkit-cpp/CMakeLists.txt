cmake_minimum_required(VERSION 3.16)
project(agenkit VERSION 0.48.0 LANGUAGES CXX)

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
option(AGENKIT_WITH_OBSERVABILITY "Build with OpenTelemetry observability support" ON)

# Dependencies
find_package(nlohmann_json 3.11.0 QUIET)

# If nlohmann_json not found, fetch it (useful for WASM builds)
if(NOT nlohmann_json_FOUND)
    message(STATUS "nlohmann_json not found, fetching from GitHub")
    include(FetchContent)
    FetchContent_Declare(
        nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG v3.11.3
    )
    FetchContent_MakeAvailable(nlohmann_json)
endif()

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

# Optional: OpenTelemetry for observability
if(AGENKIT_WITH_OBSERVABILITY)
    find_package(opentelemetry-cpp CONFIG)
    if(opentelemetry-cpp_FOUND)
        add_definitions(-DAGENKIT_WITH_OBSERVABILITY)
        message(STATUS "OpenTelemetry C++ SDK found - Observability enabled")
    else()
        message(WARNING "OpenTelemetry C++ SDK not found - Observability will be disabled. Install with: vcpkg install opentelemetry-cpp")
        set(AGENKIT_WITH_OBSERVABILITY OFF)
    endif()
else()
    message(STATUS "Observability disabled - enable with -DAGENKIT_WITH_OBSERVABILITY=ON")
endif()

# Library target
add_library(agenkit
    src/core/message.cpp
    src/core/errors.cpp
    src/adapters/echo_agent.cpp
    src/adapters/claude_agent.cpp
    src/adapters/ollama_agent.cpp
    src/adapters/openai_agent.cpp
    src/adapters/openai_compatible_agent.cpp
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
    src/evaluation/context_metrics.cpp
    src/evaluation/optimizer.cpp
    src/evaluation/ab_testing.cpp
    src/evaluation/benchmarks.cpp
    src/evaluation/bayesian_optimizer.cpp
    src/evaluation/prompt_optimizer.cpp
    src/techniques/reasoning/self_consistency.cpp
    src/techniques/reasoning/chain_of_thought.cpp
    src/techniques/reasoning/least_to_most.cpp
    src/techniques/reasoning/reasoning_tree.cpp
    src/techniques/reasoning/tree_of_thought.cpp
    src/infrastructure/validation.cpp
    src/infrastructure/permissions.cpp
    src/infrastructure/anomaly.cpp
    src/infrastructure/audit.cpp
    src/infrastructure/thread_pool.cpp
    src/infrastructure/memory/entry.cpp
    src/infrastructure/memory/working.cpp
    src/infrastructure/memory/short_term.cpp
    src/infrastructure/memory/long_term.cpp
    src/infrastructure/memory/hierarchy.cpp
    src/infrastructure/checkpointing/checkpoint.cpp
    src/infrastructure/checkpointing/storage.cpp
    src/infrastructure/checkpointing/manager.cpp
    src/infrastructure/budget/models.cpp
    src/infrastructure/budget/pricing.cpp
    src/infrastructure/budget/tracker.cpp
    src/middleware/retry.cpp
    src/middleware/timeout.cpp
    src/middleware/circuit_breaker.cpp
    src/middleware/rate_limiter.cpp
    src/middleware/per_user_rate_limiter.cpp
    src/middleware/caching.cpp
    src/middleware/batching.cpp
)

# Add observability sources if enabled
if(AGENKIT_WITH_OBSERVABILITY)
    target_sources(agenkit PRIVATE
        src/observability/tracing.cpp
        src/observability/metrics.cpp
        src/observability/logging.cpp
        src/observability/audit.cpp
    )
endif()

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

# Link OpenTelemetry if available
if(AGENKIT_WITH_OBSERVABILITY)
    target_link_libraries(agenkit
        PRIVATE
            opentelemetry-cpp::trace
            opentelemetry-cpp::metrics
            opentelemetry-cpp::otlp_http_exporter
            opentelemetry-cpp::ostream_span_exporter
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

# Documentation with Doxygen
find_package(Doxygen QUIET)
if(DOXYGEN_FOUND)
    set(DOXYGEN_IN ${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile)
    set(DOXYGEN_OUT ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile)

    # Copy Doxyfile to build directory
    configure_file(${DOXYGEN_IN} ${DOXYGEN_OUT} @ONLY)

    add_custom_target(docs
        COMMAND ${DOXYGEN_EXECUTABLE} ${DOXYGEN_OUT}
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "Generating API documentation with Doxygen"
        VERBATIM
    )

    message(STATUS "Doxygen found - 'docs' target available")
else()
    message(STATUS "Doxygen not found - documentation generation disabled")
endif()

message(STATUS "Agenkit C++ v${PROJECT_VERSION}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Build Examples: ${AGENKIT_BUILD_EXAMPLES}")
message(STATUS "Build Tests: ${AGENKIT_BUILD_TESTS}")
message(STATUS "Build Integration Tests: ${AGENKIT_BUILD_INTEGRATION_TESTS}")
message(STATUS "Build Benchmarks: ${AGENKIT_BUILD_BENCHMARKS}")
message(STATUS "AWS SDK Support: ${AGENKIT_HAS_AWS_SDK}")
