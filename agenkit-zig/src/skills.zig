/// Agenkit Agent Skills for Zig
///
/// Agent Skills let you package reusable instructions as directories containing
/// a `SKILL.md` file (YAML frontmatter + Markdown body) and inject the relevant
/// ones into an agent's input at runtime.
///
/// This is the Zig port of the Python reference (`agenkit/skills/`).
///
/// ## Example
///
/// ```zig
/// const skills = @import("agenkit").skills;
///
/// const paths = [_][]const u8{"./skills"};
/// var registry = skills.SkillRegistry.init(allocator, &paths);
/// defer registry.deinit();
///
/// var echo = try agenkit.EchoAgent.init(allocator);
/// defer echo.agent().deinit();
///
/// var agent = try skills.SkillEnabledAgent.init(allocator, echo.agent(), &registry, 3, true);
/// defer agent.agent().deinit();
///
/// const result = try agent.agent().process(msg);
/// ```
const loader = @import("skills/loader.zig");

pub const AgentSkill = loader.AgentSkill;
pub const SkillRegistry = loader.SkillRegistry;
pub const SkillError = loader.SkillError;
pub const MetadataEntry = loader.MetadataEntry;
pub const SkillEnabledAgent = @import("skills/agent.zig").SkillEnabledAgent;
pub const DEFAULT_MAX_ACTIVE_SKILLS = @import("skills/agent.zig").DEFAULT_MAX_ACTIVE_SKILLS;

pub const version = "0.86.0";

test {
    @import("std").testing.refAllDecls(@This());
    _ = @import("skills/loader.zig");
    _ = @import("skills/agent.zig");
}
