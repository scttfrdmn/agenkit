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

# Enable verbose test output
set(CMAKE_CTEST_ARGUMENTS "--output-on-failure")
