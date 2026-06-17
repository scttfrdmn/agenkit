/// Agent Skill loader and registry.
///
/// Implements the Agent Skills specification: each skill is a directory
/// containing a `SKILL.md` file with YAML frontmatter (name, description,
/// optional license and metadata) followed by Markdown instructions.
///
/// This is the Zig port of the Python reference implementation
/// (`agenkit/skills/loader.py`). It follows Agenkit Zig conventions:
/// - Explicit allocators on every fallible operation
/// - Error unions instead of exceptions
/// - Explicit memory ownership (documented per type)
///
/// ## SKILL.md format
///
/// ```text
/// ---
/// name: skill-name
/// description: What this skill does.
/// license: Apache-2.0   # optional
/// metadata:             # optional
///   key: value
/// ---
/// # Skill Title
/// Markdown instructions here.
/// ```
///
/// ## Memory ownership
///
/// - `AgentSkill` owns every string field it holds (`name`, `description`,
///   `instructions`, `license`, `skill_dir`) plus all keys/values in
///   `metadata`. Call `AgentSkill.deinit` to free them.
/// - `SkillRegistry` owns the `AgentSkill` values stored in its map and the
///   duplicated key strings. `SkillRegistry.deinit` frees all of them. The
///   slice returned by `findRelevantSkills` is owned by the caller (free the
///   slice itself with the allocator), but the `AgentSkill` elements inside it
///   remain owned by the registry — do NOT deinit them.
const std = @import("std");
const Allocator = std.mem.Allocator;
const ioc = @import("../io_compat.zig");

/// Errors raised while loading a skill from disk.
pub const SkillError = error{
    /// The directory does not contain a `SKILL.md` file.
    MissingSkillFile,
    /// The `SKILL.md` file lacks the two `---` frontmatter delimiters.
    MissingDelimiters,
    /// The frontmatter does not declare a `name:` field.
    MissingName,
    /// The frontmatter does not declare a `description:` field.
    MissingDescription,
};

/// A single key/value pair parsed from the optional `metadata:` block.
///
/// Both `key` and `value` are owned by the enclosing `AgentSkill`.
pub const MetadataEntry = struct {
    key: []const u8,
    value: []const u8,
};

