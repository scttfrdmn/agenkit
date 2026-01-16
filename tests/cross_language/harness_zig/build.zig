const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Create the harness executable
    const exe = b.addExecutable(.{
        .name = "harness_zig",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });

    // Install the executable to the parent directory (tests/cross_language/)
    // This matches the expected location for cross-language testing
    const install_exe = b.addInstallArtifact(exe, .{
        .dest_dir = .{
            .override = .{
                .custom = "..",
            },
        },
    });
    b.getInstallStep().dependOn(&install_exe.step);

    // Run step for testing
    const run_step = b.step("run", "Run the harness");
    const run_cmd = b.addRunArtifact(exe);
    run_step.dependOn(&run_cmd.step);
    if (b.args) |args| {
        run_cmd.addArgs(args);
    }
}
