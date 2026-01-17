/**
 * Comprehensive Permissions and Sandboxing Tests
 *
 * Tests cover:
 * - Role-based access control (RBAC)
 * - Permission validation
 * - Sandboxing and resource limits
 * - Permission middleware integration
 */

import { describe, it, expect } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import {
  Permission,
  Role,
  ROLE_PERMISSIONS,
  Sandbox,
  PermissionMiddleware,
  PermissionDeniedError,
  permissions,
} from '../../safety/permissions';

// ============================================
// Test Agent
// ============================================

/**
 * Simple echo agent for testing.
 */
class EchoAgent implements Agent {
  get name(): string {
    return 'echo';
  }

  get capabilities(): string[] {
    return [];
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: message.content,
    };
  }
}

// ============================================
// Permission Enum Tests
// ============================================

describe('Safety: Permission Enum', () => {
  it('should have correct permission values', () => {
    expect(Permission.READ_FILES).toBe('read:files');
    expect(Permission.WRITE_FILES).toBe('write:files');
    expect(Permission.EXECUTE_COMMANDS).toBe('execute:commands');
    expect(Permission.ACCESS_SECRETS).toBe('access:secrets');
  });
});

// ============================================
// Role and Role Permissions Tests
// ============================================

describe('Safety: Role and Permissions', () => {
  it('should have correct role values', () => {
    expect(Role.ADMIN).toBe('admin');
    expect(Role.USER).toBe('user');
    expect(Role.READONLY).toBe('readonly');
    expect(Role.RESTRICTED).toBe('restricted');
  });

  it('should give admin all permissions', () => {
    const adminPerms = ROLE_PERMISSIONS[Role.ADMIN];

    expect(adminPerms.has(Permission.READ_FILES)).toBe(true);
    expect(adminPerms.has(Permission.WRITE_FILES)).toBe(true);
    expect(adminPerms.has(Permission.DELETE_FILES)).toBe(true);
    expect(adminPerms.has(Permission.EXECUTE_COMMANDS)).toBe(true);
    expect(adminPerms.has(Permission.EXECUTE_SHELL)).toBe(true);
    expect(adminPerms.has(Permission.ACCESS_SECRETS)).toBe(true);
  });

  it('should give user standard permissions', () => {
    const userPerms = ROLE_PERMISSIONS[Role.USER];

    expect(userPerms.has(Permission.READ_FILES)).toBe(true);
    expect(userPerms.has(Permission.WRITE_FILES)).toBe(true);
    expect(userPerms.has(Permission.EXECUTE_COMMANDS)).toBe(true);

    // Should not have dangerous permissions
    expect(userPerms.has(Permission.DELETE_FILES)).toBe(false);
    expect(userPerms.has(Permission.EXECUTE_SHELL)).toBe(false);
    expect(userPerms.has(Permission.ACCESS_SECRETS)).toBe(false);
  });

  it('should give readonly limited permissions', () => {
    const readonlyPerms = ROLE_PERMISSIONS[Role.READONLY];

    expect(readonlyPerms.has(Permission.READ_FILES)).toBe(true);
    expect(readonlyPerms.has(Permission.QUERY_DATABASE)).toBe(true);

    // Should not have write permissions
    expect(readonlyPerms.has(Permission.WRITE_FILES)).toBe(false);
    expect(readonlyPerms.has(Permission.EXECUTE_COMMANDS)).toBe(false);
  });

  it('should give restricted minimal permissions', () => {
    const restrictedPerms = ROLE_PERMISSIONS[Role.RESTRICTED];

    expect(restrictedPerms.has(Permission.READ_FILES)).toBe(true);

    // Should not have other permissions
    expect(restrictedPerms.has(Permission.WRITE_FILES)).toBe(false);
    expect(restrictedPerms.has(Permission.EXECUTE_COMMANDS)).toBe(false);
  });
});

// ============================================
// Sandbox Tests
// ============================================

