/**
 * @file bench_patterns.cpp
 * @brief Performance benchmarks for all 11 agent patterns
 *
 * Benchmarks:
 * - Reflection: Self-critique cycles
 * - ReAct: Reason-act iterations
 * - Agents-as-Tools: Tool wrapping overhead
 * - Orchestration: Multi-agent coordination
 * - Reasoning with Tools: Tool-aware reasoning
 * - Conversational: History management
 * - Task: One-shot execution
 * - Multiagent: Collaboration overhead
 * - Planning: Plan generation and execution
 * - Autonomous: Goal-based operation
 * - Memory: 3-tier storage/retrieval
 */

#include <chrono>
#include <iostream>
#include <iomanip>
#include <vector>
#include <numeric>
#include <algorithm>
#include <memory>

#include "agenkit/core/message.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/patterns/reflection.hpp"
#include "agenkit/patterns/react.hpp"
#include "agenkit/patterns/agents_as_tools.hpp"
#include "agenkit/patterns/orchestration.hpp"
#include "agenkit/patterns/reasoning_with_tools.hpp"
#include "agenkit/patterns/conversational.hpp"
#include "agenkit/patterns/task.hpp"
#include "agenkit/patterns/multiagent.hpp"
#include "agenkit/patterns/planning.hpp"
#include "agenkit/patterns/autonomous.hpp"
#include "agenkit/patterns/memory.hpp"

using namespace agenkit;
using namespace std::chrono;

// Benchmark result structure
struct BenchmarkResult {
    std::string name;
    double mean_us;
    double median_us;
    double min_us;
    double max_us;
    double stddev_us;
    size_t iterations;
    size_t ops_per_iteration;  // For throughput calculation
};

class Timer {
public:
    Timer() : start_(high_resolution_clock::now()) {}

    double elapsed_us() const {
        auto end = high_resolution_clock::now();
        return duration_cast<microseconds>(end - start_).count();
    }

    void reset() {
        start_ = high_resolution_clock::now();
    }

private:
    high_resolution_clock::time_point start_;
};

// Run benchmark and collect statistics
template<typename Func>
BenchmarkResult benchmark(const std::string& name, Func func, size_t iterations = 1000, size_t ops = 1) {
    std::vector<double> times;
    times.reserve(iterations);

    // Warmup
    for (size_t i = 0; i < 10; ++i) {
        func();
    }

    // Benchmark
    for (size_t i = 0; i < iterations; ++i) {
        Timer timer;
        func();
        times.push_back(timer.elapsed_us());
    }

    // Calculate statistics
    std::sort(times.begin(), times.end());
    double sum = std::accumulate(times.begin(), times.end(), 0.0);
    double mean = sum / times.size();
    double median = times[times.size() / 2];
    double min_val = times.front();
    double max_val = times.back();

    // Calculate standard deviation
    double sq_sum = std::inner_product(times.begin(), times.end(), times.begin(), 0.0);
    double stddev = std::sqrt(sq_sum / times.size() - mean * mean);

    return {name, mean, median, min_val, max_val, stddev, iterations, ops};
}

void print_result(const BenchmarkResult& result) {
    std::cout << std::left << std::setw(35) << result.name << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.mean_us << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.median_us << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.min_us << " │ ";
    std::cout << std::right << std::setw(10) << std::fixed << std::setprecision(2) << result.max_us << " │ ";

    if (result.ops_per_iteration > 1) {
        double ops_per_sec = (1000000.0 * result.ops_per_iteration) / result.mean_us;
        std::cout << std::right << std::setw(12) << std::fixed << std::setprecision(0) << ops_per_sec << "\n";
    } else {
        std::cout << std::right << std::setw(12) << "-" << "\n";
    }
}

// ============================================================================
// Pattern Benchmarks
// ============================================================================

