/// Supervisor Pattern - Hierarchical coordination with task decomposition
///
/// The Supervisor pattern implements hierarchical task management where a
/// supervisor agent decomposes complex tasks into subtasks, delegates them
/// to specialist agents, and synthesizes the results.
///
/// # Key Concepts
/// - Hierarchical coordination (supervisor → specialists)
/// - Task decomposition and planning
/// - Specialist delegation based on task type
/// - Result synthesis and aggregation
///
/// # Performance Characteristics
/// - Time: O(planning + n × specialist + synthesis)
/// - Memory: O(n) for subtask results
/// - Can parallelize specialist execution
///
/// # Use Cases
/// - Complex workflows: Break down multi-step processes
/// - Domain specialization: Route subtasks to expert agents
/// - Project management: Plan → Execute → Review cycles
/// - Data pipelines: Extract → Transform → Load
/// - Research tasks: Gather → Analyze → Synthesize
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// // Create specialist agents
/// var specialists = std.StringHashMap(Agent).init(allocator);
/// try specialists.put("research", researcher.agent());
/// try specialists.put("analysis", analyst.agent());
///
/// // Create planner
/// var planner = try SimplePlanner.init(allocator, planning_agent.agent());
/// defer planner.deinit();
///
/// // Create supervisor
/// var supervisor = try SupervisorAgent.init(
///     allocator,
///     planner.planner(),
///     specialists,
///     "project_manager"
/// );
/// defer supervisor.deinit();
///
/// const result = try supervisor.agent().process(complex_task);
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const Allocator = std.mem.Allocator;

/// Subtask decomposed from main task
pub const Subtask = struct {
    task_type: []const u8,
    message: Message,
    metadata: std.StringHashMap([]const u8),

    pub fn deinit(self: *Subtask) void {
        self.message.deinit();
        var it = self.metadata.iterator();
        while (it.next()) |entry| {
            self.metadata.allocator.free(entry.key_ptr.*);
            self.metadata.allocator.free(entry.value_ptr.*);
        }
        self.metadata.deinit();
    }
};

/// Planner interface - decomposes tasks and synthesizes results
pub const Planner = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        plan: *const fn (ptr: *anyopaque, allocator: Allocator, message: Message) AgentError![]Subtask,
        synthesize: *const fn (ptr: *anyopaque, allocator: Allocator, results: []const Message) AgentError!Message,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Decompose a message into subtasks
    pub fn plan(self: Planner, allocator: Allocator, message: Message) AgentError![]Subtask {
        return self.vtable.plan(self.ptr, allocator, message);
    }

    /// Synthesize subtask results into final result
    pub fn synthesize(self: Planner, allocator: Allocator, results: []const Message) AgentError!Message {
        return self.vtable.synthesize(self.ptr, allocator, results);
    }

    /// Clean up planner resources
    pub fn deinit(self: Planner) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Supervisor Agent - Coordinates task decomposition and specialist delegation
