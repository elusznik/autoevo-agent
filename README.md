# AutoEvo-Agent

> **Automating the automation of automation.** A meta-agent framework that optimizes live SWE-agent-style self-evolution prompting via autonomous harness engineering.

This project combines:
- **autoagent** (kevinrgu/autoagent): Meta-agent harness engineering — the agent that optimizes agents
- **live-swe-agent** (OpenAutoCoder/live-swe-agent): Runtime self-evolution — agents that evolve themselves while solving tasks

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

### Installation

```bash
cd ~/Work/autoevo-agent

# Install dependencies
pip install -e .

# Set up environment
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
# Or OpenAI
# OPENAI_API_KEY=sk-...
EOF

# Build Docker image
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
rm -rf jobs; mkdir -p jobs

harbor run -p tasks/ \
    --task-name "<task-name>" \
    -l 1 -n 1 \
    --agent-import-path agent:AutoEvoAgent \
    -o jobs \
    --job-name latest > run.log 2>&1
```

### Running All Tasks

```bash
rm -rf jobs; mkdir -p jobs

harbor run -p tasks/ \
    -n 10 \
    --agent-import-path agent:AutoEvoAgent \
    -o jobs \
    --job-name latest > run.log 2>&1
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

## References

- [autoagent](https://github.com/kevinrgu/autoagent) — Autonomous harness engineering
- [live-swe-agent](https://github.com/OpenAutoCoder/live-swe-agent) — Runtime self-evolving SWE agent
- [Harbor](https://github.com/laude-institute/harbor) — Agent benchmark framework
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) — SWE-bench solving agent
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) — Minimal SWE-agent scaffold

## License

MIT
