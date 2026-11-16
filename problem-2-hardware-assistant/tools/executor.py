"""
Safe Command Executor for Linux Hardware Inspection.
Enforces strict allow-listing, argument sanitization, read-only execution,
and graceful permission handling.
"""

import os
import sys
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from fixtures.linux_mock import (
    LSCPU_JSON,
    LSBLK_JSON,
    FREE_OUTPUT,
    PROC_MEMINFO,
    LSPCI_OUTPUT,
    DMIDECODE_MEMORY,
    BATTERY_INFO,
)

# Strict allow-list of binary names and allowed exact flag combinations.
# Any invocation outside this matrix is rejected before execution.
ALLOWED_COMMANDS = {
    "lscpu": [
        ["-J"],
        [],
    ],
    "lsblk": [
        ["-J", "-o", "NAME,SIZE,TYPE,TRAN,MOUNTPOINTS,MODEL,ROTA"],
        ["-J"],
        [],
    ],
    "free": [
        ["-b"],
        ["-m"],
        ["-h"],
        [],
    ],
    "lspci": [
        ["-vmm"],
        ["-nnk"],
        [],
    ],
    "dmidecode": [
        ["-t", "memory"],
        ["-t", "processor"],
        ["-t", "chassis"],
        ["-t", "baseboard"],
    ],
    "uname": [
        ["-r"],
        ["-a"],
    ],
}

ALLOWED_PROC_FILES = {
    "/proc/cpuinfo",
    "/proc/meminfo",
    "/proc/version",
    "/proc/loadavg",
}

ALLOWED_SYS_PREFIXES = (
    "/sys/class/power_supply/",
    "/sys/class/dmi/id/",
    "/sys/class/thermal/",
)


class CommandExecutionError(Exception):
    """Raised when a command violates safety policies or fails."""
    pass


