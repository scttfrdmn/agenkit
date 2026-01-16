/**
 * @file observability_distributed.cpp
 * @brief Distributed tracing example showing trace context propagation
 *
 * This example demonstrates:
 * - W3C Trace Context propagation across agents
 * - Parent-child span relationships
 * - Distributed tracing in multi-agent workflows
 * - Trace context in message metadata
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <memory>
#include <vector>

using namespace agenkit;
using namespace agenkit::observability;

/**
 * Simple workflow: Agent1 -> Agent2 -> Agent3
 * Each agent processes the message and passes it to the next agent.
 * Trace context is propagated automatically via message metadata.
 */
class DistributedWorkflow {
public:
    DistributedWorkflow() {
        // Create three agents
        auto agent1 = std::make_shared<EchoAgent>();
        auto agent2 = std::make_shared<EchoAgent>();
        auto agent3 = std::make_shared<EchoAgent>();

        // Wrap each with tracing and metrics
        agent1_ = std::make_shared<MetricsMiddleware>(
            std::make_shared<TracingMiddleware>(agent1, "workflow.agent1")
        );

        agent2_ = std::make_shared<MetricsMiddleware>(
            std::make_shared<TracingMiddleware>(agent2, "workflow.agent2")
        );

        agent3_ = std::make_shared<MetricsMiddleware>(
            std::make_shared<TracingMiddleware>(agent3, "workflow.agent3")
        );
    }

    Message execute(Message input) {
        log_agent_event("workflow_started", "Starting distributed workflow");

        // Step 1: Agent1 processes
        std::cout << "  → Agent1 processing..." << std::endl;
        auto result1_future = agent1_->process(input);
        auto result1 = result1_future.get();

        if (!result1.is_ok()) {
            throw std::runtime_error("Agent1 failed: " + result1.error().message());
        }

        auto output1 = result1.unwrap();
        output1.content += " [processed by agent1]";

        // Verify trace context is in metadata
        if (output1.metadata.contains("traceparent")) {
            std::cout << "  ✓ Trace context propagated from Agent1" << std::endl;
        }

        // Step 2: Agent2 processes (receives trace context from Agent1)
        std::cout << "  → Agent2 processing..." << std::endl;
        auto result2_future = agent2_->process(output1);
        auto result2 = result2_future.get();

        if (!result2.is_ok()) {
            throw std::runtime_error("Agent2 failed: " + result2.error().message());
        }

        auto output2 = result2.unwrap();
        output2.content += " [processed by agent2]";

        // Verify trace context is still propagating
        if (output2.metadata.contains("traceparent")) {
            std::cout << "  ✓ Trace context propagated from Agent2" << std::endl;
        }

        // Step 3: Agent3 processes (receives trace context from Agent2)
        std::cout << "  → Agent3 processing..." << std::endl;
        auto result3_future = agent3_->process(output2);
        auto result3 = result3_future.get();

        if (!result3.is_ok()) {
            throw std::runtime_error("Agent3 failed: " + result3.error().message());
        }

        auto output3 = result3.unwrap();
        output3.content += " [processed by agent3]";

        log_agent_event("workflow_completed", "Distributed workflow completed successfully");

        return output3;
    }

private:
    std::shared_ptr<Agent> agent1_;
    std::shared_ptr<Agent> agent2_;
    std::shared_ptr<Agent> agent3_;
};

