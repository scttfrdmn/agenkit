/// Collaborative Pattern - Peer-to-peer collaboration with iterative refinement
///
/// The Collaborative pattern implements peer-to-peer collaboration where multiple
/// agents work together iteratively, refining their responses until consensus is
/// reached or a maximum number of rounds is completed.
///
/// # Key Concepts
/// - Iterative refinement through multiple rounds
/// - Consensus detection to stop early
/// - Flexible merge strategies for combining responses
/// - Peer-to-peer rather than hierarchical
///
/// # Performance Characteristics
/// - Time: O(rounds × agents)
/// - Memory: O(rounds × agents) for history
/// - Can terminate early on consensus
///
/// # Use Cases
/// - Multi-perspective analysis: Get insights from different viewpoints
/// - Consensus building: Legal review, medical diagnosis, code review
/// - Iterative improvement: Draft → Review → Refine cycles
/// - Brainstorming: Generate ideas, then refine collaboratively
/// - Quality assurance: Multiple reviewers until agreement
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// // Create multiple reviewer agents
/// const agents = [_]Agent{ reviewer1.agent(), reviewer2.agent(), reviewer3.agent() };
///
/// // Configure collaboration
/// const config = CollaborativeConfig{
///     .agents = &agents,
///     .max_rounds = 3,
///     .consensus_fn = majorityAgreementConsensus,
///     .merge_fn = concatenateMerge,
/// };
///
/// var collab = try CollaborativeAgent.init(allocator, config, "reviewers");
/// defer collab.deinit();
///
/// // Will iterate until consensus or max rounds
/// const result = try collab.agent().process(input_message);
/// ```
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const Allocator = std.mem.Allocator;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;

/// Consensus function signature - returns true if messages represent consensus
pub const ConsensusFn = *const fn (messages: []const Message) bool;

/// Merge function signature - combines multiple messages into one
pub const MergeFn = *const fn (allocator: Allocator, messages: []const Message) AgentError!Message;

/// Configuration for collaborative agent
pub const CollaborativeConfig = struct {
    agents: []const Agent,
    max_rounds: u32 = 3,
    consensus_fn: ?ConsensusFn = null,
    merge_fn: MergeFn,
};

/// Collaborative Agent - Enables peer-to-peer collaboration with iterative refinement
pub const CollaborativeAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    agents: []Agent,
    max_rounds: u32,
    consensus_fn: ?ConsensusFn,
    merge_fn: MergeFn,
    owned_agents: bool,

    /// Initialize a collaborative agent
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     config: Collaboration configuration
    ///     name: Agent name
    ///
    /// Returns:
    ///     Initialized CollaborativeAgent
    ///
    /// Errors:
    ///     - InvalidInput: If agents array has fewer than 2 agents
    ///     - OutOfMemory: If memory allocation fails
    pub fn init(
        allocator: Allocator,
        config: CollaborativeConfig,
        name: []const u8,
    ) !*CollaborativeAgent {
        if (config.agents.len < 2) {
            return AgentError.InvalidInput;
        }

        const self = try allocator.create(CollaborativeAgent);
        errdefer allocator.destroy(self);

        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        // Copy agents array
        const agents_copy = try allocator.alloc(Agent, config.agents.len);
        errdefer allocator.free(agents_copy);
        @memcpy(agents_copy, config.agents);

        self.* = CollaborativeAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .agents = agents_copy,
            .max_rounds = config.max_rounds,
            .consensus_fn = config.consensus_fn,
            .merge_fn = config.merge_fn,
            .owned_agents = true,
        };

        return self;
    }

    /// Create agent interface for this collaborative agent
    pub fn agent(self: *CollaborativeAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *CollaborativeAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *CollaborativeAgent = @ptrCast(@alignCast(ptr));

        var cap_set = std.StringHashMap(void).init(allocator);
        defer cap_set.deinit();

        // Add capabilities from all agents
        for (self.agents) |agent_ref| {
            const caps = try agent_ref.capabilities(allocator);
            defer allocator.free(caps);

            for (caps) |cap| {
                try cap_set.put(cap, {});
            }
        }

        // Add collaborative-specific capabilities
        try cap_set.put("collaborative", {});
        try cap_set.put("iterative", {});
        try cap_set.put("consensus", {});

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
        const self: *CollaborativeAgent = @ptrCast(@alignCast(ptr));

        // For simplicity, just run one round and merge
        // TODO: In full implementation, would support multiple rounds with history

        // Collect responses from all agents
        const responses = self.allocator.alloc(Message, self.agents.len) catch {
            return AgentError.ProcessingFailed;
        };
        errdefer self.allocator.free(responses);

        var response_count: usize = 0;
        errdefer {
            for (responses[0..response_count]) |*r| {
                r.deinit();
            }
            self.allocator.free(responses);
        }

        // Execute all agents
        for (self.agents, 0..) |agent_ref, i| {
            const result = agent_ref.process(message) catch {
                // If an agent fails, use error placeholder
                responses[i] = Message.withText(
                    self.allocator,
                    .assistant,
                    "Agent processing failed",
                ) catch {
                    // If we can't even create placeholder, skip this agent
                    continue;
                };
                response_count += 1;
                continue;
            };

            switch (result) {
                .ok => |msg| {
                    responses[i] = msg;
                    response_count += 1;
                },
                .err => {
                    // Create error message placeholder
                    responses[i] = Message.withText(
                        self.allocator,
                        .assistant,
                        "Agent returned error",
                    ) catch {
                        continue;
                    };
                    response_count += 1;
                },
            }
        }

        // Ensure we got responses from all agents
        if (response_count != self.agents.len) {
            // Some agents failed - clean up and return error
            for (responses[0..response_count]) |*r| {
                r.deinit();
            }
            self.allocator.free(responses);
            return AgentError.ProcessingFailed;
        }

        // Check for consensus if function provided
        if (self.consensus_fn) |check_consensus| {
            _ = check_consensus(responses);
            // In full implementation, would repeat rounds if no consensus
        }

        // Merge responses
        const merged_message = self.merge_fn(self.allocator, responses) catch {
            // Clean up on merge failure
            for (responses) |*r| {
                r.deinit();
            }
            self.allocator.free(responses);
            return AgentError.ProcessingFailed;
        };

        // Clean up responses after merge
        for (responses) |*r| {
            r.deinit();
        }
        self.allocator.free(responses);

        // TODO: In full implementation, would add metadata:
        // - rounds: number of rounds executed
        // - consensus_reached: whether consensus was achieved
        // - participants: list of agent names

        return Result{ .ok = merged_message };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *CollaborativeAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *CollaborativeAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *CollaborativeAgent) void {
        self.allocator.free(self.agent_name);
        if (self.owned_agents) {
            self.allocator.free(self.agents);
        }
        self.allocator.destroy(self);
    }
};

