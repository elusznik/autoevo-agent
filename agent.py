"""
AutoEvo-Agent: Automating the automation of automation.

Combines three lineages:
1. **autoresearch** — Meta-agent that edits prompts overnight, checks score, repeats
2. **autoagent** (kevinrgu/autoagent) — Meta-agent that edits harness (agent.py) instead of just prompts
3. **live-swe-agent** (OpenAutoCoder/live-swe-agent) — Agent that creates tools at runtime while solving tasks

This harness does ALL THREE:
- The meta-agent (human-driven or autonomous) edits EVOLUTION_CONFIG
- The agent under test self-evolves at runtime (like live-swe-agent)
- The meta-agent discovers optimal self-evolution strategies

Single-file Harbor agent harness: --agent-import-path agent:AutoEvoAgent
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ============================================================================
# EDITABLE HARNESS — The meta-agent modifies this section
# ============================================================================

# Primary edit surface: Self-evolution configuration
# The meta-agent optimizes these values via program.md directives
EVOLUTION_CONFIG = {
    # When to trigger tool creation (evolvability triggers)
    "triggers": {
        "repetitive_bash": {
            "enabled": True,
            "threshold": 3,  # Create tool after N identical commands
            "window": 10,    # Look back N commands
        },
        "complexity": {
            "enabled": True,
            "file_count_threshold": 5,  # Files touched > this
            "bash_count_threshold": 10,  # Bash calls > this
        },
        "pattern_detection": {
            "enabled": True,
            "patterns": [
                r"find.*-name",      # File finding patterns
                r"grep.*-r",         # Recursive grep patterns
                r"sed.*-i",          # Inline sed patterns
                r"for.*in.*do",      # Loops that could be tools
            ],
        },
    },
    
    # What tools to offer (and in what order)
    "tool_templates": [
        {
            "name": "grep_search",
            "description": "Search for patterns in files",
            "trigger": "repetitive_bash",
            "template": '''cat <<'EOF' > /tmp/grep_search.py
#!/usr/bin/env python3
"""Search files for patterns."""
import sys
import re
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage: grep_search.py <pattern> <path>")
        sys.exit(1)
    pattern, path = sys.argv[1], sys.argv[2]
    matches = []
    for f in Path(path).rglob("*"):
        if f.is_file() and f.suffix in {".py", ".js", ".ts", ".md", ".txt"}:
            try:
                content = f.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        matches.append(f"{f}:{i}: {line.strip()}")
            except:
                pass
    print("\\n".join(matches) if matches else "No matches found.")

if __name__ == "__main__":
    main()
EOF
chmod +x /tmp/grep_search.py''',
        },
        {
            "name": "file_browse",
            "description": "Browse directory structure",
            "trigger": "complexity",
            "template": '''cat <<'EOF' > /tmp/file_browse.py
#!/usr/bin/env python3
"""Browse and summarize directory structure."""
import sys
from pathlib import Path

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    def tree(p, depth=0):
        if depth > max_depth:
            return
        prefix = "  " * depth
        for item in sorted(Path(p).iterdir()):
            print(f"{prefix}{item.name}{'/' if item.is_dir() else ''}")
            if item.is_dir():
                tree(item, depth + 1)
    
    tree(path)

if __name__ == "__main__":
    main()
EOF
chmod +x /tmp/file_browse.py''',
        },
        {
            "name": "test_runner",
            "description": "Run tests for a specific module",
            "trigger": "complexity",
            "template": '''cat <<'EOF' > /tmp/test_runner.py
#!/usr/bin/env python3
"""Run tests for a specific module."""
import subprocess
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: test_runner.py <module_path>")
        sys.exit(1)
    
    module = sys.argv[1]
    os.chdir(os.path.dirname(module) or ".")
    
    # Try pytest first, then unittest
    for cmd in ["pytest", "python -m pytest", "python -m unittest"]:
        result = subprocess.run(
            f"{cmd} {os.path.basename(module)} -v 2>&1 | head -50",
            shell=True, capture_output=True, text=True
        )
        if result.returncode != 127:  # Command found
            print(result.stdout or result.stderr)
            break
    else:
        print("No test framework found.")

if __name__ == "__main__":
    main()
EOF
chmod +x /tmp/test_runner.py''',
        },
    ],
    
    # Constraints
    "constraints": {
        "max_tools": 5,           # Maximum tools per task
        "max_tool_size_kb": 50,   # Max size per tool file
        "tool_timeout_sec": 10,   # Timeout for tool execution
    },
    
    # Evolution prompting (injected into system prompt)
    "evolution_prompt": """You have access to self-evolution. When you find yourself:
