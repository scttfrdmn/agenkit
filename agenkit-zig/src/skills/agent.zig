/// SkillEnabledAgent — wraps an Agent and injects relevant skill instructions.
///
/// Zig port of the Python reference (`agenkit/skills/agent.py`).
///
/// Before delegating to the wrapped agent, the wrapper queries the registry for
/// skills relevant to the incoming message and prepends their instructions
/// inside an `<available_skills>` block. The response (when skills match)
/// carries an `active_skills` metadata entry listing the injected skill names.
///
/// ## Memory ownership
///
/// - The `SkillEnabledAgent` does NOT own the wrapped agent or the registry;
///   the caller is responsible for their lifetimes. `deinit` frees only the
///   wrapper's own allocation (its name copy and the struct itself).
/// - On each `process` call the wrapper builds a temporary augmented `Message`
///   (owned text + `active_skills` array), passes it to the wrapped agent, and
///   frees it before returning. The returned `Result` message is produced and
///   owned by the wrapped agent, exactly as in the unwrapped case.
const std = @import("std");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const StreamCallbacks = @import("../agent.zig").StreamCallbacks;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const SkillRegistry = @import("loader.zig").SkillRegistry;

/// Default number of skills to inject per request.
pub const DEFAULT_MAX_ACTIVE_SKILLS: usize = 3;

/// Agent wrapper that automatically injects relevant skill instructions.
pub const SkillEnabledAgent = struct {
    allocator: Allocator,
    agent_name: []const u8,
    inner: Agent,
    registry: *SkillRegistry,
    max_active_skills: usize,

    /// Create a skill-enabled wrapper around `inner`.
    ///
    /// Args:
    ///   - allocator: allocator for the wrapper's own state and per-request work
    ///   - inner: base agent to delegate processing to (borrowed, not owned)
    ///   - registry: registry used to look up relevant skills (borrowed)
    ///   - max_active_skills: maximum number of skills to inject
    ///   - auto_discover: whether to call `registry.discoverSkills()` now
    pub fn init(
        allocator: Allocator,
        inner: Agent,
        registry: *SkillRegistry,
        max_active_skills: usize,
        auto_discover: bool,
    ) !*SkillEnabledAgent {
        if (auto_discover) {
            try registry.discoverSkills();
        }
        const self = try allocator.create(SkillEnabledAgent);
        errdefer allocator.destroy(self);
        self.* = SkillEnabledAgent{
            .allocator = allocator,
            .agent_name = try allocator.dupe(u8, inner.name()),
            .inner = inner,
            .registry = registry,
            .max_active_skills = max_active_skills,
        };
        return self;
    }

    /// Create the `Agent` interface for this wrapper.
    pub fn agent(self: *SkillEnabledAgent) Agent {
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
        const self: *SkillEnabledAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *SkillEnabledAgent = @ptrCast(@alignCast(ptr));

        const base = try self.inner.capabilities(allocator);
        // Capability strings are borrowed from the inner agent (the array is
        // owned, the strings are not — matching SequentialAgent/ParallelAgent).
        defer allocator.free(base);

        var out = std.ArrayList([]const u8).empty;
        errdefer {
            for (out.items) |cap| allocator.free(cap);
            out.deinit(allocator);
        }

        var has_injection = false;
        for (base) |cap| {
            if (std.mem.eql(u8, cap, "skill_injection")) has_injection = true;
            try out.append(allocator, try allocator.dupe(u8, cap));
        }
        if (!has_injection) {
            try out.append(allocator, try allocator.dupe(u8, "skill_injection"));
        }

        return out.toOwnedSlice(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *SkillEnabledAgent = @ptrCast(@alignCast(ptr));

        // Query string is the message text; structured content yields an empty
        // query (mirrors Python's `str(content) if content is not None else ""`
        // for the text path — structured content simply produces no match).
        const query: []const u8 = message.contentAsText() catch "";

        const relevant = self.registry.findRelevantSkills(
            self.allocator,
            query,
            self.max_active_skills,
        ) catch return AgentError.ProcessingFailed;
        defer self.allocator.free(relevant);

        if (relevant.len == 0) {
            // Passthrough: delegate the original message untouched.
            return self.inner.process(message);
        }

        // Build the "<available_skills>...</available_skills>\n\n" + query prefix.
        var content_buf = std.ArrayList(u8).empty;
        defer content_buf.deinit(self.allocator);
        content_buf.appendSlice(self.allocator, "<available_skills>\n") catch return AgentError.ProcessingFailed;
        for (relevant, 0..) |skill, i| {
            if (i > 0) content_buf.appendSlice(self.allocator, "\n\n") catch return AgentError.ProcessingFailed;
            const block = skill.toPrompt(self.allocator) catch return AgentError.ProcessingFailed;
            defer self.allocator.free(block);
            content_buf.appendSlice(self.allocator, block) catch return AgentError.ProcessingFailed;
        }
        content_buf.appendSlice(self.allocator, "\n</available_skills>\n\n") catch return AgentError.ProcessingFailed;
        content_buf.appendSlice(self.allocator, query) catch return AgentError.ProcessingFailed;

        const augmented_text = content_buf.toOwnedSlice(self.allocator) catch return AgentError.ProcessingFailed;

        // Construct the augmented message with active_skills metadata.
        var augmented = Message.withText(self.allocator, message.role, augmented_text) catch {
            self.allocator.free(augmented_text);
            return AgentError.ProcessingFailed;
        };
        self.allocator.free(augmented_text); // withText duped the text
        // `augmented` is a transient message: the wrapped agent copies its
        // metadata by reference into the response (which the caller owns), so we
        // must not deep-free those values here. Free only `augmented`'s own
        // allocations (its content text and the metadata map's backing storage).
        defer {
            augmented.content.deinit(augmented.allocator);
            augmented.metadata.object.deinit(augmented.allocator);
        }

        // Copy existing metadata from the source message.
        var meta_it = message.metadata.object.iterator();
        while (meta_it.next()) |entry| {
            augmented.setMetadata(entry.key_ptr.*, entry.value_ptr.*) catch
                return AgentError.ProcessingFailed;
        }

        // Build the active_skills JSON array of skill-name strings.
        var skill_names = std.json.Array.init(self.allocator);
        for (relevant) |skill| {
            const name_copy = self.allocator.dupe(u8, skill.name) catch return AgentError.ProcessingFailed;
            skill_names.append(std.json.Value{ .string = name_copy }) catch return AgentError.ProcessingFailed;
        }
        augmented.setMetadata("active_skills", std.json.Value{ .array = skill_names }) catch
            return AgentError.ProcessingFailed;

        return self.inner.process(augmented);
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        callbacks.onError(AgentError.NotImplemented);
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *SkillEnabledAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer {
            for (caps) |cap| allocator.free(cap);
            allocator.free(caps);
        }
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SkillEnabledAgent = @ptrCast(@alignCast(ptr));
        self.allocator.free(self.agent_name);
        self.allocator.destroy(self);
    }
};

// ── Tests ───────────────────────────────────────────────────────────────────

const testing = std.testing;
const EchoAgent = @import("../agent.zig").EchoAgent;

fn makeSkillDir(dir: std.Io.Dir, name: []const u8, description: []const u8) !void {
    const io = testing.io;
    try dir.createDir(io, name, .default_dir);
    var sub = try dir.openDir(io, name, .{});
    defer sub.close(io);
    var buf: [4096]u8 = undefined;
    const content = try std.fmt.bufPrint(
        &buf,
        "---\nname: {s}\ndescription: {s}\n---\nInstructions here.",
        .{ name, description },
    );
    var file = try sub.createFile(io, "SKILL.md", .{});
    defer file.close(io);
    try file.writeStreamingAll(io, content);
}

fn realpathAlloc(dir: std.Io.Dir, allocator: std.mem.Allocator, sub_path: []const u8) ![]u8 {
    const io = testing.io;
    var sub = try dir.openDir(io, sub_path, .{});
    defer sub.close(io);
    var buf: [std.fs.max_path_bytes]u8 = undefined;
    const len = try sub.realPath(io, &buf);
    return allocator.dupe(u8, buf[0..len]);
}

test "skill agent augments matching message" {
    const allocator = testing.allocator;
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "pdf-processing", "Extract text from PDF documents.");
    const root = try realpathAlloc(tmp.dir, allocator, ".");
    defer allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(allocator, &paths);
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
    defer skill_agent.agent().deinit();

    var msg = try Message.withText(allocator, .user, "How do I parse pdf files?");
    defer msg.deinit();

    const result = try skill_agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "<available_skills>") != null);
    try testing.expect(std.mem.indexOf(u8, content, "pdf-processing") != null);
}

