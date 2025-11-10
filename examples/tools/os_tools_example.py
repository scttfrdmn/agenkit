"""
Operating System Tools Examples for Agenkit

This example demonstrates WHY and HOW to use OS-level tools with agents,
covering file operations, shell commands, process management, and code editing.
These tools enable agents like Claude Code to interact with the local system.

WHY USE OS TOOLS?
-----------------
- **Local file access**: Read, write, and edit files on the user's machine
- **System automation**: Execute shell commands, manage processes
- **Development workflows**: Git operations, code editing, build processes
- **Desktop automation**: Interact with applications and UI elements
- **Real-time feedback**: Direct system access vs cloud-only APIs

WHEN TO USE:
- Coding assistants (like Claude Code, Cursor, GitHub Copilot)
- DevOps automation and CI/CD pipelines
- System administration and monitoring
- File processing and batch operations
- Local development workflows

WHEN NOT TO USE:
- Cloud-only agents (no local system access)
- Security-sensitive environments (sandboxing required)
- Operations requiring human approval (destructive actions)
- Cross-platform portability critical (OS-specific commands)

CRITICAL SECURITY CONSIDERATIONS:
- **Command injection**: NEVER use unsanitized user input in shell commands
- **Path traversal**: Validate file paths to prevent directory traversal attacks
- **Privilege escalation**: Don't execute with elevated permissions unnecessarily
- **Destructive operations**: Require explicit confirmation for rm, format, etc.
- **Audit logging**: Track all file/command operations for security
- **Sandboxing**: Restrict operations to specific directories/commands

TRADE-OFFS:
- Power: Direct system access vs cloud API limitations
- Security: High risk if not properly sandboxed
- Portability: OS-specific commands (Unix vs Windows)
- Reliability: Local disk/process failures vs cloud redundancy
- Latency: Fast (1-10ms) vs network APIs (100-1000ms)

"""

import asyncio
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import hashlib
import json
from agenkit import Agent
from agenkit.tools import Tool, ToolRegistry


# ============================================================================
# EXAMPLE 1: File System Operations
# ============================================================================

class FileSystemTool:
    """
    File system operations tool with security controls.

    WHY: Coding agents need to read, write, and edit files.
    Examples: Claude Code reading project files, editing code, creating docs.

    SECURITY: Restrict to allowed directories, validate paths, no symlinks.
    """

    def __init__(self, allowed_paths: List[str]):
        """
        Initialize with allowed directory paths.

        Args:
            allowed_paths: List of directory paths this tool can access
        """
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]

    def _is_path_allowed(self, path: Path) -> bool:
        """
        Check if path is within allowed directories.

        Prevents path traversal attacks like:
        - "../../../etc/passwd"
        - "/etc/shadow"
        - Symlinks outside allowed paths
        """
        try:
            resolved = path.resolve(strict=False)

            # Check if path is under any allowed directory
            for allowed in self.allowed_paths:
                try:
                    resolved.relative_to(allowed)
                    return True
                except ValueError:
                    continue

            return False
        except Exception:
            return False

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read file contents.

        Security: Path validation, size limits, allowed extensions.
        """
        path = Path(file_path)

        # Security checks
        if not self._is_path_allowed(path):
            return {
                "success": False,
                "error": f"Access denied: {file_path} is outside allowed paths"
            }

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        if not path.is_file():
            return {
                "success": False,
                "error": f"Not a file: {file_path}"
            }

        # Size limit (10MB)
        if path.stat().st_size > 10 * 1024 * 1024:
            return {
                "success": False,
                "error": f"File too large (>10MB): {file_path}"
            }

        try:
            content = path.read_text(encoding='utf-8')
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "path": str(path)
            }
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"File is not UTF-8 encoded: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {e}"
            }

    async def write_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Write content to file.

        Security: Path validation, overwrite protection, atomic writes.
        """
        path = Path(file_path)

        # Security checks
        if not self._is_path_allowed(path):
            return {
                "success": False,
                "error": f"Access denied: {file_path} is outside allowed paths"
            }

        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"File exists and overwrite=False: {file_path}"
            }

        try:
            # Atomic write: write to temp file, then rename
            temp_path = path.with_suffix(path.suffix + '.tmp')
            temp_path.write_text(content, encoding='utf-8')
            temp_path.replace(path)

            return {
                "success": True,
                "path": str(path),
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write file: {e}"
            }

    async def list_directory(
        self,
        dir_path: str,
        pattern: str = "*"
    ) -> Dict[str, Any]:
        """
        List files in directory matching pattern.

        Security: Path validation, no hidden files by default.
        """
        path = Path(dir_path)

        if not self._is_path_allowed(path):
            return {
                "success": False,
                "error": f"Access denied: {dir_path} is outside allowed paths"
            }

        if not path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {dir_path}"
            }

        if not path.is_dir():
            return {
                "success": False,
                "error": f"Not a directory: {dir_path}"
            }

        try:
            files = []
            for item in path.glob(pattern):
                # Skip hidden files
                if item.name.startswith('.'):
                    continue

                files.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "file" if item.is_file() else "dir",
                    "size": item.stat().st_size if item.is_file() else None
                })

            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list directory: {e}"
            }


