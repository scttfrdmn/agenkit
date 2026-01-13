/// Router Pattern - Conditional agent selection based on message classification
///
/// The Router pattern implements conditional agent selection where a classifier
/// determines the message intent/category, then routes the request to an
/// appropriate specialist agent.
///
/// # Key Concepts
/// - Intent/category classification
/// - Conditional routing to specialists
/// - Single agent execution per request
/// - Dynamic agent selection based on input
///
/// # Performance Characteristics
/// - Time: O(classification + selected agent)
/// - Memory: O(1) - only one agent executes
/// - Efficient single-path execution
///
/// # Use Cases
/// - Customer service: route to billing, technical, account agents
/// - Content moderation: route to spam, abuse, quality agents
/// - Language routing: route to language-specific agents
/// - Skill-based routing: route to domain expert agents
/// - Intent-based chatbots: route to booking, info, support agents
///
/// # Example
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// // Create keyword map
/// var keywords = std.StringHashMap([]const []const u8).init(allocator);
/// const billing_keywords = &[_][]const u8{ "payment", "invoice", "charge" };
/// try keywords.put("billing", billing_keywords);
///
/// // Create classifier
/// var classifier = try SimpleClassifier.init(allocator, keywords);
/// defer classifier.deinit();
///
/// // Create agent map
/// var agents = std.StringHashMap(Agent).init(allocator);
/// try agents.put("billing", billing_agent.agent());
/// try agents.put("technical", tech_agent.agent());
///
/// // Create router
/// var router = try RouterAgent.init(
///     allocator,
///     classifier.classifier(),
///     agents,
///     "technical",  // default
///     "router"
/// );
/// defer router.deinit();
///
/// const result = try router.agent().process(input_message);
/// ```

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Classifier interface - agents that can classify messages into categories
pub const Classifier = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        classify: *const fn (ptr: *anyopaque, allocator: Allocator, message: Message) AgentError![]const u8,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Classify a message into a category
    pub fn classify(self: Classifier, allocator: Allocator, message: Message) AgentError![]const u8 {
        return self.vtable.classify(self.ptr, allocator, message);
    }

    /// Clean up classifier resources
    pub fn deinit(self: Classifier) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Router Agent - Routes messages to appropriate agents based on classification
pub const RouterAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    classifier: Classifier,
    agents: std.StringHashMap(Agent),
    default_key: ?[]const u8,
    owned_agents: bool,

    /// Initialize a router agent
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     classifier: Classifier to determine routing
    ///     agents: Map of category -> agent
    ///     default_key: Optional fallback category
    ///     name: Router name for identification
    ///
    /// Returns:
    ///     Initialized RouterAgent
    ///
    /// Errors:
    ///     - OutOfMemory: If memory allocation fails
    pub fn init(
        allocator: Allocator,
        classifier: Classifier,
        agents: std.StringHashMap(Agent),
        default_key: ?[]const u8,
        name: []const u8,
    ) !*RouterAgent {
        if (agents.count() == 0) {
            return AgentError.InvalidInput;
        }

        // Validate default key if provided
        if (default_key) |key| {
            if (!agents.contains(key)) {
                return AgentError.InvalidInput;
            }
        }

        const self = try allocator.create(RouterAgent);
        errdefer allocator.destroy(self);

        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        const default_key_copy = if (default_key) |key|
            try allocator.dupe(u8, key)
        else
            null;
        errdefer if (default_key_copy) |key| allocator.free(key);

        // Clone the agents map
        var agents_copy = std.StringHashMap(Agent).init(allocator);
        errdefer agents_copy.deinit();

        var it = agents.iterator();
        while (it.next()) |entry| {
            const key_copy = try allocator.dupe(u8, entry.key_ptr.*);
            errdefer allocator.free(key_copy);
            try agents_copy.put(key_copy, entry.value_ptr.*);
        }

        self.* = RouterAgent{
            .allocator = allocator,
            .agent_name = name_copy,
            .classifier = classifier,
            .agents = agents_copy,
            .default_key = default_key_copy,
            .owned_agents = true,
        };

        return self;
    }

    /// Create agent interface for this router
    pub fn agent(self: *RouterAgent) Agent {
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
        const self: *RouterAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *RouterAgent = @ptrCast(@alignCast(ptr));

        var cap_set = std.StringHashMap(void).init(allocator);
        defer cap_set.deinit();

        // Add capabilities from all agents
        var it = self.agents.valueIterator();
        while (it.next()) |agent_ptr| {
            const caps = try agent_ptr.capabilities(allocator);
            defer allocator.free(caps);

            for (caps) |cap| {
                try cap_set.put(cap, {});
            }
        }

        // Add router-specific capabilities
        try cap_set.put("router", {});
        try cap_set.put("conditional", {});
        try cap_set.put("classification", {});

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
        const self: *RouterAgent = @ptrCast(@alignCast(ptr));

        // Step 1: Classify the message
        const category = self.classifier.classify(self.allocator, message) catch |err| {
            return err;
        };
        defer self.allocator.free(category);

        // Step 2: Select agent based on category
        var selected_agent: ?Agent = self.agents.get(category);
        var final_category = category;

        if (selected_agent == null) {
            // Try default agent if configured
            if (self.default_key) |default| {
                selected_agent = self.agents.get(default);
                final_category = default;
            } else {
                return AgentError.ProcessingFailed;
            }
        }

        // Step 3: Execute selected agent
        const agent_to_use = selected_agent.?;
        const result = agent_to_use.process(message) catch |err| {
            return err;
        };

        // Add routing metadata (note: in production would actually modify result.message.metadata)
        // For now, just return the result
        // In a full implementation, would add: routed_category, routed_agent, available_routes

        return result;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *RouterAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *RouterAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *RouterAgent) void {
        self.allocator.free(self.agent_name);

        if (self.default_key) |key| {
            self.allocator.free(key);
        }

        // Free agents map keys
        var it = self.agents.keyIterator();
        while (it.next()) |key| {
            self.allocator.free(key.*);
        }
        self.agents.deinit();

        self.allocator.destroy(self);
    }
};