test "skill agent passthrough when no skills match" {
    const allocator = testing.allocator;
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "email-compose", "Compose professional emails.");
    const root = try realpathAlloc(tmp.dir, allocator, ".");
    defer allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(allocator, &paths);
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
    defer skill_agent.agent().deinit();

    var msg = try Message.withText(allocator, .user, "tell me a joke");
    defer msg.deinit();

    const result = try skill_agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const content = try response.contentAsText();
    try testing.expect(std.mem.indexOf(u8, content, "<available_skills>") == null);
    try testing.expectEqualStrings("tell me a joke", content);
}

test "skill agent sets active_skills metadata" {
    const allocator = testing.allocator;
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "csv-tools", "Handle and transform CSV spreadsheets.");
    const root = try realpathAlloc(tmp.dir, allocator, ".");
    defer allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(allocator, &paths);
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
    defer skill_agent.agent().deinit();

    var msg = try Message.withText(allocator, .user, "parse this csv spreadsheet data");
    defer msg.deinit();

    const result = try skill_agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const active = response.getMetadata("active_skills");
    try testing.expect(active != null);
    try testing.expect(active.? == .array);
    var found = false;
    for (active.?.array.items) |item| {
        if (item == .string and std.mem.eql(u8, item.string, "csv-tools")) found = true;
    }
    try testing.expect(found);
}

test "skill agent advertises skill_injection capability" {
    const allocator = testing.allocator;
    var registry = SkillRegistry.init(allocator, &[_][]const u8{});
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, false);
    defer skill_agent.agent().deinit();

    const caps = try skill_agent.agent().capabilities(allocator);
    defer {
        for (caps) |c| allocator.free(c);
        allocator.free(caps);
    }
    var found = false;
    for (caps) |c| {
        if (std.mem.eql(u8, c, "skill_injection")) found = true;
    }
    try testing.expect(found);
}

test "skill agent name delegates to inner" {
    const allocator = testing.allocator;
    var registry = SkillRegistry.init(allocator, &[_][]const u8{});
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, false);
    defer skill_agent.agent().deinit();

    try testing.expectEqualStrings("echo", skill_agent.agent().name());
}
