/// Checkpoint storage backends for persistent state management.
///
/// Provides:
/// - CheckpointStorage: Interface for storage backends
/// - InMemoryStorage: In-memory storage for testing/development
/// - FileStorage: File-based persistent storage for production
///
/// Example:
///   var storage = InMemoryStorage.init(allocator);
///   defer storage.deinit();
///   try storage.save(checkpoint);
///   const loaded = try storage.load(checkpoint_id);
const std = @import("std");
const ioc = @import("../../io_compat.zig");
const agksync = @import("../../sync_compat.zig");
const agktime = @import("../../time_compat.zig");
const fs = std.fs;
const Allocator = std.mem.Allocator;
const Checkpoint = @import("checkpoint.zig").Checkpoint;

/// CheckpointStorage is the interface for checkpoint storage backends.
///
/// All storage implementations must provide these methods:
/// - save: Store a checkpoint
/// - load: Retrieve a checkpoint by ID
/// - listCheckpoints: List checkpoints for a session
/// - getLatest: Get most recent checkpoint for session
/// - delete: Delete a checkpoint
/// - deleteSession: Delete all checkpoints for session
/// - getCheckpointHistory: Get checkpoint history by following parent links
pub const CheckpointStorage = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        save: *const fn (ptr: *anyopaque, checkpoint: *const Checkpoint) anyerror!void,
        load: *const fn (ptr: *anyopaque, checkpoint_id: []const u8) anyerror!?*Checkpoint,
        listCheckpoints: *const fn (ptr: *anyopaque, session_id: []const u8, limit: usize) anyerror![]const *Checkpoint,
        getLatest: *const fn (ptr: *anyopaque, session_id: []const u8) anyerror!?*Checkpoint,
        delete: *const fn (ptr: *anyopaque, checkpoint_id: []const u8) anyerror!bool,
        deleteSession: *const fn (ptr: *anyopaque, session_id: []const u8) anyerror!usize,
        getCheckpointHistory: *const fn (ptr: *anyopaque, checkpoint_id: []const u8, max_depth: usize) anyerror![]const *Checkpoint,
        deinit: *const fn (ptr: *anyopaque) void,
    };

    pub fn save(self: CheckpointStorage, checkpoint: *const Checkpoint) !void {
        return self.vtable.save(self.ptr, checkpoint);
    }

    pub fn load(self: CheckpointStorage, checkpoint_id: []const u8) !?*Checkpoint {
        return self.vtable.load(self.ptr, checkpoint_id);
    }

    pub fn listCheckpoints(self: CheckpointStorage, session_id: []const u8, limit: usize) ![]const *Checkpoint {
        return self.vtable.listCheckpoints(self.ptr, session_id, limit);
    }

    pub fn getLatest(self: CheckpointStorage, session_id: []const u8) !?*Checkpoint {
        return self.vtable.getLatest(self.ptr, session_id);
    }

    pub fn delete(self: CheckpointStorage, checkpoint_id: []const u8) !bool {
        return self.vtable.delete(self.ptr, checkpoint_id);
    }

    pub fn deleteSession(self: CheckpointStorage, session_id: []const u8) !usize {
        return self.vtable.deleteSession(self.ptr, session_id);
    }

    pub fn getCheckpointHistory(self: CheckpointStorage, checkpoint_id: []const u8, max_depth: usize) ![]const *Checkpoint {
        return self.vtable.getCheckpointHistory(self.ptr, checkpoint_id, max_depth);
    }

    pub fn deinit(self: CheckpointStorage) void {
        return self.vtable.deinit(self.ptr);
    }
};

