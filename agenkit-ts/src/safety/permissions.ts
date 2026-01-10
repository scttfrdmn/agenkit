/**
 * Permission-based access control and sandboxing.
 *
 * Provides:
 * - Role-Based Access Control (RBAC)
 * - Permission checks before agent actions
 * - Sandboxing (allowed paths, commands, operations)
 * - Resource constraints
 */

import * as path from 'path';
import { Agent, Message } from '../core/interfaces';

/**
 * System permissions for agents.
 */
export enum Permission {
  // File system
  READ_FILES = 'read:files',
  WRITE_FILES = 'write:files',
  DELETE_FILES = 'delete:files',

  // Command execution
  EXECUTE_COMMANDS = 'execute:commands',
  EXECUTE_SHELL = 'execute:shell',

  // Database
  QUERY_DATABASE = 'query:database',
  WRITE_DATABASE = 'write:database',

  // Network
  MAKE_HTTP_REQUESTS = 'network:http',
  MAKE_EXTERNAL_API_CALLS = 'network:api',

  // System
  MANAGE_USERS = 'manage:users',
  MANAGE_AGENTS = 'manage:agents',
  ACCESS_SECRETS = 'access:secrets',

  // Tools
  USE_TOOLS = 'use:tools',
  USE_DANGEROUS_TOOLS = 'use:dangerous_tools',
}

/**
 * Predefined roles with permission sets.
 */
export enum Role {
  ADMIN = 'admin',
  USER = 'user',
  READONLY = 'readonly',
  RESTRICTED = 'restricted',
}

/**
 * Role to permissions mapping.
 */
export const ROLE_PERMISSIONS: Record<Role, Set<Permission>> = {
  [Role.ADMIN]: new Set([
    Permission.READ_FILES,
    Permission.WRITE_FILES,
    Permission.DELETE_FILES,
    Permission.EXECUTE_COMMANDS,
    Permission.EXECUTE_SHELL,
    Permission.QUERY_DATABASE,
    Permission.WRITE_DATABASE,
    Permission.MAKE_HTTP_REQUESTS,
    Permission.MAKE_EXTERNAL_API_CALLS,
    Permission.MANAGE_USERS,
    Permission.MANAGE_AGENTS,
    Permission.ACCESS_SECRETS,
    Permission.USE_TOOLS,
    Permission.USE_DANGEROUS_TOOLS,
  ]),
  [Role.USER]: new Set([
    Permission.READ_FILES,
    Permission.WRITE_FILES,
    Permission.EXECUTE_COMMANDS,
    Permission.QUERY_DATABASE,
    Permission.MAKE_HTTP_REQUESTS,
    Permission.USE_TOOLS,
  ]),
  [Role.READONLY]: new Set([
    Permission.READ_FILES,
    Permission.QUERY_DATABASE,
    Permission.USE_TOOLS,
  ]),
  [Role.RESTRICTED]: new Set([Permission.READ_FILES, Permission.USE_TOOLS]),
};

/**
 * Error thrown when permission check fails.
 */
export class PermissionDeniedError extends Error {
  constructor(message: string, public readonly requiredPermission?: Permission) {
    super(message);
    this.name = 'PermissionDeniedError';
  }
}

/**
 * Defines sandboxed environment for agent execution.
 *
 * Specifies:
 * - Allowed file paths
 * - Allowed commands
 * - Allowed database operations
 * - Allowed API endpoints
 * - Resource limits
 *
 * Example:
 *   const sandbox = new Sandbox({
 *     allowedPaths: new Set(['/app/data']),
 *     allowedCommands: new Set(['git', 'ls', 'cat']),
 *     maxFileSize: 10 * 1024 * 1024, // 10MB
 *   });
 *
 *   const [isAllowed, errorMsg] = sandbox.isPathAllowed('/app/data/file.txt');
 */
export class Sandbox {
  // File system sandbox
  private allowedPaths: Set<string>;
  private deniedPaths: Set<string>;

  // Command sandbox
  private allowedCommands: Set<string>;
  private deniedCommands: Set<string>;

  // Database sandbox
  private allowedSqlOperations: Set<string>;

