# Tests configuration for agenkit-cpp

# Fetch Google Test
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG release-1.12.1
)

# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(googletest)

# Enable testing
enable_testing()

# Test helper utilities (if needed in future)
# add_library(test_utils STATIC test_utils.cpp)
# target_link_libraries(test_utils agenkit gtest)

# Message tests
add_executable(test_message test_message.cpp)
target_link_libraries(test_message agenkit gtest_main)
add_test(NAME message_tests COMMAND test_message)

# Agent tests
add_executable(test_agent test_agent.cpp)
target_link_libraries(test_agent agenkit gtest_main)
add_test(NAME agent_tests COMMAND test_agent)

# Error tests
add_executable(test_errors test_errors.cpp)
target_link_libraries(test_errors agenkit gtest_main)
add_test(NAME error_tests COMMAND test_errors)

# Result tests
add_executable(test_result test_result.cpp)
target_link_libraries(test_result agenkit gtest_main)
add_test(NAME result_tests COMMAND test_result)

# HTTP transport tests
add_executable(test_http_transport test_http_transport.cpp)
target_link_libraries(test_http_transport agenkit gtest_main)
add_test(NAME http_transport_tests COMMAND test_http_transport)

# Integration tests
add_executable(test_integration test_integration.cpp)
target_link_libraries(test_integration agenkit gtest_main)
add_test(NAME integration_tests COMMAND test_integration)

# Pattern tests - Reflection
add_executable(test_reflection patterns/test_reflection.cpp)
target_link_libraries(test_reflection agenkit gtest_main)
add_test(NAME reflection_tests COMMAND test_reflection)

# Pattern tests - ReAct
add_executable(test_react patterns/test_react.cpp)
target_link_libraries(test_react agenkit gtest_main)
add_test(NAME react_tests COMMAND test_react)

# Pattern tests - Agents-as-Tools
add_executable(test_agents_as_tools patterns/test_agents_as_tools.cpp)
target_link_libraries(test_agents_as_tools agenkit gtest_main)
add_test(NAME agents_as_tools_tests COMMAND test_agents_as_tools)

# Pattern tests - Orchestration
add_executable(test_orchestration patterns/test_orchestration.cpp)
target_link_libraries(test_orchestration agenkit gtest_main)
add_test(NAME orchestration_tests COMMAND test_orchestration)

# Pattern tests - Reasoning with Tools
add_executable(test_reasoning_with_tools patterns/test_reasoning_with_tools.cpp)
target_link_libraries(test_reasoning_with_tools agenkit gtest_main)
add_test(NAME reasoning_with_tools_tests COMMAND test_reasoning_with_tools)

# Pattern tests - Conversational
add_executable(test_conversational patterns/test_conversational.cpp)
target_link_libraries(test_conversational agenkit gtest_main)
add_test(NAME conversational_tests COMMAND test_conversational)

# Pattern tests - Task
add_executable(test_task patterns/test_task.cpp)
target_link_libraries(test_task agenkit gtest_main)
add_test(NAME task_tests COMMAND test_task)

# Pattern tests - Multiagent
add_executable(test_multiagent patterns/test_multiagent.cpp)
target_link_libraries(test_multiagent agenkit gtest_main)
add_test(NAME multiagent_tests COMMAND test_multiagent)

# Pattern tests - Planning
add_executable(test_planning patterns/test_planning.cpp)
target_link_libraries(test_planning agenkit gtest_main)
add_test(NAME planning_tests COMMAND test_planning)

# Pattern tests - Autonomous
add_executable(test_autonomous patterns/test_autonomous.cpp)
target_link_libraries(test_autonomous agenkit gtest_main)
add_test(NAME autonomous_tests COMMAND test_autonomous)

# Pattern tests - Memory
add_executable(test_memory patterns/test_memory.cpp)
target_link_libraries(test_memory agenkit gtest_main)
add_test(NAME memory_tests COMMAND test_memory)

# Pattern tests - Sequential
add_executable(test_sequential patterns/test_sequential.cpp)
target_link_libraries(test_sequential agenkit gtest_main)
add_test(NAME sequential_tests COMMAND test_sequential)