/// Represents a single agent skill loaded from a directory.
///
/// All string fields are heap-allocated and owned by the skill. Use `deinit`
/// to release them.
pub const AgentSkill = struct {
    allocator: Allocator,
    name: []const u8,
    description: []const u8,
    instructions: []const u8,
    license: ?[]const u8,
    metadata: []MetadataEntry,
    skill_dir: ?[]const u8,

    /// Load a skill from a directory containing a `SKILL.md` file.
    ///
    /// `skill_dir` is the path to the skill directory (relative to the current
    /// working directory or absolute).
    ///
    /// Returns a `SkillError` if the directory lacks `SKILL.md`, the
    /// frontmatter delimiters are missing, or a required field
    /// (`name`/`description`) is absent.
    ///
    /// The returned skill owns all of its memory; the caller must `deinit` it.
    pub fn fromDirectory(allocator: Allocator, skill_dir: []const u8) !AgentSkill {
        const io = ioc.io();
        var dir = std.Io.Dir.cwd().openDir(io, skill_dir, .{}) catch {
            return SkillError.MissingSkillFile;
        };
        defer dir.close(io);

        const raw = dir.readFileAlloc(io, "SKILL.md", allocator, .unlimited) catch {
            return SkillError.MissingSkillFile;
        };
        defer allocator.free(raw);

        return fromContent(allocator, raw, skill_dir);
    }

    /// Parse a skill from raw `SKILL.md` content.
    ///
    /// Split on the first two `---` delimiters into frontmatter + markdown body,
    /// matching the Python `raw.split("---", 2)` semantics (file must start with
    /// `---`). Exposed for testing without touching the filesystem.
    pub fn fromContent(allocator: Allocator, raw: []const u8, skill_dir: ?[]const u8) !AgentSkill {
        // Equivalent to Python's raw.split("---", 2): at most 3 parts.
        // parts[0] is the text before the first delimiter (must be empty for a
        // well-formed file), parts[1] is the frontmatter, parts[2] is the body.
        const first = std.mem.indexOf(u8, raw, "---") orelse
            return SkillError.MissingDelimiters;
        const after_first = first + 3;
        const second_rel = std.mem.indexOf(u8, raw[after_first..], "---") orelse
            return SkillError.MissingDelimiters;
        const second = after_first + second_rel;

        const frontmatter_text = std.mem.trim(u8, raw[after_first..second], " \t\r\n");
        const instructions_raw = std.mem.trim(u8, raw[second + 3 ..], " \t\r\n");

        var fm = try Frontmatter.parse(allocator, frontmatter_text);
        defer fm.deinit();

        const name = fm.get("name") orelse return SkillError.MissingName;
        if (name.len == 0) return SkillError.MissingName;

        const description = fm.get("description") orelse return SkillError.MissingDescription;
        if (description.len == 0) return SkillError.MissingDescription;

        // Duplicate everything so the skill owns its memory independent of `fm`.
        const name_owned = try allocator.dupe(u8, name);
        errdefer allocator.free(name_owned);

        const desc_owned = try allocator.dupe(u8, description);
        errdefer allocator.free(desc_owned);

        const instr_owned = try allocator.dupe(u8, instructions_raw);
        errdefer allocator.free(instr_owned);

        const license_owned: ?[]const u8 = if (fm.get("license")) |lic|
            try allocator.dupe(u8, lic)
        else
            null;
        errdefer if (license_owned) |l| allocator.free(l);

        const dir_owned: ?[]const u8 = if (skill_dir) |d|
            try allocator.dupe(u8, d)
        else
            null;
        errdefer if (dir_owned) |d| allocator.free(d);

        const metadata = try fm.takeMetadata(allocator);
        errdefer freeMetadata(allocator, metadata);

        return AgentSkill{
            .allocator = allocator,
            .name = name_owned,
            .description = desc_owned,
            .instructions = instr_owned,
            .license = license_owned,
            .metadata = metadata,
            .skill_dir = dir_owned,
        };
    }

    /// Free all memory owned by this skill.
    pub fn deinit(self: *AgentSkill) void {
        self.allocator.free(self.name);
        self.allocator.free(self.description);
        self.allocator.free(self.instructions);
        if (self.license) |l| self.allocator.free(l);
        if (self.skill_dir) |d| self.allocator.free(d);
        freeMetadata(self.allocator, self.metadata);
    }

    /// Look up a metadata value by key, or null if absent.
    pub fn getMetadata(self: *const AgentSkill, key: []const u8) ?[]const u8 {
        for (self.metadata) |entry| {
            if (std.mem.eql(u8, entry.key, key)) return entry.value;
        }
        return null;
    }

    /// Render the skill as a prompt block for injection into agent messages.
    ///
    /// The returned string is allocated with `allocator` and owned by the
    /// caller.
    pub fn toPrompt(self: *const AgentSkill, allocator: Allocator) ![]u8 {
        return std.fmt.allocPrint(
            allocator,
            "# Skill: {s}\n\n## Description\n{s}\n\n## Instructions\n{s}\n",
            .{ self.name, self.description, self.instructions },
        );
    }
};

fn freeMetadata(allocator: Allocator, metadata: []MetadataEntry) void {
    for (metadata) |entry| {
        allocator.free(entry.key);
        allocator.free(entry.value);
    }
    allocator.free(metadata);
}

