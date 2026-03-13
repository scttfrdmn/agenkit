/**
 * @file metrics.hpp
 * @brief Metrics middleware for tracking agent request statistics
 *
 * Wraps an agent and collects request counts, latency statistics, and
 * in-flight request tracking. Thread-safe via atomic operations and a mutex
 * for latency state.
 *
 * @example
 * @code
 * auto agent = std::make_shared<MyAgent>();
 * auto metrics = std::make_shared<MetricsMiddleware>(agent);
 *
 * auto result = metrics->process(message).get();
 *
 * auto snapshot = metrics->get_metrics();
 * std::cout << "Total requests: " << snapshot.total_requests << "\n";
 * std::cout << "Error rate: "
 *           << (100.0 * snapshot.error_requests / snapshot.total_requests) << "%\n";
 * @endcode
 */

#pragma once

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <atomic>
#include <chrono>
#include <limits>
#include <memory>
#include <mutex>
#include <string>

namespace agenkit {
namespace middleware {

/**
 * @brief Snapshot of collected metrics at a point in time.
 */
struct MetricsSnapshot {
    /** Total number of requests processed (including in-flight) */
    uint64_t total_requests = 0;

    /** Number of requests that completed successfully */
    uint64_t success_requests = 0;

    /** Number of requests that completed with an error */
    uint64_t error_requests = 0;

    /** Number of requests currently being processed */
    uint64_t in_flight = 0;

    /** Minimum observed latency in milliseconds (for completed requests) */
    double min_latency_ms = 0.0;

    /** Maximum observed latency in milliseconds (for completed requests) */
    double max_latency_ms = 0.0;

    /** Average latency in milliseconds (for completed requests) */
    double avg_latency_ms = 0.0;

    /**
     * @brief Compute success rate as a fraction 0.0–1.0.
     * @return 0.0 if no completed requests.
     */
    double success_rate() const {
        uint64_t completed = success_requests + error_requests;
        if (completed == 0) {
            return 0.0;
        }
        return static_cast<double>(success_requests) / static_cast<double>(completed);
    }
};

/**
 * @brief Metrics middleware — collects request statistics for any Agent.
 *
 * Tracks:
 * - Total, success, and error request counts
 * - In-flight requests (allows monitoring queue depth)
 * - Min / max / average latency for completed requests
 *
 * All counter increments use std::atomic for lock-free updates.
 * Latency state (min, max, total) is protected by a single mutex.
 *
 * Usage:
 * @code
 * auto base = std::make_shared<MyAgent>();
 * auto mw = std::make_shared<MetricsMiddleware>(base);
 *
 * auto result = mw->process(msg).get();
 *
 * mw->reset_metrics();  // zero all counters
 * @endcode
 */
class MetricsMiddleware : public core::Agent {
public:
    /**
     * @brief Construct a MetricsMiddleware wrapping the given agent.
     * @param agent The wrapped agent; must not be null.
     */
    explicit MetricsMiddleware(std::shared_ptr<core::Agent> agent)
        : agent_(std::move(agent)) {}

    /**
     * @brief Agent name — delegates to wrapped agent.
     */
    std::string name() const override {
        return agent_->name();
    }

    /**
     * @brief Process a message, recording metrics around the wrapped call.
     *
     * Increments in-flight on entry, decrements on exit (success or error).
     * Latency is measured from just before the wrapped process() call to
     * resolution of the returned future.
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        total_requests_.fetch_add(1, std::memory_order_relaxed);
        in_flight_.fetch_add(1, std::memory_order_relaxed);

        auto start = std::chrono::steady_clock::now();

        // Delegate to wrapped agent
        auto future = agent_->process(std::move(message));

        // Observe result
        auto result = future.get();

        auto end = std::chrono::steady_clock::now();
        double latency_ms =
            std::chrono::duration<double, std::milli>(end - start).count();

        in_flight_.fetch_sub(1, std::memory_order_relaxed);

        if (result.is_ok()) {
            success_requests_.fetch_add(1, std::memory_order_relaxed);
        } else {
            error_requests_.fetch_add(1, std::memory_order_relaxed);
        }

        // Update latency stats under lock
        {
            std::lock_guard<std::mutex> lock(latency_mutex_);
            if (latency_ms < min_latency_ms_) {
                min_latency_ms_ = latency_ms;
            }
            if (latency_ms > max_latency_ms_) {
                max_latency_ms_ = latency_ms;
            }
            total_latency_ms_ += latency_ms;
        }

        return make_ready_future(std::move(result));
    }

    /**
     * @brief Return a snapshot of the current metrics.
     *
     * The snapshot is a consistent point-in-time view of the counters.
     * Because counters are updated with atomic relaxed operations, there may
     * be slight inconsistencies between fields in the snapshot.
     */
    MetricsSnapshot get_metrics() const {
        MetricsSnapshot snap;
        snap.total_requests   = total_requests_.load(std::memory_order_relaxed);
        snap.success_requests = success_requests_.load(std::memory_order_relaxed);
        snap.error_requests   = error_requests_.load(std::memory_order_relaxed);
        snap.in_flight        = in_flight_.load(std::memory_order_relaxed);

        std::lock_guard<std::mutex> lock(latency_mutex_);
        uint64_t completed = snap.success_requests + snap.error_requests;
        if (completed > 0) {
            snap.min_latency_ms = min_latency_ms_;
            snap.max_latency_ms = max_latency_ms_;
            snap.avg_latency_ms = total_latency_ms_ / static_cast<double>(completed);
        }
        return snap;
    }

    /**
     * @brief Reset all metrics to zero.
     */
    void reset_metrics() {
        total_requests_.store(0, std::memory_order_relaxed);
        success_requests_.store(0, std::memory_order_relaxed);
        error_requests_.store(0, std::memory_order_relaxed);
        in_flight_.store(0, std::memory_order_relaxed);

        std::lock_guard<std::mutex> lock(latency_mutex_);
        min_latency_ms_   = std::numeric_limits<double>::max();
        max_latency_ms_   = 0.0;
        total_latency_ms_ = 0.0;
    }

private:
    std::shared_ptr<core::Agent> agent_;

    std::atomic<uint64_t> total_requests_{0};
    std::atomic<uint64_t> success_requests_{0};
    std::atomic<uint64_t> error_requests_{0};
    std::atomic<uint64_t> in_flight_{0};

    mutable std::mutex latency_mutex_;
    double min_latency_ms_   = std::numeric_limits<double>::max();
    double max_latency_ms_   = 0.0;
    double total_latency_ms_ = 0.0;
};

} // namespace middleware
} // namespace agenkit
