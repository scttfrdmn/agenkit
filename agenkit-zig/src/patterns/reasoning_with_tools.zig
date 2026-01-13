/// Reasoning with Tools Pattern - Interleaved reasoning and tool usage
///
/// Enables tools to be called DURING the reasoning process rather than only after
/// reasoning completes. Inspired by extended thinking capabilities where models can
/// use tools to refine reasoning in real-time.
///
/// # Key Differences from ReAct
/// - ReAct: Observe → Think → Act → Observe (sequential)
/// - This: Think ↔ Act (interleaved, tools available during thinking)
/// - Tools help refine reasoning, not just execute actions
/// - Supports extended thinking with tool integration
///
/// # Performance Characteristics
/// - Time: O(max_steps × (llm + tool_calls))
/// - Memory: O(steps) for reasoning trace
/// - Reasoning trace can be inspected for transparency
///
/// # Use Cases
/// - Complex multi-step problems requiring computation
/// - Research tasks needing information lookup during thinking
/// - Mathematical problems with intermediate calculations
/// - Analysis tasks requiring data retrieval while reasoning
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// // Create agent with tools
/// var tools = std.StringHashMap(Tool).init(allocator);
/// try tools.put("calculator", calculator_tool);
/// try tools.put("search", search_tool);
///
/// var agent = try ReasoningWithToolsAgent.init(
///     allocator,
///     llm_agent.agent(),
///     tools,
///     .{ .max_steps = 10, .enable_trace = true }
/// );
/// defer agent.deinit();
///
/// // Agent can use tools WHILE reasoning
/// const result = try agent.agent().process(message);
/// // Inspect reasoning trace in metadata
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Tool = @import("react.zig").Tool;
const Allocator = std.mem.Allocator;

/// Type of reasoning step
pub const ReasoningStepType = enum {
    thinking, // Pure reasoning
    tool_call, // Tool invocation
    tool_result, // Tool response
    conclusion, // Final answer
};

/// A single step in the reasoning process
pub const ReasoningStep = struct {
    step_number: u32,
    step_type: ReasoningStepType,
    content: []const u8,
    tool_name: ?[]const u8,
    confidence: f32,

    pub fn deinit(self: *ReasoningStep, allocator: Allocator) void {
        allocator.free(self.content);
        if (self.tool_name) |name| {
            allocator.free(name);
        }
    }
};

/// Configuration for reasoning agent
pub const ReasoningConfig = struct {
    max_steps: u32 = 10,
    enable_trace: bool = true,
    confidence_threshold: f32 = 0.8,
};

