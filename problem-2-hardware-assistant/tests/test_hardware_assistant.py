"""
Unit and integration tests for the Linux Hardware Q&A Assistant.
Validates security boundaries, command allow-listing, parsers, and multi-turn conversations.
"""

import pytest
from tools.executor import SafeCommandExecutor, CommandExecutionError
from tools.parsers import (
    parse_lscpu,
    parse_lsblk,
    parse_free,
    parse_proc_meminfo,
    parse_lspci,
    parse_dmidecode_memory,
)
from tools.system_tools import HardwareInspectionToolkit
from agent.llm import HardwareAgent
from fixtures.linux_mock import (
    LSCPU_JSON,
    LSBLK_JSON,
    FREE_OUTPUT,
    PROC_MEMINFO,
    LSPCI_OUTPUT,
    DMIDECODE_MEMORY,
)


class TestSecurityAndAllowList:
    """Ensures no arbitrary command execution or privilege bypass can occur."""

    def setup_method(self):
        self.executor = SafeCommandExecutor(force_mock=True)

    def test_allow_listed_commands_pass(self):
        cmd = ["lscpu", "-J"]
        binary, args = self.executor.validate_command(cmd)
        assert binary == "lscpu"
        assert args == ["-J"]

    def test_unlisted_command_rejected(self):
        with pytest.raises(CommandExecutionError) as exc:
            self.executor.validate_command(["rm", "-rf", "/"])
        assert "not in the hardware inspection allow-list" in str(exc.value)

    def test_shell_injection_attempt_rejected(self):
        with pytest.raises(CommandExecutionError):
            self.executor.validate_command(["lscpu; cat /etc/passwd"])

    def test_unlisted_flag_rejected(self):
        with pytest.raises(CommandExecutionError):
            # Only -J or empty is allowed for lscpu
            self.executor.validate_command(["lscpu", "--destructive-flag"])

    def test_disallowed_proc_file_rejected(self):
        with pytest.raises(CommandExecutionError):
            self.executor.read_system_file("/etc/shadow")

    def test_allowed_proc_file_succeeds(self):
        res = self.executor.read_system_file("/proc/meminfo")
        assert res["success"] is True
        assert "MemTotal" in res["content"]


class TestParsers:
    """Tests parsing raw Linux outputs into clean structured data."""

    def test_parse_lscpu(self):
        parsed = parse_lscpu(LSCPU_JSON)
        assert "i7-1260P" in parsed["model_name"]
        assert parsed["physical_cores"] == 12
        assert parsed["total_threads"] == 16
        assert parsed["architecture"] == "x86_64"

    def test_parse_lsblk_nvme(self):
        parsed = parse_lsblk(LSBLK_JSON)
        assert parsed["has_nvme"] is True
        assert len(parsed["disks"]) == 1
        disk = parsed["disks"][0]
        assert "Samsung SSD 980 PRO" in disk["model"]
        assert disk["is_nvme"] is True
        assert len(disk["partitions"]) == 3

    def test_parse_dmidecode_ram_upgradability(self):
        """Validates the exact interview example scenario (16 GB in 1 of 2 slots, max 64 GB)."""
        parsed = parse_dmidecode_memory(DMIDECODE_MEMORY)
        assert parsed["supported"] is True
        assert parsed["max_board_capacity"] == "64 GB"
        assert parsed["total_slots"] == 2
        assert parsed["populated_slots_count"] == 1
        assert parsed["empty_slots_count"] == 1
        assert parsed["can_upgrade"] is True

        populated = parsed["populated_slots"][0]
        assert populated["size"] == "16 GB"
        assert populated["type"] == "DDR5"
        assert populated["form_factor"] == "SODIMM"

    def test_parse_free(self):
        parsed = parse_free(FREE_OUTPUT)
        assert "total_bytes" in parsed
        assert parsed["total_bytes"] == 16558480
        assert "available_bytes" in parsed

    def test_parse_lspci(self):
        parsed = parse_lspci(LSPCI_OUTPUT)
        assert parsed["gpu_count"] >= 2  # Intel iGPU + NVIDIA RTX 3050
        assert parsed["is_hybrid_graphics"] is True
        gpus_str = str(parsed["gpus"])
        assert "Intel" in gpus_str
        assert "NVIDIA" in gpus_str


class TestAgentConversationFlow:
    """Validates the end-to-end questions from the interview prompt."""

    def setup_method(self):
        executor = SafeCommandExecutor(force_mock=True)
        toolkit = HardwareInspectionToolkit(executor=executor)
        self.agent = HardwareAgent(toolkit=toolkit, force_offline_mode=True)

    def test_question_can_i_add_more_ram(self):
        """User: 'Can I add more RAM, and how much?'"""
        res = self.agent.ask("Can I add more RAM, and how much?")
        answer = res["answer"]
        assert "16" in answer
        assert "64 GB" in answer
        assert "slot" in answer.lower()
        assert "inspect_memory" in res["tools_used"]

    def test_question_is_my_ssd_nvme(self):
        """User: 'Is my SSD NVMe?'"""
        res = self.agent.ask("Is my SSD NVMe?")
        answer = res["answer"]
        assert "NVMe" in answer
        assert "Samsung" in answer
        assert "inspect_storage" in res["tools_used"]

    def test_followup_question_and_what_about_the_gpu(self):
        """User asks about RAM first, then asks 'and what about the GPU?'"""
        self.agent.ask("How much RAM do I have?")
        res2 = self.agent.ask("and what about the GPU?")
        answer = res2["answer"]
        assert any(brand in answer for brand in ["Intel", "NVIDIA", "graphics"])
        assert "inspect_gpu" in res2["tools_used"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])