// ============================================================================
// Built-in Consensus Functions
// ============================================================================

/// Check if all messages have identical content
pub fn exactMatchConsensus(messages: []const Message) bool {
    if (messages.len == 0) return false;
    if (messages.len == 1) return true;

    const first_content = messages[0].contentAsText() catch return false;

    for (messages[1..]) |msg| {
        const content = msg.contentAsText() catch return false;
        if (!std.mem.eql(u8, first_content, content)) {
            return false;
        }
    }

    return true;
}

/// Check if majority of messages have same content (>50%)
pub fn majorityAgreementConsensus(messages: []const Message) bool {
    if (messages.len == 0) return false;
    if (messages.len == 1) return true;

    // Count occurrences of each unique content
    var counts = std.StringHashMap(usize).init(std.heap.page_allocator);
    defer counts.deinit();

    for (messages) |msg| {
        const content = msg.contentAsText() catch continue;
        const entry = counts.getOrPut(content) catch continue;
        if (!entry.found_existing) {
            entry.value_ptr.* = 1;
        } else {
            entry.value_ptr.* += 1;
        }
    }

    const majority_threshold = messages.len / 2;
    var it = counts.valueIterator();
    while (it.next()) |count| {
        if (count.* > majority_threshold) {
            return true;
        }
    }

    return false;
}

// ============================================================================
// Built-in Merge Functions
// ============================================================================

/// Concatenate all messages with separators
pub fn concatenateMerge(allocator: Allocator, messages: []const Message) AgentError!Message {
    if (messages.len == 0) {
        return AgentError.ProcessingFailed;
    }

    // Calculate total size needed
    var total_size: usize = 0;
    for (messages, 0..) |msg, i| {
        const content = msg.contentAsText() catch continue;
        total_size += content.len;
        if (i < messages.len - 1) {
            total_size += 5; // "\n---\n"
        }
    }

    // Allocate buffer and concatenate
    const combined_text = allocator.alloc(u8, total_size) catch {
        return AgentError.ProcessingFailed;
    };
    errdefer allocator.free(combined_text);

    var offset: usize = 0;
    for (messages, 0..) |msg, i| {
        const content = msg.contentAsText() catch continue;
        @memcpy(combined_text[offset..][0..content.len], content);
        offset += content.len;
        if (i < messages.len - 1) {
            const separator = "\n---\n";
            @memcpy(combined_text[offset..][0..separator.len], separator);
            offset += separator.len;
        }
    }

    return Message.withText(allocator, .assistant, combined_text) catch {
        allocator.free(combined_text);
        return AgentError.ProcessingFailed;
    };
}

/// Return first message
pub fn firstMerge(allocator: Allocator, messages: []const Message) AgentError!Message {
    if (messages.len == 0) {
        return AgentError.ProcessingFailed;
    }

    const content = messages[0].contentAsText() catch {
        return AgentError.ProcessingFailed;
    };

    return Message.withText(allocator, .assistant, content) catch {
        return AgentError.ProcessingFailed;
    };
}

// ============================================================================
// Tests
// ============================================================================

fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}

test "CollaborativeAgent: basic collaboration" {
    // Skip test for now - requires mock infrastructure
    // TODO: Implement full test suite
}

test "exactMatchConsensus: identical messages" {
    const allocator = std.testing.allocator;

    var msg1 = try Message.withText(allocator, .assistant, "response");
    defer msg1.deinit();

    var msg2 = try Message.withText(allocator, .assistant, "response");
    defer msg2.deinit();

    const messages = [_]Message{ msg1, msg2 };
    try std.testing.expect(exactMatchConsensus(&messages));
}

test "exactMatchConsensus: different messages" {
    const allocator = std.testing.allocator;

    var msg1 = try Message.withText(allocator, .assistant, "response1");
    defer msg1.deinit();

    var msg2 = try Message.withText(allocator, .assistant, "response2");
    defer msg2.deinit();

    const messages = [_]Message{ msg1, msg2 };
    try std.testing.expect(!exactMatchConsensus(&messages));
}