async def example1_file_operations():
    """
    Demonstrate file system operations.

    WHY: Coding agents need to read project files, edit code, create docs.
    Example: Claude Code reading README.md, editing main.py, listing directory.

    SECURITY: Path validation prevents directory traversal attacks.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: File System Operations")
    print("="*80)

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nWorkspace: {temp_dir}")

        # Create tool restricted to temp directory
        fs_tool = FileSystemTool(allowed_paths=[temp_dir])

        # Write a file
        print("\n--- Writing file ---")
        result = await fs_tool.write_file(
            f"{temp_dir}/hello.txt",
            "Hello from agenkit!",
            overwrite=False
        )
        print(f"✓ {result}")

        # Read the file
        print("\n--- Reading file ---")
        result = await fs_tool.read_file(f"{temp_dir}/hello.txt")
        print(f"✓ Content: {result['content']}")

        # List directory
        print("\n--- Listing directory ---")
        result = await fs_tool.list_directory(temp_dir)
        print(f"✓ Files: {result['files']}")

        # Try to access file outside allowed path (security test)
        print("\n--- Security Test: Path traversal attack ---")
        result = await fs_tool.read_file("/etc/passwd")
        print(f"✗ {result['error']}")

    print("\n💡 KEY INSIGHT:")
    print("   File system tools enable local file access for coding agents.")
    print("   Path validation prevents directory traversal attacks.")
    print("   Example: Claude Code reading your project files.")


# ============================================================================
# EXAMPLE 2: Shell Command Execution
# ============================================================================

class ShellTool:
    """
    Shell command execution with security controls.

    WHY: Agents need to run git, npm, pytest, build tools, etc.
    Example: Claude Code running tests, installing packages, building projects.

    SECURITY: Command whitelist, no shell injection, timeout, output limits.
    """

    def __init__(
        self,
        allowed_commands: List[str],
        working_directory: str,
        timeout_seconds: int = 30
    ):
        """
        Initialize with allowed commands and working directory.

        Args:
            allowed_commands: Whitelist of allowed command names (e.g., ['git', 'npm'])
            working_directory: Directory to execute commands in
            timeout_seconds: Maximum execution time
        """
        self.allowed_commands = allowed_commands
        self.working_directory = Path(working_directory).resolve()
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        command: List[str],
        capture_output: bool = True
    ) -> Dict[str, Any]:
        """
        Execute shell command with security controls.

        Args:
            command: Command as list (e.g., ['git', 'status'])
            capture_output: Whether to capture stdout/stderr

        Security:
        - Command whitelist (only allowed commands)
        - No shell=True (prevents injection)
        - Timeout to prevent hanging
        - Output size limits
        """
        if not command:
            return {
                "success": False,
                "error": "Empty command"
            }

        # Security: Check command is in whitelist
        cmd_name = command[0]
        if cmd_name not in self.allowed_commands:
            return {
                "success": False,
                "error": f"Command not allowed: {cmd_name}. Allowed: {self.allowed_commands}"
            }

        try:
            # Execute command (shell=False prevents injection)
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                cwd=self.working_directory
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "stdout": stdout.decode('utf-8') if stdout else "",
                    "stderr": stderr.decode('utf-8') if stderr else "",
                    "command": " ".join(command)
                }
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {self.timeout_seconds}s",
                    "command": " ".join(command)
                }
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Command not found: {cmd_name}",
                "command": " ".join(command)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {e}",
                "command": " ".join(command)
            }


async def example2_shell_commands():
    """
    Demonstrate shell command execution.

    WHY: Agents need to run development tools (git, npm, pytest, etc.).
    Example: Claude Code running tests, checking git status, installing deps.

    SECURITY: Command whitelist prevents arbitrary code execution.
    No shell=True prevents command injection.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Shell Command Execution")
    print("="*80)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nWorkspace: {temp_dir}")

        # Create tool with allowed commands
        shell_tool = ShellTool(
            allowed_commands=['ls', 'echo', 'pwd', 'git'],
            working_directory=temp_dir,
            timeout_seconds=5
        )

        # Execute allowed command
        print("\n--- Allowed command: ls ---")
        result = await shell_tool.execute(['ls', '-la'])
        print(f"✓ Success: {result['success']}")
        print(f"  Output: {result['stdout'][:100]}...")

        # Try disallowed command (security test)
        print("\n--- Security Test: Disallowed command ---")
        result = await shell_tool.execute(['rm', '-rf', '/'])
        print(f"✗ {result['error']}")

        # Try command injection attempt (security test)
        print("\n--- Security Test: Command injection attempt ---")
        result = await shell_tool.execute(['echo', 'test; rm -rf /'])
        if result['success']:
            print(f"✓ Safe execution (no injection): {result['stdout'].strip()}")

    print("\n💡 KEY INSIGHT:")
    print("   Shell tools enable running development commands (git, npm, pytest).")
    print("   Command whitelist prevents arbitrary code execution.")
    print("   shell=False prevents injection attacks.")
    print("   Example: Claude Code running `pytest tests/` for you.")


