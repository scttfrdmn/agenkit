/**
 * @file observability_production.cpp
 * @brief Production-ready observability setup with OTLP exporters
 *
 * This example demonstrates:
 * - Production observability configuration
 * - OTLP exporters for tracing and metrics
 * - JSON structured logging
 * - Comprehensive audit logging
 * - Error handling and recovery
 * - Security event auditing
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <memory>
#include <cstdlib>

using namespace agenkit;
using namespace agenkit::observability;

/**
 * Production observability configuration
 */
struct ObservabilityConfig {
    std::string otlp_endpoint;
    std::string log_format;
    std::string log_level;
    std::string audit_log_path;
    size_t audit_buffer_size;

    static ObservabilityConfig from_environment() {
        ObservabilityConfig config;

        // OTLP endpoint (default to localhost)
        const char* endpoint_env = std::getenv("OTLP_ENDPOINT");
        config.otlp_endpoint = endpoint_env ? endpoint_env : "http://localhost:4317";

        // Log format (default to JSON for production)
        const char* format_env = std::getenv("LOG_FORMAT");
        config.log_format = format_env ? format_env : "json";

        // Log level (default to info)
        const char* level_env = std::getenv("LOG_LEVEL");
        config.log_level = level_env ? level_env : "info";

        // Audit log path
        const char* audit_path_env = std::getenv("AUDIT_LOG_PATH");
        config.audit_log_path = audit_path_env ? audit_path_env : "/var/log/agenkit/audit.log";

        // Audit buffer size
        const char* buffer_size_env = std::getenv("AUDIT_BUFFER_SIZE");
        config.audit_buffer_size = buffer_size_env ? std::stoul(buffer_size_env) : 100;

        return config;
    }

    void print() const {
        std::cout << "Configuration:" << std::endl;
        std::cout << "  OTLP Endpoint: " << otlp_endpoint << std::endl;
        std::cout << "  Log Format: " << log_format << std::endl;
        std::cout << "  Log Level: " << log_level << std::endl;
        std::cout << "  Audit Log: " << audit_log_path << std::endl;
        std::cout << "  Audit Buffer: " << audit_buffer_size << " events" << std::endl;
    }
};

/**
 * Initialize production observability stack
 */
bool initialize_observability(const ObservabilityConfig& config) {
    std::cout << "Initializing observability stack..." << std::endl;

    // Initialize tracing with OTLP
    try {
        // Use console for demo, replace with "otlp" for production
        init_tracing("console", config.otlp_endpoint);
        std::cout << "✓ Tracing initialized" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to initialize tracing: " << e.what() << std::endl;
        std::cerr << "  Hint: Ensure OTLP collector is running at " << config.otlp_endpoint << std::endl;
        return false;
    }

    // Initialize metrics with OTLP
    try {
        // Use console for demo, replace with "otlp" for production
        init_metrics("console", config.otlp_endpoint);
        std::cout << "✓ Metrics initialized" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to initialize metrics: " << e.what() << std::endl;
        return false;
    }

    // Configure structured logging
    try {
        configure_logging(config.log_format, config.log_level);
        std::cout << "✓ Logging configured" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to configure logging: " << e.what() << std::endl;
        return false;
    }

    return true;
}

/**
 * Production agent with full observability
 */
class ProductionAgent {
public:
    ProductionAgent(const std::string& name, std::shared_ptr<AuditLogger> audit)
        : name_(name), audit_(audit) {

        // Create base agent
        auto base = std::make_shared<EchoAgent>();

        // Wrap with tracing
        auto traced = std::make_shared<TracingMiddleware>(base, name + ".process");

        // Wrap with metrics
        agent_ = std::make_shared<MetricsMiddleware>(traced);

        // Audit agent creation
        audit_->log(
            AuditEvent::create(AuditEventType::AgentCreated, name_, "production_session")
                .with_detail("middleware", "tracing,metrics")
                .with_detail("environment", "production")
                .with_severity(Severity::INFO)
        );

        log_agent_event("agent_created", "Production agent initialized: " + name_);
    }