/// Minimal YAML frontmatter parser.
///
/// Supports exactly the subset used by SKILL.md frontmatter:
/// - top-level `key: value` scalars
/// - a `metadata:` block whose immediate two-space-indented children are
///   `key: value` scalars
///
/// Values are unquoted (surrounding single or double quotes are stripped).
/// This is intentionally small — there is no external YAML dependency.
const Frontmatter = struct {
    allocator: Allocator,
    /// Top-level scalar fields (name, description, license, ...). Borrowed
    /// slices into the input text; not owned.
    fields: std.StringHashMap([]const u8),
    /// Children of the `metadata:` block. Borrowed slices into the input text.
    metadata: std.ArrayList(MetadataEntry),

    fn parse(allocator: Allocator, text: []const u8) !Frontmatter {
        var self = Frontmatter{
            .allocator = allocator,
            .fields = std.StringHashMap([]const u8).init(allocator),
            .metadata = std.ArrayList(MetadataEntry).empty,
        };
        errdefer self.deinit();

        var in_metadata = false;
        var lines = std.mem.splitScalar(u8, text, '\n');
        while (lines.next()) |raw_line| {
            const line = std.mem.trimEnd(u8, raw_line, " \t\r");
            if (line.len == 0) continue;

            const indent = leadingSpaces(line);
            const trimmed = line[indent..];
            if (trimmed.len == 0) continue;
            // Skip YAML comments.
            if (trimmed[0] == '#') continue;

            const colon = std.mem.indexOfScalar(u8, trimmed, ':') orelse continue;
            const key = std.mem.trim(u8, trimmed[0..colon], " \t");
            const value = stripQuotes(std.mem.trim(u8, trimmed[colon + 1 ..], " \t"));

            if (indent == 0) {
                if (std.mem.eql(u8, key, "metadata")) {
                    in_metadata = true;
                    continue;
                }
                in_metadata = false;
                try self.fields.put(key, value);
            } else if (in_metadata) {
                // Indented child of the metadata block.
                if (value.len == 0) continue;
                try self.metadata.append(allocator, .{ .key = key, .value = value });
            }
        }

        return self;
    }

    fn get(self: *const Frontmatter, key: []const u8) ?[]const u8 {
        return self.fields.get(key);
    }

    /// Build an owned copy of the metadata entries for transfer to an
    /// `AgentSkill`. The caller owns the returned slice and its strings.
    fn takeMetadata(self: *const Frontmatter, allocator: Allocator) ![]MetadataEntry {
        const out = try allocator.alloc(MetadataEntry, self.metadata.items.len);
        var filled: usize = 0;
        errdefer {
            for (out[0..filled]) |e| {
                allocator.free(e.key);
                allocator.free(e.value);
            }
            allocator.free(out);
        }
        for (self.metadata.items, 0..) |entry, i| {
            const key_copy = try allocator.dupe(u8, entry.key);
            errdefer allocator.free(key_copy);
            const value_copy = try allocator.dupe(u8, entry.value);
            out[i] = .{ .key = key_copy, .value = value_copy };
            filled = i + 1;
        }
        return out;
    }

    fn deinit(self: *Frontmatter) void {
        self.fields.deinit();
        self.metadata.deinit(self.allocator);
    }
};

fn leadingSpaces(line: []const u8) usize {
    var i: usize = 0;
    while (i < line.len and line[i] == ' ') : (i += 1) {}
    return i;
}

fn stripQuotes(s: []const u8) []const u8 {
    if (s.len >= 2) {
        const first = s[0];
        const last = s[s.len - 1];
        if ((first == '\'' and last == '\'') or (first == '"' and last == '"')) {
            return s[1 .. s.len - 1];
        }
    }
    return s;
}