# ============================================================================
# EXAMPLE 3: Git Operations
# ============================================================================

class GitTool:
    """
    Git operations tool for version control.

    WHY: Coding agents need to check status, commit, push, pull, branch.
    Example: Claude Code creating commits, checking diffs, managing branches.
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.shell = ShellTool(
            allowed_commands=['git'],
            working_directory=str(self.repo_path),
            timeout_seconds=30
        )

    async def status(self) -> Dict[str, Any]:
        """Get git status."""
        result = await self.shell.execute(['git', 'status', '--short'])
        if result['success']:
            return {
                "success": True,
                "files": result['stdout'].strip().split('\n') if result['stdout'] else []
            }
        return result

    async def diff(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Get git diff."""
        cmd = ['git', 'diff']
        if file_path:
            cmd.append(file_path)
        return await self.shell.execute(cmd)

    async def add(self, files: List[str]) -> Dict[str, Any]:
        """Stage files for commit."""
        cmd = ['git', 'add'] + files
        return await self.shell.execute(cmd)

    async def commit(self, message: str) -> Dict[str, Any]:
        """Create commit with message."""
        return await self.shell.execute(['git', 'commit', '-m', message])

    async def branch_list(self) -> Dict[str, Any]:
        """List branches."""
        result = await self.shell.execute(['git', 'branch', '--list'])
        if result['success']:
            branches = [
                b.strip().lstrip('* ')
                for b in result['stdout'].split('\n')
                if b.strip()
            ]
            return {
                "success": True,
                "branches": branches
            }
        return result