/// Simple keyword-based classifier
///
/// This classifier uses basic keyword matching to determine message category.
/// For each category, it counts keyword matches and returns the category
/// with the most matches.
pub const SimpleClassifier = struct {
    allocator: Allocator,
    keywords: std.StringHashMap([]const []const u8),

    /// Initialize a simple keyword classifier
    ///
    /// Args:
    ///     allocator: Memory allocator
    ///     keywords: Map of category -> keyword list
    ///
    /// Returns:
    ///     Initialized SimpleClassifier
    pub fn init(allocator: Allocator, keywords: std.StringHashMap([]const []const u8)) !*SimpleClassifier {
        if (keywords.count() == 0) {
            return AgentError.InvalidInput;
        }

        const self = try allocator.create(SimpleClassifier);
        errdefer allocator.destroy(self);

        // Clone the keywords map
        var keywords_copy = std.StringHashMap([]const []const u8).init(allocator);
        errdefer keywords_copy.deinit();

        var it = keywords.iterator();
        while (it.next()) |entry| {
            const key_copy = try allocator.dupe(u8, entry.key_ptr.*);
            errdefer allocator.free(key_copy);

            const keyword_list = entry.value_ptr.*;
            const list_copy = try allocator.alloc([]const u8, keyword_list.len);
            errdefer allocator.free(list_copy);

            for (keyword_list, 0..) |kw, i| {
                list_copy[i] = try allocator.dupe(u8, kw);
            }

            try keywords_copy.put(key_copy, list_copy);
        }

        self.* = SimpleClassifier{
            .allocator = allocator,
            .keywords = keywords_copy,
        };

        return self;
    }

    /// Create classifier interface
    pub fn classifier(self: *SimpleClassifier) Classifier {
        return Classifier{
            .ptr = self,
            .vtable = &.{
                .classify = classifyImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn classifyImpl(ptr: *anyopaque, allocator: Allocator, message: Message) AgentError![]const u8 {
        const self: *SimpleClassifier = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch return AgentError.ProcessingFailed;
        const content_lower = std.ascii.allocLowerString(allocator, content) catch return AgentError.ProcessingFailed;
        defer allocator.free(content_lower);

        var best_category: ?[]const u8 = null;
        var best_count: usize = 0;

        var it = self.keywords.iterator();
        while (it.next()) |entry| {
            const category = entry.key_ptr.*;
            const keyword_list = entry.value_ptr.*;

            var count: usize = 0;
            for (keyword_list) |keyword| {
                if (std.mem.indexOf(u8, content_lower, keyword)) |_| {
                    count += 1;
                }
            }

            if (count > best_count) {
                best_count = count;
                best_category = category;
            }
        }

        if (best_category) |category| {
            return allocator.dupe(u8, category) catch return AgentError.ProcessingFailed;
        }

        // If no keywords matched, return first category
        var it2 = self.keywords.iterator();
        const first_entry = it2.next() orelse return AgentError.ProcessingFailed;
        return allocator.dupe(u8, first_entry.key_ptr.*) catch return AgentError.ProcessingFailed;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SimpleClassifier = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *SimpleClassifier) void {
        var it = self.keywords.iterator();
        while (it.next()) |entry| {
            // Free keyword list
            const keyword_list = entry.value_ptr.*;
            for (keyword_list) |kw| {
                self.allocator.free(kw);
            }
            self.allocator.free(keyword_list);

            // Free category key
            self.allocator.free(entry.key_ptr.*);
        }
        self.keywords.deinit();

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

test "RouterAgent: basic routing" {
    // Skip test for now - requires more complex mock infrastructure
    // TODO: Implement full test suite
}

test "SimpleClassifier: keyword matching" {
    const allocator = std.testing.allocator;

    // Create keyword map
    var keywords = std.StringHashMap([]const []const u8).init(allocator);
    defer {
        // Clean up keyword map after classifier init
        var it = keywords.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.value_ptr.*);
        }
        keywords.deinit();
    }

    const billing_keywords = try allocator.alloc([]const u8, 2);
    billing_keywords[0] = "payment";
    billing_keywords[1] = "invoice";

    const tech_keywords = try allocator.alloc([]const u8, 2);
    tech_keywords[0] = "error";
    tech_keywords[1] = "bug";

    try keywords.put("billing", billing_keywords);
    try keywords.put("technical", tech_keywords);

    var classifier = try SimpleClassifier.init(allocator, keywords);
    defer classifier.deinit();

    // Test classification
    var msg = try Message.withText(allocator, .user, "I have a payment question");
    defer msg.deinit();

    const category = try classifier.classifier().classify(allocator, msg);
    defer allocator.free(category);

    try std.testing.expectEqualStrings("billing", category);
}
