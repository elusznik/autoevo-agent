# Agent Workspace

This directory contains artifacts for the agent's workspace.

## Purpose

The meta-agent can use this directory to:
- Store notes about experiments
- Keep track of successful configurations
- Save diagnostic observations

## Structure

```
.agent/
├── notes.md           # Agent's working notes
├── prompts/           # Saved prompt variations
└── results/           # Analysis of past runs
```

## Notes

- The meta-agent writes here during experiments
- Human can review contents but doesn't need to manage
- Useful for debugging failed experiments