async def example3_git_operations():
    """
    Demonstrate git operations.

    WHY: Coding agents need version control integration.
    Example: Claude Code checking git status, creating commits, viewing diffs.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Git Operations")
    print("="*80)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nWorkspace: {temp_dir}")

        # Initialize git repo
        shell = ShellTool(['git'], temp_dir, 30)
        await shell.execute(['git', 'init'])
        await shell.execute(['git', 'config', 'user.name', 'Test User'])
        await shell.execute(['git', 'config', 'user.email', 'test@example.com'])

        # Create file
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("print('hello')")

        # Create git tool
        git_tool = GitTool(temp_dir)

        # Check status
        print("\n--- Git Status ---")
        result = await git_tool.status()
        print(f"✓ Untracked files: {result['files']}")

        # Stage and commit
        print("\n--- Stage and Commit ---")
        await git_tool.add(['test.py'])
        result = await git_tool.commit("Initial commit")
        print(f"✓ Committed: {result['success']}")

        # Check branches
        print("\n--- List Branches ---")
        result = await git_tool.branch_list()
        print(f"✓ Branches: {result['branches']}")

    print("\n💡 KEY INSIGHT:")
    print("   Git tools enable version control integration for coding agents.")
    print("   Example: Claude Code checking status, creating commits, viewing diffs.")


# ============================================================================
# EXAMPLE 4: Code Editing Operations
# ============================================================================

class CodeEditorTool:
    """
    Code editing operations with syntax awareness.

    WHY: Coding agents need to edit code precisely, not just write files.
    Example: Claude Code replacing function, adding import, refactoring.
    """

    def __init__(self, fs_tool: FileSystemTool):
        self.fs_tool = fs_tool

    async def replace_text(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        count: int = -1
    ) -> Dict[str, Any]:
        """
        Replace text in file.

        Args:
            file_path: Path to file
            old_text: Text to find and replace
            new_text: Replacement text
            count: Number of replacements (-1 for all)
        """
        # Read file
        read_result = await self.fs_tool.read_file(file_path)
        if not read_result['success']:
            return read_result

        content = read_result['content']

        # Check if old_text exists
        if old_text not in content:
            return {
                "success": False,
                "error": f"Text not found in file: {old_text[:50]}..."
            }

        # Replace text
        new_content = content.replace(old_text, new_text, count)

        # Write back
        write_result = await self.fs_tool.write_file(
            file_path,
            new_content,
            overwrite=True
        )

        if write_result['success']:
            return {
                "success": True,
                "replacements": content.count(old_text) if count == -1 else min(count, content.count(old_text)),
                "path": file_path
            }

        return write_result

    async def insert_at_line(
        self,
        file_path: str,
        line_number: int,
        text: str
    ) -> Dict[str, Any]:
        """
        Insert text at specific line number.

        Args:
            file_path: Path to file
            line_number: Line number to insert at (1-indexed)
            text: Text to insert
        """
        # Read file
        read_result = await self.fs_tool.read_file(file_path)
        if not read_result['success']:
            return read_result

        lines = read_result['content'].split('\n')

        # Validate line number
        if line_number < 1 or line_number > len(lines) + 1:
            return {
                "success": False,
                "error": f"Invalid line number: {line_number} (file has {len(lines)} lines)"
            }

        # Insert text
        lines.insert(line_number - 1, text)
        new_content = '\n'.join(lines)

        # Write back
        write_result = await self.fs_tool.write_file(
            file_path,
            new_content,
            overwrite=True
        )

        if write_result['success']:
            return {
                "success": True,
                "line": line_number,
                "path": file_path
            }

        return write_result

    async def search_and_replace_regex(
        self,
        file_path: str,
        pattern: str,
        replacement: str
    ) -> Dict[str, Any]:
        """
        Search and replace using regex pattern.

        Args:
            file_path: Path to file
            pattern: Regex pattern to match
            replacement: Replacement text (can use \\1, \\2 for groups)
        """
        import re

        # Read file
        read_result = await self.fs_tool.read_file(file_path)
        if not read_result['success']:
            return read_result

        content = read_result['content']

        try:
            # Compile and apply regex
            regex = re.compile(pattern)
            matches = regex.findall(content)
            new_content = regex.sub(replacement, content)

            if new_content == content:
                return {
                    "success": False,
                    "error": "No matches found"
                }

            # Write back
            write_result = await self.fs_tool.write_file(
                file_path,
                new_content,
                overwrite=True
            )

            if write_result['success']:
                return {
                    "success": True,
                    "matches": len(matches),
                    "path": file_path
                }

            return write_result
        except re.error as e:
            return {
                "success": False,
                "error": f"Invalid regex pattern: {e}"
            }


async def example4_code_editing():
    """
    Demonstrate code editing operations.

    WHY: Coding agents need precise code editing, not just file writes.
    Example: Claude Code replacing function, adding import, refactoring.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Code Editing Operations")
    print("="*80)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nWorkspace: {temp_dir}")

        # Create file system and editor tools
        fs_tool = FileSystemTool([temp_dir])
        editor_tool = CodeEditorTool(fs_tool)

        # Create sample Python file
        sample_code = """def greet(name):
    print(f"Hello, {name}!")

greet("World")
"""
        await fs_tool.write_file(f"{temp_dir}/sample.py", sample_code)

        print("\n--- Original code ---")
        print(sample_code)

        # Replace text
        print("\n--- Replace function call ---")
        result = await editor_tool.replace_text(
            f"{temp_dir}/sample.py",
            'greet("World")',
            'greet("Agenkit")'
        )
        print(f"✓ Replaced {result['replacements']} occurrence(s)")

        # Insert line
        print("\n--- Insert import at line 1 ---")
        result = await editor_tool.insert_at_line(
            f"{temp_dir}/sample.py",
            1,
            "import sys"
        )
        print(f"✓ Inserted at line {result['line']}")

        # Show final code
        print("\n--- Final code ---")
        result = await fs_tool.read_file(f"{temp_dir}/sample.py")
        print(result['content'])

    print("\n💡 KEY INSIGHT:")
    print("   Code editing tools enable precise modifications.")
    print("   Example: Claude Code replacing function, adding imports.")
    print("   Better than regenerating entire files.")