class SafeCommandExecutor:
    """Executes read-only system inspection commands with strict safety boundaries."""

    def __init__(self, force_mock: bool = False, timeout_sec: float = 5.0):
        self.timeout_sec = timeout_sec
        # If not on Linux, automatically force mock mode for portable testing
        is_linux = sys.platform.startswith("linux")
        self.is_mock = force_mock or not is_linux
        self.is_linux = is_linux

    def is_root(self) -> bool:
        """Check if the process is running as root."""
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
        return False

    def validate_command(self, cmd: List[str]) -> Tuple[str, List[str]]:
        """
        Validate that the command and its arguments strictly match the allow-list.
        Rejects shell meta-characters, redirections, or unlisted flags.
        """
        if not cmd:
            raise CommandExecutionError("Command list cannot be empty.")

        binary = cmd[0]
        args = cmd[1:]

        # Handle 'sudo dmidecode' pattern if allowed
        if binary == "sudo":
            if not args or args[0] != "dmidecode":
                raise CommandExecutionError("sudo is only permitted for 'dmidecode'")
            binary = "dmidecode"
            args = args[1:]

        if binary not in ALLOWED_COMMANDS:
            raise CommandExecutionError(
                f"Command '{binary}' is not in the hardware inspection allow-list. "
                f"Allowed commands: {list(ALLOWED_COMMANDS.keys())}"
            )

        allowed_arg_sets = ALLOWED_COMMANDS[binary]
        if args not in allowed_arg_sets:
            raise CommandExecutionError(
                f"Arguments {args} are not permitted for '{binary}'. "
                f"Allowed combinations: {allowed_arg_sets}"
            )

        return binary, args

    def run_command(self, cmd: List[str], use_sudo_if_needed: bool = False) -> Dict[str, Any]:
        """
        Safely execute an allow-listed command. Returns stdout, stderr, exit_code,
        and permission metadata.
        """
        binary, args = self.validate_command(cmd)

        # Mock mode fallback (e.g. running on Windows, macOS, or in unit tests)
        if self.is_mock:
            return self._run_mock_command(binary, args)

        # Check binary existence on the host
        binary_path = shutil.which(binary)
        if not binary_path:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Executable '{binary}' was not found in system PATH.",
                "exit_code": 127,
                "permission_denied": False,
                "missing_tool": True,
            }

        full_cmd = [binary_path] + args
        if use_sudo_if_needed and binary == "dmidecode" and not self.is_root():
            sudo_path = shutil.which("sudo")
            if sudo_path:
                full_cmd = [sudo_path, "-n"] + full_cmd  # -n = non-interactive

        try:
            # shell=False is strictly enforced
            res = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_sec,
                shell=False,
            )

            is_permission_denied = (
                res.returncode != 0
                and any(w in res.stderr.lower() for w in ["permission denied", "operation not permitted"])
            )

            return {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "exit_code": res.returncode,
                "permission_denied": is_permission_denied,
                "missing_tool": False,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command '{binary}' timed out after {self.timeout_sec}s.",
                "exit_code": -1,
                "permission_denied": False,
                "missing_tool": False,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "permission_denied": False,
                "missing_tool": False,
            }

    def read_system_file(self, filepath: str) -> Dict[str, Any]:
        """
        Safely read specific allow-listed /proc or /sys files.
        Guards against directory traversal and arbitrary file reads.
        """
        # Clean path and verify allow-list
        norm_path = os.path.normpath(filepath).replace("\\", "/")

        is_allowed = (
            norm_path in ALLOWED_PROC_FILES
            or any(norm_path.startswith(prefix) for prefix in ALLOWED_SYS_PREFIXES)
        )

        if not is_allowed:
            raise CommandExecutionError(
                f"Path '{filepath}' is not an allow-listed hardware system file."
            )

        if self.is_mock:
            return self._read_mock_file(norm_path)

        if not os.path.exists(norm_path):
            return {
                "success": False,
                "content": "",
                "error": f"File '{norm_path}' does not exist on this machine.",
            }

        try:
            with open(norm_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"success": True, "content": content, "error": None}
        except PermissionError:
            return {
                "success": False,
                "content": "",
                "error": f"Permission denied reading '{norm_path}'.",
            }
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}

    def _run_mock_command(self, binary: str, args: List[str]) -> Dict[str, Any]:
        """Provides simulated Linux hardware outputs for cross-platform portability."""
        if binary == "lscpu":
            return {"success": True, "stdout": LSCPU_JSON, "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}
        elif binary == "lsblk":
            return {"success": True, "stdout": LSBLK_JSON, "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}
        elif binary == "free":
            return {"success": True, "stdout": FREE_OUTPUT, "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}
        elif binary == "lspci":
            return {"success": True, "stdout": LSPCI_OUTPUT, "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}
        elif binary == "dmidecode":
            if "-t" in args and "memory" in args:
                return {"success": True, "stdout": DMIDECODE_MEMORY, "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}
            return {"success": True, "stdout": "SMBIOS Mock Data", "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}
        elif binary == "uname":
            return {"success": True, "stdout": "6.8.0-45-generic\n", "stderr": "", "exit_code": 0, "permission_denied": False, "missing_tool": False}

        return {"success": False, "stdout": "", "stderr": "Unknown mock command", "exit_code": 1, "permission_denied": False, "missing_tool": False}

    def _read_mock_file(self, filepath: str) -> Dict[str, Any]:
        if filepath == "/proc/meminfo":
            return {"success": True, "content": PROC_MEMINFO, "error": None}
        elif filepath == "/proc/cpuinfo":
            return {"success": True, "content": "model name : 12th Gen Intel(R) Core(TM) i7-1260P\ncpu cores : 12\n", "error": None}
        elif filepath.startswith("/sys/class/power_supply/"):
            param = filepath.split("/")[-1]
            val = BATTERY_INFO.get(param, "unknown")
            return {"success": True, "content": f"{val}\n", "error": None}
        return {"success": False, "content": "", "error": "Mock file not found"}

