/// Task Pattern - One-shot Agent Execution with Lifecycle Management
///
/// The Task pattern wraps an Agent for single-use execution with automatic
/// resource cleanup and explicit lifecycle management.
///
/// # Key Concepts
///
/// - **One-shot Semantics**: Execute once, then cleanup
/// - **Resource Management**: Automatic cleanup after completion
/// - **Retry Logic**: Multiple attempts on failures
/// - **Reuse Prevention**: Cannot execute the same Task twice
///
/// # Use Cases
///
/// - Single-purpose operations (summarize, classify, extract)
/// - Tasks requiring explicit resource cleanup
/// - Operations needing retry at task level
/// - Batch processing with independent tasks
///
/// # Agent vs Task
///
/// - **Agent**: Multi-turn conversation with state
/// - **Task**: One-shot execution, then cleanup
///
/// # Example
///
/// ```zig
/// const std = @import("std");
/// const agenkit = @import("agenkit");
///
/// pub fn main() !void {
///     var gpa = std.heap.GeneralPurposeAllocator(.{}){};
///     defer _ = gpa.deinit();
///     const allocator = gpa.allocator();
///
///     var echo = try agenkit.EchoAgent.init(allocator);
///     defer echo.agent().deinit();
///
///     var config = agenkit.patterns.TaskConfig{
///         .retries = 2,
///     };
///
///     var task = try agenkit.patterns.Task.init(allocator, echo.agent(), config);
///     defer task.deinit();
///
///     var msg = try agenkit.Message.withText(allocator, .user, "Task input");
///     defer msg.deinit();
///
///     const result = try task.execute(msg);
///     var response = try result.unwrap();
///     defer response.deinit();
///
///     // Task automatically marked as completed, cannot reuse
/// }
/// ```

const std = @import("std");
const Allocator = std.mem.Allocator;
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Message = @import("../message.zig").Message;
const Result = @import("../agent.zig").Result;

/// Configuration for Task execution
pub const TaskConfig = struct {
    /// Number of retry attempts on failure (default: 0)
    retries: usize = 0,
};

/// State tracking for Task execution
const TaskState = enum {
    pending,
    running,
    completed,
    failed,
};

/// One-shot agent execution with lifecycle management
pub const Task = struct {
    allocator: Allocator,
    agent: Agent,
    config: TaskConfig,
    state: TaskState,
    result: ?Message,
    error_msg: ?[]const u8,

    /// Creates a new Task
    pub fn init(allocator: Allocator, agent: Agent, config: TaskConfig) !Task {
        return Task{
            .allocator = allocator,
            .agent = agent,
            .config = config,
            .state = .pending,
            .result = null,
            .error_msg = null,
        };
    }

    pub fn deinit(self: *Task) void {
        if (self.result) |*result| {
            result.deinit();
        }
        if (self.error_msg) |err| {
            self.allocator.free(err);
        }
    }

    /// Execute the task once
    ///
    /// This method can only be called once per Task instance. After execution
    /// completes (successfully or with error), the Task is marked as completed
    /// and cannot be reused.
    pub fn execute(self: *Task, message: Message) AgentError!Result {
        // Check if already completed
        if (self.state == .completed or self.state == .failed) {
            return AgentError.InvalidInput;
        }

        self.state = .running;

        const attempts = self.config.retries + 1; // retries=0 means 1 attempt
        var last_error: ?AgentError = null;

        var attempt: usize = 0;
        while (attempt < attempts) : (attempt += 1) {
            // Execute agent
            const result = self.agent.process(message) catch |err| {
                last_error = err;

                // If this was the last attempt, fail
                if (attempt == attempts - 1) {
                    self.state = .failed;
                    const error_msg = std.fmt.allocPrint(self.allocator, "Task failed after {d} attempts: {s}", .{ attempts, @errorName(err) }) catch {
                        return AgentError.ProcessingFailed;
                    };
                    self.error_msg = error_msg;
                    return err;
                }

                // Otherwise, retry
                continue;
            };

            // Success - mark completed and return
            self.state = .completed;

            // Clone result for storage
            var response = result.unwrap() catch |err| {
                self.state = .failed;
                return err;
            };

            const response_clone = cloneMessage(self.allocator, response) catch {
                response.deinit();
                self.state = .failed;
                return AgentError.ProcessingFailed;
            };
            self.result = response_clone;

            return Result{ .ok = response };
        }

        // Mark as failed
        self.state = .failed;

        if (last_error) |err| {
            return err;
        } else {
            return AgentError.ProcessingFailed;
        }
    }

    /// Check if the task has been completed
    pub fn completed(self: *const Task) bool {
        return self.state == .completed or self.state == .failed;
    }

    /// Get the current state
    pub fn getState(self: *const Task) TaskState {
        return self.state;
    }

    /// Get the result of the task (if completed successfully)
    pub fn getResult(self: *const Task) ?Message {
        return self.result;
    }

    /// Get error message if task failed
    pub fn getErrorMessage(self: *const Task) ?[]const u8 {
        return self.error_msg;
    }
};