describe('Safety: Sandbox', () => {
  it('should allow paths by default when no restrictions set', () => {
    const sandbox = new Sandbox({ allowedPaths: new Set() });

    const [isAllowed, error] = sandbox.isPathAllowed('/tmp/test.txt');
    expect(isAllowed).toBe(true);
    expect(error).toBe(null);
  });

  it('should deny system directories by default', () => {
    const sandbox = new Sandbox();

    // Should deny /etc
    let [isAllowed, error] = sandbox.isPathAllowed('/etc/passwd');
    expect(isAllowed).toBe(false);
    expect(error).toContain('denied directory');

    // Should deny /sys
    [isAllowed, error] = sandbox.isPathAllowed('/sys/kernel/test');
    expect(isAllowed).toBe(false);
  });

  it('should allow paths in specified directories', () => {
    const sandbox = new Sandbox({ allowedPaths: new Set(['/app/data', '/tmp']) });

    let [isAllowed, error] = sandbox.isPathAllowed('/app/data/file.txt');
    expect(isAllowed).toBe(true);
    expect(error).toBe(null);

    [isAllowed, error] = sandbox.isPathAllowed('/tmp/test.txt');
    expect(isAllowed).toBe(true);
  });

  it('should deny paths outside allowed directories', () => {
    const sandbox = new Sandbox({ allowedPaths: new Set(['/app/data']) });

    const [isAllowed, error] = sandbox.isPathAllowed('/home/user/file.txt');
    expect(isAllowed).toBe(false);
    expect(error).toContain('outside allowed directories');
  });

  it('should allow commands by default', () => {
    const sandbox = new Sandbox();

    let [isAllowed, error] = sandbox.isCommandAllowed('ls -la');
    expect(isAllowed).toBe(true);
    expect(error).toBe(null);

    [isAllowed, error] = sandbox.isCommandAllowed('git status');
    expect(isAllowed).toBe(true);
  });

  it('should deny dangerous commands', () => {
    const sandbox = new Sandbox();

    let [isAllowed, error] = sandbox.isCommandAllowed('rm -rf /');
    expect(isAllowed).toBe(false);
    expect(error).toContain('denied');

    [isAllowed, error] = sandbox.isCommandAllowed('sudo apt-get install');
    expect(isAllowed).toBe(false);
  });

  it('should deny commands not in allowed list', () => {
    const sandbox = new Sandbox({ allowedCommands: new Set(['ls', 'cat']) });

    const [isAllowed, error] = sandbox.isCommandAllowed('python script.py');
    expect(isAllowed).toBe(false);
    expect(error).toContain('not in allowed list');
  });

  it('should allow SQL queries', () => {
    const sandbox = new Sandbox();

    let [isAllowed, error] = sandbox.isSqlOperationAllowed('SELECT * FROM users');
    expect(isAllowed).toBe(true);
    expect(error).toBe(null);

    [isAllowed, error] = sandbox.isSqlOperationAllowed('EXPLAIN SELECT * FROM users');
    expect(isAllowed).toBe(true);
  });

  it('should deny write SQL operations by default', () => {
    const sandbox = new Sandbox();

    let [isAllowed, error] = sandbox.isSqlOperationAllowed('DELETE FROM users');
    expect(isAllowed).toBe(false);
    expect(error).toContain('not allowed');

    [isAllowed, error] = sandbox.isSqlOperationAllowed('DROP TABLE users');
    expect(isAllowed).toBe(false);
  });

  it('should allow domains by default when no restrictions set', () => {
    const sandbox = new Sandbox({ allowedDomains: new Set() });

    const [isAllowed, error] = sandbox.isDomainAllowed('example.com');
    expect(isAllowed).toBe(true);
    expect(error).toBe(null);
  });

  it('should deny localhost by default', () => {
    const sandbox = new Sandbox();

    let [isAllowed, error] = sandbox.isDomainAllowed('localhost');
    expect(isAllowed).toBe(false);
    expect(error).toContain('denied');

    [isAllowed, error] = sandbox.isDomainAllowed('127.0.0.1');
    expect(isAllowed).toBe(false);
  });

  it('should allow domains in allowed list', () => {
    const sandbox = new Sandbox({
      allowedDomains: new Set(['api.example.com', 'cdn.example.com']),
    });

    const [isAllowed, error] = sandbox.isDomainAllowed('api.example.com');
    expect(isAllowed).toBe(true);
    expect(error).toBe(null);
  });

  it('should deny domains not in allowed list', () => {
    const sandbox = new Sandbox({ allowedDomains: new Set(['api.example.com']) });

    const [isAllowed, error] = sandbox.isDomainAllowed('evil.com');
    expect(isAllowed).toBe(false);
    expect(error).toContain('not in allowed list');
  });
});

