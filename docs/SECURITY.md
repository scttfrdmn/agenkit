# Security Best Practices for Agenkit Tools

**Last Updated**: November 2025
**Status**: Living document - continuously updated

This document outlines critical security considerations when building and deploying agent tools, especially those that interact with local systems, databases, and external APIs.

---

## Table of Contents

1. [Threat Model](#threat-model)
2. [General Principles](#general-principles)
3. [OS Tools Security](#os-tools-security)
4. [Database Tools Security](#database-tools-security)
5. [API Tools Security](#api-tools-security)
6. [Authentication & Authorization](#authentication--authorization)
7. [Input Validation](#input-validation)
8. [Output Sanitization](#output-sanitization)
9. [Audit Logging](#audit-logging)
10. [Deployment Security](#deployment-security)
11. [Incident Response](#incident-response)
12. [Security Checklist](#security-checklist)

---

## Threat Model

### Attack Vectors

**1. Malicious User Input**
- Command injection: `ls; rm -rf /`
- Path traversal: `../../../etc/passwd`
- SQL injection: `' OR '1'='1`
- XXE/XML injection in data

**2. Compromised Agent**
- LLM prompt injection attacks
- Tool misuse by hijacked agent
- Privilege escalation attempts

**3. External Dependencies**
- Compromised API keys
- Man-in-the-middle attacks
- Supply chain vulnerabilities

**4. Insider Threats**
- Malicious administrators
- Accidental misconfiguration
- Credential leakage

### Assets to Protect

- User data and PII
- API keys and credentials
- File system integrity
- Database contents
- System resources (CPU, memory, network)
- Audit logs

---

## General Principles

### 1. Principle of Least Privilege

**Grant minimum necessary permissions**

```python
# ❌ BAD: Agent has unrestricted access
agent = Agent(permissions="*")

# ✅ GOOD: Agent has specific permissions
agent = Agent(permissions=[
    "read:/data/documents",
    "write:/data/output",
    "execute:git",
    "query:database.readonly"
])
```

### 2. Defense in Depth

**Layer multiple security controls**

```python
# Multiple layers of protection
tool = DatabaseTool(
    connection_string=secrets.get("DB_URL"),  # 1. Secret management
    allowed_operations=["SELECT"],             # 2. Operation whitelist
    max_rows=1000,                             # 3. Result size limit
    timeout=5,                                 # 4. Timeout protection
    audit_logger=audit_log                     # 5. Audit trail
)
```

### 3. Fail Securely

**Default to denial, log failures**

```python
def execute_command(command: str) -> Result:
    """Execute command with secure defaults."""
    try:
        # Validate first
        if not is_command_allowed(command):
            audit_log.warning(f"Blocked command: {command}")
            return Result(success=False, error="Command not allowed")

        # Execute with timeout
        result = subprocess.run(
            command.split(),  # No shell=True
            timeout=5,
            capture_output=True
        )

        audit_log.info(f"Executed: {command}")
        return Result(success=True, output=result.stdout)

    except Exception as e:
        # Log error but don't expose internals
        audit_log.error(f"Command failed: {command}", exc_info=True)
        return Result(success=False, error="Command execution failed")
```

### 4. Zero Trust

**Verify everything, trust nothing**

```python
def process_request(request: Request, user: User) -> Response:
    """Process request with zero trust."""
    # 1. Authenticate user
    if not auth.verify(user.token):
        return Response(error="Authentication failed")

    # 2. Authorize action
    if not authz.can_perform(user, request.action):
        return Response(error="Unauthorized")

    # 3. Validate input
    if not validate_input(request.data):
        return Response(error="Invalid input")

    # 4. Rate limit
    if not rate_limiter.allow(user.id):
        return Response(error="Rate limit exceeded")

    # 5. Execute with monitoring
    result = execute_with_audit(request, user)
    return result
```

---

## OS Tools Security

### File System Access

#### Path Validation - CRITICAL

**Prevent directory traversal attacks**

```python
from pathlib import Path

class SecureFileSystem:
    """File system tool with path validation."""

    def __init__(self, allowed_paths: List[str]):
        """Initialize with allowed directory paths."""
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        try:
            # Resolve to absolute path (resolves symlinks, .., etc.)
            resolved = path.resolve(strict=False)

            # Check if under any allowed directory
            for allowed in self.allowed_paths:
                try:
                    resolved.relative_to(allowed)
                    return True
                except ValueError:
                    continue

            return False
        except Exception:
            # Fail closed on any error
            return False

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file with security checks."""
        path = Path(file_path)

        # Security checks
        if not self._is_path_allowed(path):
            audit_log.warning(f"Path traversal blocked: {file_path}")
            return {"error": "Access denied"}

        if not path.exists() or not path.is_file():
            return {"error": "File not found"}

        # Size limit (prevent memory exhaustion)
        if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
            return {"error": "File too large"}

        # Read file
        try:
            content = path.read_text(encoding='utf-8')
            audit_log.info(f"Read file: {file_path}")
            return {"success": True, "content": content}
        except Exception as e:
            audit_log.error(f"Read failed: {file_path}", exc_info=True)
            return {"error": "Failed to read file"}
```

**Attack examples prevented:**

```python
# ❌ These attacks are blocked
filesystem.read_file("../../../etc/passwd")           # Path traversal
filesystem.read_file("/etc/shadow")                    # Outside sandbox
filesystem.read_file("/app/data/../../etc/hosts")      # Double encoding
filesystem.read_file("/app/data/link_to_etc")          # Symlink outside
```

#### Atomic File Operations

**Prevent race conditions and partial writes**

```python
async def write_file_atomic(path: Path, content: str):
    """Write file atomically to prevent corruption."""
    # Write to temporary file first
    temp_path = path.with_suffix(path.suffix + '.tmp')

    try:
        temp_path.write_text(content, encoding='utf-8')

        # Atomic rename (OS-level atomic operation)
        temp_path.replace(path)

        audit_log.info(f"Wrote file: {path}")
    except Exception as e:
        # Clean up temp file on failure
        if temp_path.exists():
            temp_path.unlink()
        raise
```

### Shell Command Execution

#### Command Injection Prevention - CRITICAL

**NEVER use shell=True with user input**

```python
import subprocess
import shlex

class SecureShell:
    """Shell command execution with security controls."""

    def __init__(self, allowed_commands: List[str], working_dir: str):
        self.allowed_commands = set(allowed_commands)
        self.working_dir = Path(working_dir).resolve()

    async def execute(self, command: List[str]) -> Dict[str, Any]:
        """Execute command with security checks."""
        if not command:
            return {"error": "Empty command"}

        # 1. Command whitelist
        cmd_name = command[0]
        if cmd_name not in self.allowed_commands:
            audit_log.warning(f"Blocked command: {cmd_name}")
            return {"error": f"Command not allowed: {cmd_name}"}

        # 2. Validate working directory
        if not self._is_path_safe(self.working_dir):
            return {"error": "Invalid working directory"}

        try:
            # 3. Execute WITHOUT shell=True (prevents injection)
            process = await asyncio.create_subprocess_exec(
                *command,  # ✅ Command as list, no shell
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.working_dir,
                timeout=30  # 4. Timeout protection
            )

            stdout, stderr = await process.communicate()

            audit_log.info(f"Executed: {' '.join(command)}")

            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }

        except asyncio.TimeoutError:
            process.kill()
            audit_log.warning(f"Command timed out: {command}")
            return {"error": "Command timed out"}
        except Exception as e:
            audit_log.error(f"Command failed: {command}", exc_info=True)
            return {"error": "Command execution failed"}
```

**Why this is secure:**

```python
# ❌ VULNERABLE: shell=True allows injection
command = f"ls {user_input}"
subprocess.run(command, shell=True)  # NEVER DO THIS
# Attack: user_input = "; rm -rf /"
# Result: Executes "ls ; rm -rf /"

# ✅ SAFE: Command as list, no shell
command = ["ls", user_input]
subprocess.run(command, shell=False)  # Safe
# Attack: user_input = "; rm -rf /"
# Result: Tries to list directory named "; rm -rf /" (fails harmlessly)
```

#### Environment Variable Sanitization

**Don't leak sensitive environment variables**

```python
def execute_with_clean_env(command: List[str]) -> subprocess.CompletedProcess:
    """Execute command with sanitized environment."""
    # Start with minimal environment
    clean_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "en_US.UTF-8"
    }

    # Explicitly add only needed variables
    if "CUSTOM_VAR" in os.environ:
        clean_env["CUSTOM_VAR"] = os.environ["CUSTOM_VAR"]

    # Execute with clean environment
    return subprocess.run(
        command,
        env=clean_env,  # Don't inherit parent environment
        capture_output=True
    )
```

---

## Database Tools Security

### SQL Injection Prevention - CRITICAL

**ALWAYS use parameterized queries**

```python
import psycopg2

class SecureDatabaseTool:
    """Database tool with SQL injection prevention."""

    async def query_users(self, role: str) -> List[Dict]:
        """Query users by role - SECURE VERSION."""

        # ✅ SAFE: Parameterized query
        sql = "SELECT * FROM users WHERE role = %s"
        params = (role,)

        async with self.pool.acquire() as conn:
            results = await conn.fetch(sql, *params)
            return [dict(row) for row in results]

    async def query_users_UNSAFE(self, role: str) -> List[Dict]:
        """❌ VULNERABLE VERSION - DO NOT USE"""

        # ❌ UNSAFE: String interpolation allows SQL injection
        sql = f"SELECT * FROM users WHERE role = '{role}'"

        async with self.pool.acquire() as conn:
            results = await conn.fetch(sql)
            return [dict(row) for row in results]
```

**Attack example:**

```python
# With unsafe version
role = "admin' OR '1'='1"
# Becomes: SELECT * FROM users WHERE role = 'admin' OR '1'='1'
# Returns ALL users (bypasses role check)

# With safe version (parameterized)
role = "admin' OR '1'='1"
# Params: ('admin\' OR \'1\'=\'1',)
# Returns: No users (treats as literal role name)
```

### Operation Whitelisting

**Restrict to safe operations**

```python
class ReadOnlyDatabase:
    """Database tool restricted to read operations."""

    ALLOWED_OPERATIONS = {"SELECT", "EXPLAIN", "DESCRIBE", "SHOW"}

    async def execute(self, sql: str) -> Dict[str, Any]:
        """Execute query with operation check."""
        # Extract operation
        operation = sql.strip().upper().split()[0]

        if operation not in self.ALLOWED_OPERATIONS:
            audit_log.warning(f"Blocked SQL operation: {operation}")
            return {
                "error": f"Operation not allowed: {operation}",
                "allowed": list(self.ALLOWED_OPERATIONS)
            }

        # Additional validation
        if any(keyword in sql.upper() for keyword in ["DROP", "DELETE", "UPDATE", "INSERT"]):
            audit_log.warning(f"Blocked dangerous SQL: {sql}")
            return {"error": "Dangerous keywords detected"}

        # Execute query
        return await self._execute_safe(sql)
```

### Connection String Security

**Protect database credentials**

```python
from dataclasses import dataclass
import os

@dataclass
class DatabaseConfig:
    """Database configuration with secure defaults."""
    host: str
    port: int
    database: str
    user: str
    password: str  # Should come from secret manager
    ssl_mode: str = "require"  # Force SSL
    connect_timeout: int = 10
    max_connections: int = 10

    @classmethod
    def from_env(cls):
        """Load from environment variables (not hardcoded)."""
        return cls(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "5432")),
            database=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],  # From secret manager
            ssl_mode=os.environ.get("DB_SSL_MODE", "require")
        )

    def get_connection_string(self) -> str:
        """Get connection string (password is masked in logs)."""
        return (
            f"postgresql://{self.user}:****@"
            f"{self.host}:{self.port}/{self.database}"
        )

# ❌ NEVER hardcode credentials
db = psycopg2.connect("postgresql://user:password@localhost/db")

# ✅ Load from environment/secret manager
config = DatabaseConfig.from_env()
db = psycopg2.connect(
    host=config.host,
    port=config.port,
    database=config.database,
    user=config.user,
    password=config.password,
    sslmode=config.ssl_mode
)
```

---

## API Tools Security

### API Key Management

**Never hardcode or log API keys**

```python
import os
from typing import Optional

class SecureAPIClient:
    """API client with secure key management."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from environment."""
        # Load from environment, not parameter
        self.api_key = api_key or os.environ.get("API_KEY")

        if not self.api_key:
            raise ValueError("API_KEY environment variable not set")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers (key not logged)."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "agenkit/1.0"
        }

    async def make_request(self, endpoint: str, data: dict) -> dict:
        """Make API request with secure logging."""
        # ✅ Log request without exposing key
        audit_log.info(f"API request to {endpoint}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers=self._get_headers(),
                json=data,
                timeout=30
            )

            # ✅ Log response without exposing key
            audit_log.info(f"API response: status={response.status_code}")

            return response.json()
```

### Rate Limiting

**Protect APIs from abuse**

```python
import time
from collections import defaultdict
from typing import Dict

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        max_calls: int = 60,
        time_window: int = 60,  # seconds
        burst_size: int = 10
    ):
        self.max_calls = max_calls
        self.time_window = time_window
        self.burst_size = burst_size
        self.calls: Dict[str, List[float]] = defaultdict(list)

    def allow(self, user_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()

        # Clean old timestamps
        self.calls[user_id] = [
            ts for ts in self.calls[user_id]
            if now - ts < self.time_window
        ]

        # Check limits
        if len(self.calls[user_id]) >= self.max_calls:
            audit_log.warning(f"Rate limit exceeded: {user_id}")
            return False

        # Check burst
        recent = [ts for ts in self.calls[user_id] if now - ts < 1.0]
        if len(recent) >= self.burst_size:
            audit_log.warning(f"Burst limit exceeded: {user_id}")
            return False

        # Allow request
        self.calls[user_id].append(now)
        return True


class RateLimitedAPITool:
    """API tool with rate limiting."""

    def __init__(self, api_client: SecureAPIClient):
        self.client = api_client
        self.rate_limiter = RateLimiter(max_calls=60, time_window=60)

    async def execute(self, user_id: str, action: str, **kwargs) -> Dict:
        """Execute with rate limiting."""
        if not self.rate_limiter.allow(user_id):
            return {
                "error": "Rate limit exceeded",
                "retry_after": 60
            }

        return await self.client.make_request(action, kwargs)
```

### Request Validation

**Validate all inputs before sending to API**

```python
from pydantic import BaseModel, validator, Field

class APIRequest(BaseModel):
    """Validated API request."""
    prompt: str = Field(..., min_length=1, max_length=4000)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @validator("prompt")
    def validate_prompt(cls, v):
        """Ensure prompt doesn't contain malicious content."""
        # Check for prompt injection attempts
        dangerous_patterns = [
            "ignore previous instructions",
            "disregard all",
            "system:",
            "sudo",
        ]

        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f"Suspicious prompt content: {pattern}")

        return v

class ValidatedAPITool:
    """API tool with input validation."""

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict:
        """Generate with validated inputs."""
        try:
            # Validate inputs
            request = APIRequest(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Make request
            return await self.client.generate(request.dict())

        except ValueError as e:
            audit_log.warning(f"Invalid API request: {e}")
            return {"error": str(e)}
```

---

## Authentication & Authorization

### Authentication

**Verify identity before allowing operations**

```python
from datetime import datetime, timedelta
import jwt
from typing import Optional

class AuthenticationService:
    """JWT-based authentication."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=24)

    def create_token(self, user_id: str, role: str) -> str:
        """Create authentication token."""
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + self.token_expiry,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        audit_log.info(f"Token created for user: {user_id}")
        return token

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            audit_log.warning("Expired token")
            return None
        except jwt.InvalidTokenError:
            audit_log.warning("Invalid token")
            return None

# Usage with tools
class AuthenticatedTool:
    """Tool requiring authentication."""

    def __init__(self, auth: AuthenticationService):
        self.auth = auth

    async def execute(self, token: str, action: str, **kwargs) -> Dict:
        """Execute with authentication check."""
        # Verify token
        payload = self.auth.verify_token(token)
        if not payload:
            return {"error": "Authentication failed"}

        # Execute action
        result = await self._execute_action(
            user_id=payload["user_id"],
            role=payload["role"],
            action=action,
            **kwargs
        )

        return result
```

### Authorization (RBAC)

**Control who can do what**

```python
from enum import Enum
from dataclasses import dataclass
from typing import Set

class Permission(Enum):
    """System permissions."""
    READ_FILES = "read:files"
    WRITE_FILES = "write:files"
    EXECUTE_COMMANDS = "execute:commands"
    QUERY_DATABASE = "query:database"
    MANAGE_USERS = "manage:users"

class Role(Enum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

# Role -> Permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.EXECUTE_COMMANDS,
        Permission.QUERY_DATABASE,
        Permission.MANAGE_USERS,
    },
    Role.USER: {
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.QUERY_DATABASE,
    },
    Role.READONLY: {
        Permission.READ_FILES,
    }
}

@dataclass
class User:
    """User with role."""
    id: str
    username: str
    role: Role

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission."""
        return permission in ROLE_PERMISSIONS.get(self.role, set())

class AuthorizedTool:
    """Tool with permission checks."""

    REQUIRED_PERMISSION = Permission.EXECUTE_COMMANDS

    async def execute(self, user: User, command: str) -> Dict:
        """Execute with authorization check."""
        # Check permission
        if not user.has_permission(self.REQUIRED_PERMISSION):
            audit_log.warning(
                f"Permission denied: {user.username} "
                f"tried {self.REQUIRED_PERMISSION.value}"
            )
            return {
                "error": "Permission denied",
                "required": self.REQUIRED_PERMISSION.value
            }

        # Execute command
        audit_log.info(f"Authorized: {user.username} executing {command}")
        return await self._execute_command(command)
```

---

## Input Validation

### Validation Strategies

1. **Whitelist validation** (preferred)
2. Blacklist validation (supplementary)
3. Type checking
4. Range checking
5. Format validation

```python
from typing import Any
import re

class InputValidator:
    """Comprehensive input validation."""

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename (whitelist approach)."""
        # Only allow alphanumeric, dash, underscore, dot
        pattern = r'^[a-zA-Z0-9._-]+$'

        if not re.match(pattern, filename):
            return False

        # Disallow path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False

        # Disallow hidden files
        if filename.startswith('.'):
            return False

        return True

    @staticmethod
    def validate_command(command: str, allowed: Set[str]) -> bool:
        """Validate command against whitelist."""
        cmd_name = command.split()[0] if command else ""
        return cmd_name in allowed

    @staticmethod
    def validate_sql(sql: str, allowed_operations: Set[str]) -> bool:
        """Validate SQL operation."""
        operation = sql.strip().upper().split()[0]
        return operation in allowed_operations

    @staticmethod
    def validate_integer_range(value: Any, min_val: int, max_val: int) -> bool:
        """Validate integer is in range."""
        try:
            int_value = int(value)
            return min_val <= int_value <= max_val
        except (TypeError, ValueError):
            return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
```

---

## Output Sanitization

### Prevent Information Leakage

```python
class SecureOutput:
    """Sanitize outputs to prevent information leakage."""

    @staticmethod
    def sanitize_error(error: Exception) -> str:
        """Return safe error message."""
        # ❌ DON'T expose internal details
        # return f"Database error: {error}"

        # ✅ DO return generic message
        error_id = generate_error_id()
        audit_log.error(f"Error {error_id}: {error}", exc_info=True)
        return f"An error occurred. Reference: {error_id}"

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Return sanitized path (hide internal structure)."""
        # Convert /home/app/data/file.txt -> file.txt
        return Path(path).name

    @staticmethod
    def redact_sensitive_data(data: Dict) -> Dict:
        """Redact sensitive fields."""
        sensitive_fields = {"password", "api_key", "token", "secret"}

        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = SecureOutput.redact_sensitive_data(value)
            else:
                sanitized[key] = value

        return sanitized
```

---

## Audit Logging

### Comprehensive Audit Trail

```python
import logging
import json
from datetime import datetime
from typing import Optional

class AuditLogger:
    """Structured audit logging."""

    def __init__(self, log_file: str = "audit.log"):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # File handler with rotation
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10
        )

        # Structured JSON format
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_access(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str,
        **kwargs
    ):
        """Log access attempt."""
        event = {
            "event_type": "access",
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        self.logger.info(json.dumps(event))

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        **kwargs
    ):
        """Log security-related event."""
        event = {
            "event_type": "security",
            "severity": severity,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        self.logger.warning(json.dumps(event))

# Usage
audit_log = AuditLogger()

def execute_command(user: User, command: str):
    """Execute command with audit logging."""
    try:
        # Log attempt
        audit_log.log_access(
            user_id=user.id,
            action="execute_command",
            resource=command,
            result="attempting"
        )

        # Execute
        result = subprocess.run(command.split(), capture_output=True)

        # Log success
        audit_log.log_access(
            user_id=user.id,
            action="execute_command",
            resource=command,
            result="success",
            return_code=result.returncode
        )

        return result

    except Exception as e:
        # Log failure
        audit_log.log_security_event(
            event_type="command_execution_failed",
            severity="high",
            description=f"Command execution failed: {command}",
            user_id=user.id,
            error=str(e)
        )
        raise
```

---

## Deployment Security

### Environment Configuration

```bash
# .env.example (commit to repo)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
DB_USER=
DB_PASSWORD=
API_KEY=
JWT_SECRET=

# .env (DO NOT commit - add to .gitignore)
DB_HOST=prod-db.example.com
DB_PORT=5432
DB_NAME=production
DB_USER=prod_user
DB_PASSWORD=super_secret_password_from_vault
API_KEY=sk-xxx
JWT_SECRET=random_secret_from_vault
```

### Secret Management

```python
import os
from typing import Optional

class SecretManager:
    """Interface to secret management system."""

    def __init__(self, backend: str = "env"):
        """Initialize with backend (env, vault, aws_secrets, etc.)."""
        self.backend = backend

    def get(self, key: str) -> Optional[str]:
        """Get secret from backend."""
        if self.backend == "env":
            return os.environ.get(key)
        elif self.backend == "vault":
            return self._get_from_vault(key)
        elif self.backend == "aws_secrets":
            return self._get_from_aws_secrets(key)

        raise ValueError(f"Unknown backend: {self.backend}")

    def _get_from_vault(self, key: str) -> Optional[str]:
        """Get from HashiCorp Vault."""
        import hvac
        client = hvac.Client(url=os.environ["VAULT_URL"])
        client.token = os.environ["VAULT_TOKEN"]
        secret = client.secrets.kv.v2.read_secret_version(path=key)
        return secret["data"]["data"]["value"]

    def _get_from_aws_secrets(self, key: str) -> Optional[str]:
        """Get from AWS Secrets Manager."""
        import boto3
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=key)
        return response["SecretString"]

# Usage
secrets = SecretManager(backend="vault")
db_password = secrets.get("database/password")
api_key = secrets.get("openai/api_key")
```

### Container Security

```dockerfile
# Dockerfile with security best practices

# Use specific version, not latest
FROM python:3.11.5-slim

# Run as non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Set secure environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["python", "main.py"]
```

---

## Incident Response

### Detection

```python
class SecurityMonitor:
    """Monitor for security incidents."""

    def __init__(self):
        self.alert_thresholds = {
            "failed_auth": 5,  # 5 failed auths in 5 minutes
            "rate_limit": 10,  # 10 rate limit hits in 1 minute
            "blocked_commands": 3,  # 3 blocked commands in 1 minute
        }
        self.event_counts = defaultdict(list)

    def record_event(self, event_type: str, user_id: str):
        """Record security event."""
        now = time.time()
        self.event_counts[(event_type, user_id)].append(now)

        # Clean old events
        self._clean_old_events(event_type, user_id)

        # Check thresholds
        if self._threshold_exceeded(event_type, user_id):
            self._trigger_alert(event_type, user_id)

    def _threshold_exceeded(self, event_type: str, user_id: str) -> bool:
        """Check if threshold exceeded."""
        threshold = self.alert_thresholds.get(event_type, float('inf'))
        count = len(self.event_counts[(event_type, user_id)])
        return count >= threshold

    def _trigger_alert(self, event_type: str, user_id: str):
        """Trigger security alert."""
        alert = {
            "severity": "high",
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(self.event_counts[(event_type, user_id)])
        }

        # Send to alerting system (PagerDuty, Slack, etc.)
        self._send_alert(alert)

        # Log incident
        audit_log.log_security_event(**alert)
```

### Response Procedures

1. **Immediate Response** (< 5 minutes)
   - Identify affected systems
   - Isolate compromised components
   - Block malicious users/IPs
   - Notify security team

2. **Investigation** (< 1 hour)
   - Review audit logs
   - Identify attack vector
   - Assess damage
   - Document findings

3. **Remediation** (< 4 hours)
   - Patch vulnerabilities
   - Rotate compromised credentials
   - Update security controls
   - Test fixes

4. **Post-Incident** (< 1 week)
   - Root cause analysis
   - Update security policies
   - Improve monitoring
   - Train team

---

## Security Checklist

### Development

- [ ] Input validation on all user inputs
- [ ] Parameterized queries for database
- [ ] No shell=True for subprocess
- [ ] Path validation for file operations
- [ ] Rate limiting implemented
- [ ] Authentication required
- [ ] Authorization checks enforced
- [ ] Secrets not hardcoded
- [ ] Error messages don't leak info
- [ ] Audit logging comprehensive

### Testing

- [ ] Penetration testing performed
- [ ] SQL injection tests
- [ ] Command injection tests
- [ ] Path traversal tests
- [ ] Authentication bypass tests
- [ ] Authorization bypass tests
- [ ] Rate limit tests
- [ ] Fuzzing performed

### Deployment

- [ ] Secrets from secret manager
- [ ] TLS/SSL enabled
- [ ] Container runs as non-root
- [ ] Network segmentation configured
- [ ] Firewall rules applied
- [ ] Monitoring and alerting set up
- [ ] Incident response plan documented
- [ ] Backups configured and tested

### Ongoing

- [ ] Regular security audits (quarterly)
- [ ] Dependency updates automated
- [ ] Penetration testing (annually)
- [ ] Security training (annually)
- [ ] Incident response drills (quarterly)
- [ ] Access reviews (quarterly)
- [ ] Audit log reviews (monthly)

---

## Resources

### Tools
- **SAST**: Bandit (Python), gosec (Go), Semgrep
- **Dependency Scanning**: Snyk, Dependabot
- **Secrets Detection**: TruffleHog, git-secrets
- **Container Scanning**: Trivy, Clair
- **Runtime Protection**: Falco, Aqua Security

### Standards
- OWASP Top 10
- CWE Top 25
- NIST Cybersecurity Framework
- ISO 27001

### References
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [CWE Database](https://cwe.mitre.org/)
- [NIST Guidelines](https://www.nist.gov/cybersecurity)

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email: security@agenkit.example.com
3. Include: Description, steps to reproduce, impact
4. We will respond within 48 hours

---

Last updated: November 2025
Next review: February 2026
