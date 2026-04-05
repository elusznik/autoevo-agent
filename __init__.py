"""AutoEvo-Agent entry point."""

from agent import AutoEvoAgent, AutoEvoAgentAdapter, EVOLUTION_CONFIG, SYSTEM_PROMPT, MODEL


def main():
    """Quick test of the agent."""
    agent = AutoEvoAgent(evolution_config=EVOLUTION_CONFIG)
    print(f"AutoEvo-Agent initialized")
    print(f"Model: {MODEL}")
    print(f"Evolution triggers: {list(EVOLUTION_CONFIG['triggers'].keys())}")
    print(f"Tool templates: {[t['name'] for t in EVOLUTION_CONFIG['tool_templates']]}")
    print(f"Max tools: {EVOLUTION_CONFIG['constraints']['max_tools']}")


if __name__ == "__main__":
    main()
