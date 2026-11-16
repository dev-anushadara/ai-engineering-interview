# 🐧 Linux Laptop Hardware Q&A Assistant

> An AI-powered conversational assistant that runs locally on a Linux laptop and answers hardware questions in plain, accessible language by calling safe, read-only system inspection tools.

---

## Table of Contents

1. [Architecture & Flow](#architecture--flow)
2. [Tool-Calling Design & Safety Allow-List](#tool-calling-design--safety-allow-list)
3. [Parsing & Normalization](#parsing--normalization)
4. [Permissions & Root Handling](#permissions--root-handling)
5. [Accuracy & Hallucination Prevention](#accuracy--hallucination-prevention)
6. [Portability Across Distros](#portability-across-distros)
7. [Privacy & Local LLMs](#privacy--local-llms)
8. [Quick Start & Usage](#quick-start--usage)
9. [Project Structure](#project-structure)

---

## Architecture & Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Hardware Q&A Assistant                          │
│                                                                        │
│    User Question: "Can I add more RAM, and how much?"                 │
│                                │                                       │
│                                ▼                                       │
│                     ┌────────────────────┐                             │
│                     │   HardwareAgent    │                             │
│                     │  (Conversation &   │                             │
│                     │   Tool Dispatch)   │                             │
│                     └─────────┬──────────┘                             │
│                               │                                        │
│               LLM Tool Call:  ▼ inspect_memory()                       │
│                     ┌────────────────────┐                             │
│                     │HardwareInspection- │                             │
│                     │     Toolkit        │                             │
│                     └─────────┬──────────┘                             │
│                               │                                        │
│          Allow-listed Command:▼ `free -b`, `/proc/meminfo`,            │
│                               │ `dmidecode -t memory`                  │
│                     ┌────────────────────┐                             │
│                     │SafeCommandExecutor │                             │
│                     │ • Strict Allow-list│                             │
│                     │ • shell=False      │                             │
│                     │ • Timeout Guards   │                             │
│                     └─────────┬──────────┘                             │
│                               │                                        │
│            Raw Output JSON/KV:▼                                        │
│                     ┌────────────────────┐                             │
│                     │  Normalized Parser │                             │
│                     │  (parsers.py)      │                             │
│                     └─────────┬──────────┘                             │
│                               │                                        │
│     Structured Hardware Fact: ▼                                        │
│     { installed: "16 GB", slots_used: 1, total_slots: 2, max: "64 GB" }│
│                               │                                        │
│                               ▼                                        │
│                     ┌────────────────────┐                             │
│                     │   LLM Response     │                             │
│                     │    Synthesizer     │                             │
│                     └─────────┬──────────┘                             │
│                               │                                        │
│                               ▼                                        │
│    "You have 16 GB in 1 of 2 slots. The board supports up to 64 GB,   │
│     so you can add a stick of up to 32 GB."                            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Tool-Calling Design & Safety Allow-List

### Why Allow-Listing Matters
Giving an LLM an open `bash` or `sh -c` tool is dangerous. A prompt injection or hallucinated command could run destructive operations (`rm -rf`, disk wipes, privilege escalations).

### The Security Model:
1. **Zero Shell Evaluation (`shell=False`)**: Every command is executed directly via `subprocess.run(["binary", "arg1"])`. Shell metacharacters (`|`, `;`, `&&`, `>`, `` ` ``) are never parsed or evaluated.
2. **Fixed Command Matrix**: The assistant can only invoke a strictly enumerated dictionary of binaries and pre-approved flag combinations:
   - `lscpu -J`
   - `lsblk -J -o NAME,SIZE,TYPE,TRAN,MOUNTPOINTS,MODEL,ROTA`
   - `free -b`
   - `lspci -nnk`, `lspci -vmm`
   - `dmidecode -t memory`, `dmidecode -t processor`
   - `uname -r`
3. **Safe File Reader**: Direct file access is restricted exclusively to specific `/proc/` and `/sys/class/power_supply/` paths using strict path normalization to eliminate directory traversal.
4. **Execution Timeouts**: All system inspections have a 5-second hard timeout to guard against hanging I/O.

---

## Parsing & Normalization

Raw command output consumes excessive LLM context and introduces noise. The assistant features dedicated parsers in [tools/parsers.py](file:///C:/Users/anush/.gemini/antigravity/scratch/hardware-assistant/tools/parsers.py):
- **`parse_lscpu`**: Converts JSON into structured physical cores, logical threads, base/boost clock frequencies, and architecture.
- **`parse_lsblk`**: Detects NVMe vs SATA transport (`tran: "nvme"`), rotational HDDs vs SSDs, capacity, and active mount points.
- **`parse_dmidecode_memory`**: Dissects SMBIOS DMI Type 16 (Physical Memory Array) and Type 17 (Memory Device) tables to calculate:
  - Motherboard maximum supported RAM capacity.
  - Number of physical slots.
  - Occupied vs. empty slots.
  - Module form factors (SODIMM vs soldered LPDDR).
- **Unit Normalization**: Automatically converts bytes to `GiB`, `TiB`, or `MiB` for consistent human comprehension.

---

## Permissions & Root Handling

### The Problem
Tools like `lscpu`, `lsblk`, `free`, and `/proc/meminfo` can be run by unprivileged users. However, reading raw DMI tables via `dmidecode` requires `CAP_SYS_RAWIO` or `root` permissions.

### Solution Architecture:
1. **Graceful Degradation**: If `dmidecode` fails with `Permission Denied`, the assistant does not crash. It provides the total installed RAM from `/proc/meminfo` and explicitly explains:
   > *"You have 16 GB installed. Motherboard slot details and maximum supported capacity require root privileges to read via dmidecode."*
2. **Non-Interactive Sudo Support**: The executor supports `sudo -n dmidecode`. If the user has configured passwordless sudo for `dmidecode`, the assistant seamlessly reads slot data.
3. **Recommended Sudoers Configuration**:
   ```bash
   # Add to /etc/sudoers.d/hardware-assistant
   %wheel ALL=(ALL) NOPASSWD: /usr/sbin/dmidecode
   ```
4. **Alternative Modern Path**: On systems with `systemd`, `systemd-dmi` or `lshw` capabilities can be used without full root escalation.

---

## Accuracy & Hallucination Prevention

1. **System Prompt Hard Grounding**:
   - The LLM is instructed: *"Only state hardware specifications that appear directly in the tool results. If a spec is missing, say 'I cannot determine this from the available system information.' Never fabricate maximum RAM or bus types."*
2. **Structured Intermediate Facts**: By feeding the LLM parsed JSON dictionaries rather than raw text dumps, ambiguity is eliminated.
3. **Context Retention for Follow-ups**:
   - User: *"How much RAM do I have?"* -> Agent calls `inspect_memory()`
   - User: *"and what about the GPU?"* -> Agent remembers the RAM conversation and calls `inspect_gpu()`

---

## Portability Across Distros

Linux distributions vary widely (Debian/Ubuntu, Fedora, Arch, Alpine, RHEL):
- **JSON Flags Preferred**: Modern `lscpu` and `lsblk` support `-J` for machine-readable JSON across all modern distros.
- **Fallback Chains**:
  - `lscpu -J` fails? -> Fallback to `/proc/cpuinfo`.
  - `lsblk -J` fails? -> Fallback to `/sys/block/`.
  - `free -b` missing? -> Fallback to `/proc/meminfo`.
- **Cross-Platform Mock Engine**: Built-in mock fixtures allow full development, testing, and CI execution on non-Linux environments (Windows, macOS, Docker).

---

## Privacy & Local LLMs

- **Data Locality**: System hardware details never need to leave the machine.
- **Pluggable LLM Backends**:
  - **Google Gemini** (via API key) for high-speed cloud reasoning.
  - **Local Deterministic Engine** (built-in, zero network access) for air-gapped or privacy-conscious users.
  - **Ollama / Local LLM Integration**: The architecture easily points to `localhost:11434` running Llama 3 / Mistral with tool-calling capabilities.

---

## Quick Start & Usage

### 1. Installation

```bash
cd hardware-assistant
pip install -r requirements.txt
```

### 2. Run the Interactive CLI

```bash
# Run with Gemini (requires GEMINI_API_KEY in .env)
python cli.py

# Run in Mock Mode (works anywhere, uses simulated ThinkPad fixtures)
python cli.py --mock

# Run completely offline (deterministic local tool engine)
python cli.py --offline
```

### 3. One-Shot Question Mode

```bash
python cli.py -q "Can I add more RAM, and how much?"
python cli.py -q "Is my SSD NVMe?"
```

### 4. Run the Automated Demo

```bash
python demo.py
```

### 5. Run the Test Suite

```bash
pytest tests/ -v
```

---

## Project Structure

```
hardware-assistant/
├── agent/
│   ├── __init__.py
│   ├── conversation.py       # Multi-turn dialog context & memory
│   └── llm.py                # HardwareAgent (Gemini tools & offline engine)
├── fixtures/
│   ├── __init__.py
│   └── linux_mock.py         # Realistic Linux laptop hardware outputs
├── tools/
│   ├── __init__.py
│   ├── executor.py           # SafeCommandExecutor (allow-list, read-only)
│   ├── parsers.py            # Structured parsers for lscpu, lsblk, dmidecode
│   └── system_tools.py       # High-level tool declarations for the LLM
├── tests/
│   ├── __init__.py
│   └── test_hardware_assistant.py  # Security & parser test suite
├── cli.py                    # Interactive terminal interface
├── main.py                   # Application entry point
├── demo.py                   # Automated demo script
├── requirements.txt
├── .env.example
└── README.md
```

---
*Built for safe, grounded Linux hardware inspection.*

