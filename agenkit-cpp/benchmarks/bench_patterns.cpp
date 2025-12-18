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
#include "agenkit/patterns/sequential.hpp"
#include "agenkit/patterns/parallel.hpp"
#include "agenkit/patterns/router.hpp"
#include "agenkit/patterns/fallback.hpp"
#include "agenkit/patterns/collaborative.hpp"
#include "agenkit/patterns/human_in_loop.hpp"
#include "agenkit/patterns/supervisor.hpp"

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
// Helper Classes for Benchmarks
// ============================================================================

// Simple echo classifier for Router benchmarks
class EchoClassifier : public patterns::ClassifierAgent {
public:
    std::string name() const override { return "echo-classifier"; }
    std::vector<std::string> capabilities() const override { return {"classify"}; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::promise<core::Result<core::Message, core::AgentError>> promise;
        promise.set_value(core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", "route1")));
        return promise.get_future();
    }

    core::Result<std::string, core::AgentError>
    classify(const core::Message& message) override {
        return core::Result<std::string, core::AgentError>::ok("route1");
    }
};

// Note: EchoPlanner removed - Supervisor benchmark skipped due to complex PlannerAgent interface

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
        // Clear history after each iteration to prevent accumulation
        conv.clear_history();
    }, 1000);  // Increased to 1000 iterations now that history is cleared

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

    auto result = benchmark("Autonomous (5 iterations)", [&]() {
        // Create fresh agent for each iteration to reset goal state
        patterns::AutonomousAgent autonomous("Complete objective", config);
        autonomous.add_goal("Goal 1", 1);
        autonomous.add_goal("Goal 2", 1);
        auto _ = autonomous.run();
    }, 100);  // Increased iterations now that we measure correctly

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

void bench_sequential() {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();
    auto agent3 = std::make_shared<adapters::EchoAgent>();

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent sequential(agents);

    auto result = benchmark("Sequential (3 agents)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = sequential.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_parallel() {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();
    auto agent3 = std::make_shared<adapters::EchoAgent>();

    // Simple aggregator: concatenate responses
    auto aggregator = [](const std::vector<core::Message>& messages) {
        return messages.empty() ? core::Message::with_text("assistant", "")
                                : messages[0];
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto result = benchmark("Parallel (3 agents)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = parallel.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_router() {
    auto classifier = std::make_shared<EchoClassifier>();
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents = {
        {"route1", agent1},
        {"route2", agent2}
    };

    patterns::RouterConfig config{classifier, agents, "route1"};
    patterns::RouterAgent router(config);

    auto result = benchmark("Router (2 routes)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = router.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_fallback() {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::FallbackAgent fallback(agents);

    auto result = benchmark("Fallback (2 agents)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = fallback.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_collaborative() {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};

    // Merge function: return first response
    auto merge_func = [](const std::vector<core::Message>& messages) {
        return messages.empty() ? core::Message::with_text("assistant", "")
                                : messages[0];
    };

    patterns::CollaborativeConfig config{agents, 2, nullptr, merge_func};
    patterns::CollaborativeAgent collaborative(config);

    auto result = benchmark("Collaborative (2 rounds)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = collaborative.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_human_in_loop() {
    auto agent = std::make_shared<adapters::EchoAgent>();

    // Auto-approve callback for benchmarking
    auto approval_func = [](const patterns::ApprovalRequest& req) {
        patterns::ApprovalResponse response(true, "approved");
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(response);
    };

    patterns::HumanInLoopConfig config{agent, 0.8, approval_func, "confidence"};
    patterns::HumanInLoopAgent hil(config);

    auto result = benchmark("Human-in-Loop (auto-approve)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = hil.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
}

void bench_supervisor() {
    auto echo_agent = std::make_shared<adapters::EchoAgent>();
    auto planner = std::make_shared<patterns::SimplePlanner>(echo_agent);

    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists = {
        {"specialist1", std::make_shared<adapters::EchoAgent>()},
        {"specialist2", std::make_shared<adapters::EchoAgent>()}
    };

    patterns::SupervisorAgent supervisor(planner, specialists);

    auto result = benchmark("Supervisor (2 specialists)", [&]() {
        auto msg = core::Message::with_text("user", "Test");
        auto future = supervisor.process(std::move(msg));
        auto _ = future.get();
    }, 100);

    print_result(result);
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

    std::cout << std::string(100, '-') << "\n";

    // Composition patterns
    std::cout << "Running sequential...\n" << std::flush;
    bench_sequential();
    std::cout << "Running parallel...\n" << std::flush;
    bench_parallel();
    std::cout << "Running router...\n" << std::flush;
    bench_router();
    std::cout << "Running fallback...\n" << std::flush;
    bench_fallback();
    std::cout << "Running collaborative...\n" << std::flush;
    bench_collaborative();
    std::cout << "Running human_in_loop...\n" << std::flush;
    bench_human_in_loop();
    std::cout << "Running supervisor...\n" << std::flush;
    bench_supervisor();

    std::cout << std::string(100, '=') << "\n\n";

    std::cout << "Notes:\n";
    std::cout << "  • Measurements in microseconds (μs)\n";
    std::cout << "  • All benchmarks use EchoAgent for agent operations\n";
    std::cout << "  • Real-world performance depends on actual LLM latency\n";
    std::cout << "  • These benchmarks measure framework overhead only\n\n";

    return 0;
}