/// Discovers and searches agent skills across filesystem paths.
///
/// Skills are discovered by walking search paths and loading any subdirectory
/// that contains a `SKILL.md` file. Invalid skill directories are skipped.
///
/// The registry owns every `AgentSkill` it holds and the duplicated key
/// strings of its internal map. `deinit` frees them all.
pub const SkillRegistry = struct {
    allocator: Allocator,
    /// Search paths to scan during `discoverSkills`. Borrowed; not owned.
    search_paths: []const []const u8,
    /// name -> skill. Keys are owned (duplicated from `skill.name`); values are
    /// owned skills.
    skills: std.StringHashMap(AgentSkill),

    /// Create a registry over the given search paths.
    ///
    /// `search_paths` is borrowed and must outlive the registry; the registry
    /// does not copy it.
    pub fn init(allocator: Allocator, search_paths: []const []const u8) SkillRegistry {
        return SkillRegistry{
            .allocator = allocator,
            .search_paths = search_paths,
            .skills = std.StringHashMap(AgentSkill).init(allocator),
        };
    }

    /// Free all loaded skills and the registry's internal storage.
    pub fn deinit(self: *SkillRegistry) void {
        var it = self.skills.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            entry.value_ptr.deinit();
        }
        self.skills.deinit();
    }

    /// Walk each search path and load all valid skill directories.
    ///
    /// Subdirectories without a `SKILL.md` or with invalid format are skipped.
    /// If a skill name is already loaded it is replaced (matching the Python
    /// `self._skills[skill.name] = skill` behaviour).
    pub fn discoverSkills(self: *SkillRegistry) !void {
        const io = ioc.io();
        for (self.search_paths) |search_path| {
            var dir = std.Io.Dir.cwd().openDir(io, search_path, .{ .iterate = true }) catch continue;
            defer dir.close(io);

            var iter = dir.iterate();
            while (try iter.next(io)) |entry| {
                if (entry.kind != .directory) continue;

                const skill_path = try std.fs.path.join(
                    self.allocator,
                    &.{ search_path, entry.name },
                );
                defer self.allocator.free(skill_path);

                var skill = AgentSkill.fromDirectory(self.allocator, skill_path) catch continue;
                self.putSkill(&skill) catch {
                    skill.deinit();
                    return error.OutOfMemory;
                };
            }
        }
    }

    /// Insert a skill, replacing any existing skill with the same name and
    /// freeing the old one. Takes ownership of `skill`'s memory on success.
    fn putSkill(self: *SkillRegistry, skill: *AgentSkill) !void {
        if (self.skills.getEntry(skill.name)) |existing| {
            // Replace value in place; key already matches by name.
            existing.value_ptr.deinit();
            existing.value_ptr.* = skill.*;
            return;
        }
        const key = try self.allocator.dupe(u8, skill.name);
        errdefer self.allocator.free(key);
        try self.skills.put(key, skill.*);
    }

    /// Return skills most relevant to `query`, best match first.
    ///
    /// Scoring (mirrors the Python reference):
    ///   +10 if query (lowercased) appears in the skill name (lowercased)
    ///   +5  if query (lowercased) appears in the skill description (lowercased)
    ///   +1  for each whitespace-delimited query word also present as a word in
    ///       the description
    ///
    /// Only skills with score > 0 are returned, capped at `max_results`.
    ///
    /// The returned slice is owned by the caller and must be freed with
    /// `allocator.free`. The `*const AgentSkill` elements remain owned by the
    /// registry — do not deinit them.
    pub fn findRelevantSkills(
        self: *const SkillRegistry,
        allocator: Allocator,
        query: []const u8,
        max_results: usize,
    ) ![]*const AgentSkill {
        const query_lower = try std.ascii.allocLowerString(allocator, query);
        defer allocator.free(query_lower);

        const Scored = struct {
            score: i64,
            skill: *const AgentSkill,
        };

        var scored = std.ArrayList(Scored).empty;
        defer scored.deinit(allocator);

        var it = self.skills.iterator();
        while (it.next()) |entry| {
            const skill = entry.value_ptr;

            const name_lower = try std.ascii.allocLowerString(allocator, skill.name);
            defer allocator.free(name_lower);
            const desc_lower = try std.ascii.allocLowerString(allocator, skill.description);
            defer allocator.free(desc_lower);

            var score: i64 = 0;
            if (query_lower.len > 0 and std.mem.indexOf(u8, name_lower, query_lower) != null) {
                score += 10;
            }
            if (query_lower.len > 0 and std.mem.indexOf(u8, desc_lower, query_lower) != null) {
                score += 5;
            }
            score += wordOverlap(query_lower, desc_lower);

            if (score > 0) {
                try scored.append(allocator, .{ .score = score, .skill = skill });
            }
        }

        // Sort by score descending (stable so ties keep iteration order).
        std.mem.sort(Scored, scored.items, {}, struct {
            fn lessThan(_: void, a: Scored, b: Scored) bool {
                return a.score > b.score;
            }
        }.lessThan);

        const count_out = @min(max_results, scored.items.len);
        const out = try allocator.alloc(*const AgentSkill, count_out);
        for (out, 0..) |*slot, i| slot.* = scored.items[i].skill;
        return out;
    }

    /// Return the skill with the given name, or null if not found.
    ///
    /// The returned pointer is borrowed from the registry.
    pub fn getSkill(self: *const SkillRegistry, name: []const u8) ?*const AgentSkill {
        return self.skills.getPtr(name);
    }

    /// Number of loaded skills.
    pub fn count(self: *const SkillRegistry) usize {
        return self.skills.count();
    }
};