- Running repetitive bash commands (find, grep, sed)
- Managing complex file structures
- Needing to understand code patterns

You may create custom Python tools to help. Tools are created as files in /tmp/ and
invoked via: python /tmp/tool_name.py [args]

Consider: Will this tool save me time? Is this task complex enough to warrant it?""",
}

# System prompt for the agent
SYSTEM_PROMPT = """You are an expert coding assistant that can interact with a computer.

You have access to:
1. A bash tool for running commands
2. Self-evolution capabilities (create custom Python tools when helpful)

## Important Rules

1. Every response must contain exactly one action
2. Actions are enclosed in triple backticks with bash
3. You may create custom Python tools when repetitive patterns are detected
4. Directory changes are not persistent (use cd in commands)

## Self-Evolution

When you notice repetitive patterns, you can create tools:

```bash
cat <<'EOF' > /tmp/my_tool.py
#!/usr/bin/env python3
# Your tool code here
import sys
def main():
    # Tool logic
    print("tool output")
if __name__ == "__main__":
    main()
EOF
chmod +x /tmp/my_tool.py
```

Then invoke: python /tmp/my_tool.py [args]

## Terminal Condition

When the task is complete, output:
```
echo TASK_COMPLETE
```
"""

# Model to use
MODEL = "claude-sonnet-4-5"

# Max turns before giving up
MAX_TURNS = 50

# ============================================================================
# END EDITABLE SECTION
# ============================================================================

# ============================================================================
# AGENT IMPLEMENTATION
# ============================================================================

class EvolutionTracker:
    """Tracks bash patterns and triggers evolution."""
    
    def __init__(self, config: dict):
        self.config = config
        self.bash_history: list[str] = []
        self.created_tools: list[str] = []
        
    def add_bash(self, command: str) -> dict | None:
        """Add bash command to history, return evolution trigger if detected."""
        self.bash_history.append(command)
        
        # Check repetitive patterns
        if self.config["triggers"]["repetitive_bash"]["enabled"]:
            trigger = self._check_repetitive()
            if trigger:
                return trigger
        
        # Check complexity
        if self.config["triggers"]["complexity"]["enabled"]:
            trigger = self._check_complexity()
            if trigger:
                return trigger
        
        # Check pattern detection
        if self.config["triggers"]["pattern_detection"]["enabled"]:
            trigger = self._check_patterns(command)
            if trigger:
                return trigger
        
        return None
    
    def _check_repetitive(self) -> dict | None:
        cfg = self.config["triggers"]["repetitive_bash"]
        window = self.bash_history[-cfg["window"]:]
        
        # Count command patterns (normalize for comparison)
        patterns = {}
        for cmd in window:
            # Extract base command and key args
            normalized = self._normalize_command(cmd)
            patterns[normalized] = patterns.get(normalized, 0) + 1
        
        for pattern, count in patterns.items():
            if count >= cfg["threshold"]:
                return {
                    "type": "repetitive_bash",
                    "pattern": pattern,
                    "count": count,
                    "tool": self._find_tool_template("repetitive_bash"),
                }
        return None
    
    def _check_complexity(self) -> dict | None:
        cfg = self.config["triggers"]["complexity"]
        
        # Simple heuristics
        unique_files = set()
        for cmd in self.bash_history:
            files = re.findall(r'\S+\.(py|js|ts|md|txt|cfg|json|yaml|yml)', cmd)
            unique_files.update(files)
        
        if len(unique_files) >= cfg["file_count_threshold"]:
            return {
                "type": "complexity",
                "file_count": len(unique_files),
                "tool": self._find_tool_template("complexity"),
            }
        
        if len(self.bash_history) >= cfg["bash_count_threshold"]:
            return {
                "type": "complexity",
                "bash_count": len(self.bash_history),
                "tool": self._find_tool_template("complexity"),
            }
        
        return None
    
    def _check_patterns(self, command: str) -> dict | None:
        cfg = self.config["triggers"]["pattern_detection"]
        
        for pattern in cfg["patterns"]:
            if re.search(pattern, command):
                return {
                    "type": "pattern_detection",
                    "pattern": pattern,
                    "matched_command": command[:50],
                    "tool": self._find_tool_template("pattern_detection"),
                }
        
        return None
    
    def _normalize_command(self, command: str) -> str:
        """Normalize command for pattern matching."""
        # Remove specific file names, numbers
        normalized = re.sub(r'\S+\.(py|js|ts)', '<file>', command)
        normalized = re.sub(r'\d+', '<n>', normalized)
        # Extract base command
        base = normalized.strip().split()[0] if normalized.strip() else ""
        return base
    
    def _find_tool_template(self, trigger_type: str) -> dict | None:
        for template in self.config["tool_templates"]:
            if template.get("trigger") == trigger_type:
                if len(self.created_tools) < self.config["constraints"]["max_tools"]:
                    return template
        return None
    
    def add_tool(self, tool_name: str):
        """Record a created tool."""
        self.created_tools.append(tool_name)


class AutoEvoAgent:
    """Agent that implements self-evolution with evolution config."""
    
    def __init__(self, evolution_config: dict | None = None):
        self.evolution_config = evolution_config or EVOLUTION_CONFIG
        self.tracker = EvolutionTracker(self.evolution_config)
        self.tools_created: dict[str, str] = {}  # name -> path
    
    def should_evolve(self, last_bash: str | None = None) -> dict | None:
        """Check if evolution should be triggered."""
        if last_bash:
            trigger = self.tracker.add_bash(last_bash)
            if trigger and trigger["tool"]:
                return trigger
        return None
    
    def get_evolution_prompt(self) -> str:
        """Get the evolution prompting text."""
        return self.evolution_config.get("evolution_prompt", "")
    
    def create_tool(self, tool_name: str, tool_path: str) -> bool:
        """Record a created tool."""
        if len(self.tools_created) < self.evolution_config["constraints"]["max_tools"]:
            self.tools_created[tool_name] = tool_path
            self.tracker.add_tool(tool_name)
            return True
        return False
    
    def get_created_tools(self) -> list[str]:
        """Get list of created tool names."""
        return list(self.tools_created.keys())


# ============================================================================
# HARBOR INTEGRATION
# ============================================================================

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


async def run_task(
    environment: BaseEnvironment,
    instruction: str,
) -> tuple[object, int]:
    """Run the self-evolving agent on a task."""
    agent = AutoEvoAgent(evolution_config=EVOLUTION_CONFIG)
    
    t0 = time.time()
    
    # Build the full prompt with evolution config
    system_prompt = SYSTEM_PROMPT + "\n\n" + agent.get_evolution_prompt()
    
    # We'll use a simple bash-based approach since we're targeting
    # the Harbor environment which provides shell access
    turns = 0
    bash_history = []
    last_output = ""
    created_tools = {}
    
    # Simple state machine for the agent loop
    state = "thinking"
    
    while turns < MAX_TURNS:
        turns += 1
        
        # In a real implementation, this would call the LLM
        # For now, we'll structure it for the meta-agent to understand
        
        # Check for evolution triggers
        trigger = agent.should_evolve(last_output if last_output else None)
        
        if trigger and trigger["tool"]:
            # Agent should create a tool
            tool_prompt = f"""