/// InMemoryStorage provides in-memory checkpoint storage.
///
/// Good for:
///   - Testing
///   - Development
///   - Short-lived sessions
///
/// Not suitable for:
///   - Production (no persistence)
///   - Long-running agents (lost on restart)
///
/// Example:
///   var storage = InMemoryStorage.init(allocator);
///   defer storage.deinit();
///   try storage.save(&checkpoint);
pub const InMemoryStorage = struct {
    allocator: Allocator,
    mutex: agksync.Mutex,
    checkpoints: std.StringHashMap(*Checkpoint),
    session_checkpoints: std.StringHashMap(std.ArrayList([]const u8)),

    pub fn init(allocator: Allocator) InMemoryStorage {
        return .{
            .allocator = allocator,
            .mutex = .{},
            .checkpoints = std.StringHashMap(*Checkpoint).init(allocator),
            .session_checkpoints = std.StringHashMap(std.ArrayList([]const u8)).init(allocator),
        };
    }

    pub fn deinit(self: *InMemoryStorage) void {
        // Free all checkpoints and their keys
        var checkpoint_iter = self.checkpoints.iterator();
        while (checkpoint_iter.next()) |entry| {
            self.allocator.free(entry.key_ptr.*); // Free the HashMap key
            entry.value_ptr.*.deinit();
            self.allocator.destroy(entry.value_ptr.*);
        }
        self.checkpoints.deinit();

        // Free session checkpoint lists
        var session_iter = self.session_checkpoints.valueIterator();
        while (session_iter.next()) |list| {
            for (list.items) |checkpoint_id| {
                self.allocator.free(checkpoint_id);
            }
            list.deinit(self.allocator);
        }
        self.session_checkpoints.deinit();
    }

    pub fn save(self: *InMemoryStorage, checkpoint: *const Checkpoint) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        // Create a copy of the checkpoint
        const checkpoint_copy = try self.allocator.create(Checkpoint);
        checkpoint_copy.* = try self.copyCheckpoint(checkpoint);

        // Store checkpoint
        const key = try self.allocator.dupe(u8, checkpoint.checkpoint_id);
        try self.checkpoints.put(key, checkpoint_copy);

        // Add to session index (use the copy's session_id, not the original)
        const session_id = checkpoint_copy.session_id;
        const gop = try self.session_checkpoints.getOrPut(session_id);

        if (!gop.found_existing) {
            gop.value_ptr.* = .empty;
        }

        // Check if already in list
        var found = false;
        for (gop.value_ptr.items) |cid| {
            if (std.mem.eql(u8, cid, checkpoint.checkpoint_id)) {
                found = true;
                break;
            }
        }

        if (!found) {
            const checkpoint_id_copy = try self.allocator.dupe(u8, checkpoint.checkpoint_id);
            try gop.value_ptr.append(self.allocator, checkpoint_id_copy);

            // Sort by timestamp (most recent first)
            const Context = struct {
                checkpoints: *std.StringHashMap(*Checkpoint),
                pub fn lessThan(ctx: @This(), a: []const u8, b: []const u8) bool {
                    const checkpoint_a = ctx.checkpoints.get(a) orelse return false;
                    const checkpoint_b = ctx.checkpoints.get(b) orelse return true;
                    return checkpoint_a.timestamp > checkpoint_b.timestamp;
                }
            };
            std.mem.sort([]const u8, gop.value_ptr.items, Context{ .checkpoints = &self.checkpoints }, Context.lessThan);
        }
    }

    pub fn load(self: *InMemoryStorage, checkpoint_id: []const u8) !?*Checkpoint {
        self.mutex.lock();
        defer self.mutex.unlock();

        const checkpoint = self.checkpoints.get(checkpoint_id) orelse return null;

        // Return a copy
        const checkpoint_copy = try self.allocator.create(Checkpoint);
        checkpoint_copy.* = try self.copyCheckpoint(checkpoint);
        return checkpoint_copy;
    }

    pub fn listCheckpoints(self: *InMemoryStorage, session_id: []const u8, limit: usize) ![]const *Checkpoint {
        self.mutex.lock();
        defer self.mutex.unlock();

        const checkpoint_ids = self.session_checkpoints.get(session_id) orelse {
            return &[_]*Checkpoint{};
        };

        const actual_limit = if (limit > 0 and checkpoint_ids.items.len > limit) limit else checkpoint_ids.items.len;

        const result = try self.allocator.alloc(*Checkpoint, actual_limit);
        for (result, 0..) |*item, i| {
            const checkpoint_id = checkpoint_ids.items[i];
            const checkpoint = self.checkpoints.get(checkpoint_id).?;
            const checkpoint_copy = try self.allocator.create(Checkpoint);
            checkpoint_copy.* = try self.copyCheckpoint(checkpoint);
            item.* = checkpoint_copy;
        }

        return result;
    }

    pub fn getLatest(self: *InMemoryStorage, session_id: []const u8) !?*Checkpoint {
        const checkpoints = try self.listCheckpoints(session_id, 1);
        defer self.allocator.free(checkpoints);

        if (checkpoints.len == 0) {
            return null;
        }

        // Return checkpoint without freeing (caller owns it)
        return checkpoints[0];
    }

    pub fn delete(self: *InMemoryStorage, checkpoint_id: []const u8) !bool {
        self.mutex.lock();
        defer self.mutex.unlock();

        const checkpoint = self.checkpoints.get(checkpoint_id) orelse return false;
        const session_id = checkpoint.session_id;

        // Remove from checkpoints map
        _ = self.checkpoints.remove(checkpoint_id);
        checkpoint.deinit();
        self.allocator.destroy(checkpoint);

        // Remove from session index
        if (self.session_checkpoints.getPtr(session_id)) |list| {
            var i: usize = 0;
            while (i < list.items.len) {
                if (std.mem.eql(u8, list.items[i], checkpoint_id)) {
                    const removed = list.orderedRemove(i);
                    self.allocator.free(removed);
                    break;
                }
                i += 1;
            }
        }

        return true;
    }

    pub fn deleteSession(self: *InMemoryStorage, session_id: []const u8) !usize {
        self.mutex.lock();
        defer self.mutex.unlock();

        const checkpoint_ids = self.session_checkpoints.get(session_id) orelse return 0;

        const count = checkpoint_ids.items.len;

        // Delete all checkpoints for session
        for (checkpoint_ids.items) |checkpoint_id| {
            if (self.checkpoints.get(checkpoint_id)) |checkpoint| {
                _ = self.checkpoints.remove(checkpoint_id);
                checkpoint.deinit();
                self.allocator.destroy(checkpoint);
            }
            self.allocator.free(checkpoint_id);
        }

        // Remove session entry
        var list = self.session_checkpoints.fetchRemove(session_id).?.value;
        list.deinit(self.allocator);

        return count;
    }

    pub fn getCheckpointHistory(self: *InMemoryStorage, checkpoint_id: []const u8, max_depth: usize) ![]const *Checkpoint {
        var history: std.ArrayList(*Checkpoint) = .empty;
        defer history.deinit(self.allocator);

        var current_id = checkpoint_id;
        var depth: usize = 0;

        while (depth < max_depth) : (depth += 1) {
            const checkpoint = try self.load(current_id) orelse break;
            try history.append(self.allocator, checkpoint);

            if (checkpoint.parent_checkpoint_id) |parent_id| {
                current_id = parent_id;
            } else {
                break;
            }
        }

        return history.toOwnedSlice(self.allocator);
    }

    pub fn storage(self: *InMemoryStorage) CheckpointStorage {
        return .{
            .ptr = self,
            .vtable = &.{
                .save = saveImpl,
                .load = loadImpl,
                .listCheckpoints = listCheckpointsImpl,
                .getLatest = getLatestImpl,
                .delete = deleteImpl,
                .deleteSession = deleteSessionImpl,
                .getCheckpointHistory = getCheckpointHistoryImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn saveImpl(ptr: *anyopaque, checkpoint: *const Checkpoint) anyerror!void {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.save(checkpoint);
    }

    fn loadImpl(ptr: *anyopaque, checkpoint_id: []const u8) anyerror!?*Checkpoint {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.load(checkpoint_id);
    }

    fn listCheckpointsImpl(ptr: *anyopaque, session_id: []const u8, limit: usize) anyerror![]const *Checkpoint {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.listCheckpoints(session_id, limit);
    }

    fn getLatestImpl(ptr: *anyopaque, session_id: []const u8) anyerror!?*Checkpoint {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.getLatest(session_id);
    }

    fn deleteImpl(ptr: *anyopaque, checkpoint_id: []const u8) anyerror!bool {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.delete(checkpoint_id);
    }

    fn deleteSessionImpl(ptr: *anyopaque, session_id: []const u8) anyerror!usize {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.deleteSession(session_id);
    }

    fn getCheckpointHistoryImpl(ptr: *anyopaque, checkpoint_id: []const u8, max_depth: usize) anyerror![]const *Checkpoint {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        return self.getCheckpointHistory(checkpoint_id, max_depth);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *InMemoryStorage = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    fn copyJsonValue(self: *InMemoryStorage, value: std.json.Value) !std.json.Value {
        return switch (value) {
            .null => .null,
            .bool => |b| .{ .bool = b },
            .integer => |i| .{ .integer = i },
            .float => |f| .{ .float = f },
            .number_string => |ns| .{ .number_string = try self.allocator.dupe(u8, ns) },
            .string => |s| .{ .string = try self.allocator.dupe(u8, s) },
            .array => |arr| {
                var array_copy = std.json.Array.init(self.allocator);
                for (arr.items) |item| {
                    try array_copy.append(try self.copyJsonValue(item));
                }
                return .{ .array = array_copy };
            },
            .object => |obj| {
                var object_copy = std.json.ObjectMap.empty;
                var iter = obj.iterator();
                while (iter.next()) |entry| {
                    const key_copy = try self.allocator.dupe(u8, entry.key_ptr.*);
                    const value_copy = try self.copyJsonValue(entry.value_ptr.*);
                    try object_copy.put(self.allocator, key_copy, value_copy);
                }
                return .{ .object = object_copy };
            },
        };
    }

    fn copyCheckpoint(self: *InMemoryStorage, checkpoint: *const Checkpoint) !Checkpoint {
        // Deep copy state ObjectMap (including keys and values)
        var state_copy = std.json.ObjectMap.empty;
        var state_iter = checkpoint.state.object.iterator();
        while (state_iter.next()) |entry| {
            const key_copy = try self.allocator.dupe(u8, entry.key_ptr.*);
            const value_copy = try self.copyJsonValue(entry.value_ptr.*);
            try state_copy.put(self.allocator, key_copy, value_copy);
        }

        // Deep copy metadata ObjectMap (including keys and values)
        var metadata_copy = std.json.ObjectMap.empty;
        var metadata_iter = checkpoint.metadata.object.iterator();
        while (metadata_iter.next()) |entry| {
            const key_copy = try self.allocator.dupe(u8, entry.key_ptr.*);
            const value_copy = try self.copyJsonValue(entry.value_ptr.*);
            try metadata_copy.put(self.allocator, key_copy, value_copy);
        }

        // Create a deep copy of the checkpoint
        var copy = Checkpoint{
            .checkpoint_id = try self.allocator.dupe(u8, checkpoint.checkpoint_id),
            .session_id = try self.allocator.dupe(u8, checkpoint.session_id),
            .agent_name = try self.allocator.dupe(u8, checkpoint.agent_name),
            .timestamp = checkpoint.timestamp,
            .step_number = checkpoint.step_number,
            .state = std.json.Value{ .object = state_copy },
            .messages = try self.allocator.alloc(@TypeOf(checkpoint.messages[0]), checkpoint.messages.len),
            .metadata = std.json.Value{ .object = metadata_copy },
            .parent_checkpoint_id = if (checkpoint.parent_checkpoint_id) |pid|
                try self.allocator.dupe(u8, pid)
            else
                null,
            .allocator = self.allocator,
        };

        // Deep copy messages
        const Message = @import("../../message.zig").Message;
        for (checkpoint.messages, 0..) |msg, i| {
            copy.messages[i] = try Message.withText(self.allocator, msg.role, try msg.contentAsText());
        }

        return copy;
    }
};

/// FileStorage provides file-based checkpoint storage.
///
/// Stores each checkpoint as a JSON file on disk for persistence.
///
/// Directory structure:
///   checkpoint_dir/
///     {session_id}/
///       {checkpoint_id}.json
///       {checkpoint_id}.json
///       ...
///
/// Good for:
///   - Production (persistent)
///   - Single-machine deployments
///   - Development with persistence
///
/// Example:
///   var storage = try FileStorage.init(allocator, "./checkpoints");
///   defer storage.deinit();
///   try storage.save(&checkpoint);
pub const FileStorage = struct {
    allocator: Allocator,
    checkpoint_dir: []const u8,

    pub fn init(allocator: Allocator, checkpoint_dir: []const u8) !FileStorage {
        // Create directory if it doesn't exist
        std.Io.Dir.cwd().createDirPath(ioc.io(), checkpoint_dir) catch |err| switch (err) {
            error.PathAlreadyExists => {},
            else => return err,
        };

        return .{
            .allocator = allocator,
            .checkpoint_dir = try allocator.dupe(u8, checkpoint_dir),
        };
    }

    pub fn deinit(self: *FileStorage) void {
        self.allocator.free(self.checkpoint_dir);
    }

    pub fn save(self: *FileStorage, checkpoint: *const Checkpoint) !void {
        // Create session directory
        const session_dir = try self.getSessionDir(checkpoint.session_id);
        defer self.allocator.free(session_dir);

        std.Io.Dir.cwd().createDirPath(ioc.io(), session_dir) catch |err| switch (err) {
            error.PathAlreadyExists => {},
            else => return err,
        };

        // Serialize checkpoint
        const json_data = try checkpoint.toJson();
        defer self.allocator.free(json_data);

        // Write to file
        const checkpoint_path = try self.getCheckpointPath(checkpoint.session_id, checkpoint.checkpoint_id);
        defer self.allocator.free(checkpoint_path);

        const file = try std.Io.Dir.cwd().createFile(ioc.io(), checkpoint_path, .{});
        defer file.close(ioc.io());

        try file.writeStreamingAll(ioc.io(), json_data);
    }

    pub fn load(self: *FileStorage, checkpoint_id: []const u8) !?*Checkpoint {
        // Search through session directories
        var checkpoint_dir = try std.Io.Dir.cwd().openDir(ioc.io(), self.checkpoint_dir, .{ .iterate = true });
        defer checkpoint_dir.close(ioc.io());

        var dir_iter = checkpoint_dir.iterate();
        while (try dir_iter.next(ioc.io())) |entry| {
            if (entry.kind != .directory) continue;

            const checkpoint_filename = try std.fmt.allocPrint(self.allocator, "{s}.json", .{checkpoint_id});
            defer self.allocator.free(checkpoint_filename);

            const checkpoint_path = try std.fmt.allocPrint(
                self.allocator,
                "{s}/{s}/{s}",
                .{ self.checkpoint_dir, entry.name, checkpoint_filename },
            );
            defer self.allocator.free(checkpoint_path);

            // Check if file exists
            const json_data = std.Io.Dir.cwd().readFileAlloc(ioc.io(), checkpoint_path, self.allocator, .limited(10 * 1024 * 1024)) catch |err| switch (err) {
                error.FileNotFound => continue,
                else => return err,
            };
            defer self.allocator.free(json_data);

            const checkpoint = try self.allocator.create(Checkpoint);
            checkpoint.* = try Checkpoint.fromJson(self.allocator, json_data);
            return checkpoint;
        }

        return null;
    }

    pub fn listCheckpoints(self: *FileStorage, session_id: []const u8, limit: usize) ![]const *Checkpoint {
        const session_dir_path = try self.getSessionDir(session_id);
        defer self.allocator.free(session_dir_path);

        var session_dir = std.Io.Dir.cwd().openDir(ioc.io(), session_dir_path, .{ .iterate = true }) catch |err| switch (err) {
            error.FileNotFound => return &[_]*Checkpoint{},
            else => return err,
        };
        defer session_dir.close(ioc.io());

        var checkpoints: std.ArrayList(*Checkpoint) = .empty;
        defer checkpoints.deinit(self.allocator);

        var dir_iter = session_dir.iterate();
        while (try dir_iter.next(ioc.io())) |entry| {
            if (entry.kind != .file) continue;
            if (!std.mem.endsWith(u8, entry.name, ".json")) continue;

            const file_path = try std.fmt.allocPrint(
                self.allocator,
                "{s}/{s}",
                .{ session_dir_path, entry.name },
            );
            defer self.allocator.free(file_path);

            const json_data = std.Io.Dir.cwd().readFileAlloc(ioc.io(), file_path, self.allocator, .limited(10 * 1024 * 1024)) catch continue;
            defer self.allocator.free(json_data);

            const checkpoint = self.allocator.create(Checkpoint) catch continue;
            checkpoint.* = Checkpoint.fromJson(self.allocator, json_data) catch {
                self.allocator.destroy(checkpoint);
                continue;
            };

            try checkpoints.append(self.allocator, checkpoint);
        }

        // Sort by timestamp (most recent first)
        const items = try checkpoints.toOwnedSlice(self.allocator);
        std.mem.sort(*Checkpoint, items, {}, struct {
            fn lessThan(_: void, a: *Checkpoint, b: *Checkpoint) bool {
                return a.timestamp > b.timestamp;
            }
        }.lessThan);

        // Apply limit
        if (limit > 0 and items.len > limit) {
            // Free checkpoints beyond limit
            for (items[limit..]) |checkpoint| {
                checkpoint.deinit();
                self.allocator.destroy(checkpoint);
            }
            // Allocate new slice of correct size
            const limited = try self.allocator.alloc(*Checkpoint, limit);
            @memcpy(limited, items[0..limit]);
            self.allocator.free(items); // Free original allocation
            return limited;
        }

        return items;
    }

    pub fn getLatest(self: *FileStorage, session_id: []const u8) !?*Checkpoint {
        const checkpoints = try self.listCheckpoints(session_id, 1);
        // Only free if not empty (empty slice is stack-allocated)
        defer if (checkpoints.len > 0) self.allocator.free(checkpoints);

        if (checkpoints.len == 0) {
            return null;
        }

        return checkpoints[0];
    }

    pub fn delete(self: *FileStorage, checkpoint_id: []const u8) !bool {
        // Search through session directories
        var checkpoint_dir = try std.Io.Dir.cwd().openDir(ioc.io(), self.checkpoint_dir, .{ .iterate = true });
        defer checkpoint_dir.close(ioc.io());

        var dir_iter = checkpoint_dir.iterate();
        while (try dir_iter.next(ioc.io())) |entry| {
            if (entry.kind != .directory) continue;

            const checkpoint_filename = try std.fmt.allocPrint(self.allocator, "{s}.json", .{checkpoint_id});
            defer self.allocator.free(checkpoint_filename);

            const checkpoint_path = try std.fmt.allocPrint(
                self.allocator,
                "{s}/{s}/{s}",
                .{ self.checkpoint_dir, entry.name, checkpoint_filename },
            );
            defer self.allocator.free(checkpoint_path);

            std.Io.Dir.cwd().deleteFile(ioc.io(), checkpoint_path) catch |err| switch (err) {
                error.FileNotFound => continue,
                else => return err,
            };

            return true;
        }

        return false;
    }

    pub fn deleteSession(self: *FileStorage, session_id: []const u8) !usize {
        const session_dir_path = try self.getSessionDir(session_id);
        defer self.allocator.free(session_dir_path);

        var session_dir = std.Io.Dir.cwd().openDir(ioc.io(), session_dir_path, .{ .iterate = true }) catch |err| switch (err) {
            error.FileNotFound => return 0,
            else => return err,
        };
        defer session_dir.close(ioc.io());

        var count: usize = 0;
        var dir_iter = session_dir.iterate();
        while (try dir_iter.next(ioc.io())) |entry| {
            if (entry.kind != .file) continue;
            if (!std.mem.endsWith(u8, entry.name, ".json")) continue;

            const file_path = try std.fmt.allocPrint(
                self.allocator,
                "{s}/{s}",
                .{ session_dir_path, entry.name },
            );
            defer self.allocator.free(file_path);

            std.Io.Dir.cwd().deleteFile(ioc.io(), file_path) catch continue;
            count += 1;
        }

        // Try to remove session directory
        std.Io.Dir.cwd().deleteDir(ioc.io(), session_dir_path) catch {};

        return count;
    }

    pub fn getCheckpointHistory(self: *FileStorage, checkpoint_id: []const u8, max_depth: usize) ![]const *Checkpoint {
        var history: std.ArrayList(*Checkpoint) = .empty;
        defer history.deinit(self.allocator);

        var current_id_buf: [256]u8 = undefined;
        @memcpy(current_id_buf[0..checkpoint_id.len], checkpoint_id);
        var current_id = current_id_buf[0..checkpoint_id.len];

        var depth: usize = 0;
        while (depth < max_depth) : (depth += 1) {
            const checkpoint = try self.load(current_id) orelse break;
            try history.append(self.allocator, checkpoint);

            if (checkpoint.parent_checkpoint_id) |parent_id| {
                if (parent_id.len > current_id_buf.len) break;
                @memcpy(current_id_buf[0..parent_id.len], parent_id);
                current_id = current_id_buf[0..parent_id.len];
            } else {
                break;
            }
        }

        return history.toOwnedSlice(self.allocator);
    }

    fn getSessionDir(self: *FileStorage, session_id: []const u8) ![]const u8 {
        return std.fmt.allocPrint(self.allocator, "{s}/{s}", .{ self.checkpoint_dir, session_id });
    }

    fn getCheckpointPath(self: *FileStorage, session_id: []const u8, checkpoint_id: []const u8) ![]const u8 {
        const session_dir = try self.getSessionDir(session_id);
        defer self.allocator.free(session_dir);
        return std.fmt.allocPrint(self.allocator, "{s}/{s}.json", .{ session_dir, checkpoint_id });
    }

    pub fn storage(self: *FileStorage) CheckpointStorage {
        return .{
            .ptr = self,
            .vtable = &.{
                .save = saveImpl,
                .load = loadImpl,
                .listCheckpoints = listCheckpointsImpl,
                .getLatest = getLatestImpl,
                .delete = deleteImpl,
                .deleteSession = deleteSessionImpl,
                .getCheckpointHistory = getCheckpointHistoryImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn saveImpl(ptr: *anyopaque, checkpoint: *const Checkpoint) anyerror!void {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.save(checkpoint);
    }

    fn loadImpl(ptr: *anyopaque, checkpoint_id: []const u8) anyerror!?*Checkpoint {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.load(checkpoint_id);
    }

    fn listCheckpointsImpl(ptr: *anyopaque, session_id: []const u8, limit: usize) anyerror![]const *Checkpoint {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.listCheckpoints(session_id, limit);
    }

    fn getLatestImpl(ptr: *anyopaque, session_id: []const u8) anyerror!?*Checkpoint {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.getLatest(session_id);
    }

    fn deleteImpl(ptr: *anyopaque, checkpoint_id: []const u8) anyerror!bool {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.delete(checkpoint_id);
    }

    fn deleteSessionImpl(ptr: *anyopaque, session_id: []const u8) anyerror!usize {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.deleteSession(session_id);
    }

    fn getCheckpointHistoryImpl(ptr: *anyopaque, checkpoint_id: []const u8, max_depth: usize) anyerror![]const *Checkpoint {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        return self.getCheckpointHistory(checkpoint_id, max_depth);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *FileStorage = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

// Tests
test "InMemoryStorage save and load" {
    const allocator = std.testing.allocator;

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
    defer checkpoint.deinit();

    try storage.save(&checkpoint);

    const loaded = try storage.load(checkpoint.checkpoint_id);
    try std.testing.expect(loaded != null);
    defer {
        if (loaded) |cp| {
            cp.deinit();
            allocator.destroy(cp);
        }
    }

    try std.testing.expectEqualStrings(checkpoint.session_id, loaded.?.session_id);
    try std.testing.expectEqualStrings(checkpoint.agent_name, loaded.?.agent_name);
    try std.testing.expectEqual(checkpoint.step_number, loaded.?.step_number);
}

test "InMemoryStorage list checkpoints" {
    const allocator = std.testing.allocator;

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    // Create multiple checkpoints
    var checkpoint1 = try Checkpoint.init(allocator, "session-1", "assistant", 1);
    defer checkpoint1.deinit();
    try storage.save(&checkpoint1);

    var checkpoint2 = try Checkpoint.init(allocator, "session-1", "assistant", 2);
    defer checkpoint2.deinit();
    try storage.save(&checkpoint2);

    var checkpoint3 = try Checkpoint.init(allocator, "session-1", "assistant", 3);
    defer checkpoint3.deinit();
    try storage.save(&checkpoint3);

    // List all checkpoints
    const checkpoints = try storage.listCheckpoints("session-1", 0);
    defer {
        for (checkpoints) |cp| {
            cp.deinit();
            allocator.destroy(cp);
        }
        allocator.free(checkpoints);
    }

    try std.testing.expectEqual(@as(usize, 3), checkpoints.len);
    // Should be sorted by timestamp (most recent first)
    try std.testing.expect(checkpoints[0].step_number >= checkpoints[1].step_number);
}

test "InMemoryStorage delete" {
    const allocator = std.testing.allocator;

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
    defer checkpoint.deinit();

    try storage.save(&checkpoint);

    const deleted = try storage.delete(checkpoint.checkpoint_id);
    try std.testing.expect(deleted);

    const loaded = try storage.load(checkpoint.checkpoint_id);
    try std.testing.expect(loaded == null);
}

test "InMemoryStorage getLatest" {
    const allocator = std.testing.allocator;

    var storage = InMemoryStorage.init(allocator);
    defer storage.deinit();

    var checkpoint1 = try Checkpoint.init(allocator, "session-1", "assistant", 1);
    defer checkpoint1.deinit();
    try storage.save(&checkpoint1);

    agktime.sleep(1 * std.time.ns_per_ms); // Small delay to ensure different timestamps

    var checkpoint2 = try Checkpoint.init(allocator, "session-1", "assistant", 2);
    defer checkpoint2.deinit();
    try storage.save(&checkpoint2);

    const latest = try storage.getLatest("session-1");
    try std.testing.expect(latest != null);
    defer {
        if (latest) |cp| {
            cp.deinit();
            allocator.destroy(cp);
        }
    }

    try std.testing.expectEqual(@as(usize, 2), latest.?.step_number);
}

test "FileStorage save and load" {
    const allocator = std.testing.allocator;

    var storage = try FileStorage.init(allocator, "/tmp/checkpoint_test");
    defer storage.deinit();

    var checkpoint = try Checkpoint.init(allocator, "session-1", "assistant", 5);
    defer checkpoint.deinit();

    try storage.save(&checkpoint);

    const loaded = try storage.load(checkpoint.checkpoint_id);
    try std.testing.expect(loaded != null);
    defer {
        if (loaded) |cp| {
            cp.deinit();
            allocator.destroy(cp);
        }
    }

    try std.testing.expectEqualStrings(checkpoint.session_id, loaded.?.session_id);
    try std.testing.expectEqualStrings(checkpoint.agent_name, loaded.?.agent_name);
    try std.testing.expectEqual(checkpoint.step_number, loaded.?.step_number);

    // Cleanup
    _ = try storage.deleteSession("session-1");
}
