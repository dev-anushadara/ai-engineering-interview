"""
Interactive Terminal CLI for the Linux Hardware Q&A Assistant.
Features real-time tool inspection indicators, rich formatting, and conversational turns.
"""

import sys
import argparse
import os
from typing import Optional
from dotenv import load_dotenv

from tools.executor import SafeCommandExecutor
from tools.system_tools import HardwareInspectionToolkit
from agent.llm import HardwareAgent

load_dotenv()

# ANSI Color codes for friendly, dependency-free terminal styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def print_banner(is_mock: bool, backend: str):
    mode_label = f"{YELLOW}[MOCK MODE]{RESET}" if is_mock else f"{GREEN}[LIVE SYSTEM]{RESET}"
    print(f"""
{CYAN}{BOLD}==================================================================
  🐧 Linux Laptop Hardware Q&A Assistant
=================================================================={RESET}
  Mode:    {mode_label}
  Backend: {MAGENTA}{backend}{RESET}
  Commands: Type {BOLD}/help{RESET} for options, {BOLD}/tools{RESET} to see tools, or {BOLD}/exit{RESET} to quit.
------------------------------------------------------------------
""")


def print_help():
    print(f"""
{BOLD}Available Commands:{RESET}
  {CYAN}/help{RESET}    - Show this help message
  {CYAN}/tools{RESET}   - List available system inspection tools & allow-listed commands
  {CYAN}/summary{RESET} - Display a full snapshot of machine hardware
  {CYAN}/clear{RESET}   - Clear conversation history
  {CYAN}/exit{RESET}    - Exit the assistant

{BOLD}Sample Questions to Try:{RESET}
  • "How much RAM do I have, and can I add more?"
  • "Is my SSD NVMe?"
  • "What CPU is installed, and how many cores does it have?"
  • "What about the GPU?"
  • "Check my battery health."
""")


def print_tools_info(toolkit: HardwareInspectionToolkit):
    print(f"""
{BOLD}Allow-listed System Tools:{RESET}
  1. {CYAN}inspect_cpu(){RESET}        -> Executes: `lscpu -J` (Fallback: `/proc/cpuinfo`)
  2. {CYAN}inspect_memory(){RESET}     -> Executes: `free -b`, `/proc/meminfo`, `dmidecode -t memory`
  3. {CYAN}inspect_storage(){RESET}    -> Executes: `lsblk -J -o NAME,SIZE,TYPE,TRAN,MOUNTPOINTS,MODEL,ROTA`
  4. {CYAN}inspect_gpu(){RESET}        -> Executes: `lspci -nnk` (Fallback: `lspci -vmm`)
  5. {CYAN}inspect_battery(){RESET}    -> Reads: `/sys/class/power_supply/BAT*/`
  6. {CYAN}inspect_system_summary(){RESET} -> High-level snapshot of kernel, CPU, RAM, and disks

{DIM}Safety guarantee: Zero arbitrary shell execution. No subshells, no redirections.{RESET}
""")


def run_cli():
    parser = argparse.ArgumentParser(description="Linux Laptop Hardware Q&A Assistant")
    parser.add_argument("--mock", action="store_true", help="Force mock Linux laptop fixtures (useful on Windows/macOS or CI)")
    parser.add_argument("--offline", action="store_true", help="Force offline deterministic tool runner without calling Gemini API")
    parser.add_argument("--system-info", action="store_true", help="Print structured system hardware dump and exit")
    parser.add_argument("--question", "-q", type=str, help="Ask a single question non-interactively and exit")
    args = parser.parse_args()

    # Determine mock status
    is_linux = sys.platform.startswith("linux")
    force_mock = args.mock or (not is_linux)

    executor = SafeCommandExecutor(force_mock=force_mock)
    toolkit = HardwareInspectionToolkit(executor=executor)

    if args.system_info:
        import pprint
        print("\n--- [System Hardware Summary Dump] ---")
        pprint.pprint(toolkit.inspect_system_summary())
        return

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    backend_name = "Offline Deterministic" if (args.offline or not gemini_key) else "Google Gemini (gemini-1.5-flash)"

    agent = HardwareAgent(
        toolkit=toolkit,
        gemini_api_key=gemini_key if not args.offline else None,
        force_offline_mode=args.offline,
    )

    # One-shot CLI question mode
    if args.question:
        result = agent.ask(args.question)
        print(f"\n{BOLD}Q:{RESET} {args.question}")
        if result["tools_used"]:
            print(f"{DIM}[Tools called: {', '.join(result['tools_used'])}]{RESET}")
        print(f"\n{result['answer']}\n")
        return

    # Interactive REPL
    print_banner(is_mock=force_mock, backend=backend_name)

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}User ▶ {RESET}").strip()
            if not user_input:
                continue

            # Command handling
            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                print(f"\n{CYAN}Goodbye! 👋{RESET}")
                break
            elif user_input.lower() == "/help":
                print_help()
                continue
            elif user_input.lower() == "/tools":
                print_tools_info(toolkit)
                continue
            elif user_input.lower() == "/summary":
                res = agent.ask("Give me a complete hardware summary of this laptop.")
                print(f"\n{CYAN}{BOLD}Assistant ◀{RESET}\n{res['answer']}\n")
                continue
            elif user_input.lower() == "/clear":
                agent.session.clear()
                print(f"{DIM}Conversation memory cleared.{RESET}\n")
                continue

            # Send question to agent
            res = agent.ask(user_input)

            # Show tool transparency
            if res.get("tools_used"):
                tools_str = ", ".join(f"`{t}`" for t in res["tools_used"])
                print(f"{DIM}⚙️  Tools queried: {tools_str}{RESET}")

            print(f"\n{CYAN}{BOLD}Assistant ◀{RESET}\n{res['answer']}\n")

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{CYAN}Session ended. Bye!{RESET}")
            break


if __name__ == "__main__":
    run_cli()

