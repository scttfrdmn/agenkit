const std = @import("std");

// Although this function looks imperative, it does not perform the build
// directly and instead it mutates the build graph (`b`) that will be then
// executed by an external runner. The functions in `std.Build` implement a DSL
// for defining build steps and express dependencies between them, allowing the
// build runner to parallelize the build automatically (and the cache system to
// know when a step doesn't need to be re-run).
pub fn build(b: *std.Build) void {
    // Standard target options allow the person running `zig build` to choose
    // what target to build for. Here we do not override the defaults, which
    // means any target is allowed, and the default is native. Other options
    // for restricting supported target set are available.
    const target = b.standardTargetOptions(.{});
    // Standard optimization options allow the person running `zig build` to select
    // between Debug, ReleaseSafe, ReleaseFast, and ReleaseSmall. Here we do not
    // set a preferred release mode, allowing the user to decide how to optimize.
    const optimize = b.standardOptimizeOption(.{});
    // It's also possible to define more custom flags to toggle optional features
    // of this build script using `b.option()`. All defined flags (including
    // target and optimize options) will be listed when running `zig build --help`
    // in this directory.

    // This creates a module, which represents a collection of source files alongside
    // some compilation options, such as optimization mode and linked system libraries.
    // Zig modules are the preferred way of making Zig code available to consumers.
    // addModule defines a module that we intend to make available for importing
    // to our consumers. We must give it a name because a Zig package can expose
    // multiple modules and consumers will need to be able to specify which
    // module they want to access.
    const mod = b.addModule("agenkit", .{
        // The root source file is the "entry point" of this module. Users of
        // this module will only be able to access public declarations contained
        // in this file, which means that if you have declarations that you
        // intend to expose to consumers that were defined in other files part
        // of this module, you will have to make sure to re-export them from
        // the root file.
        .root_source_file = b.path("src/root.zig"),
        // Later on we'll use this module as the root module of a test executable
        // which requires us to specify a target.
        .target = target,
    });

    // Here we define an executable. An executable needs to have a root module
    // which needs to expose a `main` function. While we could add a main function
    // to the module defined above, it's sometimes preferable to split business
    // logic and the CLI into two separate modules.
    //
    // If your goal is to create a Zig library for others to use, consider if
    // it might benefit from also exposing a CLI tool. A parser library for a
    // data serialization format could also bundle a CLI syntax checker, for example.
    //
    // If instead your goal is to create an executable, consider if users might
    // be interested in also being able to embed the core functionality of your
    // program in their own executable in order to avoid the overhead involved in
    // subprocessing your CLI tool.
    //
    // If neither case applies to you, feel free to delete the declaration you
    // don't need and to put everything under a single module.
    const exe = b.addExecutable(.{
        .name = "agenkit",
        .root_module = b.createModule(.{
            // b.createModule defines a new module just like b.addModule but,
            // unlike b.addModule, it does not expose the module to consumers of
            // this package, which is why in this case we don't have to give it a name.
            .root_source_file = b.path("src/main.zig"),
            // Target and optimization levels must be explicitly wired in when
            // defining an executable or library (in the root module), and you
            // can also hardcode a specific target for an executable or library
            // definition if desireable (e.g. firmware for embedded devices).
            .target = target,
            .optimize = optimize,
            // List of modules available for import in source files part of the
            // root module.
            .imports = &.{
                // Here "agenkit" is the name you will use in your source code to
                // import this module (e.g. `@import("agenkit")`). The name is
                // repeated because you are allowed to rename your imports, which
                // can be extremely useful in case of collisions (which can happen
                // importing modules from different packages).
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // This declares intent for the executable to be installed into the
    // install prefix when running `zig build` (i.e. when executing the default
    // step). By default the install prefix is `zig-out/` but can be overridden
    // by passing `--prefix` or `-p`.
    b.installArtifact(exe);

    // This creates a top level step. Top level steps have a name and can be
    // invoked by name when running `zig build` (e.g. `zig build run`).
    // This will evaluate the `run` step rather than the default step.
    // For a top level step to actually do something, it must depend on other
    // steps (e.g. a Run step, as we will see in a moment).
    const run_step = b.step("run", "Run the app");

    // This creates a RunArtifact step in the build graph. A RunArtifact step
    // invokes an executable compiled by Zig. Steps will only be executed by the
    // runner if invoked directly by the user (in the case of top level steps)
    // or if another step depends on it, so it's up to you to define when and
    // how this Run step will be executed. In our case we want to run it when
    // the user runs `zig build run`, so we create a dependency link.
    const run_cmd = b.addRunArtifact(exe);
    run_step.dependOn(&run_cmd.step);

    // By making the run step depend on the default step, it will be run from the
    // installation directory rather than directly from within the cache directory.
    run_cmd.step.dependOn(b.getInstallStep());

    // This allows the user to pass arguments to the application in the build
    // command itself, like this: `zig build run -- arg1 arg2 etc`
    if (b.args) |args| {
        run_cmd.addArgs(args);
    }

    // Creates an executable that will run `test` blocks from the provided module.
    // Here `mod` needs to define a target, which is why earlier we made sure to
    // set the releative field.
    const mod_tests = b.addTest(.{
        .root_module = mod,
    });

    // A run step that will run the test executable.
    const run_mod_tests = b.addRunArtifact(mod_tests);

    // Creates an executable that will run `test` blocks from the executable's
    // root module. Note that test executables only test one module at a time,
    // hence why we have to create two separate ones.
    const exe_tests = b.addTest(.{
        .root_module = exe.root_module,
    });

    // A run step that will run the second test executable.
    const run_exe_tests = b.addRunArtifact(exe_tests);

    // A top level step for running all tests. dependOn can be called multiple
    // times and since the two run steps do not depend on one another, this will
    // make the two of them run in parallel.
    const test_step = b.step("test", "Run tests");
    test_step.dependOn(&run_mod_tests.step);
    test_step.dependOn(&run_exe_tests.step);

    // Just like flags, top level steps are also listed in the `--help` menu.
    //
    // The Zig build system is entirely implemented in userland, which means
    // that it cannot hook into private compiler APIs. All compilation work
    // orchestrated by the build system will result in other Zig compiler
    // subcommands being invoked with the right flags defined. You can observe
    // these invocations when one fails (or you pass a flag to increase
    // verbosity) to validate assumptions and diagnose problems.
    //
    // Lastly, the Zig build system is relatively simple and self-contained,
    // and reading its source code will allow you to master it.

    // Add echo example executable
    const echo_example = b.addExecutable(.{
        .name = "echo_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/basic/echo.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install echo example
    b.installArtifact(echo_example);

    // Create echo example run step
    const echo_step = b.step("run-echo", "Run the echo agent example");
    const echo_run = b.addRunArtifact(echo_example);
    echo_step.dependOn(&echo_run.step);
    echo_run.step.dependOn(b.getInstallStep());

    // Add workflow example executable
    const workflow_example = b.addExecutable(.{
        .name = "workflow_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/basic/workflow.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install workflow example
    b.installArtifact(workflow_example);

    // Create workflow example run step
    const workflow_step = b.step("run-workflow", "Run the simple workflow example");
    const workflow_run = b.addRunArtifact(workflow_example);
    workflow_step.dependOn(&workflow_run.step);
    workflow_run.step.dependOn(b.getInstallStep());

    // Add error handling example executable
    const error_example = b.addExecutable(.{
        .name = "error_handling_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/basic/error_handling.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install error handling example
    b.installArtifact(error_example);

    // Create error handling example run step
    const error_step = b.step("run-error-handling", "Run the error handling example");
    const error_run = b.addRunArtifact(error_example);
    error_step.dependOn(&error_run.step);
    error_run.step.dependOn(b.getInstallStep());

    // Add memory management example executable
    const memory_example = b.addExecutable(.{
        .name = "memory_management_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/basic/memory_management.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install memory management example
    b.installArtifact(memory_example);

    // Create memory management example run step
    const memory_step = b.step("run-memory", "Run the memory management example");
    const memory_run = b.addRunArtifact(memory_example);
    memory_step.dependOn(&memory_run.step);
    memory_run.step.dependOn(b.getInstallStep());

    // Add testing patterns example executable
    const testing_example = b.addExecutable(.{
        .name = "testing_patterns_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/basic/testing_patterns.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install testing patterns example
    b.installArtifact(testing_example);

    // Create testing patterns example run step
    const testing_step = b.step("run-testing", "Run the testing patterns example");
    const testing_run = b.addRunArtifact(testing_example);
    testing_step.dependOn(&testing_run.step);
    testing_run.step.dependOn(b.getInstallStep());

    // Add Sequential pattern example executable
    const sequential_example = b.addExecutable(.{
        .name = "sequential_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/sequential.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install Sequential pattern example
    b.installArtifact(sequential_example);

    // Create Sequential pattern example run step
    const sequential_step = b.step("run-sequential", "Run the Sequential pattern example");
    const sequential_run = b.addRunArtifact(sequential_example);
    sequential_step.dependOn(&sequential_run.step);
    sequential_run.step.dependOn(b.getInstallStep());

    // Add Parallel pattern example executable
    const parallel_example = b.addExecutable(.{
        .name = "parallel_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/parallel.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install Parallel pattern example
    b.installArtifact(parallel_example);

    // Create Parallel pattern example run step
    const parallel_step = b.step("run-parallel", "Run the Parallel pattern example");
    const parallel_run = b.addRunArtifact(parallel_example);
    parallel_step.dependOn(&parallel_run.step);
    parallel_run.step.dependOn(b.getInstallStep());

    // Add Reflection pattern example executable
    const reflection_example = b.addExecutable(.{
        .name = "reflection_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/reflection.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install Reflection pattern example
    b.installArtifact(reflection_example);

    // Create Reflection pattern example run step
    const reflection_step = b.step("run-reflection", "Run the Reflection pattern example");
    const reflection_run = b.addRunArtifact(reflection_example);
    reflection_step.dependOn(&reflection_run.step);
    reflection_run.step.dependOn(b.getInstallStep());

    // Add Conversational pattern example executable
    const conversational_example = b.addExecutable(.{
        .name = "conversational_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/conversational.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "agenkit", .module = mod },
            },
        }),
    });

    // Install Conversational pattern example
    b.installArtifact(conversational_example);

    // Create Conversational pattern example run step
    const conversational_step = b.step("run-conversational", "Run the Conversational pattern example");
    const conversational_run = b.addRunArtifact(conversational_example);
    conversational_step.dependOn(&conversational_run.step);
    conversational_run.step.dependOn(b.getInstallStep());

    // Add Task pattern example
    const task_example = b.addExecutable(.{
        .name = "task_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/task.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(task_example);
    const task_step = b.step("run-task", "Run the Task pattern example");
    const task_run = b.addRunArtifact(task_example);
    task_step.dependOn(&task_run.step);
    task_run.step.dependOn(b.getInstallStep());

    // Add Multiagent pattern example
    const multiagent_example = b.addExecutable(.{
        .name = "multiagent_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/multiagent.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(multiagent_example);
    const multiagent_step = b.step("run-multiagent", "Run the Multiagent pattern example");
    const multiagent_run = b.addRunArtifact(multiagent_example);
    multiagent_step.dependOn(&multiagent_run.step);
    multiagent_run.step.dependOn(b.getInstallStep());

    // Add Memory Hierarchy pattern example
    const memory_hierarchy_example = b.addExecutable(.{
        .name = "memory_hierarchy_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/memory_hierarchy.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(memory_hierarchy_example);
    const memory_hierarchy_step = b.step("run-memory-hierarchy", "Run the Memory Hierarchy pattern example");
    const memory_hierarchy_run = b.addRunArtifact(memory_hierarchy_example);
    memory_hierarchy_step.dependOn(&memory_hierarchy_run.step);
    memory_hierarchy_run.step.dependOn(b.getInstallStep());

    // Add Router pattern example
    const router_example = b.addExecutable(.{
        .name = "router_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/router_example.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(router_example);
    const router_step = b.step("run-router", "Run the Router pattern example");
    const router_run = b.addRunArtifact(router_example);
    router_step.dependOn(&router_run.step);
    router_run.step.dependOn(b.getInstallStep());

    // Add Fallback pattern example
    const fallback_example = b.addExecutable(.{
        .name = "fallback_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/fallback_example.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(fallback_example);
    const fallback_step = b.step("run-fallback", "Run the Fallback pattern example");
    const fallback_run = b.addRunArtifact(fallback_example);
    fallback_step.dependOn(&fallback_run.step);
    fallback_run.step.dependOn(b.getInstallStep());

    // Add Collaborative pattern example
    const collaborative_example = b.addExecutable(.{
        .name = "collaborative_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/collaborative_example.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(collaborative_example);
    const collaborative_step = b.step("run-collaborative", "Run the Collaborative pattern example");
    const collaborative_run = b.addRunArtifact(collaborative_example);
    collaborative_step.dependOn(&collaborative_run.step);
    collaborative_run.step.dependOn(b.getInstallStep());

    // Add Agents-as-Tools pattern example
    const agents_as_tools_example = b.addExecutable(.{
        .name = "agents_as_tools_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/agents_as_tools.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(agents_as_tools_example);
    const agents_as_tools_step = b.step("run-agents-as-tools", "Run the Agents-as-Tools pattern example");
    const agents_as_tools_run = b.addRunArtifact(agents_as_tools_example);
    agents_as_tools_step.dependOn(&agents_as_tools_run.step);
    agents_as_tools_run.step.dependOn(b.getInstallStep());

    // Add ReAct pattern example
    const react_example = b.addExecutable(.{
        .name = "react_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/react.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(react_example);
    const react_step = b.step("run-react", "Run the ReAct pattern example");
    const react_run = b.addRunArtifact(react_example);
    react_step.dependOn(&react_run.step);
    react_run.step.dependOn(b.getInstallStep());

    // Add Planning pattern example
    const planning_example = b.addExecutable(.{
        .name = "planning_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/planning.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(planning_example);
    const planning_step = b.step("run-planning", "Run the Planning pattern example");
    const planning_run = b.addRunArtifact(planning_example);
    planning_step.dependOn(&planning_run.step);
    planning_run.step.dependOn(b.getInstallStep());

    // Add Autonomous pattern example
    const autonomous_example = b.addExecutable(.{
        .name = "autonomous_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/patterns/autonomous.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(autonomous_example);
    const autonomous_step = b.step("run-autonomous", "Run the Autonomous pattern example");
    const autonomous_run = b.addRunArtifact(autonomous_example);
    autonomous_step.dependOn(&autonomous_run.step);
    autonomous_run.step.dependOn(b.getInstallStep());

    // Integration examples

    // Add Multi-Pattern Workflow integration example
    const multi_pattern_example = b.addExecutable(.{
        .name = "multi_pattern_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/integration/multi_pattern_workflow.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(multi_pattern_example);
    const multi_pattern_step = b.step("run-multi-pattern", "Run the Multi-Pattern Workflow integration example");
    const multi_pattern_run = b.addRunArtifact(multi_pattern_example);
    multi_pattern_step.dependOn(&multi_pattern_run.step);
    multi_pattern_run.step.dependOn(b.getInstallStep());

    // Add Long-Running Agent integration example
    const long_running_example = b.addExecutable(.{
        .name = "long_running_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/integration/long_running_agent.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(long_running_example);
    const long_running_step = b.step("run-long-running", "Run the Long-Running Agent integration example");
    const long_running_run = b.addRunArtifact(long_running_example);
    long_running_step.dependOn(&long_running_run.step);
    long_running_run.step.dependOn(b.getInstallStep());

    // Add Evaluation Pipeline integration example
    const evaluation_example = b.addExecutable(.{
        .name = "evaluation_example",
        .root_module = b.createModule(.{
            .root_source_file = b.path("examples/integration/evaluation_pipeline.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{ .{ .name = "agenkit", .module = mod } },
        }),
    });
    b.installArtifact(evaluation_example);
    const evaluation_step = b.step("run-evaluation", "Run the Evaluation Pipeline integration example");
    const evaluation_run = b.addRunArtifact(evaluation_example);
    evaluation_step.dependOn(&evaluation_run.step);
    evaluation_run.step.dependOn(b.getInstallStep());
}