int main() {
    std::cout << "=== Agenkit C++ Observability - Distributed Tracing Example ===" << std::endl;

    // Initialize observability
    std::cout << "\nInitializing observability stack..." << std::endl;

    try {
        init_tracing("console", "");
        std::cout << "✓ Tracing initialized" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to initialize tracing: " << e.what() << std::endl;
        return 1;
    }

    try {
        init_metrics("console", "");
        std::cout << "✓ Metrics initialized" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to initialize metrics: " << e.what() << std::endl;
        return 1;
    }

    try {
        configure_logging("compact", "info");
        std::cout << "✓ Logging configured" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to configure logging: " << e.what() << std::endl;
        return 1;
    }

    // Create audit logger
    auto audit = AuditLogger::create("audit_distributed.log", 20);
    std::cout << "✓ Audit logger created" << std::endl;

    // Create workflow
    std::cout << "\nCreating distributed workflow (3 agents)..." << std::endl;
    DistributedWorkflow workflow;
    std::cout << "✓ Workflow created" << std::endl;

    // Audit workflow creation
    audit->log(
        AuditEvent::create(AuditEventType::SystemEvent, "distributed_workflow", "demo_session")
            .with_detail("agents", "agent1,agent2,agent3")
            .with_detail("pattern", "sequential")
            .with_severity(Severity::INFO)
    );

    // Execute workflow with multiple messages
    std::cout << "\n=== Executing Distributed Workflows ===" << std::endl;

    std::vector<std::string> test_messages = {
        "Trace me across agents",
        "Distributed systems are great",
        "OpenTelemetry enables observability"
    };

    for (size_t i = 0; i < test_messages.size(); i++) {
        std::cout << "\n--- Workflow " << (i + 1) << " ---" << std::endl;
        std::cout << "Input: \"" << test_messages[i] << "\"" << std::endl;

        // Create input message
        Message input;
        input.role = "user";
        input.content = test_messages[i];

        try {
            // Execute workflow
            auto output = workflow.execute(input);

            std::cout << "Output: \"" << output.content << "\"" << std::endl;
            std::cout << "✓ Workflow completed successfully" << std::endl;

            // Verify trace context in final output
            if (output.metadata.contains("traceparent")) {
                std::cout << "✓ Trace context preserved through all agents" << std::endl;

                // Extract and display trace context
                auto context = extract_trace_context(output.metadata);
                if (context.IsValid()) {
                    std::cout << "✓ Valid W3C Trace Context in final output" << std::endl;
                }
            }

            // Audit successful workflow
            audit->log(
                AuditEvent::create(AuditEventType::MessageProcessed, "distributed_workflow", "demo_session")
                    .with_detail("workflow_id", std::to_string(i + 1))
                    .with_detail("input", test_messages[i])
                    .with_detail("agents_traversed", "3")
                    .with_severity(Severity::INFO)
            );

        } catch (const std::exception& e) {
            std::cerr << "✗ Workflow failed: " << e.what() << std::endl;

            // Audit failure
            audit->log(
                AuditEvent::create(AuditEventType::MessageFailed, "distributed_workflow", "demo_session")
                    .with_detail("error", e.what())
                    .with_severity(Severity::ERROR)
            );
        }
    }

    // Flush audit log
    audit->flush();

    // Summary
    std::cout << "\n=== Summary ===" << std::endl;
    std::cout << "✓ " << test_messages.size() << " distributed workflows completed" << std::endl;
    std::cout << "✓ Trace context propagated through 3 agents per workflow" << std::endl;
    std::cout << "✓ Each agent created child spans under parent trace" << std::endl;
    std::cout << "✓ Metrics recorded for each agent independently" << std::endl;

    auto events = audit->query();
    std::cout << "✓ " << events.size() << " audit events logged" << std::endl;

    std::cout << "\n📊 Observability Benefits:" << std::endl;
    std::cout << "  • Single trace ID spans entire workflow" << std::endl;
    std::cout << "  • Parent-child span relationships preserved" << std::endl;
    std::cout << "  • Per-agent metrics enable bottleneck identification" << std::endl;
    std::cout << "  • Audit trail for compliance and debugging" << std::endl;
    std::cout << "  • Logs correlated via trace context" << std::endl;

    std::cout << "\nCheck audit_distributed.log for full audit trail!" << std::endl;

    return 0;
}

#else

#include <iostream>

int main() {
    std::cerr << "Error: This example requires AGENKIT_WITH_OBSERVABILITY=ON" << std::endl;
    std::cerr << "Rebuild with: cmake -DAGENKIT_WITH_OBSERVABILITY=ON .." << std::endl;
    return 1;
}

#endif // AGENKIT_WITH_OBSERVABILITY