// ============================================
// Permission Middleware Tests
// ============================================

describe('Safety: PermissionMiddleware', () => {
  it('should allow all operations for admin role', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.ADMIN);

    const message: Message = { role: 'user', content: 'delete file /tmp/test.txt' };
    const response = await middleware.process(message);
    expect(response.content).toBe(message.content);
  });

  it('should block dangerous operations for user role', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.USER);

    const message: Message = { role: 'user', content: 'execute shell command rm -rf' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/execute:shell/i);
  });

  it('should block write operations for readonly role', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.READONLY);

    const message: Message = { role: 'user', content: 'write file config.json' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/write:files/i);
  });

  it('should block most operations for restricted role', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.RESTRICTED);

    const message: Message = { role: 'user', content: 'execute command ls' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/execute:commands/i);
  });

  it('should allow custom permissions to override role', async () => {
    const customPerms = new Set([Permission.READ_FILES, Permission.WRITE_FILES]);
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.ADMIN, customPerms);

    const message: Message = { role: 'user', content: 'execute command ls' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
  });

  it('should expose hasPermission check', () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.USER);

    expect(middleware.hasPermission(Permission.READ_FILES)).toBe(true);
    expect(middleware.hasPermission(Permission.WRITE_FILES)).toBe(true);
    expect(middleware.hasPermission(Permission.DELETE_FILES)).toBe(false);
    expect(middleware.hasPermission(Permission.ACCESS_SECRETS)).toBe(false);
  });

  it('should delegate name property', () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.USER);
    expect(middleware.name).toBe(agent.name);
  });

  it('should delegate capabilities property', () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.USER);
    expect(middleware.capabilities).toEqual(agent.capabilities);
  });

  it('should detect database write operations', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.READONLY);

    const message: Message = { role: 'user', content: 'delete from users where id = 1' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/write:database/i);
  });

  it('should allow safe content through', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.USER);

    const message: Message = { role: 'user', content: 'What is the weather today?' };
    const response = await middleware.process(message);

    expect(response.content).toBe(message.content);
  });

  it('should detect delete file operations', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.USER);

    const message: Message = { role: 'user', content: 'delete file /tmp/test.txt' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/delete:files/i);
  });

  it('should detect database insert operations', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.READONLY);

    const message: Message = {
      role: 'user',
      content: "insert into users (name) values ('Bob')",
    };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/write:database/i);
  });

  it('should detect database update operations', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.READONLY);

    const message: Message = { role: 'user', content: 'update users set active = true' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/write:database/i);
  });

  it('should detect drop table operations', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.READONLY);

    const message: Message = { role: 'user', content: 'drop table old_data' };

    await expect(middleware.process(message)).rejects.toThrow(PermissionDeniedError);
    await expect(middleware.process(message)).rejects.toThrow(/write:database/i);
  });

  it('should allow database queries for readonly', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.READONLY);

    const message: Message = { role: 'user', content: 'select * from users' };
    const response = await middleware.process(message);

    expect(response.content).toBe(message.content);
  });

  it('should include required permission in error', async () => {
    const agent = new EchoAgent();
    const middleware = new PermissionMiddleware(agent, Role.RESTRICTED);

    const message: Message = { role: 'user', content: 'write file test.txt' };

    try {
      await middleware.process(message);
      expect.fail('Should have thrown PermissionDeniedError');
    } catch (error) {
      expect(error).toBeInstanceOf(PermissionDeniedError);
      expect((error as PermissionDeniedError).requiredPermission).toBe(Permission.WRITE_FILES);
    }
  });
});

// ============================================
// Sandbox Extended Tests
// ============================================

