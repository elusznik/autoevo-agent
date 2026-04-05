# AutoEvo-Agent: Meta-Agent Instructions

## Overview

You are optimizing **AutoEvo-Agent**, a hybrid agent that combines three lineages:

1. [**autoresearch**](https://github.com/asgaardlab/autoresearch) — The overnight meta-agent loop: edit prompt → run eval → check score → keep/discard → repeat
2. [**autoagent**](https://github.com/kevinrgu/autoagent) — "Like autoresearch but for agent engineering." You (the meta-agent) edit `agent.py` (harness), not just prompts
3. [**live-swe-agent**](https://github.com/OpenAutoCoder/live-swe-agent) — Runtime self-evolution: the agent creates its own tools *during* task solving, not just between runs

**AutoEvo-Agent does all three**: overnight harness optimization (autoagent/autoresearch) *plus* runtime tool creation (live-swe-agent), with the meta-agent discovering optimal self-evolution strategies.

The agent under test (`agent.py`) uses an `EVOLUTION_CONFIG` dict that controls:
- When to trigger tool creation (repetitive bash, complexity thresholds, pattern detection)
- What tool templates to offer
- Constraints on tool creation (max tools, max size, etc.)
- Evolution prompting injected into the system prompt

Your job: **Hill-climb on benchmark score by editing `agent.py`** (specifically `EVOLUTION_CONFIG`).

## The Agentic Loop (Your Edit Surface)

In `agent.py`, you can modify:

### 1. `EVOLUTION_CONFIG` (PRIMARY)

```python
EVOLUTION_CONFIG = {
    # When to trigger tool creation
    "triggers": {
        "repetitive_bash": {
            "enabled": True,
            "threshold": 3,  # Create tool after N identical commands
            "window": 10,    # Look back N commands
        },
        "complexity": {
            "enabled": True,
            "file_count_threshold": 5,
            "bash_count_threshold": 10,
        },
        "pattern_detection": {
            "enabled": True,
            "patterns": [
                r"find.*-name",
                r"grep.*-r",
                # Add more patterns
            ],
        },
    },
    
    # What tools to offer
    "tool_templates": [
        {
            "name": "grep_search",
            "description": "...",
            "trigger": "repetitive_bash",
            "template": """cat <<'EOF' > /tmp/tool.py
# Tool code here
EOF""",
        },
        # Add/modify/remove tool templates
    ],
    
    # Constraints
    "constraints": {
        "max_tools": 5,
        "max_tool_size_kb": 50,
        "tool_timeout_sec": 10,
    },
    
    # Evolution prompting
    "evolution_prompt": """You can create custom tools when...
    """,
}
```

### 2. `SYSTEM_PROMPT`

The base system prompt for the agent. Can add:
- Specific guidance on when to evolve
- Tool creation examples
- Anti-patterns (when NOT to create tools)

### 3. `MODEL`

Which model to use:
- `"claude-sonnet-4-5"` (default, good balance)
- `"claude-opus-4-5"` (better but slower/expensive)
- `"gpt-4o"` (OpenAI option)

### 4. `MAX_TURNS`

Maximum agent turns before giving up. Default: 50

## Optimization Strategy

### High-Impact Changes

1. **Evolution triggers**
   - Lower `threshold` = more aggressive tool creation
   - More patterns = more triggers
   - Tradeoff: More tools = more overhead, context pressure

2. **Tool templates**
   - Add task-specific tools (test runners, formatters, etc.)
   - Improve existing templates with better error handling
   - Remove templates that don't get used

3. **Constraints**
   - `max_tools`: Too few = no evolution. Too many = context bloat
   - `max_tool_size_kb`: Larger tools = more capable but slower

4. **Evolution prompt**
   - Clearer triggers = more consistent tool creation
   - Examples = better tool quality

### Low-Risk Experiments

- Enable/disable specific triggers
- Adjust numeric thresholds by 2-3x
- Add/remove regex patterns

### High-Risk Experiments

- Completely new trigger types
- Removing all tool templates
- Changing MAX_TURNS significantly

## Running the Benchmark

### Single task:
```bash
rm -rf jobs; mkdir -p jobs
harbor run -p tasks/ --task-name "<task>" -l 1 -n 1 \
    --agent-import-path agent:AutoEvoAgent \
    -o jobs --job-name latest > run.log 2>&1
```

### All tasks:
```bash
rm -rf jobs; mkdir -p jobs
harbor run -p tasks/ -n 10 \
    --agent-import-path agent:AutoEvoAgent \
    -o jobs --job-name latest > run.log 2>&1
```

### Check results:
```bash
cat results.tsv
```

## The Experiment Loop

```
1. Edit agent.py (EVOLUTION_CONFIG or other settings)
2. Run benchmark
3. Check score (0.0 - 1.0 per task)
4. If score improved → keep change
5. If score decreased → revert change
6. Repeat with new experiments
```

## Adding New Tool Templates

Tool templates should be:
1. **Generalizable**: Work across many tasks
2. **Simple**: < 50 lines of Python
3. **Useful**: Solve real repetitive patterns

Example template structure:
```python
{
    "name": "my_tool",
    "description": "What this tool does",
    "trigger": "which trigger activates this",
    "template": '''cat <<'EOF' > /tmp/my_tool.py
#!/usr/bin/env python3
import sys
# Tool implementation
print("output")
if __name__ == "__main__":
    main()
EOF
chmod +x /tmp/my_tool.py''',
}
```

## Anti-Patterns to Avoid

1. **Don't over-evolve**: Creating tools for trivial tasks wastes time
2. **Don't under-evolve**: Ignoring obvious patterns means agent is slower
3. **Don't create huge tools**: Context bloat hurts more than help
4. **Don't forget terminal conditions**: Agent needs clear exit criteria

## Questions to Explore

- What `threshold` values work best for repetitive_bash?
- Which tool templates are most valuable across tasks?
- Should `max_tools` vary by task complexity?
- What's the optimal evolution prompt length/format?
- Do certain models benefit more from self-evolution?

## Success Metrics

Your goal: Maximize average score across tasks.

```
Baseline (no evolution): ~50% solve rate
live-swe-agent: 75.4%
AutoEvo-Agent target: > 75.4% (by optimizing evolution strategy)
```

Good experiments should improve score by > 1% on average.

## References

- [autoresearch](https://github.com/asgaardlab/autoresearch) — The original meta-agent overnight loop
- [autoagent](https://github.com/kevinrgu/autoagent) — Harness engineering (this repo's primary lineage)
- [live-swe-agent](https://github.com/OpenAutoCoder/live-swe-agent) — Runtime self-evolution (this repo's runtime layer)
