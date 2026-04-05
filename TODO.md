# TODO: Fix AutoEvo-Agent

## Current Status: ⚠️ BROKEN

The agent runs in Harbor but **does not complete tasks**. Last run: 0.0 score.

## What Works
- ✅ Runs with Harbor on terminal-bench@2.0
- ✅ MiniMax M2.7 tool calling works
- ✅ Bash execution in Docker container
- ✅ Self-evolution triggers (created 1 tool)

## What's Broken

### 1. Agent doesn't complete tasks

**Symptom:** Agent runs 11 turns, explores files, then says "Completed" without writing output.

**Root cause:** System prompt doesn't tell agent WHERE to write output or WHAT the success criteria is.

**Task example:**
> "Write me a dependency-free C file at /app/gpt2.c that..."

**Agent behavior:** Explored files, created a tool, then exited without writing `/app/gpt2.c`.

### 2. System prompt is unclear

Current prompt says:
```
When the task is complete, output:
echo TASK_COMPLETE
```

But it never says:
- WHERE to write the solution
- WHAT format the solution should be
- WHEN the task is actually complete

## Fixes Needed

### Priority 1: Fix system prompt

The system prompt should include:
1. "Your solution MUST be written to a specific file path (read from the task instruction)"
2. "After writing, verify your solution exists before saying TASK_COMPLETE"
3. Explicit check: `if not os.path.exists(output_path): raise Error("Solution not written")`

### Priority 2: Add verification step

Before completing, agent should:
1. Read the instruction file
2. Identify what file needs to be written
3. Verify that file exists
4. Only then say TASK_COMPLETE

### Priority 3: Improve tool templates

Current templates are too generic. Add:
- File write template
- Compile/check template  
- Test verification template

## Code Locations

| File | Purpose | Status |
|------|---------|--------|
| `agent.py` | Main harness | Needs fix |
| `program.md` | Meta-agent instructions | OK |
| `SYSTEM_PROMPT` | Agent prompt | BROKEN |

## Test Command

```bash
cd ~/Work/autoevo-agent
uv run harbor run -d terminal-bench@2.0 -l 1 -n 1 \
    --agent-import-path agent:AutoEvoAgentAdapter \
    -o jobs --job-name test
```

## Success Criteria

Agent should:
1. Read task instruction from `/task/instruction.md`
2. Identify required output file path
3. Write solution to that path
4. Verify file exists
5. Say TASK_COMPLETE

Result: Score > 0.0 on tbench