/// Count how many unique whitespace-delimited words in `query_lower` appear as
/// whole words in `desc_lower`. Mirrors Python's
/// `len(query_words & set(desc_lower.split()))` (set semantics: each query word
/// counts at most once).
fn wordOverlap(query_lower: []const u8, desc_lower: []const u8) i64 {
    var overlap: i64 = 0;

    var qwords = std.mem.tokenizeAny(u8, query_lower, " \t\r\n");
    outer: while (qwords.next()) |qw| {
        // De-duplicate query words (set semantics): skip if this exact word
        // already appeared earlier in the query.
        var prior = std.mem.tokenizeAny(u8, query_lower, " \t\r\n");
        while (prior.next()) |pw| {
            if (pw.ptr == qw.ptr) break; // reached the current word
            if (std.mem.eql(u8, pw, qw)) continue :outer; // earlier duplicate
        }

        var dwords = std.mem.tokenizeAny(u8, desc_lower, " \t\r\n");
        while (dwords.next()) |dw| {
            if (std.mem.eql(u8, dw, qw)) {
                overlap += 1;
                continue :outer;
            }
        }
    }
    return overlap;
}

// ── Tests ───────────────────────────────────────────────────────────────────

const testing = std.testing;

/// Create a minimal valid skill directory inside `dir`.
fn makeSkillDir(dir: std.Io.Dir, name: []const u8, description: []const u8, body: []const u8) !void {
    const io = testing.io;
    try dir.createDir(io, name, .default_dir);
    var sub = try dir.openDir(io, name, .{});
    defer sub.close(io);
    var buf: [4096]u8 = undefined;
    const content = try std.fmt.bufPrint(
        &buf,
        "---\nname: {s}\ndescription: {s}\n---\n{s}",
        .{ name, description, body },
    );
    var file = try sub.createFile(io, "SKILL.md", .{});
    defer file.close(io);
    try file.writeStreamingAll(io, content);
}

fn realpathAlloc(dir: std.Io.Dir, allocator: Allocator, sub_path: []const u8) ![]u8 {
    const io = testing.io;
    var sub = try dir.openDir(io, sub_path, .{});
    defer sub.close(io);
    var buf: [std.fs.max_path_bytes]u8 = undefined;
    const len = try sub.realPath(io, &buf);
    return allocator.dupe(u8, buf[0..len]);
}

fn writeRawFile(dir: std.Io.Dir, sub_path: []const u8, data: []const u8) !void {
    const io = testing.io;
    var file = try dir.createFile(io, sub_path, .{});
    defer file.close(io);
    try file.writeStreamingAll(io, data);
}

test "fromContent loads a valid skill" {
    var skill = try AgentSkill.fromContent(
        testing.allocator,
        "---\nname: pdf-processing\ndescription: Extract text from PDFs.\n---\n# PDF\nDo stuff.",
        "skills/pdf-processing",
    );
    defer skill.deinit();

    try testing.expectEqualStrings("pdf-processing", skill.name);
    try testing.expectEqualStrings("Extract text from PDFs.", skill.description);
    try testing.expect(std.mem.indexOf(u8, skill.instructions, "Do stuff.") != null);
    try testing.expectEqualStrings("skills/pdf-processing", skill.skill_dir.?);
}

test "fromContent parses license and metadata" {
    var skill = try AgentSkill.fromContent(
        testing.allocator,
        "---\nname: advanced\ndescription: Advanced skill.\nlicense: Apache-2.0\nmetadata:\n  version: '1.0'\n---\nAdvanced instructions.",
        null,
    );
    defer skill.deinit();

    try testing.expectEqualStrings("Apache-2.0", skill.license.?);
    try testing.expectEqualStrings("1.0", skill.getMetadata("version").?);
}

test "fromContent missing delimiters" {
    try testing.expectError(
        SkillError.MissingDelimiters,
        AgentSkill.fromContent(testing.allocator, "name: foo\ndescription: bar\n", null),
    );
}

