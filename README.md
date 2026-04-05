# AutoEvo-Agent

> **Automating the automation of automation.** A meta-agent framework that optimizes live SWE-agent-style self-evolution prompting via autonomous harness engineering.

This project combines three insights:

1. [**autoresearch**](https://github.com/asgaardlab/autoresearch) — The original insight: an agent that runs overnight, edits its own prompt, checks score, keeps or discards changes, repeats. (The loop that everything else builds on.)

2. [**autoagent**](https://github.com/kevinrgu/autoagent) — "Like autoresearch but for agent engineering." A meta-agent that edits the *harness* (agent.py) rather than just the prompt, enabling optimization of tools, orchestration, and agent architecture.

3. [**live-swe-agent**](https://github.com/OpenAutoCoder/live-swe-agent) — Runtime self-evolution: an agent that creates its own Python tools *while solving a task*, without waiting for an overnight meta-agent loop.

The insight: live-swe-agent shows LLMs can extend themselves at runtime. autoagent shows meta-agents can optimize harnesses automatically. **This project does both** — a meta-agent that discovers *when and how* agents should self-evolve.

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│  AutoEvo-Agent Architecture                                         │
│                                                                      │
│  Meta-Agent (overnight, autonomous)                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ • Reads program.md (directive)                              │    │
│  │ • Inspects current agent.py harness                          │    │
│  │ • Runs benchmark on tasks/                                   │    │
│  │ • Diagnoses failures                                        │    │
│  │ • Modifies agent.py (self-evolution config)                │    │
│  │ • Repeats until score plateaus                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  Agent Under Test (runtime, live)                                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ • Starts with minimal bash tool                             │    │
│  │ • Self-evolves: creates Python tools at runtime             │    │
│  │ • Decides: create tool? continue? stop evolving?           │    │
│  │ • Solves SWE-bench task                                    │    │
│  │ • Score = 0.0 or 1.0                                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker, Python 3.10+
- API keys for your LLM provider
- [Harbor](https://github.com/laude-institute/harbor) installed

### Supported Models

Uses **litellm** for provider-agnostic model access. Any litellm-supported model works:

| Provider | Model | Cost/task | tbench 2.0 Score |
|---------|-------|-----------|-------------------|
| MiniMax | minimax-m2.7 | ~$0.001 | ~42% (M2.5) |
| Anthropic | claude-sonnet-4-5 | ~$0.02 | ~40% |
| OpenAI | gpt-4o | ~$0.01 | ~50% |
| Google | gemini-2.0-flash-exp | varies | varies |
| **OpenRouter** | any model | provider rates | varies |

OpenRouter example:
```bash
export AUTOEVO_MODEL=openrouter/anthropic/claude-sonnet-4-5
# Or any OpenRouter model:
export AUTOEVO_MODEL=openrouter/mistralai/mistral-large-2411
export AUTOEVO_MODEL=openrouter/deepseek/deepseek-chat-v3-0324
```

Set via environment variable:
```bash
export AUTOEVO_MODEL=minimax/minimax-m2.7
```

### Installation

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Set up environment variables
cat > .env << 'EOF'
# For MiniMax:
MINIMAX_API_KEY=...

# For OpenRouter:
OPENROUTER_API_KEY=...

# Or any litellm-supported provider:
# ANTHROPIC_API_KEY=...
# OPENAI_API_KEY=...
EOF

# 4. Build base image
docker build -f Dockerfile.base -t autoevo-base .
```

### Running the Meta-Agent

Point your coding agent (pi, Claude Desktop, etc.) at the repo:

```
Read program.md and let's kick off a new experiment!
```

The meta-agent will:
1. Read the directive in `program.md`
2. Inspect the current `agent.py` harness
3. Run the benchmark on `tasks/`
4. Diagnose failures
5. Modify `agent.py` (specifically the `EVOLUTION_CONFIG`)
6. Repeat and hill-climb on score

### Running a Single Task Manually

```bash
# Set model
export AUTOEVO_MODEL=minimax/minimax-m2.7

# Run single task (using local tasks/ directory)
rm -rf jobs; mkdir -p jobs
uv run harbor run -p tasks/ --task-name "<task-name>" -l 1 -n 1 \
    --agent-import-path agent:AutoEvoAgentAdapter \
    -o jobs --job-name latest > run.log 2>&1

# Or run on Harbor's built-in tbench 2.0 dataset:
rm -rf jobs; mkdir -p jobs
uv run harbor run -d terminal-bench@2.0 -l 1 -n 1 \
    --agent-import-path agent:AutoEvoAgentAdapter \
    -o jobs --job-name latest > run.log 2>&1
```

### Running All Tasks

```bash
# Set model
export AUTOEVO_MODEL=minimax/minimax-m2.7

# Run all tasks in parallel (-n = concurrency)
rm -rf jobs; mkdir -p jobs
uv run harbor run -d terminal-bench@2.0 -n 10 \
    --agent-import-path agent:AutoEvoAgentAdapter \
    -o jobs --job-name latest > run.log 2>&1
```

## Project Structure

```
autoevo-agent/
├── README.md                    # This file
├── agent.py                     # Agent harness under test (single file)
│   ├── EVOLUTION_CONFIG         # ← PRIMARY EDIT SURFACE for meta-agent
│   ├── SYSTEM_PROMPT            # ← Can also be edited
│   └── tool definitions
├── program.md                   # Meta-agent instructions + directive
├── config/
│   └── livesweagent.yaml        # Base live-swe-agent config (reference)
├── tasks/                      # Benchmark tasks in Harbor format
│   └── example-task/
│       ├── task.toml
│       ├── instruction.md
│       ├── tests/
│       │   └── test.sh
│       ├── environment/
│       │   └── Dockerfile
│       └── files/
├── .agent/                      # Optional agent workspace artifacts
├── jobs/                        # Harbor job outputs
├── results.tsv                  # Experiment log (gitignored)
├── run.log                      # Latest run output
├── requirements.txt
├── pyproject.toml
└── Dockerfile.base               # Base Docker image
```

## The Evolution Config

The key optimization target is `EVOLUTION_CONFIG` in `agent.py`:

```python
EVOLUTION_CONFIG = {
    # When to trigger evolution?
    "trigger_on": [
        "repetitive_bash_patterns",    # Detected via bash history analysis
        "complexity_threshold",        # Task complexity > N
        "explicit_request",            # Agent asks for tools
    ],
    
    # What tools to create?
    "tool_patterns": [
        "grep_based_search",          # File content search
        "file_diff",                  # Compare file versions
        "test_runner",                 # Run specific tests
        "context_summarizer",          # Summarize large files
    ],
    
    # When to stop evolving?
    "stop_conditions": {
        "max_tools": 5,                # Don't create > N tools
        "tool_persistence": "task",    # Per-task or per-session
        "complexity_benefit": 0.1,      # Stop if last tool didn't improve
    },
    
    # Model prompting for evolution
    "evolution_prompt": """
        You can create custom tools in Python to help you.
        Consider creating a tool when:
        - You find yourself running the same bash commands repeatedly
        - The task requires understanding complex file structures
        - You need to extract specific patterns from code
    """,
}
```

## Design Philosophy

1. **Program the meta-agent, not the harness directly.** The human steers through `program.md`, while the meta-agent edits `agent.py`.

2. **Single-file harness.** Everything is in `agent.py` for simplicity, but structured so the harness can evolve cleanly.

3. **Docker isolation.** The agent runs in a container. It can't damage the host.

4. **Score-driven.** Every experiment produces a numeric score. Keep if better, discard if not.

5. **Self-evolution as first-class.** Unlike autoagent (which edits static tools), this optimizes *when and how* the agent should evolve itself.

## Adding Tasks

Tasks use Harbor's format. Add your own to `tasks/`:

```text
tasks/my-task/
├── task.toml           # Config (timeouts, metadata)
├── instruction.md      # Prompt sent to the agent
├── tests/
│   └── test.sh         # Entry point, writes /logs/reward.txt
├── environment/
│   └── Dockerfile      # Task container (FROM autoevo-base)
└── files/              # Reference files mounted into container
```

See [Harbor docs](https://harborframework.com/docs) for full details.

## Cleanup

```bash
# Harbor's cached task images + cache
harbor cache clean -f

# Full Docker nuke
docker system prune -a -f
```

## Benchmarks

This project supports any Harbor-format benchmark. See [benchmark-info.md](benchmark-info.md) for details.

### Recommended Benchmarks

| Benchmark | Tasks | Cost (est.) | Notes |
|-----------|-------|-------------|-------|
| [SWE-bench Lite](https://www.swebench.com/lite.html) | 300 | ~$400 | Quick, representative |
| [SpreadsheetBench](https://spreadsheetbench.github.io/) | 400-912 | ~$200-500 | Excel manipulation |
| [TerminalBench](https://www.tbench.ai/) | 80-89 | ~$100 | Terminal tasks |

### kevinrgu's Original Run (for reference)

Kevin Gu's autoagent achieved:
- **96.5%** on SpreadsheetBench (first place)
- **55.1%** on TerminalBench (top GPT-5 score)
- In **24 hours** with **~32 experiments**
- Estimated cost: **~$10,000-30,000**

## Results Tracking

```bash
# Plot progress from results.tsv
pip install matplotlib
python plot_progress.py --benchmark spreadsheet

# Manual logging
# Edit results.tsv after each experiment:
# experiment	score	change	intervention	kept
# 0	0.45	baseline	initial config	yes
# 1	0.48	+0.03	lowered threshold	yes
# 2	0.47	-0.01	removed tool	yes
```

## References

- [autoresearch](https://github.com/asgaardlab/autoresearch) — The original "meta-agent that edits itself overnight" (prompt hill-climbing)
- [autoagent](https://github.com/kevinrgu/autoagent) — "Like autoresearch but for agent engineering" (harness engineering)
- [live-swe-agent](https://github.com/OpenAutoCoder/live-swe-agent) — Runtime self-evolving SWE agent
- [Harbor](https://github.com/laude-institute/harbor) — Agent benchmark framework
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) — SWE-bench solving agent
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) — Minimal SWE-agent scaffold

## License

MIT
