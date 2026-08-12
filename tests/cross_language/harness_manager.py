"""
Cross-language test harness manager.

Manages communication with language-specific test harnesses via JSON protocol.
"""

import json
import subprocess
import uuid
from collections.abc import Callable
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


class HarnessDiscoveryError(RuntimeError):
    """Raised when an expected harness is missing or unsupported.

    Distinct from a plain RuntimeError so callers (and tests) can catch this
    specifically rather than any execution failure that happens to bubble up
    through the same call.
    """


# Languages with ANY cross-language harness code, mapped to a function that
# computes their discovery path. This is the sole source of truth for "which
# languages can this runner test" -- see LANGUAGES_WITHOUT_HARNESS below for
# the languages that are known to the toolkit but have no harness at all yet.
#
# These paths point at tests/cross_language/harness_<lang>/, the harnesses
# that actually call each language's real agenkit core (verified: harness_go
# imports agenkit-go/patterns, harness_rust links agenkit-rust, etc. -- see
# each harness's own source). Every other language ALSO carries a stale,
# unbuilt mock harness checked in at agenkit-<lang>/tests/cross_language_harness.*
# (e.g. agenkit-go/tests/cross_language_harness.go) that string-matches
# hardcoded inputs and never touches its own core. discover_harnesses() used
# to point here, at the mocks, before #763 -- a 6-language "passing" run was
# really 1 real harness (python) plus 5 mocks agreeing with each other about
# what a hardcoded string should look like. The mock sources are dead code
# kept only as a historical trap; do not repoint discovery at them again.
_HARNESS_PATHS: dict[str, Callable[[Path], Path]] = {
    "python": lambda root: root / "tests" / "cross_language" / "harness_python.py",
    "go": lambda root: root / "tests" / "cross_language" / "harness_go" / "harness_go",
    "typescript": lambda root: root
    / "tests"
    / "cross_language"
    / "harness_ts"
    / "dist"
    / "index.js",
    "rust": lambda root: root
    / "tests"
    / "cross_language"
    / "harness_rust"
    / "target"
    / "release"
    / "harness_rust",
    "cpp": lambda root: root / "tests" / "cross_language" / "harness_cpp" / "build" / "harness_cpp",
    "zig": lambda root: root / "tests" / "cross_language" / "harness_zig" / "harness_zig",
}

# Languages the toolkit ships (per CLAUDE.md's canonical 9-language list) that
# have no cross-language harness at all yet. Building them is tracked
# separately (#754 item 2) and is explicitly out of scope for the harness
# runner itself -- but a user asking for one of these languages should get a
# clear, specific error rather than argparse's generic "invalid choice",
# which is what happened before #763 (the --languages flag hardcoded a
# 6-language choices list that didn't even know these names existed).
LANGUAGES_WITHOUT_HARNESS = ("csharp", "java", "scala")

# Every language name this runner will accept on --languages, whether or not
# a harness exists for it yet. Used by run_equivalence_tests.py so the CLI
# never hardcodes its own separate 6-language list (the third instance of
# that exact bug pattern per #763, after expected_languages and
# MIN_FEATURE_COUNTS, both fixed in #757).
ALL_KNOWN_LANGUAGES = tuple(_HARNESS_PATHS.keys()) + LANGUAGES_WITHOUT_HARNESS


def discover_harnesses(
    root_dir: Path, expected_languages: list[str] | None = None
) -> list[HarnessConfig]:
    """
    Discover language harnesses in the repository.

    Unlike a plain existence-check chain, this treats `expected_languages` as
    a hard requirement: any language in that list without a built harness (or
    with no harness code at all) raises rather than being silently dropped.
    Before #763, `--health-check-only` could report "3 of 6 harnesses found"
    and still exit 0 -- the same absent-means-pass shape fixed for the parity
    report in #757, applied here.

    Args:
        root_dir: Root directory of the repository
        expected_languages: Languages that MUST have a working harness. If
            None, defaults to every language with harness code
            (`_HARNESS_PATHS`) -- i.e. discovery requires the full fleet
            unless the caller explicitly asks for a subset.

    Returns:
        List of discovered harness configurations, one per expected language.

    Raises:
        HarnessDiscoveryError: an expected language has no harness code at
            all (e.g. csharp/java/scala -- see LANGUAGES_WITHOUT_HARNESS), or
            has harness code but no built binary at the expected path.
    """
    if expected_languages is None:
        expected_languages = list(_HARNESS_PATHS.keys())

    unsupported = [lang for lang in expected_languages if lang not in _HARNESS_PATHS]
    if unsupported:
        raise HarnessDiscoveryError(
            f"No cross-language harness exists yet for: {', '.join(unsupported)}. "
            "Building these is tracked separately (#754 item 2), not by this runner."
        )

    harnesses = []
    missing = []
    for lang in expected_languages:
        path = _HARNESS_PATHS[lang](root_dir)
        if path.exists():
            harnesses.append(HarnessConfig(language=lang, executable_path=path))
        else:
            missing.append((lang, path))

    if missing:
        details = "; ".join(f"{lang} (expected at {path})" for lang, path in missing)
        raise HarnessDiscoveryError(
            f"Harness binary missing for: {details}. Build it first -- see "
            "tests/cross_language/README.md and each harness_<lang>/README.md."
        )

    return harnesses
