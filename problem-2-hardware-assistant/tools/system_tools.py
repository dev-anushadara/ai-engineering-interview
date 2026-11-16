"""
System inspection tools exposed for LLM Tool Calling / Function Calling.
Each tool calls the SafeCommandExecutor, parses raw output into structured schemas,
and returns clean JSON-compatible dictionaries.
"""

from typing import Dict, Any, Optional
from tools.executor import SafeCommandExecutor
from tools.parsers import (
    parse_lscpu,
    parse_lsblk,
    parse_free,
    parse_proc_meminfo,
    parse_lspci,
    parse_dmidecode_memory,
)


class HardwareInspectionToolkit:
    """Toolkit of safe system inspection tools."""

    def __init__(self, executor: Optional[SafeCommandExecutor] = None):
        self.executor = executor or SafeCommandExecutor()

    def inspect_cpu(self) -> Dict[str, Any]:
        """
        Inspect the laptop's CPU / processor specs.
        Returns model name, architecture, core and thread count, max clock speed, and cache.
        """
        res = self.executor.run_command(["lscpu", "-J"])
        if res["success"]:
            return parse_lscpu(res["stdout"])

        # Fallback to /proc/cpuinfo
        file_res = self.executor.read_system_file("/proc/cpuinfo")
        if file_res["success"]:
            return parse_lscpu(file_res["content"])

        return {"error": "Could not inspect CPU specs", "details": res.get("stderr")}

    def inspect_memory(self, query_motherboard_slots: bool = True) -> Dict[str, Any]:
        """
        Inspect RAM / Memory capacity, slot usage, and upgradability.
        Returns installed RAM, available memory, swap space, and if permissions allow,
        the motherboard maximum capacity, number of slots, and slot population.
        """
        output = {}

        # 1. Basic memory usage from /proc/meminfo or free
        meminfo = self.executor.read_system_file("/proc/meminfo")
        if meminfo["success"]:
            output["installed_ram"] = parse_proc_meminfo(meminfo["content"])
        else:
            free_res = self.executor.run_command(["free", "-b"])
            if free_res["success"]:
                output["installed_ram"] = parse_free(free_res["stdout"])

        # 2. Motherboard slots and max upgrade capacity (requires dmidecode)
        if query_motherboard_slots:
            dmi_res = self.executor.run_command(["dmidecode", "-t", "memory"], use_sudo_if_needed=True)
            if dmi_res["success"]:
                dmi_parsed = parse_dmidecode_memory(dmi_res["stdout"])
                output["motherboard_and_slots"] = dmi_parsed
            else:
                output["motherboard_and_slots"] = {
                    "supported": False,
                    "reason": "Permission denied for dmidecode (requires root/sudo) or utility missing.",
                    "note": "Run with sudo or grant dmidecode capability to inspect slot layout and max supported capacity.",
                }

        return output

    def inspect_storage(self) -> Dict[str, Any]:
        """
        Inspect all storage disks, SSDs, HDDs, NVMe drives, and partitions.
        Returns device names, models, sizes, transport bus (NVMe vs SATA), and mount points.
        """
        res = self.executor.run_command(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,TRAN,MOUNTPOINTS,MODEL,ROTA"])
        if res["success"]:
            return parse_lsblk(res["stdout"])

        # Try default lsblk -J
        res2 = self.executor.run_command(["lsblk", "-J"])
        if res2["success"]:
            return parse_lsblk(res2["stdout"])

        return {"error": "Could not inspect storage devices", "details": res.get("stderr")}

    def inspect_gpu(self) -> Dict[str, Any]:
        """
        Inspect graphics processing units (GPU / video controllers).
        Detects integrated and dedicated graphics (NVIDIA, AMD, Intel) and active drivers.
        """
        res = self.executor.run_command(["lspci", "-nnk"])
        if res["success"]:
            return parse_lspci(res["stdout"])

        res2 = self.executor.run_command(["lspci", "-vmm"])
        if res2["success"]:
            return parse_lspci(res2["stdout"])

        return {"error": "Could not inspect GPU devices", "details": res.get("stderr")}

    def inspect_battery(self) -> Dict[str, Any]:
        """
        Inspect laptop battery health, capacity, and status.
        Reads safe sysfs values from /sys/class/power_supply/.
        """
        battery_data = {}
        fields = ["capacity", "status", "technology", "model_name", "energy_now", "energy_full", "energy_full_design"]

        found_any = False
        for field in fields:
            res = self.executor.read_system_file(f"/sys/class/power_supply/BAT0/{field}")
            if res["success"]:
                battery_data[field] = res["content"].strip()
                found_any = True

        if not found_any:
            # Try BAT1
            for field in fields:
                res = self.executor.read_system_file(f"/sys/class/power_supply/BAT1/{field}")
                if res["success"]:
                    battery_data[field] = res["content"].strip()
                    found_any = True

        if not found_any:
            return {"battery_detected": False, "note": "No battery found (might be desktop/VM or non-standard path)."}

        # Calculate health % if full vs design energy exists
        if "energy_full" in battery_data and "energy_full_design" in battery_data:
            try:
                full = float(battery_data["energy_full"])
                design = float(battery_data["energy_full_design"])
                if design > 0:
                    battery_data["health_percentage"] = f"{(full / design) * 100:.1f}%"
            except ValueError:
                pass

        battery_data["battery_detected"] = True
        return battery_data

    def inspect_system_summary(self) -> Dict[str, Any]:
        """
        Quick comprehensive summary of OS, kernel, CPU, and total RAM.
        """
        uname_res = self.executor.run_command(["uname", "-r"])
        kernel = uname_res["stdout"].strip() if uname_res["success"] else "Unknown"

        cpu = self.inspect_cpu()
        storage = self.inspect_storage()
        mem = self.inspect_memory(query_motherboard_slots=False)
        gpu = self.inspect_gpu()

        return {
            "kernel_version": kernel,
            "cpu_model": cpu.get("model_name"),
            "cpu_cores": cpu.get("physical_cores"),
            "total_ram": mem.get("installed_ram", {}).get("total_ram_human", "Unknown"),
            "primary_storage": [f"{d['model']} ({d['size_human']}, {d['transport'].upper()})" for d in storage.get("disks", [])],
            "gpus": [g.get("description") for g in gpu.get("gpus", [])],
        }