# Pattern tests - Parallel
add_executable(test_parallel patterns/test_parallel.cpp)
target_link_libraries(test_parallel agenkit gtest_main)
add_test(NAME parallel_tests COMMAND test_parallel)

# Pattern tests - Supervisor
add_executable(test_supervisor patterns/test_supervisor.cpp)
target_link_libraries(test_supervisor agenkit gtest_main)
add_test(NAME supervisor_tests COMMAND test_supervisor)

# Pattern tests - Router
add_executable(test_router patterns/test_router.cpp)
target_link_libraries(test_router agenkit gtest_main)
add_test(NAME router_tests COMMAND test_router)

# Pattern tests - Collaborative
add_executable(test_collaborative patterns/test_collaborative.cpp)
target_link_libraries(test_collaborative agenkit gtest_main)
add_test(NAME collaborative_tests COMMAND test_collaborative)

# Pattern tests - Human-in-Loop
add_executable(test_human_in_loop patterns/test_human_in_loop.cpp)
target_link_libraries(test_human_in_loop agenkit gtest_main)
add_test(NAME human_in_loop_tests COMMAND test_human_in_loop)

# Pattern tests - Fallback
add_executable(test_fallback patterns/test_fallback.cpp)
target_link_libraries(test_fallback agenkit gtest_main)
add_test(NAME fallback_tests COMMAND test_fallback)

# Adapter tests - LiteLLM
add_executable(test_litellm_adapter test_litellm_adapter.cpp)
target_link_libraries(test_litellm_adapter agenkit gtest_main)
add_test(NAME litellm_adapter_tests COMMAND test_litellm_adapter)

# Adapter tests - Gemini
add_executable(test_gemini_adapter test_gemini_adapter.cpp)
target_link_libraries(test_gemini_adapter agenkit gtest_main)
add_test(NAME gemini_adapter_tests COMMAND test_gemini_adapter)

# Adapter tests - Bedrock
add_executable(test_bedrock_adapter test_bedrock_adapter.cpp)
target_link_libraries(test_bedrock_adapter agenkit gtest_main)
add_test(NAME bedrock_adapter_tests COMMAND test_bedrock_adapter)

# Evaluation tests - Optimizer
add_executable(test_optimizer unit/test_optimizer.cpp)
target_link_libraries(test_optimizer agenkit gtest_main)
add_test(NAME optimizer_tests COMMAND test_optimizer)

# Evaluation tests - A/B Testing
add_executable(test_ab_testing unit/test_ab_testing.cpp)
target_link_libraries(test_ab_testing agenkit gtest_main)
add_test(NAME ab_testing_tests COMMAND test_ab_testing)

# Evaluation tests - Benchmarks
add_executable(test_benchmarks unit/test_benchmarks.cpp)
target_link_libraries(test_benchmarks agenkit gtest_main)
add_test(NAME benchmarks_tests COMMAND test_benchmarks)

# Evaluation tests - Bayesian Optimizer
add_executable(test_bayesian_optimizer unit/test_bayesian_optimizer.cpp)
target_link_libraries(test_bayesian_optimizer agenkit gtest_main)
add_test(NAME bayesian_optimizer_tests COMMAND test_bayesian_optimizer)

# Evaluation tests - Prompt Optimizer
add_executable(test_prompt_optimizer unit/test_prompt_optimizer.cpp)
target_link_libraries(test_prompt_optimizer agenkit gtest_main)
add_test(NAME prompt_optimizer_tests COMMAND test_prompt_optimizer)

# Cross-language test harness (standalone executable, not a gtest)
add_executable(cross_language_harness cross_language_harness.cpp)
target_link_libraries(cross_language_harness nlohmann_json::nlohmann_json)
# Copy to build directory for easy access
add_custom_command(TARGET cross_language_harness POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:cross_language_harness> ${CMAKE_BINARY_DIR}/cross_language_harness
)

# Integration tests (optional, requires -DAGENKIT_BUILD_INTEGRATION_TESTS=ON)
if(AGENKIT_BUILD_INTEGRATION_TESTS)
    add_subdirectory(integration)
endif()

# Enable verbose test output
set(CMAKE_CTEST_ARGUMENTS "--output-on-failure")
