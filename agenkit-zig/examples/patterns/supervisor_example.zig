//! Supervisor Pattern Example
//!
//! This example demonstrates the Supervisor pattern for hierarchical
//! coordination where a supervisor decomposes tasks and delegates to
//! specialist agents.
//!
//! Build: zig build
//! Run: zig build run-supervisor

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const SupervisorAgent = agenkit.patterns.SupervisorAgent;
const SimplePlanner = agenkit.patterns.SimplePlanner;

/// Mock specialist agent
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

        std.debug.print("  [{s}] Processing: {s}\n", .{ self.specialty, content });

        // Build response
        const response = std.fmt.allocPrint(
            self.allocator,
            "[{s} Result] Completed: {s}",
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

/// Mock planning agent (not actually used in SimplePlanner)
const PlanningAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*PlanningAgent {
        const self = try allocator.create(PlanningAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn agent(self: *PlanningAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "PlanningAgent";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = try allocator.dupe(u8, "planning");
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) agenkit.AgentError!agenkit.Result {
        const self: *PlanningAgent = @ptrCast(@alignCast(ptr));
        const content = message.contentAsText() catch return agenkit.AgentError.ProcessingFailed;

        const response = std.fmt.allocPrint(
            self.allocator,
            "Planned: {s}",
            .{content},
        ) catch return agenkit.AgentError.ProcessingFailed;
        defer self.allocator.free(response);

        const response_msg = Message.withText(self.allocator, .assistant, response) catch return agenkit.AgentError.ProcessingFailed;
        return agenkit.Result{ .ok = response_msg };
    }

    fn introspectImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const caps = try capabilitiesImpl(undefined, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, "PlanningAgent", caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *PlanningAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *PlanningAgent) void {
        self.allocator.destroy(self);
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Supervisor Pattern Example ===\n\n", .{});

    // ========================================================================
    // Example 1: Project Management with Specialists
    // ========================================================================
    std.debug.print("Example 1: Project Management with Specialists\n", .{});
    std.debug.print("-----------------------------------------------\n", .{});

    // Create specialist agents
    var researcher = try SpecialistAgent.init(allocator, "Researcher", "research");
    defer researcher.deinit();

    var analyst = try SpecialistAgent.init(allocator, "Analyst", "analysis");
    defer analyst.deinit();

    // Create specialists map
    var specialists = std.StringHashMap(Agent).init(allocator);
    defer specialists.deinit();

    try specialists.put("research", researcher.agent());
    try specialists.put("analysis", analyst.agent());

    // Create planner
    var planning_agent = try PlanningAgent.init(allocator);
    defer planning_agent.deinit();

    var planner = try SimplePlanner.init(allocator, planning_agent.agent());
    defer planner.deinit();

    // Create supervisor
    var supervisor = try SupervisorAgent.init(
        allocator,
        planner.planner(),
        specialists,
        "ProjectManager",
    );
    defer supervisor.deinit();

    std.debug.print("\nInput: Complete market analysis\n", .{});
    std.debug.print("Supervisor will decompose into subtasks and delegate\n\n", .{});

    var msg1 = try Message.withText(allocator, .user, "Complete market analysis");
    defer msg1.deinit();

    const result1 = supervisor.agent().process(msg1) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };

    switch (result1) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("\nSynthesized Result:\n{s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 2: Multi-Specialist Workflow
    // ========================================================================
    std.debug.print("\n\nExample 2: Complex Multi-Specialist Workflow\n", .{});
    std.debug.print("---------------------------------------------\n", .{});

    // Add more specialists
    var designer = try SpecialistAgent.init(allocator, "Designer", "design");
    defer designer.deinit();

    var developer = try SpecialistAgent.init(allocator, "Developer", "development");
    defer developer.deinit();

    var specialists2 = std.StringHashMap(Agent).init(allocator);
    defer specialists2.deinit();

    try specialists2.put("research", researcher.agent());
    try specialists2.put("analysis", analyst.agent());
    try specialists2.put("design", designer.agent());
    try specialists2.put("development", developer.agent());

    var planner2 = try SimplePlanner.init(allocator, planning_agent.agent());
    defer planner2.deinit();

    var supervisor2 = try SupervisorAgent.init(
        allocator,
        planner2.planner(),
        specialists2,
        "TechnicalLead",
    );
    defer supervisor2.deinit();

    std.debug.print("\nInput: Build new feature\n", .{});
    std.debug.print("Note: SimplePlanner creates research + analysis subtasks\n", .{});
    std.debug.print("      In production, planner would intelligently decompose\n\n", .{});

    var msg2 = try Message.withText(allocator, .user, "Build new feature");
    defer msg2.deinit();

    const result2 = supervisor2.agent().process(msg2) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("\n=== Supervisor Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result2) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("\nSynthesized Result:\n{s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    std.debug.print("\n=== Supervisor Pattern Complete ===\n\n", .{});
}
