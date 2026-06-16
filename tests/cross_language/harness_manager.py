"""
Cross-language test harness manager.

Manages communication with language-specific test harnesses via JSON protocol.
"""

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "1.0"
DEFAULT_TIMEOUT = 60  # seconds


@dataclass
class HarnessConfig:
    """Configuration for a language harness."""

    language: str
    executable_path: Path
    timeout: int = DEFAULT_TIMEOUT
    env: dict[str, str] | None = None


@dataclass
class TestRequest:
    """Test execution request."""

    pattern: str
    scenario_id: str
    input_data: dict[str, Any]
    timeout: int | None = None


@dataclass
class TestResult:
    """Test execution result."""

    status: str  # success, error, timeout, not_implemented
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    execution_info: dict[str, Any] | None = None


class HarnessManager:
    """Manages language-specific test harnesses."""

    def __init__(self, harness_configs: list[HarnessConfig]):
        """
        Initialize harness manager.

        Args:
            harness_configs: List of harness configurations
        """
        self.harnesses = {config.language: config for config in harness_configs}
        self._validate_harnesses()

    def _validate_harnesses(self) -> None:
        """Validate that all harness executables exist."""
        for language, config in self.harnesses.items():
            if not config.executable_path.exists():
                raise FileNotFoundError(
                    f"Harness executable not found for {language}: {config.executable_path}"
                )

    def execute_test(self, language: str, request: TestRequest) -> TestResult:
        """
        Execute a test on a specific language harness.

        Args:
            language: Language to test (python, go, typescript, rust, cpp, zig)
            request: Test request details

        Returns:
            Test execution result

        Raises:
            ValueError: Language harness not configured
            RuntimeError: Harness execution failed
        """
        if language not in self.harnesses:
            raise ValueError(f"No harness configured for language: {language}")

        config = self.harnesses[language]
        timeout = request.timeout or config.timeout

        # Build request message
        request_msg = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": str(uuid.uuid4()),
            "command": "execute_test",
            "payload": {
                "pattern": request.pattern,
                "scenario_id": request.scenario_id,
                "input": request.input_data,
            },
        }

        try:
            # Execute harness
            result = self._execute_harness(
                config.executable_path,
                request_msg,
                timeout=timeout,
                env=config.env,
            )

            # Parse response
            return self._parse_response(result)

        except subprocess.TimeoutExpired:
            return TestResult(
                status="timeout",
                error={
                    "type": "TimeoutError",
                    "message": f"Test timed out after {timeout}s",
                },
            )
        except Exception as e:
            return TestResult(
                status="error",
                error={
                    "type": type(e).__name__,
                    "message": str(e),
                },
            )

    def get_harness_info(self, language: str) -> dict[str, Any]:
        """
        Get information about a language harness.

        Args:
            language: Language to query

        Returns:
            Harness information (version, supported patterns, etc.)
        """
        if language not in self.harnesses:
            raise ValueError(f"No harness configured for language: {language}")

        config = self.harnesses[language]

        request_msg = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": str(uuid.uuid4()),
            "command": "get_info",
            "payload": {},
        }

        try:
            result = self._execute_harness(config.executable_path, request_msg, timeout=10)
            response = self._parse_response(result)
            return response.output or {}
        except Exception as e:
            return {
                "error": str(e),
                "language": language,
            }

    def health_check(self, language: str) -> bool:
        """
        Check if a language harness is healthy.

        Args:
            language: Language to check

        Returns:
            True if healthy, False otherwise
        """
        if language not in self.harnesses:
            return False

        config = self.harnesses[language]

        request_msg = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": str(uuid.uuid4()),
            "command": "health_check",
            "payload": {},
        }

        try:
            result = self._execute_harness(config.executable_path, request_msg, timeout=5)
            response = self._parse_response(result)
            return response.status == "success" and response.output.get("healthy", False)
        except Exception:
            return False

    def health_check_all(self) -> dict[str, bool]:
        """
        Check health of all harnesses.

        Returns:
            Dictionary mapping language names to health status
        """
        return {language: self.health_check(language) for language in self.harnesses}

    def _execute_harness(
        self,
        executable: Path,
        request: dict[str, Any],
        timeout: int,
        env: dict[str, str] | None = None,
    ) -> str:
        """
        Execute harness subprocess.

        Args:
            executable: Path to harness executable
            request: Request message dict
            timeout: Execution timeout in seconds
            env: Optional environment variables

        Returns:
            Harness stdout output

        Raises:
            subprocess.TimeoutExpired: Harness timed out
            subprocess.CalledProcessError: Harness returned non-zero exit code
        """
        # Serialize request to JSON
        request_json = json.dumps(request)

        # Execute harness
        result = subprocess.run(
            [str(executable)],
            input=request_json,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,  # Don't raise on non-zero exit
        )

        # Check for errors
        if result.returncode not in {0, 1}:
            # Exit codes 0 (success) and 1 (error with JSON) are acceptable
            raise RuntimeError(
                f"Harness failed with exit code {result.returncode}: {result.stderr}"
            )

        return result.stdout

    def _parse_response(self, response_json: str) -> TestResult:
        """
        Parse harness response JSON.

        Args:
            response_json: JSON response string

        Returns:
            Parsed test result

        Raises:
            ValueError: Invalid JSON or protocol violation
        """
        try:
            data = json.loads(response_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        # Validate protocol version
        protocol_version = data.get("protocol_version")
        if protocol_version != PROTOCOL_VERSION:
            raise ValueError(
                f"Protocol version mismatch: expected {PROTOCOL_VERSION}, got {protocol_version}"
            )

        # Parse result
        result = data.get("result", {})

        # For execute_test, result contains nested "output" and "execution_info"
        # For other commands (health_check, get_info), result is the direct output
        if result and isinstance(result, dict) and "output" in result:
            # execute_test response format
            output = result.get("output")
            execution_info = result.get("execution_info")
        else:
            # health_check / get_info response format
            output = result
            execution_info = None

        return TestResult(
            status=data.get("status", "error"),
            output=output,
            error=data.get("error"),
            execution_info=execution_info,
        )

    def get_available_languages(self) -> list[str]:
        """
        Get list of configured languages.

        Returns:
            List of language names
        """
        return list(self.harnesses.keys())

    def execute_test_parallel(
        self, languages: list[str], request: TestRequest
    ) -> dict[str, TestResult]:
        """
        Execute test on multiple languages in parallel.

        Args:
            languages: List of languages to test
            request: Test request

        Returns:
            Dictionary mapping language names to test results
        """
        # TODO: Implement parallel execution using multiprocessing
        # For now, execute sequentially
        results = {}
        for language in languages:
            try:
                result = self.execute_test(language, request)
                results[language] = result
            except Exception as e:
                results[language] = TestResult(
                    status="error",
                    error={
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                )
        return results


def discover_harnesses(root_dir: Path) -> list[HarnessConfig]:
    """
    Auto-discover language harnesses in the repository.

    Args:
        root_dir: Root directory of the repository

    Returns:
        List of discovered harness configurations
    """
    harnesses = []

    # Python harness
    python_harness = root_dir / "tests" / "cross_language" / "harness_python.py"
    if python_harness.exists():
        harnesses.append(
            HarnessConfig(
                language="python",
                executable_path=python_harness,
            )
        )

    # Go harness
    go_harness = root_dir / "agenkit-go" / "tests" / "cross_language_harness"
    if go_harness.exists():
        harnesses.append(
            HarnessConfig(
                language="go",
                executable_path=go_harness,
            )
        )

    # TypeScript harness (via node)
    ts_harness = root_dir / "agenkit-ts" / "tests" / "cross_language_harness.js"
    if ts_harness.exists():
        harnesses.append(
            HarnessConfig(
                language="typescript",
                executable_path=ts_harness,
            )
        )

    # Rust harness
    rust_harness = root_dir / "agenkit-rust" / "target" / "release" / "cross_language_harness"
    if rust_harness.exists():
        harnesses.append(
            HarnessConfig(
                language="rust",
                executable_path=rust_harness,
            )
        )

    # C++ harness
    cpp_harness = root_dir / "agenkit-cpp" / "build" / "cross_language_harness"
    if cpp_harness.exists():
        harnesses.append(
            HarnessConfig(
                language="cpp",
                executable_path=cpp_harness,
            )
        )

    # Zig harness
    zig_harness = root_dir / "agenkit-zig" / "zig-out" / "bin" / "cross_language_harness"
    if zig_harness.exists():
        harnesses.append(
            HarnessConfig(
                language="zig",
                executable_path=zig_harness,
            )
        )

    return harnesses
