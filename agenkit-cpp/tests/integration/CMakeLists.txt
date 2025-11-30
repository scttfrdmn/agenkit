# Integration tests for agenkit-cpp
#
# These tests verify real functionality including:
# - Adapter integration with external services
# - Pattern composition and execution
# - Evaluation framework
# - Core functionality
# - Cross-language compatibility
#
# Some tests require external services or API keys:
# - OPENAI_API_KEY for OpenAI tests
# - ANTHROPIC_API_KEY for Claude tests
# - Ollama service running locally for Ollama tests
#
# Build with: cmake -DAGENKIT_BUILD_INTEGRATION_TESTS=ON ..

# Adapter integration tests
add_executable(test_integration_adapters test_adapters.cpp)
target_link_libraries(test_integration_adapters agenkit gtest_main)
add_test(NAME integration_adapters COMMAND test_integration_adapters)

# Pattern integration tests
add_executable(test_integration_patterns test_patterns.cpp)
target_link_libraries(test_integration_patterns agenkit gtest_main)
add_test(NAME integration_patterns COMMAND test_integration_patterns)

# Evaluation integration tests
add_executable(test_integration_evaluation test_evaluation.cpp)
target_link_libraries(test_integration_evaluation agenkit gtest_main)
add_test(NAME integration_evaluation COMMAND test_integration_evaluation)

# Core functionality integration tests
add_executable(test_integration_core test_core.cpp)
target_link_libraries(test_integration_core agenkit gtest_main)
add_test(NAME integration_core COMMAND test_integration_core)

# Cross-language compatibility tests
add_executable(test_integration_cross_language test_cross_language.cpp)
target_link_libraries(test_integration_cross_language agenkit gtest_main)
add_test(NAME integration_cross_language COMMAND test_integration_cross_language)

# Set test properties
set_tests_properties(
    integration_adapters
    integration_patterns
    integration_evaluation
    integration_core
    integration_cross_language
    PROPERTIES
        LABELS "integration"
        TIMEOUT 60
)

# Set environment variables for tests
# Note: These can be overridden at runtime
set_tests_properties(integration_adapters PROPERTIES
    ENVIRONMENT "SKIP_OLLAMA_TESTS=0"
)

message(STATUS "Integration tests configured")
message(STATUS "  - Adapter tests: test_integration_adapters")
message(STATUS "  - Pattern tests: test_integration_patterns")
message(STATUS "  - Evaluation tests: test_integration_evaluation")
message(STATUS "  - Core tests: test_integration_core")
message(STATUS "  - Cross-language tests: test_integration_cross_language")
message(STATUS "")
message(STATUS "Note: Some tests require API keys or services:")
message(STATUS "  - Set OPENAI_API_KEY for OpenAI tests")
message(STATUS "  - Set ANTHROPIC_API_KEY for Claude tests")
message(STATUS "  - Run Ollama locally for Ollama tests (or set SKIP_OLLAMA_TESTS=1)")