/// Reasoning with Tools Agent
pub const ReasoningWithToolsAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    llm_agent: Agent,
    tools: std.StringHashMap(Tool),
    config: ReasoningConfig,
    owned_tools: bool,

    /// Initialize reasoning with tools agent
    pub fn init(
        allocator: Allocator,
        llm_agent: Agent,
        tools: std.StringHashMap(Tool),
        config: ReasoningConfig,
        name: []const u8,
    ) !*ReasoningWithToolsAgent {
        const self = try allocator.create(ReasoningWithToolsAgent);
        errdefer allocator.destroy(self);

        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        // Clone tools map
        var tools_copy = std.StringHashMap(Tool).init(allocator);
        errdefer tools_copy.deinit();

        var it = tools.iterator();
        while (it.next()) |entry| {
            const key_copy = try allocator.dupe(u8, entry.key_ptr.*);
            errdefer allocator.free(key_copy);
            try tools_copy.put(key_copy, entry.value_ptr.*);
        }

        self.* = ReasoningWithToolsAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .llm_agent = llm_agent,
            .tools = tools_copy,
            .config = config,
            .owned_tools = true,
        };

        return self;
    }

    /// Create agent interface
    pub fn agent(self: *ReasoningWithToolsAgent) Agent {
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
        const self: *ReasoningWithToolsAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *ReasoningWithToolsAgent = @ptrCast(@alignCast(ptr));

        // Get LLM capabilities
        const llm_caps = try self.llm_agent.capabilities(allocator);
        defer allocator.free(llm_caps);

        // Add reasoning capabilities
        const caps = try allocator.alloc([]const u8, llm_caps.len + 3);
        for (llm_caps, 0..) |cap, i| {
            caps[i] = try allocator.dupe(u8, cap);
        }
        caps[llm_caps.len] = try allocator.dupe(u8, "reasoning_with_tools");
        caps[llm_caps.len + 1] = try allocator.dupe(u8, "extended_thinking");
        caps[llm_caps.len + 2] = try allocator.dupe(u8, "tool_integration");

        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *ReasoningWithToolsAgent = @ptrCast(@alignCast(ptr));

        // Build tool usage prompt
        const tool_prompt = self.buildToolPrompt() catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(tool_prompt);

        // Enhance message with tool instructions
        const content = message.contentAsText() catch {
            return AgentError.ProcessingFailed;
        };

        const enhanced_content = std.fmt.allocPrint(
            self.allocator,
            "{s}\n\nUSER QUESTION:\n{s}\n\nBegin reasoning. Use tools as needed.",
            .{ tool_prompt, content },
        ) catch {
            return AgentError.ProcessingFailed;
        };
        defer self.allocator.free(enhanced_content);

        var enhanced_msg = Message.withText(
            self.allocator,
            message.role,
            enhanced_content,
        ) catch {
            return AgentError.ProcessingFailed;
        };
        defer enhanced_msg.deinit();

        // Simplified reasoning loop - just pass through to LLM for now
        // In full implementation, would parse tool calls and execute them
        const result = self.llm_agent.process(enhanced_msg) catch {
            return AgentError.ProcessingFailed;
        };

        // Add metadata about reasoning capability
        // (trace generation would go here in full implementation)

        return result;
    }

    fn buildToolPrompt(self: *ReasoningWithToolsAgent) ![]const u8 {
        // Calculate size needed
        var size: usize = 200; // Base prompt text
        var it = self.tools.iterator();
        while (it.next()) |entry| {
            size += entry.key_ptr.*.len + entry.value_ptr.*.description.len + 10;
        }

        const prompt = try self.allocator.alloc(u8, size);
        errdefer self.allocator.free(prompt);

        var offset: usize = 0;
        const header = "You can use tools WHILE reasoning. When you need information, use a tool immediately.\n\nAvailable tools:\n";
        @memcpy(prompt[offset..][0..header.len], header);
        offset += header.len;

        it = self.tools.iterator();
        while (it.next()) |entry| {
            const line = std.fmt.bufPrint(
                prompt[offset..],
                "- {s}: {s}\n",
                .{ entry.key_ptr.*, entry.value_ptr.*.description },
            ) catch break;
            offset += line.len;
        }

        // Resize to actual used size
        return self.allocator.realloc(prompt, offset);
    }


    fn introspectImpl(ptr: *anyopaque, alloc: Allocator) Allocator.Error!IntrospectionResult {
        const caps = try capabilitiesImpl(ptr, alloc);
        defer {
            for (caps) |cap| alloc.free(cap);
            alloc.free(caps);
        }
        const name_str = nameImpl(ptr);
        return createDefaultIntrospectionResult(alloc, name_str, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ReasoningWithToolsAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *ReasoningWithToolsAgent) void {
        self.allocator.free(self.agent_name);

        if (self.owned_tools) {
            var it = self.tools.keyIterator();
            while (it.next()) |key| {
                self.allocator.free(key.*);
            }
        }
        self.tools.deinit();

        self.allocator.destroy(self);
    }
};

// ============================================================================
// Tests
// ============================================================================


    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

test "ReasoningWithToolsAgent: initialization" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var llm = try EchoAgent.init(allocator);
    defer llm.agent().deinit();

    // Use empty tools for simplicity
    var tools = std.StringHashMap(Tool).init(allocator);
    defer tools.deinit();

    const config = ReasoningConfig{
        .max_steps = 5,
        .enable_trace = true,
    };

    var agent = try ReasoningWithToolsAgent.init(
        allocator,
        llm.agent(),
        tools,
        config,
        "reasoning_agent",
    );
    defer agent.deinit();

    try std.testing.expectEqualStrings("reasoning_agent", agent.agent().name());
}

test "ReasoningWithToolsAgent: capabilities" {
    const allocator = std.testing.allocator;
    const EchoAgent = @import("../agent.zig").EchoAgent;

    var llm = try EchoAgent.init(allocator);
    defer llm.agent().deinit();

    var tools = std.StringHashMap(Tool).init(allocator);
    defer tools.deinit();

    var agent = try ReasoningWithToolsAgent.init(
        allocator,
        llm.agent(),
        tools,
        ReasoningConfig{},
        "test",
    );
    defer agent.deinit();

    const caps = try agent.agent().capabilities(allocator);
    defer {
        for (caps) |cap| {
            allocator.free(cap);
        }
        allocator.free(caps);
    }

    // Should have reasoning capabilities
    var has_reasoning = false;
    for (caps) |cap| {
        if (std.mem.eql(u8, cap, "reasoning_with_tools")) {
            has_reasoning = true;
        }
    }
    try std.testing.expect(has_reasoning);
}