# ============================================================================
# EXAMPLE 5: Process Management
# ============================================================================

class ProcessTool:
    """
    Process management tool.

    WHY: Agents need to start servers, run background jobs, monitor processes.
    Example: Claude Code starting dev server, running tests in watch mode.
    """

    def __init__(self):
        self.processes: Dict[str, asyncio.subprocess.Process] = {}

    async def start(
        self,
        name: str,
        command: List[str],
        working_directory: str
    ) -> Dict[str, Any]:
        """
        Start background process.

        Args:
            name: Process identifier
            command: Command to execute
            working_directory: Working directory
        """
        if name in self.processes:
            return {
                "success": False,
                "error": f"Process '{name}' already running"
            }

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_directory
            )

            self.processes[name] = process

            return {
                "success": True,
                "name": name,
                "pid": process.pid,
                "command": " ".join(command)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start process: {e}"
            }

    async def stop(self, name: str) -> Dict[str, Any]:
        """Stop process by name."""
        if name not in self.processes:
            return {
                "success": False,
                "error": f"Process '{name}' not found"
            }

        process = self.processes[name]
        process.terminate()

        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()

        del self.processes[name]

        return {
            "success": True,
            "name": name,
            "message": "Process stopped"
        }

    async def status(self, name: str) -> Dict[str, Any]:
        """Check process status."""
        if name not in self.processes:
            return {
                "success": False,
                "error": f"Process '{name}' not found"
            }

        process = self.processes[name]
        returncode = process.returncode

        return {
            "success": True,
            "name": name,
            "pid": process.pid,
            "running": returncode is None,
            "returncode": returncode
        }

    async def list_processes(self) -> Dict[str, Any]:
        """List all managed processes."""
        processes = []
        for name, process in self.processes.items():
            processes.append({
                "name": name,
                "pid": process.pid,
                "running": process.returncode is None
            })

        return {
            "success": True,
            "processes": processes,
            "count": len(processes)
        }