describe('Safety: Sandbox Extended', () => {
  it('should configure resource limits', () => {
    const sandbox = new Sandbox({
      maxFileSize: 5 * 1024 * 1024, // 5MB
      maxExecutionTime: 60,
      maxMemoryMb: 1024,
    });

    expect(sandbox.maxFileSize).toBe(5 * 1024 * 1024);
    expect(sandbox.maxExecutionTime).toBe(60);
    expect(sandbox.maxMemoryMb).toBe(1024);
  });

  it('should support custom denied paths', () => {
    const sandbox = new Sandbox({
      deniedPaths: new Set(['/etc', '/var', '/usr/local/sensitive']),
    });

    const [isAllowed, error] = sandbox.isPathAllowed('/var/log/test.log');
    expect(isAllowed).toBe(false);
    expect(error).toContain('denied directory');
  });

  it('should support custom allowed commands', () => {
    const sandbox = new Sandbox({
      allowedCommands: new Set(['echo', 'date', 'whoami']),
    });

    let [isAllowed, _] = sandbox.isCommandAllowed('echo hello');
    expect(isAllowed).toBe(true);

    const [isAllowed2, error] = sandbox.isCommandAllowed('curl example.com');
    expect(isAllowed2).toBe(false);
    expect(error).toContain('not in allowed list');
  });

  it('should support custom SQL operations', () => {
    const sandbox = new Sandbox({
      allowedSqlOperations: new Set(['SELECT', 'EXPLAIN', 'DESCRIBE']),
    });

    let [isAllowed, _] = sandbox.isSqlOperationAllowed('DESCRIBE users');
    expect(isAllowed).toBe(true);

    const [isAllowed2, error] = sandbox.isSqlOperationAllowed('INSERT INTO users VALUES (1)');
    expect(isAllowed2).toBe(false);
    expect(error).toContain('not allowed');
  });

  it('should reject empty command', () => {
    const sandbox = new Sandbox();

    const [isAllowed, error] = sandbox.isCommandAllowed('');
    expect(isAllowed).toBe(false);
    expect(error).toContain('not in allowed list');
  });

  it('should reject empty SQL statement', () => {
    const sandbox = new Sandbox();

    const [isAllowed, error] = sandbox.isSqlOperationAllowed('');
    expect(isAllowed).toBe(false);
    expect(error).toContain('not allowed');
  });

  it('should handle subdomains correctly', () => {
    const sandbox = new Sandbox({
      allowedDomains: new Set(['example.com', 'api.example.com']),
    });

    let [isAllowed, _] = sandbox.isDomainAllowed('api.example.com');
    expect(isAllowed).toBe(true);

    // Subdomain not explicitly allowed
    const [isAllowed2, error] = sandbox.isDomainAllowed('staging.example.com');
    expect(isAllowed2).toBe(false);
    expect(error).toContain('not in allowed list');
  });
});

// ============================================
// Decorator Function Tests
// ============================================

describe('Safety: permissions Decorator', () => {
  it('should create middleware with decorator', () => {
    const agent = new EchoAgent();
    const middlewareFn = permissions({ role: Role.USER });

    const wrapped = middlewareFn(agent);

    expect(wrapped).toBeInstanceOf(PermissionMiddleware);
    expect(wrapped.role).toBe(Role.USER);
  });

  it('should support sandbox in decorator', () => {
    const sandbox = new Sandbox({ allowedPaths: new Set(['/app/data']) });
    const agent = new EchoAgent();
    const middlewareFn = permissions({ role: Role.READONLY, sandbox });

    const wrapped = middlewareFn(agent);

    expect(wrapped).toBeInstanceOf(PermissionMiddleware);
    expect(wrapped.role).toBe(Role.READONLY);
    expect(wrapped.sandbox).toBe(sandbox);
  });

  it('should support custom permissions in decorator', () => {
    const customPerms = new Set([Permission.READ_FILES, Permission.QUERY_DATABASE]);
    const agent = new EchoAgent();
    const middlewareFn = permissions({ customPermissions: customPerms });

    const wrapped = middlewareFn(agent);

    expect(wrapped).toBeInstanceOf(PermissionMiddleware);
    expect(wrapped.permissions).toBe(customPerms);
  });
});