/// Helper function to clone a message
fn cloneMessage(allocator: Allocator, msg: Message) !Message {
    const text = try msg.contentAsText();
    return try Message.withText(allocator, msg.role, text);
}

// Tests
const testing = std.testing;
const EchoAgent = @import("../agent.zig").EchoAgent;

test "TaskConfig default" {
    const config = TaskConfig{};
    try testing.expectEqual(@as(usize, 0), config.retries);
}

test "Task creation" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const config = TaskConfig{ .retries = 2 };

    var task = try Task.init(allocator, echo.agent(), config);
    defer task.deinit();

    try testing.expectEqual(TaskState.pending, task.state);
    try testing.expect(!task.completed());
}

test "Task execute once" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const config = TaskConfig{ .retries = 0 };

    var task = try Task.init(allocator, echo.agent(), config);
    defer task.deinit();

    var msg = try Message.withText(allocator, .user, "Test input");
    defer msg.deinit();

    const result = try task.execute(msg);
    var response = try result.unwrap();
    defer response.deinit();

    try testing.expect(task.completed());
    try testing.expectEqual(TaskState.completed, task.getState());

    const content = try response.contentAsText();
    try testing.expectEqualStrings("Test input", content);
}

test "Task cannot execute twice" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const config = TaskConfig{ .retries = 0 };

    var task = try Task.init(allocator, echo.agent(), config);
    defer task.deinit();

    var msg = try Message.withText(allocator, .user, "Test input");
    defer msg.deinit();

    // First execution should succeed
    const result1 = try task.execute(msg);
    var response1 = try result1.unwrap();
    defer response1.deinit();

    try testing.expect(task.completed());

    // Second execution should fail
    const result2 = task.execute(msg);
    try testing.expectError(AgentError.InvalidInput, result2);
}

test "Task getResult" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const config = TaskConfig{ .retries = 0 };

    var task = try Task.init(allocator, echo.agent(), config);
    defer task.deinit();

    try testing.expect(task.getResult() == null);

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try task.execute(msg);
    var response = try result.unwrap();
    defer response.deinit();

    try testing.expect(task.getResult() != null);
}

test "Task with retries" {
    const allocator = testing.allocator;

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const config = TaskConfig{ .retries = 3 };

    var task = try Task.init(allocator, echo.agent(), config);
    defer task.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try task.execute(msg);
    var response = try result.unwrap();
    defer response.deinit();

    try testing.expect(task.completed());
    try testing.expectEqual(TaskState.completed, task.getState());
}

// Mock agent that fails N times before succeeding
const FailingAgent = struct {
    allocator: Allocator,
    fail_count: usize,
    attempts: usize,
    agent_name: []const u8,

    pub fn init(allocator: Allocator, fail_count: usize) !FailingAgent {
        return FailingAgent{
            .allocator = allocator,
            .fail_count = fail_count,
            .attempts = 0,
            .agent_name = try allocator.dupe(u8, "FailingAgent"),
        };
    }

    pub fn deinit(self: *FailingAgent) void {
        self.allocator.free(self.agent_name);
    }

    pub fn agent(self: *FailingAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .process = processImpl,
                .deinit = deinitImpl,
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
            },
        };
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *FailingAgent = @ptrCast(@alignCast(ptr));

        self.attempts += 1;

        if (self.attempts <= self.fail_count) {
            return AgentError.ProcessingFailed;
        }

        // Success after N failures
        const text = message.contentAsText() catch {
            return AgentError.InvalidInput;
        };

        const response = Message.withText(self.allocator, .assistant, text) catch {
            return AgentError.ProcessingFailed;
        };

        return Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *FailingAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *FailingAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = [_][]const u8{"failing"};
        const result = try allocator.alloc([]const u8, caps.len);
        for (caps, 0..) |cap, i| {
            result[i] = try allocator.dupe(u8, cap);
        }
        return result;
    }
};

test "Task retry on failure" {
    const allocator = testing.allocator;

    // Agent that fails twice then succeeds
    var failing = try FailingAgent.init(allocator, 2);
    defer failing.agent().deinit();

    const config = TaskConfig{ .retries = 3 }; // 4 total attempts

    var task = try Task.init(allocator, failing.agent(), config);
    defer task.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = try task.execute(msg);
    var response = try result.unwrap();
    defer response.deinit();

    try testing.expect(task.completed());
    try testing.expectEqual(TaskState.completed, task.getState());
    try testing.expectEqual(@as(usize, 3), failing.attempts);
}

test "Task fails after retries exhausted" {
    const allocator = testing.allocator;

    // Agent that always fails
    var failing = try FailingAgent.init(allocator, 10);
    defer failing.agent().deinit();

    const config = TaskConfig{ .retries = 2 }; // 3 total attempts

    var task = try Task.init(allocator, failing.agent(), config);
    defer task.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const result = task.execute(msg);
    try testing.expectError(AgentError.ProcessingFailed, result);

    try testing.expect(task.completed());
    try testing.expectEqual(TaskState.failed, task.getState());
    try testing.expectEqual(@as(usize, 3), failing.attempts);
}
