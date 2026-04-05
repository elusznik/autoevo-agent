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

Supported providers via litellm:
- anthropic: claude-sonnet-4-5, claude-opus-4-5, etc.
- openai: gpt-4o, gpt-5, etc.
- minimax: minimax-m2, minimax-m2.7, etc.
- google: gemini-2.0-flash, gemini-3-flash, etc.
- fireworks: fireworks_ai models
- together: together_ai models
- ollama: local models

Example MODEL values:
- "anthropic/claude-sonnet-4-5"
- "openai/gpt-4o"
- "minimax/minimax-m2.7"
- "google/gemini-2.0-flash-exp"
- "ollama/llama3"
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

# Model configuration
# Format: "provider/model-name" (litellm format)
# See litellm documentation for full list of supported models
#
# Recommended models (April 2026):
#   - "minimax/minimax-m3" (cheapest, latest MiniMax)
#   - "google/gemini-3.1-pro" (SOTA, Gemini 3.1)
#   - "anthropic/claude-sonnet-4-6" (Claude Sonnet 4.6)
#   - "anthropic/claude-opus-4-6" (Claude Opus 4.6, expensive)
#   - "openai/gpt-5.4" (GPT-5.4, latest)
#   - "x-ai/grok-4.20" (Grok 4.20)
#   - "deepseek/deepseek-3.2" (DeepSeek 3.2)
#
# Free options (rate limited):
#   - "openrouter/qwen/qwen3.6-plus:free"
MODEL = os.environ.get("AUTOEVO_MODEL", "minimax/minimax-m2.7")

# Model-specific settings
MODEL_SETTINGS = {
    # Temperature for generation
    "temperature": 0.0,
    # Max tokens to generate
    "max_tokens": 4096,
    # Thinking/reasoning settings (provider-specific)
    "thinking": None,  # Set to {"type": "enabled", "budget_tokens": 10000} for Anthropic
}

# Max turns before giving up
MAX_TURNS = 50

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

# ============================================================================
# AGENT IMPLEMENTATION
# ============================================================================

# Import litellm for model calls
try:
    import litellm
    litellm.drop_params = True  # Allow extra params like 'thinking'
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    print("Warning: litellm not installed. Run: pip install litellm")


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
        normalized = re.sub(r'\S+\.(py|js|ts)', '<file>', command)
        normalized = re.sub(r'\d+', '<n>', normalized)
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
    
    def __init__(self, evolution_config: dict | None = None, model: str = MODEL, model_settings: dict | None = None):
        self.evolution_config = evolution_config or EVOLUTION_CONFIG
        self.model = model
        self.model_settings = model_settings or MODEL_SETTINGS
        self.tracker = EvolutionTracker(self.evolution_config)
        self.tools_created: dict[str, str] = {}
        self.conversation_history: list[dict] = []
    
    def get_system_prompt(self) -> str:
        """Get the full system prompt with evolution config."""
        return SYSTEM_PROMPT + "\n\n" + self.evolution_config.get("evolution_prompt", "")
    
    def should_evolve(self, last_bash: str | None = None) -> dict | None:
        """Check if evolution should be triggered."""
        if last_bash:
            return self.tracker.add_bash(last_bash)
        return None
    
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
    
    def call_model(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """
        Call the LLM via litellm.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            
        Returns:
            Response dict with 'content', 'tool_calls', etc.
        """
        if not LITELLM_AVAILABLE:
            raise RuntimeError("litellm not available. Install with: pip install litellm")
        
        # Build litellm params
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.model_settings.get("temperature", 0.0),
            "max_tokens": self.model_settings.get("max_tokens", 4096),
        }
        
        # Add thinking if supported and configured
        thinking = self.model_settings.get("thinking")
        if thinking:
            params["thinking"] = thinking
        
        # Add tools if provided
        if tools:
            params["tools"] = tools
        
        # Make the call
        response = litellm.completion(**params)
        
        return response
    
    def format_tool_result(self, tool_name: str, result: str) -> dict:
        """Format a tool result for the conversation."""
        return {
            "role": "tool",
            "content": result,
            "tool_call_id": tool_name,  # Simplified - real impl would use actual IDs
        }


# ============================================================================
# HARBOR INTEGRATION
# ============================================================================

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


def create_bash_tool(environment: BaseEnvironment):
    """Create a bash tool that runs commands in the Harbor environment."""
    async def run_bash(command: str, timeout: int = 120) -> str:
        try:
            result = await environment.exec(command=command, timeout_sec=timeout)
            out = ""
            if result.stdout:
                out += result.stdout
            if result.stderr:
                out += f"\nSTDERR:\n{result.stderr}"
            return out or "(no output)"
        except Exception as exc:
            return f"ERROR: {exc}"
    return run_bash


