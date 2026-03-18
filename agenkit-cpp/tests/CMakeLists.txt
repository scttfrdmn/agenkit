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

# Fetch RapidCheck (property-based testing)
# GIT_SUBMODULES "" prevents cloning ext/googletest since we already have it
FetchContent_Declare(
    rapidcheck
    GIT_REPOSITORY https://github.com/emil-e/rapidcheck.git
    GIT_TAG        master
    GIT_SUBMODULES ""
)
set(RC_ENABLE_GTEST ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(rapidcheck)

# Enable testing
enable_testing()

# Test utilities tests
add_executable(test_test_utils test_test_utils.cpp)
target_link_libraries(test_test_utils agenkit gtest_main)
add_test(NAME test_utils_tests COMMAND test_test_utils)

# Message tests
add_executable(test_message test_message.cpp)
target_link_libraries(test_message agenkit gtest_main)
add_test(NAME message_tests COMMAND test_message)

# Cross-language message serialization tests
add_executable(test_cross_language_message_serialization test_cross_language_message_serialization.cpp)
target_link_libraries(test_cross_language_message_serialization agenkit gtest_main)
add_test(NAME cross_language_message_serialization_tests COMMAND test_cross_language_message_serialization WORKING_DIRECTORY ${CMAKE_BINARY_DIR})

# Cross-language API consistency tests
add_executable(test_cross_language_api_consistency cross_language_api_consistency_test.cpp)
target_link_libraries(test_cross_language_api_consistency agenkit gtest_main)
add_test(NAME cross_language_api_consistency_tests COMMAND test_cross_language_api_consistency)

# Cross-language retry behavior tests
add_executable(test_cross_language_retry_behavior cross_language_retry_behavior_test.cpp)
target_link_libraries(test_cross_language_retry_behavior agenkit gtest_main)
add_test(NAME cross_language_retry_behavior_tests COMMAND test_cross_language_retry_behavior)

# Cross-language timeout behavior tests
add_executable(test_cross_language_timeout_behavior cross_language_timeout_behavior_test.cpp)
target_link_libraries(test_cross_language_timeout_behavior agenkit gtest_main)
add_test(NAME cross_language_timeout_behavior_tests COMMAND test_cross_language_timeout_behavior)

# Cross-language circuit breaker behavior tests
add_executable(test_cross_language_circuit_breaker_behavior cross_language_circuit_breaker_behavior_test.cpp)
target_link_libraries(test_cross_language_circuit_breaker_behavior agenkit gtest_main)
add_test(NAME cross_language_circuit_breaker_behavior_tests COMMAND test_cross_language_circuit_breaker_behavior)

# Cross-language rate limiter behavior tests
add_executable(test_cross_language_rate_limiter_behavior cross_language_rate_limiter_behavior_test.cpp)
target_link_libraries(test_cross_language_rate_limiter_behavior agenkit gtest_main)
add_test(NAME cross_language_rate_limiter_behavior_tests COMMAND test_cross_language_rate_limiter_behavior)

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

# LLM validation tests
add_executable(test_llm_validation test_llm_validation.cpp)
target_link_libraries(test_llm_validation agenkit gtest_main)
add_test(NAME llm_validation_tests COMMAND test_llm_validation)

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

# Adapter tests - OpenAI-Compatible
add_executable(test_openai_compatible_adapter test_openai_compatible_adapter.cpp)
target_link_libraries(test_openai_compatible_adapter agenkit gtest_main)
add_test(NAME openai_compatible_adapter_tests COMMAND test_openai_compatible_adapter)

# Validation tests - LLM parameter validation
add_executable(test_validation test_validation.cpp)
target_link_libraries(test_validation agenkit gtest_main)
add_test(NAME validation_tests COMMAND test_validation)

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

# Technique tests - Chain-of-Thought
add_executable(test_chain_of_thought techniques/reasoning/test_chain_of_thought.cpp)
target_link_libraries(test_chain_of_thought agenkit gtest_main)
add_test(NAME chain_of_thought_tests COMMAND test_chain_of_thought)

# Technique tests - Least-to-Most
add_executable(test_least_to_most techniques/reasoning/test_least_to_most.cpp)
target_link_libraries(test_least_to_most agenkit gtest_main)
add_test(NAME least_to_most_tests COMMAND test_least_to_most)

# Technique tests - Tree-of-Thought
add_executable(test_tree_of_thought techniques/reasoning/test_tree_of_thought.cpp)
target_link_libraries(test_tree_of_thought agenkit gtest_main)
add_test(NAME tree_of_thought_tests COMMAND test_tree_of_thought)

# Technique tests - Plan-and-Solve
add_executable(test_plan_and_solve techniques/reasoning/test_plan_and_solve.cpp)
target_link_libraries(test_plan_and_solve agenkit gtest_main)
add_test(NAME plan_and_solve_tests COMMAND test_plan_and_solve)

# Technique tests - Graph-of-Thought
add_executable(test_graph_of_thought techniques/reasoning/test_graph_of_thought.cpp)
target_link_libraries(test_graph_of_thought agenkit gtest_main)
add_test(NAME graph_of_thought_tests COMMAND test_graph_of_thought)

# Technique tests - Self-Consistency
add_executable(test_self_consistency techniques/reasoning/test_self_consistency.cpp)
target_link_libraries(test_self_consistency agenkit gtest_main)
add_test(NAME self_consistency_tests COMMAND test_self_consistency)

# Adapter tests - Claude
add_executable(test_claude_adapter test_claude_adapter.cpp)
target_link_libraries(test_claude_adapter agenkit gtest_main)
add_test(NAME claude_adapter_tests COMMAND test_claude_adapter)

# Adapter tests - OpenAI
add_executable(test_openai_adapter test_openai_adapter.cpp)
target_link_libraries(test_openai_adapter agenkit gtest_main)
add_test(NAME openai_adapter_tests COMMAND test_openai_adapter)

# Infrastructure tests - Safety
add_executable(test_safety infrastructure/test_safety.cpp)
target_link_libraries(test_safety agenkit gtest_main)
add_test(NAME safety_tests COMMAND test_safety)

# Infrastructure tests - Memory
add_executable(test_memory_infra infrastructure/test_memory.cpp)
target_link_libraries(test_memory_infra agenkit gtest_main)
add_test(NAME memory_infrastructure_tests COMMAND test_memory_infra)

# Infrastructure tests - Object Pool
add_executable(test_object_pool infrastructure/test_object_pool.cpp)
target_link_libraries(test_object_pool agenkit gtest_main)
add_test(NAME object_pool_tests COMMAND test_object_pool)

# Infrastructure tests - Thread Pool
add_executable(test_thread_pool infrastructure/test_thread_pool.cpp)
target_link_libraries(test_thread_pool agenkit gtest_main)
add_test(NAME thread_pool_tests COMMAND test_thread_pool)

# Utils tests - SIMD
add_executable(test_simd utils/test_simd.cpp)
target_link_libraries(test_simd agenkit gtest_main)
add_test(NAME simd_tests COMMAND test_simd)

# Infrastructure tests - Checkpointing
add_executable(test_checkpointing infrastructure/test_checkpointing.cpp)
target_link_libraries(test_checkpointing agenkit gtest_main)
add_test(NAME checkpointing_tests COMMAND test_checkpointing)

# Infrastructure tests - Budget
add_executable(test_budget infrastructure/test_budget.cpp)
target_link_libraries(test_budget agenkit gtest_main)
add_test(NAME budget_tests COMMAND test_budget)

# Infrastructure tests - Middleware
add_executable(test_middleware infrastructure/test_middleware.cpp)
target_link_libraries(test_middleware agenkit gtest_main)
add_test(NAME middleware_tests COMMAND test_middleware)

# Middleware tests - Batching
add_executable(test_batching middleware/test_batching.cpp)
target_link_libraries(test_batching agenkit gtest_main)
add_test(NAME batching_middleware_tests COMMAND test_batching)

# Property tests - Message invariants
add_executable(test_message_properties property/message_properties_test.cpp)
target_link_libraries(test_message_properties agenkit rapidcheck rapidcheck_gtest gtest_main)
add_test(NAME message_property_tests COMMAND test_message_properties)

# Property tests - Agent response invariants
add_executable(test_agent_properties property/agent_properties_test.cpp)
target_link_libraries(test_agent_properties agenkit rapidcheck rapidcheck_gtest gtest_main)
add_test(NAME agent_property_tests COMMAND test_agent_properties)

# Property tests - Middleware behavior invariants
add_executable(test_middleware_properties property/middleware_properties_test.cpp)
target_link_libraries(test_middleware_properties agenkit rapidcheck rapidcheck_gtest gtest_main)
add_test(NAME middleware_property_tests COMMAND test_middleware_properties)

# Technique tests - ReasoningTree data structure
add_executable(test_reasoning_tree techniques/reasoning/test_reasoning_tree.cpp)
target_link_libraries(test_reasoning_tree agenkit gtest_main)
add_test(NAME reasoning_tree_tests COMMAND test_reasoning_tree)

# Technique tests - ReasoningGraph data structure
add_executable(test_reasoning_graph techniques/reasoning/test_reasoning_graph.cpp)
target_link_libraries(test_reasoning_graph agenkit gtest_main)
add_test(NAME reasoning_graph_tests COMMAND test_reasoning_graph)

# MCP protocol tests
add_executable(test_mcp test_mcp.cpp)
target_link_libraries(test_mcp agenkit GTest::gtest_main)
target_include_directories(test_mcp PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME mcp_tests COMMAND test_mcp)

# Cross-language test harness (standalone executable, not a gtest)
add_executable(cross_language_harness cross_language_harness.cpp)
target_link_libraries(cross_language_harness nlohmann_json::nlohmann_json)
# Copy to build directory for easy access
add_custom_command(TARGET cross_language_harness POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:cross_language_harness> ${CMAKE_BINARY_DIR}/cross_language_harness
)

# Observability tests (optional, requires OpenTelemetry)
if(AGENKIT_WITH_OBSERVABILITY)
    add_executable(test_observability_tracing observability/test_tracing.cpp)
    target_link_libraries(test_observability_tracing agenkit gtest_main)
    add_test(NAME observability_tracing_tests COMMAND test_observability_tracing)

    add_executable(test_observability_metrics observability/test_metrics.cpp)
    target_link_libraries(test_observability_metrics agenkit gtest_main)
    add_test(NAME observability_metrics_tests COMMAND test_observability_metrics)

    add_executable(test_observability_logging observability/test_logging.cpp)
    target_link_libraries(test_observability_logging agenkit gtest_main)
    add_test(NAME observability_logging_tests COMMAND test_observability_logging)

    add_executable(test_observability_audit observability/test_audit.cpp)
    target_link_libraries(test_observability_audit agenkit gtest_main)
    add_test(NAME observability_audit_tests COMMAND test_observability_audit)

    add_executable(test_observability_integration observability/test_integration.cpp)
    target_link_libraries(test_observability_integration agenkit gtest_main)
    add_test(NAME observability_integration_tests COMMAND test_observability_integration)
endif()

# Integration tests (optional, requires -DAGENKIT_BUILD_INTEGRATION_TESTS=ON)
if(AGENKIT_BUILD_INTEGRATION_TESTS)
    add_subdirectory(integration)
endif()

# Enable verbose test output
set(CMAKE_CTEST_ARGUMENTS "--output-on-failure")
