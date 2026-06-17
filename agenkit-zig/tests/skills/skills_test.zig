/// Agent Skills tests — exercises the public `agenkit.skills` API.
///
/// Ports the Python suites tests/skills/test_skill_loader.py and
/// tests/skills/test_skill_agent.py through the public package surface.
/// (The implementation files also carry their own inline `test` blocks; this
/// file verifies the API as consumers see it.)
///
/// Run with: zig build test

const std = @import("std");
const testing = std.testing;
const agenkit = @import("agenkit");
const skills = agenkit.skills;
const Message = agenkit.Message;
const EchoAgent = agenkit.EchoAgent;

/// Create a minimal valid skill directory inside `dir`.
fn makeSkillDir(dir: std.fs.Dir, name: []const u8, description: []const u8) !void {
    try dir.makeDir(name);
    var sub = try dir.openDir(name, .{});
    defer sub.close();
    var buf: [4096]u8 = undefined;
    const content = try std.fmt.bufPrint(
        &buf,
        "---\nname: {s}\ndescription: {s}\n---\nInstructions here.",
        .{ name, description },
    );
    const file = try sub.createFile("SKILL.md", .{});
    defer file.close();
    try file.writeAll(content);
}

// ── AgentSkill.fromDirectory / fromContent ────────────────────────────────────

test "load skill valid" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    {
        try tmp.dir.makeDir("pdf-processing");
        var sub = try tmp.dir.openDir("pdf-processing", .{});
        defer sub.close();
        const file = try sub.createFile("SKILL.md", .{});
        defer file.close();
        try file.writeAll("---\nname: pdf-processing\ndescription: Extract text from PDFs.\n---\n# PDF\nDo stuff.");
    }
    const path = try tmp.dir.realpathAlloc(testing.allocator, "pdf-processing");
    defer testing.allocator.free(path);

    var skill = try skills.AgentSkill.fromDirectory(testing.allocator, path);
    defer skill.deinit();

    try testing.expectEqualStrings("pdf-processing", skill.name);
    try testing.expectEqualStrings("Extract text from PDFs.", skill.description);
    try testing.expect(std.mem.indexOf(u8, skill.instructions, "Do stuff.") != null);
    try testing.expectEqualStrings(path, skill.skill_dir.?);
}

test "load skill with license and metadata" {
    var skill = try skills.AgentSkill.fromContent(
        testing.allocator,
        "---\nname: advanced\ndescription: Advanced skill.\nlicense: Apache-2.0\nmetadata:\n  version: '1.0'\n---\nAdvanced instructions.",
        null,
    );
    defer skill.deinit();

    try testing.expectEqualStrings("Apache-2.0", skill.license.?);
    try testing.expectEqualStrings("1.0", skill.getMetadata("version").?);
}

test "load skill missing SKILL.md" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try tmp.dir.makeDir("empty");
    const path = try tmp.dir.realpathAlloc(testing.allocator, "empty");
    defer testing.allocator.free(path);

    try testing.expectError(skills.SkillError.MissingSkillFile, skills.AgentSkill.fromDirectory(testing.allocator, path));
}

test "load skill invalid frontmatter" {
    try testing.expectError(
        skills.SkillError.MissingDelimiters,
        skills.AgentSkill.fromContent(testing.allocator, "name: foo\ndescription: bar\n", null),
    );
}

test "load skill missing name" {
    try testing.expectError(
        skills.SkillError.MissingName,
        skills.AgentSkill.fromContent(testing.allocator, "---\ndescription: A skill without a name.\n---\nInstructions.", null),
    );
}

test "load skill missing description" {
    try testing.expectError(
        skills.SkillError.MissingDescription,
        skills.AgentSkill.fromContent(testing.allocator, "---\nname: nodesc\n---\nInstructions.", null),
    );
}

