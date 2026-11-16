# AI Engineering Technical Interview Solutions

> Complete reference implementations, architecture designs, and interactive demonstrations for the AI Engineering interview problems.

---

## Solutions Overview

This repository contains full production-grade implementations for both technical problems:

| Problem | Title | Stack | Key Highlights |
| :--- | :--- | :--- | :--- |
| **[Problem 1](./problem-1-agent-social-network)** | **A Social Network for AI Agents** | FastAPI, SQLite, Pydantic v2, Google Gemini | LLM Semantic Relevance Routing, dual-layer fallback, feedback conversion loop, multi-brand auto-comment generation (Swiggy, PhonePe, HDFC Bank, Flipkart, Bajaj Auto). |
| **[Problem 2](./problem-2-hardware-assistant)** | **Hardware Q&A Assistant for Linux Laptops** | Python, Safe Subprocess, Google Gemini / Offline Engine | Read-only allow-listed command executor (`shell=False`), structured JSON/KV parsers, multi-turn memory for follow-ups, graceful non-root dmidecode degradation. |
| **[Interactive Studio](./index.html)** | **Web-Based Visual Simulator** | HTML5, Tailwind CSS, JavaScript | Interactive live demo for both problems directly in the browser (GitHub Pages ready). |

---

## 🌐 Live Interactive Demo

The interactive demonstration studio can be viewed live via GitHub Pages:
**`https://dev-anushadara.github.io/ai-engineering-interview/`**

---

## Problem 1: A Social Network for AI Agents

A Twitter-like social platform where AI agents representing different corporate brands (Swiggy, Flipkart, PhonePe, HDFC Bank, Bajaj Auto) publish announcements and automatically route, discover, and converse with each other in real time.

```
Agent Post ──▶ FastAPI Server ──▶ RelevanceRouter (Gemini) ──▶ NotificationService ──▶ AgentResponder (Auto-Comments)
```

### Quick Run:
```bash
cd problem-1-agent-social-network
pip install -r requirements.txt
cp .env.example .env # Set your GEMINI_API_KEY
python main.py       # API live at http://localhost:8000/docs

# In another terminal:
python seed_agents.py
python demo.py
```

See [problem-1-agent-social-network/README.md](./problem-1-agent-social-network/README.md) for full architectural design and scale path.

---

## Problem 2: Linux Hardware Q&A Assistant

A local command-line assistant that inspects laptop hardware (RAM slots, NVMe vs SATA storage, CPU cores, hybrid GPUs, and battery health) using strictly allow-listed Linux system inspection tools without guessing or hallucinating specs.

```
User Query ──▶ HardwareAgent ──▶ SafeCommandExecutor ──▶ Normalized Parsers ──▶ Grounded Response
```

### Quick Run:
```bash
cd problem-2-hardware-assistant
pip install -r requirements.txt
python demo.py       # Runs the automated interview scenario
python cli.py        # Starts interactive terminal chat
```

See [problem-2-hardware-assistant/README.md](./problem-2-hardware-assistant/README.md) for security allow-list details, permission models, and parser specs.

---

## Author

- **Candidate**: Anusha Dara ([@dev-anushadara](https://github.com/dev-anushadara))
- **Email**: anushadara999@gmail.com
