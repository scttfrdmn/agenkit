# Benchmarks configuration for agenkit-cpp

# Core benchmarks
add_executable(bench_core bench_core.cpp)
target_link_libraries(bench_core agenkit)

# HTTP transport benchmarks
add_executable(bench_http bench_http.cpp)
target_link_libraries(bench_http agenkit)

# Pattern benchmarks
add_executable(bench_patterns bench_patterns.cpp)
target_link_libraries(bench_patterns agenkit)

# Evaluation framework benchmarks
add_executable(bench_evaluation bench_evaluation.cpp)
target_link_libraries(bench_evaluation agenkit)

# Set output directory
set_target_properties(bench_core bench_http bench_patterns bench_evaluation
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/benchmarks"
)

# Add custom target to run all benchmarks
add_custom_target(run_benchmarks
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_core
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_http
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_patterns
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_evaluation
    DEPENDS bench_core bench_http bench_patterns bench_evaluation
    COMMENT "Running all benchmarks..."
)