void bench_reflection() {
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto reflector = std::make_shared<adapters::EchoAgent>();
    patterns::ReflectionAgent reflection(agent, reflector, 2);

    auto result = benchmark("Reflection (2 iterations)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = reflection.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_react() {
    auto agent = std::make_shared<adapters::EchoAgent>();
    patterns::ReactAgent react(agent, 3); // max_steps

    auto result = benchmark("ReAct (3 steps)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = react.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_agents_as_tools() {
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto tool = patterns::AgentToolBuilder(agent, "test", "Test tool").build();

    auto result = benchmark("Agents-as-Tools (call)", [&]() {
        auto _ = tool->execute("test input");
    }, 100);

    print_result(result);
}

void bench_orchestration() {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    patterns::OrchestrationAgent orchestrator;
    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("agent2", agent2);

    auto result = benchmark("Orchestration (2 agents)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = orchestrator.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_reasoning_with_tools() {
    auto agent = std::make_shared<adapters::EchoAgent>();
    patterns::ReasoningAgent reasoning(agent);

    auto result = benchmark("Reasoning with Tools", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = reasoning.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_conversational() {
    auto agent = std::make_shared<adapters::EchoAgent>();
    patterns::ConversationalConfig config;
    config.max_history = 10;
    patterns::ConversationalAgent conv(agent, config);

    auto result = benchmark("Conversational (10 history)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = conv.process(std::move(msg));
        auto _ = future.get();
    }, 10);  // Reduced to 10 iterations to prevent memory buildup

    print_result(result);
}

void bench_task() {
    auto agent = std::make_shared<adapters::EchoAgent>();

    auto result = benchmark("Task (one-shot)", [&]() {
        patterns::Task task(agent);
        auto msg = core::Message::with_text("user", "Test");
        auto future = task.execute(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_multiagent() {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    patterns::MultiAgentOrchestrator orchestrator(patterns::MultiAgentStrategy::Sequential);
    orchestrator.register_agent("agent1", agent1);
    orchestrator.register_agent("agent2", agent2);

    auto result = benchmark("Multiagent (2 sequential)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = orchestrator.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_planning() {
    auto planner = std::make_shared<adapters::EchoAgent>();
    patterns::PlanningAgent planning(planner, 5); // max_steps

    auto result = benchmark("Planning (plan + execute)", [&]() {
        auto msg = core::Message::with_text("user", "Create a plan");
        auto future = planning.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_autonomous() {
    patterns::AutonomousConfig config;
    config.max_iterations = 5;
    patterns::AutonomousAgent autonomous("Complete objective", config);

    autonomous.add_goal("Goal 1", 1);
    autonomous.add_goal("Goal 2", 1);

    auto result = benchmark("Autonomous (5 iterations)", [&]() {
        auto _ = autonomous.run();
    }, 10);  // Fewer iterations as this is more expensive

    print_result(result);
}

void bench_memory_working() {
    auto result = benchmark("Memory: Working store", [&]() {
        patterns::WorkingMemory memory(10);
        patterns::MemoryEntry entry("Test content", 0.5);
        memory.store(entry);
    }, 100, 1);

    print_result(result);

    // Benchmark retrieval
    patterns::WorkingMemory memory(10);
    for (int i = 0; i < 5; ++i) {
        patterns::MemoryEntry entry("Test content " + std::to_string(i), 0.5);
        memory.store(entry);
    }

    auto result2 = benchmark("Memory: Working retrieve", [&]() {
        auto _ = memory.retrieve("Test", 5);
    }, 100, 1);

    print_result(result2);
}

void bench_memory_hierarchy() {
    auto result = benchmark("Memory: Hierarchy store", [&]() {
        patterns::MemoryHierarchy hierarchy(10, 100, 3600, 0.5);
        hierarchy.store("Test content", 0.7);
    }, 100, 1);

    print_result(result);

    // Benchmark retrieval
    patterns::MemoryHierarchy hierarchy(10, 100, 3600, 0.5);
    for (int i = 0; i < 10; ++i) {
        hierarchy.store("Content " + std::to_string(i), 0.6);
    }

    auto result2 = benchmark("Memory: Hierarchy retrieve", [&]() {
        auto _ = hierarchy.retrieve("Content", 5);
    }, 100, 1);

    print_result(result2);
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "\n";
    std::cout << "==============================================================================\n";
    std::cout << "              AgentKit C++ Pattern Performance Benchmarks                    \n";
    std::cout << "==============================================================================\n\n";

    std::cout << std::left << std::setw(35) << "Pattern" << " │ ";
    std::cout << std::right << std::setw(10) << "Mean (μs)" << " │ ";
    std::cout << std::right << std::setw(10) << "Median (μs)" << " │ ";
    std::cout << std::right << std::setw(10) << "Min (μs)" << " │ ";
    std::cout << std::right << std::setw(10) << "Max (μs)" << " │ ";
    std::cout << std::right << std::setw(12) << "Ops/sec" << "\n";
    std::cout << std::string(100, '-') << "\n";

    // Core patterns
    std::cout << "Running reflection...\n" << std::flush;
    bench_reflection();
    std::cout << "Running react...\n" << std::flush;
    bench_react();
    std::cout << "Running agents_as_tools...\n" << std::flush;
    bench_agents_as_tools();
    std::cout << "Running orchestration...\n" << std::flush;
    bench_orchestration();
    std::cout << "Running reasoning_with_tools...\n" << std::flush;
    bench_reasoning_with_tools();

    std::cout << std::string(100, '-') << "\n";

    // Advanced patterns
    std::cout << "Running conversational...\n" << std::flush;
    bench_conversational();
    std::cout << "Running task...\n" << std::flush;
    bench_task();
    std::cout << "Running multiagent...\n" << std::flush;
    bench_multiagent();
    std::cout << "Running planning...\n" << std::flush;
    bench_planning();
    std::cout << "Running autonomous...\n" << std::flush;
    bench_autonomous();

    std::cout << std::string(100, '-') << "\n";

    // Memory patterns
    std::cout << "Running memory_working...\n" << std::flush;
    bench_memory_working();
    std::cout << "Running memory_hierarchy...\n" << std::flush;
    bench_memory_hierarchy();

    std::cout << std::string(100, '=') << "\n\n";

    std::cout << "Notes:\n";
    std::cout << "  • Measurements in microseconds (μs)\n";
    std::cout << "  • All benchmarks use EchoAgent for agent operations\n";
    std::cout << "  • Real-world performance depends on actual LLM latency\n";
    std::cout << "  • These benchmarks measure framework overhead only\n\n";

    return 0;
}