async def run_task(
    environment: BaseEnvironment,
    instruction: str,
    model: str = MODEL,
    max_turns: int = MAX_TURNS,
) -> tuple[dict, int]:
    """
    Run the self-evolving agent on a task.
    
    Args:
        environment: Harbor environment for executing commands
        instruction: Task instruction
        model: Model to use (e.g., "minimax/minimax-m2.7")
        max_turns: Maximum number of turns
        
    Returns:
        Tuple of (result_dict, duration_ms)
    """
    if not LITELLM_AVAILABLE:
        raise RuntimeError("litellm not available. Install with: pip install litellm")
    
    agent = AutoEvoAgent(
        evolution_config=EVOLUTION_CONFIG,
        model=model,
        model_settings=MODEL_SETTINGS,
    )
    
    t0 = time.time()
    
    # Build initial messages
    messages = [
        {"role": "system", "content": agent.get_system_prompt()},
        {"role": "user", "content": instruction},
    ]
    
    # Define bash tool for litellm
    bash_tool = {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command. Returns stdout and stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 120)",
                    },
                },
                "required": ["command"],
            },
        },
    }
    
    bash = create_bash_tool(environment)
    turns = 0
    bash_history = []
    created_tools = {}
    
    while turns < max_turns:
        turns += 1
        
        # Call the model
        try:
            response = agent.call_model(messages, tools=[bash_tool])
        except Exception as e:
            messages.append({
                "role": "assistant",
                "content": f"Error calling model: {e}",
            })
            break
        
        # Extract response
        if hasattr(response, "choices"):
            choice = response.choices[0]
            message = choice.message
            
            # Handle tool calls
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    func = tool_call.function
                    messages.append({
                        "role": "assistant",
                        "content": "",  # May have text before tool call
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": func.name,
                                "arguments": func.arguments,
                            },
                        }],
                    })
                    
                    # Execute tool
                    try:
                        args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                        command = args.get("command", "")
                        timeout = args.get("timeout", 120)
                        
                        result = await bash(command, timeout)
                        bash_history.append(command)
                        
                        # Check for evolution triggers
                        trigger = agent.should_evolve(command)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        })
                        
                        # If evolution triggered and we have a tool template
                        if trigger and trigger.get("tool"):
                            tool = trigger["tool"]
                            # Agent would create the tool here
                            created_tools[tool["name"]] = tool["template"]
                            agent.create_tool(tool["name"], f"/tmp/{tool['name']}.py")
                            
                            messages.append({
                                "role": "system",
                                "content": f"[EVOLUTION] Created tool: {tool['name']}",
                            })
                        
                        # Check for completion
                        if "TASK_COMPLETE" in result or "COMPLETE_TASK_AND_SUBMIT" in result:
                            break
                            
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error executing tool: {e}",
                        })
            else:
                # Text response
                content = message.content or ""
                messages.append({
                    "role": "assistant",
                    "content": content,
                })
                
                # Check for completion
                if "TASK_COMPLETE" in content:
                    break
        
        # Check for excessive turns without progress
        if turns >= max_turns:
            messages.append({
                "role": "system",
                "content": f"Max turns ({max_turns}) reached. Task incomplete.",
            })
            break
    
    duration_ms = int((time.time() - t0) * 1000)
    
    return {
        "turns": turns,
        "bash_history": bash_history,
        "created_tools": list(created_tools.keys()),
        "duration_ms": duration_ms,
        "model": model,
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
            "total_prompt_tokens": 0,  # Could track via litellm
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

        # Get model from environment or use default
        model = os.environ.get("AUTOEVO_MODEL", MODEL)
        
        # Run the self-evolving agent
        result, duration_ms = await run_task(
            environment,
            instruction,
            model=model,
            max_turns=MAX_TURNS,
        )

        # Serialize trajectory
        atif = to_atif(result, model=model, duration_ms=duration_ms)
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
            f"turns={result.get('turns', 0)} "
            f"duration_ms={duration_ms} "
            f"tools_created={len(result.get('created_tools', []))}"
        )


__all__ = [
    "AutoEvoAgent",
    "AutoEvoAgentAdapter", 
    "EVOLUTION_CONFIG",
    "SYSTEM_PROMPT",
    "MODEL",
    "MODEL_SETTINGS",
    "run_task",
]