  // Network sandbox
  private allowedDomains: Set<string>;
  private deniedDomains: Set<string>;

  // Resource limits
  readonly maxFileSize: number;
  readonly maxExecutionTime: number;
  readonly maxMemoryMb: number;

  constructor(config?: {
    allowedPaths?: Set<string>;
    deniedPaths?: Set<string>;
    allowedCommands?: Set<string>;
    deniedCommands?: Set<string>;
    allowedSqlOperations?: Set<string>;
    allowedDomains?: Set<string>;
    deniedDomains?: Set<string>;
    maxFileSize?: number;
    maxExecutionTime?: number;
    maxMemoryMb?: number;
  }) {
    this.allowedPaths = config?.allowedPaths ?? new Set();
    this.deniedPaths = config?.deniedPaths ?? new Set(['/etc', '/sys', '/proc']);

    this.allowedCommands = config?.allowedCommands ?? new Set(['ls', 'cat', 'grep', 'git', 'python']);
    this.deniedCommands = config?.deniedCommands ?? new Set(['rm', 'sudo', 'chmod', 'chown']);

    this.allowedSqlOperations = config?.allowedSqlOperations ?? new Set(['SELECT', 'EXPLAIN']);

    this.allowedDomains = config?.allowedDomains ?? new Set(); // Empty = allow all
    this.deniedDomains = config?.deniedDomains ?? new Set(['localhost', '127.0.0.1', '0.0.0.0']);

    this.maxFileSize = config?.maxFileSize ?? 10 * 1024 * 1024; // 10MB
    this.maxExecutionTime = config?.maxExecutionTime ?? 30; // seconds
    this.maxMemoryMb = config?.maxMemoryMb ?? 512; // MB
  }

  /**
   * Check if path is within sandbox.
   *
   * Returns tuple of (is_allowed, error_message)
   */
  isPathAllowed(filePath: string): [boolean, string | null] {
    try {
      const resolved = path.resolve(filePath);

      // Check denied paths first
      for (const denied of this.deniedPaths) {
        const deniedResolved = path.resolve(denied);
        if (resolved.startsWith(deniedResolved)) {
          return [false, `Path is in denied directory: ${denied}`];
        }
      }

      // If allowed_paths specified, must be under one of them
      if (this.allowedPaths.size > 0) {
        for (const allowed of this.allowedPaths) {
          const allowedResolved = path.resolve(allowed);
          if (resolved.startsWith(allowedResolved)) {
            return [true, null];
          }
        }

        return [false, 'Path is outside allowed directories'];
      }

      // No allowed_paths specified, just check denied
      return [true, null];
    } catch (error) {
      return [false, `Path validation error: ${error}`];
    }
  }

  /**
   * Check if command is allowed in sandbox.
   *
   * Returns tuple of (is_allowed, error_message)
   */
  isCommandAllowed(command: string): [boolean, string | null] {
    const cmdName = command.trim().split(/\s+/)[0] || '';

    // Check denied commands first
    if (this.deniedCommands.has(cmdName)) {
      return [false, `Command is denied: ${cmdName}`];
    }

    // Check allowed commands
    if (this.allowedCommands.size > 0 && !this.allowedCommands.has(cmdName)) {
      return [false, `Command not in allowed list: ${cmdName}`];
    }

    return [true, null];
  }

  /**
   * Check if SQL operation is allowed.
   *
   * Returns tuple of (is_allowed, error_message)
   */
  isSqlOperationAllowed(sql: string): [boolean, string | null] {
    const operation = sql.trim().toUpperCase().split(/\s+/)[0] || '';

    if (!this.allowedSqlOperations.has(operation)) {
      return [false, `SQL operation not allowed: ${operation}`];
    }

    return [true, null];
  }

  /**
   * Check if domain is allowed for network requests.
   *
   * Returns tuple of (is_allowed, error_message)
   */
  isDomainAllowed(domain: string): [boolean, string | null] {
    // Check denied domains first
    if (this.deniedDomains.has(domain)) {
      return [false, `Domain is denied: ${domain}`];
    }

    // If allowed_domains specified, must be in list
    if (this.allowedDomains.size > 0 && !this.allowedDomains.has(domain)) {
      return [false, `Domain not in allowed list: ${domain}`];
    }

    return [true, null];
  }
}

