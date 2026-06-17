/// Infrastructure modules for production agent systems.
///
/// This module provides production-ready infrastructure for:
/// - Checkpointing: Durable execution with state persistence
/// - Budget tracking: Cost monitoring and limits (coming soon)
/// - Memory systems: Hierarchical conversation memory ✅
/// - Load balancing: Distribute requests across multiple agents ✅
/// - Health checks: Kubernetes-style probes with monitoring ✅
/// - Enhanced retry: Jitter, error classification, budget awareness ✅
pub const checkpointing = struct {
    pub const Checkpoint = @import("checkpointing/checkpoint.zig").Checkpoint;
    pub const CheckpointStorage = @import("checkpointing/storage.zig").CheckpointStorage;
    pub const InMemoryStorage = @import("checkpointing/storage.zig").InMemoryStorage;
    pub const FileStorage = @import("checkpointing/storage.zig").FileStorage;
    pub const CheckpointManager = @import("checkpointing/manager.zig").CheckpointManager;
    pub const DurableAgent = @import("checkpointing/durable.zig").DurableAgent;
};

pub const memory = struct {
    // Base types
    pub const MemoryEntry = @import("memory/base.zig").MemoryEntry;
    pub const Memory = @import("memory/base.zig").Memory;
    pub const Role = @import("memory/base.zig").Role;

    // Implementations
    pub const InMemoryMemory = @import("memory/in_memory.zig").InMemoryMemory;
    pub const InMemoryConfig = @import("memory/in_memory.zig").InMemoryConfig;
    pub const HierarchyMemory = @import("memory/hierarchy.zig").HierarchyMemory;
    pub const HierarchyConfig = @import("memory/hierarchy.zig").HierarchyConfig;
    pub const Tier = @import("memory/hierarchy.zig").Tier;

    // Strategies
    pub const strategies = @import("memory/strategies/mod.zig");
};

// Production Infrastructure Components
pub const LoadBalancer = @import("load_balancer.zig").LoadBalancer;
pub const LoadBalancingStrategy = @import("load_balancer.zig").LoadBalancingStrategy;
pub const LoadBalancerConfig = @import("load_balancer.zig").LoadBalancerConfig;
pub const LoadBalancerMetrics = @import("load_balancer.zig").LoadBalancerMetrics;
pub const AgentBackend = @import("load_balancer.zig").AgentBackend;
pub const BackendStats = @import("load_balancer.zig").BackendStats;

pub const HealthChecker = @import("health.zig").HealthChecker;
pub const HealthStatus = @import("health.zig").HealthStatus;
pub const ProbeType = @import("health.zig").ProbeType;
pub const HealthCheckResult = @import("health.zig").HealthCheckResult;
pub const HealthCheckConfig = @import("health.zig").HealthCheckConfig;
pub const HealthMetrics = @import("health.zig").HealthMetrics;

pub const EnhancedRetryDecorator = @import("retry_enhanced.zig").EnhancedRetryDecorator;
pub const JitterType = @import("retry_enhanced.zig").JitterType;
pub const ErrorClass = @import("retry_enhanced.zig").ErrorClass;
pub const ErrorStrategy = @import("retry_enhanced.zig").ErrorStrategy;
pub const RetryBudget = @import("retry_enhanced.zig").RetryBudget;
pub const EnhancedRetryConfig = @import("retry_enhanced.zig").EnhancedRetryConfig;
pub const EnhancedRetryMetrics = @import("retry_enhanced.zig").EnhancedRetryMetrics;