    Message process(const Message& input) {
        log_agent_event("message_received", "Agent " + name_ + " processing message");

        try {
            // Validate input
            if (input.content.empty()) {
                log_agent_warning("empty_message", "Received empty message content");

                audit_->log(
                    AuditEvent::create(AuditEventType::MessageFailed, name_, "production_session")
                        .with_detail("reason", "empty_content")
                        .with_severity(Severity::WARNING)
                );

                throw std::runtime_error("Empty message content");
            }

            // Check for security violations (demo: check for "malicious" keyword)
            if (input.content.find("malicious") != std::string::npos) {
                log_agent_error("security_violation", "Potentially malicious content detected",
                              "Content contains blacklisted keyword");

                audit_->log(
                    AuditEvent::create(AuditEventType::SecurityViolation, name_, "production_session")
                        .with_detail("violation_type", "blacklisted_content")
                        .with_detail("keyword", "malicious")
                        .with_severity(Severity::CRITICAL)
                );

                throw std::runtime_error("Security violation: blacklisted content");
            }

            // Process message
            auto result_future = agent_->process(input);
            auto result = result_future.get();

            if (!result.is_ok()) {
                throw std::runtime_error(result.error().message());
            }

            auto output = result.unwrap();

            // Audit successful processing
            audit_->log(
                AuditEvent::create(AuditEventType::MessageProcessed, name_, "production_session")
                    .with_detail("input_length", std::to_string(input.content.length()))
                    .with_detail("output_length", std::to_string(output.content.length()))
                    .with_severity(Severity::INFO)
            );

            log_agent_event("message_processed", "Agent " + name_ + " completed successfully");

            return output;

        } catch (const std::exception& e) {
            log_agent_error("processing_error", "Agent " + name_ + " encountered error", e.what());

            audit_->log(
                AuditEvent::create(AuditEventType::ErrorOccurred, name_, "production_session")
                    .with_detail("error", e.what())
                    .with_severity(Severity::ERROR)
            );

            throw;
        }
    }

private:
    std::string name_;
    std::shared_ptr<Agent> agent_;
    std::shared_ptr<AuditLogger> audit_;
};