pub const SupervisorAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    planner: Planner,
    specialists: std.StringHashMap(Agent),
    owned_specialists: bool,

    /// Initialize a supervisor agent
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     planner: Planner for task decomposition
    ///     specialists: Map of task_type -> specialist agent
    ///     name: Supervisor name
    ///
    /// Returns:
    ///     Initialized SupervisorAgent
    ///
    /// Errors:
    ///     - InvalidInput: If specialists map is empty
    ///     - OutOfMemory: If memory allocation fails
    pub fn init(
        allocator: Allocator,
        planner: Planner,
        specialists: std.StringHashMap(Agent),
        name: []const u8,
    ) !*SupervisorAgent {
        if (specialists.count() == 0) {
            return AgentError.InvalidInput;
        }

        const self = try allocator.create(SupervisorAgent);
        errdefer allocator.destroy(self);

        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        // Clone specialists map
        var specialists_copy = std.StringHashMap(Agent).init(allocator);
        errdefer specialists_copy.deinit();

        var it = specialists.iterator();
        while (it.next()) |entry| {
            const key_copy = try allocator.dupe(u8, entry.key_ptr.*);
            errdefer allocator.free(key_copy);
            try specialists_copy.put(key_copy, entry.value_ptr.*);
        }

        self.* = SupervisorAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .planner = planner,
            .specialists = specialists_copy,
            .owned_specialists = true,
        };

        return self;
    }

    /// Create agent interface for this supervisor
    pub fn agent(self: *SupervisorAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *SupervisorAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *SupervisorAgent = @ptrCast(@alignCast(ptr));

        var cap_set = std.StringHashMap(void).init(allocator);
        defer cap_set.deinit();

        // Add capabilities from all specialists
        var it = self.specialists.valueIterator();
        while (it.next()) |agent_ptr| {
            const caps = try agent_ptr.capabilities(allocator);
            defer allocator.free(caps);

            for (caps) |cap| {
                try cap_set.put(cap, {});
            }
        }

        // Add supervisor-specific capabilities
        try cap_set.put("supervisor", {});
        try cap_set.put("hierarchical", {});
        try cap_set.put("task_decomposition", {});
        try cap_set.put("coordination", {});

        // Convert set to slice
        var capabilities = try allocator.alloc([]const u8, cap_set.count());
        var i: usize = 0;
        var cap_it = cap_set.keyIterator();
        while (cap_it.next()) |key| {
            capabilities[i] = try allocator.dupe(u8, key.*);
            i += 1;
        }

        return capabilities;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *SupervisorAgent = @ptrCast(@alignCast(ptr));

        // Step 1: Decompose task into subtasks
        const subtasks = self.planner.plan(self.allocator, message) catch {
            return AgentError.ProcessingFailed;
        };
        defer {
            for (subtasks) |*subtask| {
                subtask.deinit();
            }
            self.allocator.free(subtasks);
        }

        if (subtasks.len == 0) {
            return AgentError.ProcessingFailed;
        }

        // Step 2: Execute subtasks with specialists
        const results = self.allocator.alloc(Message, subtasks.len) catch {
            return AgentError.ProcessingFailed;
        };
        errdefer self.allocator.free(results);

        var result_count: usize = 0;
        errdefer {
            for (results[0..result_count]) |*r| {
                r.deinit();
            }
            self.allocator.free(results);
        }

        for (subtasks, 0..) |subtask, i| {
            // Get specialist for this task type
            const specialist = self.specialists.get(subtask.task_type) orelse {
                // Unknown task type - create error message
                results[i] = Message.withText(
                    self.allocator,
                    .assistant,
                    "Unknown specialist type",
                ) catch {
                    continue;
                };
                result_count += 1;
                continue;
            };

            // Execute specialist
            const result = specialist.process(subtask.message) catch {
                // Specialist failed - create error message
                results[i] = Message.withText(
                    self.allocator,
                    .assistant,
                    "Specialist processing failed",
                ) catch {
                    continue;
                };
                result_count += 1;
                continue;
            };

            switch (result) {
                .ok => |msg| {
                    results[i] = msg;
                    result_count += 1;
                },
                .err => {
                    // Create error placeholder
                    results[i] = Message.withText(
                        self.allocator,
                        .assistant,
                        "Specialist returned error",
                    ) catch {
                        continue;
                    };
                    result_count += 1;
                },
            }
        }

        // Ensure we got all results
        if (result_count != subtasks.len) {
            for (results[0..result_count]) |*r| {
                r.deinit();
            }
            self.allocator.free(results);
            return AgentError.ProcessingFailed;
        }

        // Step 3: Synthesize results
        const synthesized = self.planner.synthesize(self.allocator, results) catch {
            for (results) |*r| {
                r.deinit();
            }
            self.allocator.free(results);
            return AgentError.ProcessingFailed;
        };

        // Clean up results after synthesis
        for (results) |*r| {
            r.deinit();
        }
        self.allocator.free(results);

        // TODO: Add metadata: subtask_count, specialists_used, execution_order

        return Result{ .ok = synthesized };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SupervisorAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *SupervisorAgent) void {
        self.allocator.free(self.agent_name);

        if (self.owned_specialists) {
            // Free specialist map keys
            var it = self.specialists.keyIterator();
            while (it.next()) |key| {
                self.allocator.free(key.*);
            }
        }
        self.specialists.deinit();

        self.allocator.destroy(self);
    }
};

