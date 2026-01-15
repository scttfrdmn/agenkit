/// Infrastructure modules for production agent systems.
///
/// This module provides production-ready infrastructure for:
/// - Checkpointing: Durable execution with state persistence
/// - Budget tracking: Cost monitoring and limits (coming soon)
/// - Memory systems: Hierarchical conversation memory ✅

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
