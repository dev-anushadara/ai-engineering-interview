"""
Parsers for normalising Linux command outputs into clean, structured dictionaries.
Prevents LLM token bloat and ensures grounded, hallucination-free reasoning.
"""

import json
import re
from typing import Dict, Any, List, Optional


def bytes_to_human(n_bytes: int) -> str:
    """Format bytes into human-readable string (GiB / MiB / TiB)."""
    if n_bytes >= 1024**4:
        return f"{n_bytes / (1024**4):.2f} TiB"
    elif n_bytes >= 1024**3:
        return f"{n_bytes / (1024**3):.2f} GiB"
    elif n_bytes >= 1024**2:
        return f"{n_bytes / (1024**2):.1f} MiB"
    return f"{n_bytes} bytes"


def parse_lscpu(raw_output: str) -> Dict[str, Any]:
    """Parse lscpu -J or plaintext output into structured CPU specifications."""
    data = {}
    try:
        # Try JSON first
        obj = json.loads(raw_output)
        for item in obj.get("lscpu", []):
            field = item.get("field", "").rstrip(":").strip()
            val = item.get("data", "").strip()
            data[field] = val
    except json.JSONDecodeError:
        # Fallback to key-value parsing
        for line in raw_output.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()

    # Normalize into standard fields
    cores = int(data.get("Core(s) per socket", data.get("Core(s)", 1)))
    sockets = int(data.get("Socket(s)", 1))
    threads_per_core = int(data.get("Thread(s) per core", 1))
    total_cpus = int(data.get("CPU(s)", cores * sockets * threads_per_core))

    return {
        "model_name": data.get("Model name", data.get("model name", "Unknown CPU")),
        "architecture": data.get("Architecture", "Unknown"),
        "total_threads": total_cpus,
        "physical_cores": cores * sockets,
        "sockets": sockets,
        "threads_per_core": threads_per_core,
        "max_freq_mhz": float(data.get("CPU max MHz", 0)) if data.get("CPU max MHz") else None,
        "min_freq_mhz": float(data.get("CPU min MHz", 0)) if data.get("CPU min MHz") else None,
        "l3_cache": data.get("L3 cache", "Unknown"),
        "virtualization": data.get("Virtualization", "None detected"),
    }


def parse_lsblk(raw_output: str) -> Dict[str, Any]:
    """Parse lsblk -J output into structured storage devices and partition layout."""
    disks = []
    try:
        data = json.loads(raw_output)
        blockdevices = data.get("blockdevices", [])
    except json.JSONDecodeError:
        return {"error": "Failed to parse lsblk JSON", "devices": []}

    for dev in blockdevices:
        dev_type = dev.get("type", "")
        # Only inspect whole physical disks or loop devices
        if dev_type in ("disk", "rom"):
            tran = dev.get("tran") or "unknown"
            name = dev.get("name", "")
            if "nvme" in name and tran == "unknown":
                tran = "nvme"

            size_bytes = 0
            raw_size = dev.get("size", "0")
            try:
                size_bytes = int(raw_size)
            except ValueError:
                pass

            partitions = []
            for child in dev.get("children", []):
                part_size = 0
                try:
                    part_size = int(child.get("size", "0"))
                except ValueError:
                    pass
                partitions.append({
                    "name": child.get("name"),
                    "size_human": bytes_to_human(part_size) if part_size else child.get("size"),
                    "mountpoints": [m for m in child.get("mountpoints", []) if m],
                    "type": child.get("type"),
                })

            disks.append({
                "device_name": f"/dev/{name}",
                "model": dev.get("model", "Unknown Model"),
                "size_human": bytes_to_human(size_bytes) if size_bytes else dev.get("size"),
                "transport": tran.lower(),
                "is_nvme": tran.lower() == "nvme" or "nvme" in name,
                "is_rotational_hdd": dev.get("rota") == "1",
                "partitions": partitions,
            })

    return {
        "disks": disks,
        "total_disks": len(disks),
        "has_nvme": any(d["is_nvme"] for d in disks),
    }


def parse_free(raw_output: str) -> Dict[str, Any]:
    """Parse 'free -b' or 'free -m' output into memory statistics."""
    lines = [l.split() for l in raw_output.strip().splitlines() if l.strip()]
    res = {}
    for line in lines:
        if not line:
            continue
        header = line[0].rstrip(":")
        if header.lower() == "mem":
            try:
                res["total_bytes"] = int(line[1])
                res["used_bytes"] = int(line[2])
                res["free_bytes"] = int(line[3])
                res["available_bytes"] = int(line[6]) if len(line) > 6 else int(line[3])
                res["total_human"] = bytes_to_human(res["total_bytes"])
                res["available_human"] = bytes_to_human(res["available_bytes"])
            except (ValueError, IndexError):
                pass
        elif header.lower() == "swap":
            try:
                res["swap_total_bytes"] = int(line[1])
                res["swap_free_bytes"] = int(line[3]) if len(line) > 3 else 0
                res["swap_total_human"] = bytes_to_human(res["swap_total_bytes"])
            except (ValueError, IndexError):
                pass
    return res