int main() {
    std::cout << "=== Agenkit C++ Observability - Production Example ===" << std::endl;
    std::cout << std::endl;

    // Load configuration from environment
    auto config = ObservabilityConfig::from_environment();
    config.print();
    std::cout << std::endl;

    // Initialize observability
    if (!initialize_observability(config)) {
        std::cerr << "\nFailed to initialize observability stack" << std::endl;
        return 1;
    }

    // Create audit logger (use /tmp for demo, production would use /var/log)
    std::shared_ptr<AuditLogger> audit;
    try {
        std::string audit_path = "audit_production.log";
        audit = AuditLogger::create(audit_path, config.audit_buffer_size);
        std::cout << "✓ Audit logger created (using " << audit_path << " for demo)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Failed to create audit logger: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "\n✓ Observability stack initialized successfully" << std::endl;

    // Create production agents
    std::cout << "\n=== Creating Production Agents ===" << std::endl;
    ProductionAgent agent1("primary_agent", audit);
    ProductionAgent agent2("backup_agent", audit);
    std::cout << "✓ Agents created and instrumented" << std::endl;

    // Test scenarios
    std::cout << "\n=== Running Production Scenarios ===" << std::endl;

    // Scenario 1: Normal operation
    std::cout << "\n--- Scenario 1: Normal Operation ---" << std::endl;
    try {
        Message msg1;
        msg1.role = "user";
        msg1.content = "Process this legitimate message";

        auto output1 = agent1.process(msg1);
        std::cout << "✓ Scenario 1: SUCCESS" << std::endl;
        std::cout << "  Input:  \"" << msg1.content << "\"" << std::endl;
        std::cout << "  Output: \"" << output1.content << "\"" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Scenario 1: FAILED - " << e.what() << std::endl;
    }

    // Scenario 2: Empty message (warning)
    std::cout << "\n--- Scenario 2: Empty Message (Warning) ---" << std::endl;
    try {
        Message msg2;
        msg2.role = "user";
        msg2.content = "";

        auto output2 = agent1.process(msg2);
        std::cout << "✓ Scenario 2: SUCCESS" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "✓ Scenario 2: Handled correctly - " << e.what() << std::endl;
    }

    // Scenario 3: Security violation (critical)
    std::cout << "\n--- Scenario 3: Security Violation (Critical) ---" << std::endl;
    try {
        Message msg3;
        msg3.role = "user";
        msg3.content = "This is a malicious attempt";

        auto output3 = agent1.process(msg3);
        std::cerr << "✗ Scenario 3: Security violation not caught!" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "✓ Scenario 3: Security violation blocked - " << e.what() << std::endl;
    }

    // Scenario 4: Failover to backup agent
    std::cout << "\n--- Scenario 4: Backup Agent ---" << std::endl;
    try {
        Message msg4;
        msg4.role = "user";
        msg4.content = "Processed by backup agent";

        auto output4 = agent2.process(msg4);
        std::cout << "✓ Scenario 4: SUCCESS" << std::endl;
        std::cout << "  Backup agent operational" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "✗ Scenario 4: FAILED - " << e.what() << std::endl;
    }

    // Flush audit log
    std::cout << "\n=== Finalizing ===" << std::endl;
    audit->flush();
    std::cout << "✓ Audit log flushed to disk" << std::endl;

    // Query audit events
    auto all_events = audit->query();
    auto created = audit->query_by_type(AuditEventType::AgentCreated);
    auto processed = audit->query_by_type(AuditEventType::MessageProcessed);
    auto failed = audit->query_by_type(AuditEventType::MessageFailed);
    auto violations = audit->query_by_type(AuditEventType::SecurityViolation);
    auto errors = audit->query_by_type(AuditEventType::ErrorOccurred);

    // Query by severity
    auto critical_events = audit->query_with_filter([](const AuditEvent& e) {
        return e.severity() == Severity::CRITICAL;
    });

    // Summary
    std::cout << "\n=== Production Summary ===" << std::endl;
    std::cout << "Audit Events:" << std::endl;
    std::cout << "  Total:               " << all_events.size() << std::endl;
    std::cout << "  Agents Created:      " << created.size() << std::endl;
    std::cout << "  Messages Processed:  " << processed.size() << std::endl;
    std::cout << "  Messages Failed:     " << failed.size() << std::endl;
    std::cout << "  Security Violations: " << violations.size() << std::endl;
    std::cout << "  Errors:              " << errors.size() << std::endl;
    std::cout << "  Critical Events:     " << critical_events.size() << std::endl;

    std::cout << "\n📊 Production Observability Features:" << std::endl;
    std::cout << "  ✓ Distributed tracing with OpenTelemetry" << std::endl;
    std::cout << "  ✓ Metrics collection (requests, duration, errors)" << std::endl;
    std::cout << "  ✓ Structured JSON logging with trace correlation" << std::endl;
    std::cout << "  ✓ Comprehensive audit trail for compliance" << std::endl;
    std::cout << "  ✓ Security event detection and auditing" << std::endl;
    std::cout << "  ✓ Error handling with observability" << std::endl;

    std::cout << "\n🔧 Production Deployment:" << std::endl;
    std::cout << "  1. Deploy OpenTelemetry Collector" << std::endl;
    std::cout << "  2. Set OTLP_ENDPOINT environment variable" << std::endl;
    std::cout << "  3. Configure LOG_FORMAT=json LOG_LEVEL=info" << std::endl;
    std::cout << "  4. Mount persistent volume for audit logs" << std::endl;
    std::cout << "  5. Set up log rotation and retention policies" << std::endl;

    std::cout << "\nCheck audit_production.log for full audit trail!" << std::endl;

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
