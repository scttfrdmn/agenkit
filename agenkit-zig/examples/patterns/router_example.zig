//! Router Pattern Example
//!
//! This example demonstrates the Router pattern for conditional agent selection
//! based on message classification.
//!
//! Build: zig build
//! Run: zig build run-router

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const StreamCallbacks = agenkit.StreamCallbacks;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const RouterAgent = agenkit.patterns.RouterAgent;
const SimpleClassifier = agenkit.patterns.SimpleClassifier;

/// Mock specialist agent that responds with its specialty
const SpecialistAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,
    specialty: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, specialty: []const u8) !*SpecialistAgent {
        const self = try allocator.create(SpecialistAgent);
        self.* = .{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .specialty = try allocator.dupe(u8, specialty),
        };
        return self;
    }

    pub fn agent(self: *SpecialistAgent) Agent {
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
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = try allocator.dupe(u8, self.specialty);
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) agenkit.AgentError!agenkit.Result {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));

        const content = message.contentAsText() catch return agenkit.AgentError.ProcessingFailed;

        // Build response
        const response = std.fmt.allocPrint(
            self.allocator,
            "{s} specialist handling: {s}",
            .{ self.specialty, content },
        ) catch return agenkit.AgentError.ProcessingFailed;
        defer self.allocator.free(response);

        const response_msg = Message.withText(self.allocator, .assistant, response) catch return agenkit.AgentError.ProcessingFailed;
        return agenkit.Result{ .ok = response_msg };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SpecialistAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *SpecialistAgent) void {
        self.allocator.free(self.name);
        self.allocator.free(self.specialty);
        self.allocator.destroy(self);
    }
};


fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
    _ = ptr;
    _ = message;
    callbacks.onError(AgentError.NotImplemented);
}
pub fn main() !void {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Router Pattern Example ===\n\n", .{});

    // ========================================================================
    // Example 1: Customer Service Router
    // ========================================================================
    std.debug.print("Example 1: Customer Service Router\n", .{});
    std.debug.print("-----------------------------------\n", .{});

    // Create specialist agents
    var billing_agent = try SpecialistAgent.init(allocator, "BillingAgent", "Billing");
    defer billing_agent.deinit();

    var technical_agent = try SpecialistAgent.init(allocator, "TechnicalAgent", "Technical");
    defer technical_agent.deinit();

    var account_agent = try SpecialistAgent.init(allocator, "AccountAgent", "Account");
    defer account_agent.deinit();

    // Setup keyword classifier
    var keywords = std.StringHashMap([]const []const u8).init(allocator);
    defer {
        var it = keywords.iterator();
        while (it.next()) |entry| {
            const keyword_list = entry.value_ptr.*;
            for (keyword_list) |kw| {
                allocator.free(kw);
            }
            allocator.free(keyword_list);
        }
        keywords.deinit();
    }

    // Billing keywords
    const billing_keywords = try allocator.alloc([]const u8, 3);
    billing_keywords[0] = try allocator.dupe(u8, "payment");
    billing_keywords[1] = try allocator.dupe(u8, "invoice");
    billing_keywords[2] = try allocator.dupe(u8, "charge");
    try keywords.put("billing", billing_keywords);

    // Technical keywords
    const tech_keywords = try allocator.alloc([]const u8, 3);
    tech_keywords[0] = try allocator.dupe(u8, "error");
    tech_keywords[1] = try allocator.dupe(u8, "bug");
    tech_keywords[2] = try allocator.dupe(u8, "crash");
    try keywords.put("technical", tech_keywords);

    // Account keywords
    const account_keywords = try allocator.alloc([]const u8, 3);
    account_keywords[0] = try allocator.dupe(u8, "password");
    account_keywords[1] = try allocator.dupe(u8, "login");
    account_keywords[2] = try allocator.dupe(u8, "profile");
    try keywords.put("account", account_keywords);

    // Create classifier
    var classifier = try SimpleClassifier.init(allocator, keywords);
    defer classifier.deinit();

    // Create agent map
    var agents = std.StringHashMap(Agent).init(allocator);
    defer agents.deinit();

    try agents.put("billing", billing_agent.agent());
    try agents.put("technical", technical_agent.agent());
    try agents.put("account", account_agent.agent());

    // Create router with technical as default
    var router = try RouterAgent.init(
        allocator,
        classifier.classifier(),
        agents,
        "technical",
        "CustomerServiceRouter",
    );
    defer router.deinit();

    // Test routing with different messages
    const test_messages = [_][]const u8{
        "I have a question about my invoice",
        "The app keeps crashing",
        "I forgot my password",
        "Help me with something", // Will use default
    };

    for (test_messages) |content| {
        std.debug.print("\nInput: \"{s}\"\n", .{content});

        var msg = try Message.withText(allocator, .user, content);
        defer msg.deinit();

        const result = router.agent().process(msg) catch |err| {
            std.debug.print("Error: {}\n", .{err});
            continue;
        };

        switch (result) {
            .ok => |response| {
                var mutable_response = response;
                defer mutable_response.deinit();
                const response_text = mutable_response.contentAsText() catch "No content";
                std.debug.print("Routed to: {s}\n", .{response_text});
            },
            .err => |e| {
                std.debug.print("Error: {}\n", .{e});
            },
        }
    }

    std.debug.print("\n=== Router Pattern Complete ===\n\n", .{});
}