def parse_proc_meminfo(raw_content: str) -> Dict[str, Any]:
    """Parse /proc/meminfo key-value pairs (values in kB)."""
    kv = {}
    for line in raw_content.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            # Remove 'kB' suffix and convert
            parts = v.strip().split()
            val_kb = int(parts[0]) if parts and parts[0].isdigit() else 0
            kv[k.strip()] = val_kb

    total_bytes = kv.get("MemTotal", 0) * 1024
    avail_bytes = kv.get("MemAvailable", kv.get("MemFree", 0)) * 1024

    return {
        "total_ram_bytes": total_bytes,
        "total_ram_human": bytes_to_human(total_bytes),
        "available_ram_bytes": avail_bytes,
        "available_ram_human": bytes_to_human(avail_bytes),
        "swap_total_bytes": kv.get("SwapTotal", 0) * 1024,
        "swap_free_bytes": kv.get("SwapFree", 0) * 1024,
    }


def parse_lspci(raw_output: str) -> Dict[str, Any]:
    """Parse lspci output to detect graphics, sound, and network controllers."""
    gpus = []
    current_device = {}

    for line in raw_output.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue

        # PCI bus address pattern: 00:02.0 ...
        match = re.match(r"^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])\s+(.+)", line)
        if match:
            bus_id = match.group(1)
            desc = match.group(2)
            is_graphics = any(kw in desc.lower() for kw in ["vga", "3d controller", "display controller"])
            if is_graphics:
                current_device = {
                    "bus_id": bus_id,
                    "description": desc,
                    "kernel_driver": "Unknown",
                    "subsystem": "Unknown",
                }
                gpus.append(current_device)
            else:
                current_device = {}
        elif current_device:
            if "kernel driver in use:" in line_clean.lower():
                current_device["kernel_driver"] = line_clean.split(":", 1)[1].strip()
            elif "subsystem:" in line_clean.lower():
                current_device["subsystem"] = line_clean.split(":", 1)[1].strip()

    return {
        "gpus": gpus,
        "gpu_count": len(gpus),
        "is_hybrid_graphics": len(gpus) > 1,
    }


def parse_dmidecode_memory(raw_output: str) -> Dict[str, Any]:
    """
    Parse 'dmidecode -t memory' output.
    Extracts motherboard physical memory array capacity and per-slot DIMM details.
    """
    if "permission denied" in raw_output.lower() or not raw_output.strip():
        return {
            "supported": False,
            "error": "dmidecode requires root privileges (sudo).",
        }

    max_capacity_str = "Unknown"
    num_devices = 0
    slots = []

    # Split into DMI records
    records = raw_output.split("Handle ")
    for rec in records:
        if "DMI type 16" in rec:  # Physical Memory Array
            for line in rec.splitlines():
                if "Maximum Capacity:" in line:
                    max_capacity_str = line.split(":", 1)[1].strip()
                elif "Number Of Devices:" in line:
                    try:
                        num_devices = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
        elif "DMI type 17" in rec:  # Memory Device (Slot)
            slot_info = {}
            for line in rec.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    if k in ("Size", "Type", "Speed", "Locator", "Manufacturer", "Part Number", "Form Factor"):
                        slot_info[k] = v

            if slot_info:
                is_empty = slot_info.get("Size", "").lower() in ("no module installed", "not specified")
                slots.append({
                    "locator": slot_info.get("Locator", f"Slot {len(slots)+1}"),
                    "size": "Empty" if is_empty else slot_info.get("Size", "Unknown"),
                    "type": slot_info.get("Type", "Unknown"),
                    "speed": slot_info.get("Speed", "Unknown"),
                    "manufacturer": slot_info.get("Manufacturer", "Unknown"),
                    "form_factor": slot_info.get("Form Factor", "SODIMM"),
                    "is_empty": is_empty,
                })

    populated_slots = [s for s in slots if not s["is_empty"]]
    empty_slots = [s for s in slots if s["is_empty"]]

    # Upgradability reasoning
    can_upgrade = len(empty_slots) > 0 or any("sodimm" in s.get("form_factor", "").lower() for s in populated_slots)

    return {
        "supported": True,
        "max_board_capacity": max_capacity_str,
        "total_slots": num_devices if num_devices else len(slots),
        "populated_slots_count": len(populated_slots),
        "empty_slots_count": len(empty_slots),
        "can_upgrade": can_upgrade,
        "slots_detail": slots,
        "populated_slots": populated_slots,
        "empty_slots": empty_slots,
    }