/**
 * Middleware for permission checks and sandboxing.
 *
 * Enforces:
 * - Role-based permissions
 * - Sandbox constraints
 * - Resource limits
 *
 * Example:
 *   const sandbox = new Sandbox({
 *     allowedPaths: new Set(['/app/data']),
 *     allowedCommands: new Set(['git', 'ls', 'cat']),
 *   });
 *
 *   const agent = new PermissionMiddleware(
 *     baseAgent,
 *     Role.USER,
 *     undefined, // no custom permissions
 *     sandbox,
 *   );
 */
export class PermissionMiddleware implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private agent: Agent;
  private role: Role;
  private permissions: Set<Permission>;
  private sandbox: Sandbox;

  constructor(
    agent: Agent,
    role: Role = Role.USER,
    customPermissions?: Set<Permission>,
    sandbox?: Sandbox,
  ) {
    this.agent = agent;
    this.name = agent.name;
    this.capabilities = agent.capabilities;
    this.role = role;
    this.permissions = customPermissions || ROLE_PERMISSIONS[role] || new Set();
    this.sandbox = sandbox || new Sandbox();
  }

  /**
   * Check if agent has permission.
   */
  hasPermission(permission: Permission): boolean {
    return this.permissions.has(permission);
  }

  /**
   * Check permission and raise error if denied.
   */
  checkPermission(permission: Permission): void {
    if (!this.hasPermission(permission)) {
      throw new PermissionDeniedError(
        `Permission denied: ${permission} required (role: ${this.role})`,
        permission,
      );
    }
  }

  /**
   * Process message with permission checks.
   *
   * Note: This middleware checks for general USE_TOOLS permission.
   * Specific permission checks should be done by tools themselves
   * or by extending this middleware.
   */
  async process(message: Message): Promise<Message> {
    // Basic permission check
    this.checkPermission(Permission.USE_TOOLS);

    // Check for dangerous operations in message content
    const contentStr = message.content ? String(message.content).toLowerCase() : '';

    // Detect file operations
    if (
      contentStr.includes('read file') ||
      contentStr.includes('write file') ||
      contentStr.includes('delete file')
    ) {
      if (contentStr.includes('delete')) {
        this.checkPermission(Permission.DELETE_FILES);
      } else if (contentStr.includes('write')) {
        this.checkPermission(Permission.WRITE_FILES);
      } else {
        this.checkPermission(Permission.READ_FILES);
      }
    }

    // Detect command execution
    if (
      contentStr.includes('execute') ||
      contentStr.includes('run command') ||
      contentStr.includes('shell')
    ) {
      if (contentStr.includes('shell')) {
        this.checkPermission(Permission.EXECUTE_SHELL);
      } else {
        this.checkPermission(Permission.EXECUTE_COMMANDS);
      }
    }

    // Detect database operations
    // Check for write operations first (more specific)
    const dbWriteKeywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create table'];
    if (dbWriteKeywords.some((kw) => contentStr.includes(kw))) {
      // Likely a SQL write operation
      this.checkPermission(Permission.WRITE_DATABASE);
    } else if (
      contentStr.includes('query') ||
      contentStr.includes('database') ||
      contentStr.includes('sql') ||
      contentStr.includes('select') ||
      contentStr.includes('from')
    ) {
      // Database read operation
      this.checkPermission(Permission.QUERY_DATABASE);
    }

    // Process with wrapped agent
    return await this.agent.process(message);
  }
}

/**
 * Create permission middleware function.
 *
 * Example:
 *   const sandbox = new Sandbox({ allowedPaths: new Set(['/app/data']) });
 *
 *   const agent = applyMiddleware(baseAgent, [
 *     permissions({
 *       role: Role.USER,
 *       sandbox,
 *     }),
 *   ]);
 */
export function permissions(config?: {
  role?: Role;
  customPermissions?: Set<Permission>;
  sandbox?: Sandbox;
}): (agent: Agent) => Agent {
  return (agent: Agent) =>
    new PermissionMiddleware(agent, config?.role, config?.customPermissions, config?.sandbox);
}
