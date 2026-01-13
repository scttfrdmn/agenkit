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

# Optimization benchmarks (Phase 1-3)
add_executable(bench_optimizations bench_optimizations.cpp)
target_link_libraries(bench_optimizations agenkit)

# Set output directory
set_target_properties(bench_core bench_http bench_patterns bench_evaluation bench_optimizations
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/benchmarks"
)

# Add custom target to run all benchmarks
add_custom_target(run_benchmarks
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_core
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_http
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_patterns
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_evaluation
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/bench_optimizations
    DEPENDS bench_core bench_http bench_patterns bench_evaluation bench_optimizations
    COMMENT "Running all benchmarks..."
)