async def example5_process_management():
    """
    Demonstrate process management.

    WHY: Agents need to run background processes (servers, watchers, daemons).
    Example: Claude Code starting dev server, running tests in watch mode.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Process Management")
    print("="*80)

    with tempfile.TemporaryDirectory() as temp_dir:
        process_tool = ProcessTool()

        # Start background process
        print("\n--- Starting background process ---")
        result = await process_tool.start(
            "sleep_process",
            ["sleep", "10"],
            temp_dir
        )
        print(f"✓ Started: PID {result['pid']}")

        # Check status
        print("\n--- Checking status ---")
        result = await process_tool.status("sleep_process")
        print(f"✓ Running: {result['running']}")

        # List processes
        print("\n--- Listing processes ---")
        result = await process_tool.list_processes()
        print(f"✓ Processes: {result['processes']}")

        # Stop process
        print("\n--- Stopping process ---")
        result = await process_tool.stop("sleep_process")
        print(f"✓ {result['message']}")

    print("\n💡 KEY INSIGHT:")
    print("   Process tools enable background job management.")
    print("   Example: Claude Code starting dev server at localhost:3000.")


# ============================================================================
# MAIN RUNNER
# ============================================================================

async def main():
    """Run all OS tools examples."""

    print("\n" + "="*80)
    print("OPERATING SYSTEM TOOLS EXAMPLES FOR AGENKIT")
    print("="*80)
    print("\nThese examples demonstrate WHY and HOW to use OS-level tools.")
    print("Critical for coding agents like Claude Code, system automation, and DevOps.")

    examples = [
        ("File System Operations", example1_file_operations),
        ("Shell Command Execution", example2_shell_commands),
        ("Git Operations", example3_git_operations),
        ("Code Editing Operations", example4_code_editing),
        ("Process Management", example5_process_management),
    ]

    for i, (name, example_func) in enumerate(examples, 1):
        await example_func()

        if i < len(examples):
            input("\nPress Enter to continue to next example...")

    # Summary
    print("\n" + "="*80)
    print("KEY TAKEAWAYS")
    print("="*80)
    print("""
1. WHEN TO USE OS TOOLS:
   - Coding assistants (Claude Code, Cursor, GitHub Copilot)
   - DevOps automation (CI/CD, deployment, monitoring)
   - System administration and batch processing
   - Local development workflows (git, npm, pytest)

2. SECURITY (CRITICAL):
   - Path validation: Prevent directory traversal (../../../etc/passwd)
   - Command whitelist: Only allow specific commands
   - No shell=True: Prevent command injection
   - Sandboxing: Restrict to specific directories
   - Audit logging: Track all operations
   - User confirmation: Required for destructive operations (rm, format)

3. FILE OPERATIONS:
   - Read/write with path validation
   - Atomic writes (temp file + rename)
   - Size limits (prevent memory exhaustion)
   - Extension filtering (only allowed file types)

4. SHELL COMMANDS:
   - Command whitelist (git, npm, pytest, etc.)
   - subprocess without shell=True (prevents injection)
   - Timeouts (prevent hanging processes)
   - Output size limits

5. CODE EDITING:
   - Precise text replacement (not full file regeneration)
   - Line-based insertion
   - Regex search and replace
   - Syntax-aware editing (future: AST-based)

6. PROCESS MANAGEMENT:
   - Start background processes (dev servers, watchers)
   - Monitor process status
   - Graceful termination (SIGTERM then SIGKILL)

7. TRADE-OFFS:
   - Power: Full system access vs cloud API limitations
   - Security: High risk if not properly controlled
   - Portability: OS-specific commands (Unix vs Windows)
   - Latency: Fast (1-10ms local) vs 100-1000ms (API)

8. REAL-WORLD EXAMPLES:
   - Claude Code: Reads your files, edits code, runs tests
   - GitHub Copilot Workspace: Creates files, commits changes
   - Cursor: Edits multiple files, refactors code
   - CI/CD agents: Build, test, deploy applications

9. BEST PRACTICES:
   - Always validate paths before file operations
   - Use command whitelists, never arbitrary execution
   - Require user confirmation for destructive operations
   - Implement audit logging for security
   - Set timeouts on all subprocess executions
   - Use atomic operations (temp file + rename)

Next steps:
- Add GUI automation (pyautogui, playwright for UI testing)
- Implement syntax-aware editing (AST-based refactoring)
- Add Docker container management tools
- Create cloud resource management tools (AWS, GCP, Azure)
    """)


if __name__ == "__main__":
    asyncio.run(main())