test "fromContent missing name" {
    try testing.expectError(
        SkillError.MissingName,
        AgentSkill.fromContent(testing.allocator, "---\ndescription: A skill without a name.\n---\nInstructions.", null),
    );
}

test "fromContent missing description" {
    try testing.expectError(
        SkillError.MissingDescription,
        AgentSkill.fromContent(testing.allocator, "---\nname: nodesc\n---\nInstructions.", null),
    );
}

test "fromDirectory missing SKILL.md" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try tmp.dir.createDir(testing.io, "empty", .default_dir);
    const path = try realpathAlloc(tmp.dir, testing.allocator, "empty");
    defer testing.allocator.free(path);

    try testing.expectError(SkillError.MissingSkillFile, AgentSkill.fromDirectory(testing.allocator, path));
}

test "fromDirectory loads from disk" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "csv-tools", "Handle CSV files.", "Parse and write CSV.");
    const path = try realpathAlloc(tmp.dir, testing.allocator, "csv-tools");
    defer testing.allocator.free(path);

    var skill = try AgentSkill.fromDirectory(testing.allocator, path);
    defer skill.deinit();
    try testing.expectEqualStrings("csv-tools", skill.name);
}

test "toPrompt formatting" {
    var skill = try AgentSkill.fromContent(
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

test "registry skips non-directories" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try writeRawFile(tmp.dir, "not_a_dir.md", "ignored");
    const root = try realpathAlloc(tmp.dir, testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();
    try testing.expectEqual(@as(usize, 0), registry.count());
}

test "registry discovers valid skills" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "skill-a", "Skill A description.", "Body.");
    try makeSkillDir(tmp.dir, "skill-b", "Skill B description.", "Body.");
    const root = try realpathAlloc(tmp.dir, testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    try testing.expect(registry.getSkill("skill-a") != null);
    try testing.expect(registry.getSkill("skill-b") != null);
}

test "registry find relevant name match" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "pdf-processing", "Work with PDF documents.", "Body.");
    try makeSkillDir(tmp.dir, "csv-tools", "Handle CSV spreadsheets.", "Body.");
    const root = try realpathAlloc(tmp.dir, testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    const results = try registry.findRelevantSkills(testing.allocator, "pdf", 5);
    defer testing.allocator.free(results);
    try testing.expect(results.len >= 1);
    try testing.expectEqualStrings("pdf-processing", results[0].name);
}

test "registry find relevant respects max_results" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    var i: usize = 0;
    while (i < 6) : (i += 1) {
        var name_buf: [16]u8 = undefined;
        var desc_buf: [64]u8 = undefined;
        const name = try std.fmt.bufPrint(&name_buf, "skill-{d}", .{i});
        const desc = try std.fmt.bufPrint(&desc_buf, "A skill about document processing number {d}.", .{i});
        try makeSkillDir(tmp.dir, name, desc, "Body.");
    }
    const root = try realpathAlloc(tmp.dir, testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    const results = try registry.findRelevantSkills(testing.allocator, "document", 3);
    defer testing.allocator.free(results);
    try testing.expect(results.len <= 3);
}

test "registry get skill" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    try makeSkillDir(tmp.dir, "email-compose", "Compose professional emails.", "Body.");
    const root = try realpathAlloc(tmp.dir, testing.allocator, ".");
    defer testing.allocator.free(root);

    const paths = [_][]const u8{root};
    var registry = SkillRegistry.init(testing.allocator, &paths);
    defer registry.deinit();
    try registry.discoverSkills();

    const skill = registry.getSkill("email-compose");
    try testing.expect(skill != null);
    try testing.expectEqualStrings("email-compose", skill.?.name);
    try testing.expect(registry.getSkill("nonexistent") == null);
}

test "wordOverlap counts each query word once" {
    try testing.expectEqual(@as(i64, 1), wordOverlap("document document", "about document processing"));
    try testing.expectEqual(@as(i64, 2), wordOverlap("parse csv", "parse the csv data"));
    try testing.expectEqual(@as(i64, 0), wordOverlap("xyz", "nothing here"));
}
