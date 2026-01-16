/**
 * @file observability_basic.cpp
 * @brief Basic observability example with tracing, metrics, logging, and audit
 *
 * This example demonstrates:
 * - Initializing OpenTelemetry tracing and metrics
 * - Configuring structured logging
 * - Setting up audit logging
 * - Wrapping agents with observability middleware
 * - Processing messages with full observability
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <memory>

using namespace agenkit;
using namespace agenkit::observability;

int main() {
    std::cout << "=== Agenkit C++ Observability - Basic Example ===" << std::endl;

    // Step 1: Initialize tracing (console exporter for demo)
    std::cout << "\n1. Initializing tracing..." << std::endl;
    try {
        init_tracing("console", "");
        std::cout << "   ✓ Tracing initialized (console exporter)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "   ✗ Failed to initialize tracing: " << e.what() << std::endl;
        return 1;
    }

    // Step 2: Initialize metrics (console exporter for demo)
    std::cout << "\n2. Initializing metrics..." << std::endl;
    try {
        init_metrics("console", "");
        std::cout << "   ✓ Metrics initialized (console exporter)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "   ✗ Failed to initialize metrics: " << e.what() << std::endl;
        return 1;
    }

    // Step 3: Configure structured logging
    std::cout << "\n3. Configuring logging..." << std::endl;
    try {
        configure_logging("pretty", "info");
        std::cout << "   ✓ Logging configured (pretty format, info level)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "   ✗ Failed to configure logging: " << e.what() << std::endl;
        return 1;
    }

    // Step 4: Create audit logger
    std::cout << "\n4. Creating audit logger..." << std::endl;
    std::shared_ptr<AuditLogger> audit;
    try {
        audit = AuditLogger::create("audit_basic.log", 10);
        std::cout << "   ✓ Audit logger created (file: audit_basic.log)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "   ✗ Failed to create audit logger: " << e.what() << std::endl;
        return 1;
    }

    // Step 5: Create and wrap agent with observability
    std::cout << "\n5. Creating observable agent..." << std::endl;
    auto echo = std::make_shared<EchoAgent>();
    std::cout << "   ✓ Created EchoAgent" << std::endl;

    auto traced = std::make_shared<TracingMiddleware>(echo, "echo.process");
    std::cout << "   ✓ Wrapped with TracingMiddleware" << std::endl;

    auto observed = std::make_shared<MetricsMiddleware>(traced);
    std::cout << "   ✓ Wrapped with MetricsMiddleware" << std::endl;

    // Audit agent creation
    audit->log(
        AuditEvent::create(AuditEventType::AgentCreated, "echo_agent", "demo_session")
            .with_detail("middleware", "tracing,metrics")
            .with_detail("example", "basic")
            .with_severity(Severity::INFO)
    );
    std::cout << "   ✓ Audited agent creation" << std::endl;

    // Step 6: Process messages
    std::cout << "\n6. Processing messages..." << std::endl;

    std::vector<std::string> messages = {
        "Hello, observability!",
        "This message is traced",
        "Metrics are being recorded"
    };

    for (size_t i = 0; i < messages.size(); i++) {
        std::cout << "\n   Message " << (i + 1) << ": \"" << messages[i] << "\"" << std::endl;

        // Log the event
        log_agent_event("message_received", "Processing message " + std::to_string(i + 1));

        // Create message
        Message msg;
        msg.role = "user";
        msg.content = messages[i];

        // Process (creates span, records metrics)
        auto result_future = observed->process(msg);
        auto result = result_future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "   ✓ Response: \"" << response.content << "\"" << std::endl;

            // Log success
            log_agent_event("message_processed", "Successfully processed message " + std::to_string(i + 1));

            // Audit the operation
            audit->log(
                AuditEvent::create(AuditEventType::MessageProcessed, "echo_agent", "demo_session")
                    .with_detail("message_index", std::to_string(i + 1))
                    .with_detail("message_length", std::to_string(messages[i].length()))
                    .with_severity(Severity::INFO)
            );
        } else {
            std::cerr << "   ✗ Error: " << result.error().message() << std::endl;

            // Log error
            log_agent_error("message_failed", "Failed to process message " + std::to_string(i + 1),
                          result.error().message());

            // Audit the failure
            audit->log(
                AuditEvent::create(AuditEventType::MessageFailed, "echo_agent", "demo_session")
                    .with_detail("error", result.error().message())
                    .with_severity(Severity::ERROR)
            );
        }
    }

    // Step 7: Flush audit log
    std::cout << "\n7. Flushing audit log..." << std::endl;
    audit->flush();
    std::cout << "   ✓ Audit log flushed to disk" << std::endl;

    // Step 8: Query audit events
    std::cout << "\n8. Querying audit events..." << std::endl;
    auto events = audit->query();
    std::cout << "   ✓ Total events: " << events.size() << std::endl;

    auto created_events = audit->query_by_type(AuditEventType::AgentCreated);
    std::cout << "   ✓ Agent creation events: " << created_events.size() << std::endl;

    auto processed_events = audit->query_by_type(AuditEventType::MessageProcessed);
    std::cout << "   ✓ Message processed events: " << processed_events.size() << std::endl;

    // Step 9: Summary
    std::cout << "\n=== Summary ===" << std::endl;
    std::cout << "✓ Tracing: Spans created for each message" << std::endl;
    std::cout << "✓ Metrics: Request count and duration recorded" << std::endl;
    std::cout << "✓ Logging: Events logged with trace context" << std::endl;
    std::cout << "✓ Audit: " << events.size() << " events persisted to audit_basic.log" << std::endl;
    std::cout << "\nCheck audit_basic.log for detailed audit trail!" << std::endl;

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