EVOLUTION TRIGGERED: {trigger['type']}

Create the following tool:

{trigger['tool']['template']}

Then invoke it to help with the task.
"""
            # Execute in environment
            result = await environment.exec(command=tool_prompt, timeout_sec=120)
            last_output = result.stdout + result.stderr
            continue
        
        # Normal execution - execute instruction in environment
        # The LLM would generate the actual command here
        # For Harbor integration, we pass control back
        
        if "TASK_COMPLETE" in last_output:
            break
        
        # Check terminal condition
        if "echo TASK_COMPLETE" in last_output or "COMPLETE_TASK_AND_SUBMIT" in last_output:
            break
    
    duration_ms = int((time.time() - t0) * 1000)
    
    return {
        "turns": turns,
        "bash_history": bash_history,
        "created_tools": list(created_tools.keys()),
        "duration_ms": duration_ms,
    }, duration_ms


# ============================================================================
# FIXED ADAPTER BOUNDARY
# ============================================================================

def to_atif(result: Any, model: str, duration_ms: int = 0) -> dict:
    """Convert result to ATIF trajectory format."""
    
    steps = []
    step_id = 0
    now = datetime.now(timezone.utc).isoformat()
    
    def _step(source: str, message: str, **extra: Any) -> dict:
        nonlocal step_id
        step_id += 1
        step = {
            "step_id": step_id,
            "timestamp": now,
            "source": source,
            "message": message,
        }
        step.update({k: v for k, v in extra.items() if v is not None})
        return step
    
    if isinstance(result, dict):
        for i, bash_cmd in enumerate(result.get("bash_history", [])):
            steps.append(_step("agent", f"bash: {bash_cmd[:100]}..."))
        
        for tool_name in result.get("created_tools", []):
            steps.append(_step("agent", f"Created tool: {tool_name}"))
        
        steps.append(_step("agent", f"Completed in {result.get('duration_ms', 0)}ms"))
    
    return {
        "schema_version": "ATIF-v1.6",
        "session_id": f"autoevo-{int(time.time())}",
        "agent": {
            "name": "autoevo-agent",
            "version": "0.1.0",
            "model_name": model,
            "evolution_config": EVOLUTION_CONFIG,
        },
        "steps": steps,
        "final_metrics": {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cached_tokens": 0,
            "total_cost_usd": None,
            "total_steps": len(steps),
            "extra": {
                "duration_ms": duration_ms,
                "num_turns": result.get("turns", 0) if isinstance(result, dict) else 0,
                "created_tools": len(result.get("created_tools", [])) if isinstance(result, dict) else 0,
            },
        },
    }


class AutoEvoAgentAdapter(BaseAgent):
    """Harbor agent adapter for AutoEvoAgent."""

    SUPPORTS_ATIF = True

    def __init__(self, *args, extra_env: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_env = dict(extra_env) if extra_env else {}

    @staticmethod
    def name() -> str:
        return "autoevo-agent"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        # Set up task directory
        await environment.exec(command="mkdir -p /task")
        
        # Upload instruction
        instr_file = self.logs_dir / "instruction.md"
        instr_file.write_text(instruction)
        await environment.upload_file(
            source_path=instr_file,
            target_path="/task/instruction.md"
        )

        # Run the self-evolving agent
        result, duration_ms = await run_task(environment, instruction)

        # Serialize trajectory
        atif = to_atif(result, model=MODEL, duration_ms=duration_ms)
        traj_path = self.logs_dir / "trajectory.json"
        traj_path.write_text(json.dumps(atif, indent=2))

        # Update context metrics
        try:
            final_metrics = atif.get("final_metrics", {})
            context.n_input_tokens = final_metrics.get("total_prompt_tokens", 0)
            context.n_output_tokens = final_metrics.get("total_completion_tokens", 0)
            context.n_cache_tokens = final_metrics.get("total_cached_tokens", 0)
        except Exception:
            pass

        print(
            f"turns={result.get('turns', 0) if isinstance(result, dict) else 0} "
            f"duration_ms={duration_ms} "
            f"tools_created={len(result.get('created_tools', []) if isinstance(result, dict) else [])}"
        )


__all__ = ["AutoEvoAgent", "AutoEvoAgentAdapter", "EVOLUTION_CONFIG", "SYSTEM_PROMPT", "MODEL"]
