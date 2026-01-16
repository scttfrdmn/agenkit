# Examples configuration

# Adapter examples
add_executable(litellm_basic adapters/litellm-basic.cpp)
target_link_libraries(litellm_basic agenkit)

add_executable(gemini_basic adapters/gemini-basic.cpp)
target_link_libraries(gemini_basic agenkit)

add_executable(bedrock_basic adapters/bedrock-basic.cpp)
target_link_libraries(bedrock_basic agenkit)

# Pattern examples - Reflection
add_executable(reflection_pattern patterns/reflection-pattern.cpp)
target_link_libraries(reflection_pattern agenkit)

# Pattern examples - ReAct
add_executable(react_pattern patterns/react-pattern.cpp)
target_link_libraries(react_pattern agenkit)

# Pattern examples - Agents-as-Tools
add_executable(agents_as_tools_pattern patterns/agents-as-tools-pattern.cpp)
target_link_libraries(agents_as_tools_pattern agenkit)

# Pattern examples - Orchestration
add_executable(orchestration_pattern patterns/orchestration-pattern.cpp)
target_link_libraries(orchestration_pattern agenkit)

# Pattern examples - Reasoning with Tools
add_executable(reasoning_with_tools_pattern patterns/reasoning-with-tools-pattern.cpp)
target_link_libraries(reasoning_with_tools_pattern agenkit)

# Pattern examples - Conversational
add_executable(conversational_pattern patterns/conversational-pattern.cpp)
target_link_libraries(conversational_pattern agenkit)

# Pattern examples - Task
add_executable(task_pattern patterns/task-pattern.cpp)
target_link_libraries(task_pattern agenkit)

# Pattern examples - Multiagent
add_executable(multiagent_pattern patterns/multiagent-pattern.cpp)
target_link_libraries(multiagent_pattern agenkit)

# Pattern examples - Planning
add_executable(planning_pattern patterns/planning-pattern.cpp)
target_link_libraries(planning_pattern agenkit)

# Pattern examples - Autonomous
add_executable(autonomous_pattern patterns/autonomous-pattern.cpp)
target_link_libraries(autonomous_pattern agenkit)

# Pattern examples - Memory
add_executable(memory_hierarchy_pattern patterns/memory-hierarchy-pattern.cpp)
target_link_libraries(memory_hierarchy_pattern agenkit)

# Evaluation examples
add_executable(basic_metrics evaluation/basic_metrics.cpp)
target_link_libraries(basic_metrics agenkit)

add_executable(session_recording evaluation/session_recording.cpp)
target_link_libraries(session_recording agenkit)

add_executable(quality_scoring evaluation/quality_scoring.cpp)
target_link_libraries(quality_scoring agenkit)

add_executable(regression_detection evaluation/regression_detection.cpp)
target_link_libraries(regression_detection agenkit)

add_executable(production_monitoring evaluation/production_monitoring.cpp)
target_link_libraries(production_monitoring agenkit)

add_executable(ab_testing evaluation/ab_testing.cpp)
target_link_libraries(ab_testing agenkit)

add_executable(context_metrics evaluation/context_metrics.cpp)
target_link_libraries(context_metrics agenkit)

add_executable(optimizer_example evaluation/optimizer_example.cpp)
target_link_libraries(optimizer_example agenkit)

add_executable(ab_testing_example evaluation/ab_testing_example.cpp)
target_link_libraries(ab_testing_example agenkit)

add_executable(benchmarks_example evaluation/benchmarks_example.cpp)
target_link_libraries(benchmarks_example agenkit)

add_executable(bayesian_optimizer_example evaluation/bayesian_optimizer_example.cpp)
target_link_libraries(bayesian_optimizer_example agenkit)

add_executable(prompt_optimizer_example evaluation/prompt_optimizer_example.cpp)
target_link_libraries(prompt_optimizer_example agenkit)

# Infrastructure examples - Safety
add_executable(safety_simple_example infrastructure/safety-simple.cpp)
target_link_libraries(safety_simple_example agenkit)

add_executable(safety_framework_example infrastructure/safety-framework.cpp)
target_link_libraries(safety_framework_example agenkit)

add_executable(production_secure_example infrastructure/production-secure.cpp)
target_link_libraries(production_secure_example agenkit)

# Infrastructure examples - Checkpointing
add_executable(basic_checkpointing infrastructure/basic_checkpointing.cpp)
target_link_libraries(basic_checkpointing agenkit)

# Infrastructure examples - Budget
add_executable(basic_budget infrastructure/basic_budget.cpp)
target_link_libraries(basic_budget agenkit)

# Infrastructure examples - Middleware
add_executable(middleware_example infrastructure/middleware_example.cpp)
target_link_libraries(middleware_example agenkit)

add_executable(batching_example infrastructure/batching_example.cpp)
target_link_libraries(batching_example agenkit)

# Observability examples (optional, requires OpenTelemetry)
if(AGENKIT_WITH_OBSERVABILITY)
    add_executable(observability_basic observability_basic.cpp)
    target_link_libraries(observability_basic agenkit)

    add_executable(observability_distributed observability_distributed.cpp)
    target_link_libraries(observability_distributed agenkit)

    add_executable(observability_production observability_production.cpp)
    target_link_libraries(observability_production agenkit)

    message(STATUS "Observability examples enabled")
endif()

# Set output directory for all example executables
set(EXAMPLE_TARGETS
    litellm_basic gemini_basic bedrock_basic
    reflection_pattern react_pattern agents_as_tools_pattern
    orchestration_pattern reasoning_with_tools_pattern
    conversational_pattern task_pattern multiagent_pattern
    planning_pattern autonomous_pattern memory_hierarchy_pattern
    basic_metrics session_recording quality_scoring
    regression_detection production_monitoring ab_testing
    context_metrics optimizer_example ab_testing_example
    benchmarks_example bayesian_optimizer_example
    prompt_optimizer_example
    safety_simple_example safety_framework_example production_secure_example
    basic_checkpointing basic_budget middleware_example batching_example
)

# Add observability examples if enabled
if(AGENKIT_WITH_OBSERVABILITY)
    list(APPEND EXAMPLE_TARGETS
        observability_basic
        observability_distributed
        observability_production
    )
endif()

set_target_properties(
    ${EXAMPLE_TARGETS}
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/examples"
)
