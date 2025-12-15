"""
Example demonstrating audit logging with multiple adapters.

This example shows how to use the pluggable audit logging system to log
security-relevant events to multiple destinations simultaneously.
"""

import tempfile
from pathlib import Path

from agenkit.observability import (
    AuditLogger,
    ConsoleAuditAdapter,
    FileAuditAdapter,
    StructuredAuditAdapter,
)


def main():
    """Demonstrate audit logging with various adapters."""
    print("=== Audit Logging Example ===\n")

    # Example 1: Simple console logging (default)
    print("1. Console Logging (Development)")
    print("-" * 50)
    console_logger = AuditLogger()  # Uses ConsoleAuditAdapter by default

    console_logger.log_auth_attempt(
        user_id="alice",
        success=True,
        method="password",
        ip_address="192.168.1.10",
    )

    console_logger.log_authorization(
        user_id="alice",
        resource="document123",
        action="read",
        allowed=True,
    )

    console_logger.log_rate_limit_exceeded(
        client_id="192.168.1.100",
        endpoint="/api/process",
        limit=100,
        window="1m",
    )

    print()

    # Example 2: File logging (production)
    print("2. File Logging (Production)")
    print("-" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"

        file_logger = AuditLogger([
            FileAuditAdapter(str(log_path), structured=True)
        ])

        file_logger.log_auth_attempt(
            user_id="bob",
            success=False,
            method="token",
            ip_address="192.168.1.20",
            reason="token_expired",
        )

        file_logger.log_validation_failure(
            message_id="msg456",
            reason="field_required",
            field="email",
            value=None,
        )

        print(f"Logged to file: {log_path}")
        print(f"Contents:\n{log_path.read_text()}")

    print()

    # Example 3: Multiple adapters (console + file + structured)
    print("3. Multiple Adapters (Console + File + Structured)")
    print("-" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"

        multi_logger = AuditLogger([
            ConsoleAuditAdapter(use_colors=True),
            FileAuditAdapter(str(log_path), structured=True),
            StructuredAuditAdapter(),  # JSON to stdout
        ])

        multi_logger.log_security_violation(
            client_id="attacker",
            violation_type="sql_injection",
            description="Attempted SQL injection in search parameter",
        )

        print(f"\nLogged to {len(multi_logger.adapters)} destinations")

    print()

    # Example 4: Configuration changes
    print("4. Configuration Change Logging")
    print("-" * 50)

    audit_logger = AuditLogger([ConsoleAuditAdapter(use_colors=False)])

    audit_logger.log_configuration_change(
        user_id="admin",
        component="timeout_middleware",
        parameter="max_duration",
        old_value=30,
        new_value=60,
    )

    print()

    # Example 5: Suspicious activity detection
    print("5. Suspicious Activity Detection")
    print("-" * 50)

    audit_logger.log_suspicious_activity(
        client_id="192.168.1.200",
        activity_type="brute_force",
        description="Multiple failed login attempts from same IP",
        indicators=[
            "10_failed_logins_1min",
            "different_user_agents",
            "password_spray_pattern",
        ],
    )

    print()

    # Example 6: Real-world scenario - API request processing
    print("6. Real-World API Request Scenario")
    print("-" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "api_audit.log"

        api_logger = AuditLogger([
            ConsoleAuditAdapter(use_colors=True),
            FileAuditAdapter(str(log_path), structured=True),
        ])

        # Simulate API request flow
        user_id = "charlie"
        ip_address = "192.168.1.30"

        # 1. Authentication
        api_logger.log_auth_attempt(
            user_id=user_id,
            success=True,
            method="jwt",
            ip_address=ip_address,
        )

        # 2. Authorization check
        api_logger.log_authorization(
            user_id=user_id,
            resource="/api/agents/process",
            action="execute",
            allowed=True,
        )

        # 3. Rate limit check (passed)
        # No log needed for successful rate limit check

        # 4. Input validation (passed)
        # No log needed for successful validation

        # 5. Request processed successfully
        print("\nAPI request processed successfully with full audit trail")
        print(f"Audit log: {log_path}")


if __name__ == "__main__":
    main()
