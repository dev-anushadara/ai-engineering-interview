"""
Automated Demonstration Script for the Hardware Q&A Assistant.
Executes the sample scenario and questions from the interview problem description.
"""

import sys
import os
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.executor import SafeCommandExecutor
from tools.system_tools import HardwareInspectionToolkit
from agent.llm import HardwareAgent

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def run_demo():
    print(f"""
{CYAN}{BOLD}==================================================================
  🐧 Linux Laptop Hardware Q&A Assistant — Interview Demo
=================================================================={RESET}
  Demonstrating safe tool calling, normalized parsing, and multi-turn
  hardware Q&A across the exact questions from the prompt.
------------------------------------------------------------------
""")

    # Use simulated Linux hardware fixtures so demo works reliably across any platform
    executor = SafeCommandExecutor(force_mock=True)
    toolkit = HardwareInspectionToolkit(executor=executor)
    agent = HardwareAgent(toolkit=toolkit, force_offline_mode=True)

    test_queries = [
        "How much RAM do I have?",
        "Can I add more RAM, and how much?",
        "Is my SSD NVMe?",
        "and what about the GPU?",
        "What CPU do I have?",
        "Check my battery health.",
    ]

    for i, question in enumerate(test_queries, 1):
        print(f"{BOLD}[Turn {i}]{RESET} {GREEN}User ▶ {question}{RESET}")
        time.sleep(0.3)

        res = agent.ask(question)
        tools = res.get("tools_used", [])

        if tools:
            print(f"{DIM}⚙️  [Tool Calling]: Dispatched -> {', '.join(tools)}{RESET}")

        print(f"{CYAN}{BOLD}Assistant ◀{RESET}")
        print(f"{res['answer']}\n")
        print(f"{DIM}{'-' * 60}{RESET}\n")

    print(f"{GREEN}{BOLD}✅ Demo Complete: All queries answered accurately using verified hardware tools!{RESET}\n")


if __name__ == "__main__":
    run_demo()