test "skill to prompt" {
    var skill = try skills.AgentSkill.fromContent(
        testing.allocator,
        "---\nname: csv-tools\ndescription: Handle CSV files.\n---\nParse and write CSV.",
        null,
    );
    defer skill.deinit();

    const prompt = try skill.toPrompt(testing.allocator);
    defer testing.allocator.free(prompt);

    try testing.expect(std.mem.indexOf(u8, prompt, "# Skill: csv-tools") != null);
    try testing.expect(std.mem.indexOf(u8, prompt, "## Description") != null);
    try testing.expect(std.mem.indexOf(u8, prompt, "Handle CSV files.") != null);
    try testing.expect(std.mem.indexOf(u8, prompt, "## Instructions") != null);
    try testing.expect(std.mem.indexOf(u8, prompt, "Parse and write CSV.") != null);
}

// ── SkillRegistry ─────────────────────────────────────────────────────────────

test "registry discover skips non-dirs" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    {
        const file = try tmp.dir.createFile("not_a_dir.md", .{});
        defer file.close();
        try file.writeAll("ignored");
    }
    const root = try tmp.dir.realpathAlloc(testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();
    try testing.expectEqual(@as(usize, 0), registry.count());
}

test "registry discovers valid skills" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "skill-a", "Skill A description.");
    try makeSkillDir(tmp.dir, "skill-b", "Skill B description.");
    const root = try tmp.dir.realpathAlloc(testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    try testing.expect(registry.getSkill("skill-a") != null);
    try testing.expect(registry.getSkill("skill-b") != null);
}

test "registry find relevant name match" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "pdf-processing", "Work with PDF documents.");
    try makeSkillDir(tmp.dir, "csv-tools", "Handle CSV spreadsheets.");
    const root = try tmp.dir.realpathAlloc(testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    const results = try registry.findRelevantSkills(testing.allocator, "pdf", 5);
    defer testing.allocator.free(results);
    try testing.expect(results.len >= 1);
    try testing.expectEqualStrings("pdf-processing", results[0].name);
}

test "registry find relevant max results" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    var i: usize = 0;
    while (i < 6) : (i += 1) {
        var name_buf: [16]u8 = undefined;
        var desc_buf: [64]u8 = undefined;
        const name = try std.fmt.bufPrint(&name_buf, "skill-{d}", .{i});
        const desc = try std.fmt.bufPrint(&desc_buf, "A skill about document processing number {d}.", .{i});
        try makeSkillDir(tmp.dir, name, desc);
    }
    const root = try tmp.dir.realpathAlloc(testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    const results = try registry.findRelevantSkills(testing.allocator, "document", 3);
    defer testing.allocator.free(results);
    try testing.expect(results.len <= 3);
}

test "registry get skill" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "email-compose", "Compose professional emails.");
    const root = try tmp.dir.realpathAlloc(testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    const skill = registry.getSkill("email-compose");
    try testing.expect(skill != null);
    try testing.expectEqualStrings("email-compose", skill.?.name);
    try testing.expect(registry.getSkill("nonexistent") == null);
}

// ── SkillEnabledAgent ─────────────────────────────────────────────────────────

test "skill agent augments message" {
    const allocator = testing.allocator;
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "pdf-processing", "Extract text from PDF documents.");
    const root = try tmp.dir.realpathAlloc(allocator, ".");
    defer allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(allocator, &paths);
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try skills.SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
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

test "skill agent no skills passthrough" {
    const allocator = testing.allocator;
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "email-compose", "Compose professional emails.");
    const root = try tmp.dir.realpathAlloc(allocator, ".");
    defer allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(allocator, &paths);
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try skills.SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
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

test "skill agent active_skills metadata" {
    const allocator = testing.allocator;
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "csv-tools", "Handle and transform CSV spreadsheets.");
    const root = try tmp.dir.realpathAlloc(allocator, ".");
    defer allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = skills.SkillRegistry.init(allocator, &paths);
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try skills.SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
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

test "skill agent capabilities include skill_injection" {
    const allocator = testing.allocator;
    var registry = skills.SkillRegistry.init(allocator, &[_][]const u8{});
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try skills.SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, false);
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

test "skill agent name delegates" {
    const allocator = testing.allocator;
    var registry = skills.SkillRegistry.init(allocator, &[_][]const u8{});
    defer registry.deinit();

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var skill_agent = try skills.SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, false);
    defer skill_agent.agent().deinit();

    try testing.expectEqualStrings("echo", skill_agent.agent().name());
}