/// Simple planner that creates mock subtasks
pub const SimplePlanner = struct {
    allocator: Allocator,
    planning_agent: Agent,

    pub fn init(allocator: Allocator, planning_agent: Agent) !*SimplePlanner {
        const self = try allocator.create(SimplePlanner);
        self.* = SimplePlanner{
            .allocator = allocator,
            .planning_agent = planning_agent,
        };
        return self;
    }

    pub fn planner(self: *SimplePlanner) Planner {
        return Planner{
            .ptr = self,
            .vtable = &.{
                .plan = planImpl,
                .synthesize = synthesizeImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn planImpl(ptr: *anyopaque, allocator: Allocator, message: Message) AgentError![]Subtask {
        const self: *SimplePlanner = @ptrCast(@alignCast(ptr));

        // In a real implementation, would use planning_agent to decompose task
        // For now, create mock subtasks based on message content
        _ = self.planning_agent;

        const content = message.contentAsText() catch {
            return AgentError.ProcessingFailed;
        };

        // Simple heuristic: if message mentions multiple topics, split them
        // For demo purposes, create 2 subtasks
        const subtasks = allocator.alloc(Subtask, 2) catch {
            return AgentError.ProcessingFailed;
        };
        errdefer allocator.free(subtasks);

        // Create subtask 1
        const msg1_text = std.fmt.allocPrint(
            allocator,
            "Subtask 1: Research phase for '{s}'",
            .{content},
        ) catch {
            allocator.free(subtasks);
            return AgentError.ProcessingFailed;
        };
        errdefer allocator.free(msg1_text);

        const msg1 = Message.withText(allocator, .user, msg1_text) catch {
            allocator.free(msg1_text);
            allocator.free(subtasks);
            return AgentError.ProcessingFailed;
        };
        allocator.free(msg1_text);

        const metadata1 = std.StringHashMap([]const u8).init(allocator);

        subtasks[0] = Subtask{
            .task_type = "research",
            .message = msg1,
            .metadata = metadata1,
        };

        // Create subtask 2
        const msg2_text = std.fmt.allocPrint(
            allocator,
            "Subtask 2: Analysis phase for '{s}'",
            .{content},
        ) catch {
            subtasks[0].deinit();
            allocator.free(subtasks);
            return AgentError.ProcessingFailed;
        };
        errdefer allocator.free(msg2_text);

        const msg2 = Message.withText(allocator, .user, msg2_text) catch {
            allocator.free(msg2_text);
            subtasks[0].deinit();
            allocator.free(subtasks);
            return AgentError.ProcessingFailed;
        };
        allocator.free(msg2_text);

        const metadata2 = std.StringHashMap([]const u8).init(allocator);

        subtasks[1] = Subtask{
            .task_type = "analysis",
            .message = msg2,
            .metadata = metadata2,
        };

        return subtasks;
    }

    fn synthesizeImpl(ptr: *anyopaque, allocator: Allocator, results: []const Message) AgentError!Message {
        _ = ptr;

        if (results.len == 0) {
            return AgentError.ProcessingFailed;
        }

        // Calculate total size for concatenation
        var total_size: usize = 0;
        for (results, 0..) |msg, i| {
            const content = msg.contentAsText() catch continue;
            total_size += content.len;
            if (i < results.len - 1) {
                total_size += 6; // "\n\n---\n"
            }
        }

        // Allocate and concatenate
        const combined = allocator.alloc(u8, total_size) catch {
            return AgentError.ProcessingFailed;
        };
        errdefer allocator.free(combined);

        var offset: usize = 0;
        for (results, 0..) |msg, i| {
            const content = msg.contentAsText() catch continue;
            @memcpy(combined[offset..][0..content.len], content);
            offset += content.len;
            if (i < results.len - 1) {
                const separator = "\n\n---\n";
                @memcpy(combined[offset..][0..separator.len], separator);
                offset += separator.len;
            }
        }

        const msg = Message.withText(allocator, .assistant, combined) catch {
            allocator.free(combined);
            return AgentError.ProcessingFailed;
        };
        allocator.free(combined);
        return msg;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SimplePlanner = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *SimplePlanner) void {
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Tests
// ============================================================================

test "SupervisorAgent: basic coordination" {
    // Skip test for now - requires mock infrastructure
    // TODO: Implement full test suite
}

test "SimplePlanner: task decomposition" {
    const allocator = std.testing.allocator;

    var msg = try Message.withText(allocator, .user, "Complete project");
    defer msg.deinit();

    const mock_agent = Agent{
        .ptr = undefined,
        .vtable = undefined,
    };

    var planner_impl = try SimplePlanner.init(allocator, mock_agent);
    defer planner_impl.deinit();

    const subtasks = try planner_impl.planner().plan(allocator, msg);
    defer {
        for (subtasks) |*subtask| {
            subtask.deinit();
        }
        allocator.free(subtasks);
    }

    try std.testing.expect(subtasks.len == 2);
}
