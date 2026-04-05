#!/bin/bash
# Run AutoEvo-Agent on Terminal-Bench 2.0 using Harbor
#
# Usage:
#   ./run_eval.sh                    # Run with default model (MiniMax M2.7)
#   ./run_eval.sh --model anthropic/claude-sonnet-4-5
#   ./run_eval.sh --model openai/gpt-4o
#   ./run_eval.sh --n 10             # Run 10 tasks
#
# Environment variables:
#   AUTOEVO_MODEL=minimax/minimax-m2.7
#   MINIMAX_API_KEY=...
#   ANTHROPIC_API_KEY=...
#   OPENAI_API_KEY=...
#
# Requirements:
#   - Docker running
#   - API keys set (depending on model)
#   - pip install -r requirements.txt

set -e

# Default settings
N_CONCURRENT="${N_CONCURRENT:-4}"
DATASET="terminal-bench@2.0"
MODEL="${AUTOEVO_MODEL:-minimax/minimax-m2.7}"
AGENT="autoevo-agent"
N_TASKS="${N_TASKS:-}"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --n)
            N_TASKS="--n $2"
            shift 2
            ;;
        --model|-m)
            MODEL="$2"
            shift 2
            ;;
        --concurrent)
            N_CONCURRENT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "  --model <name>   Model to use (default: minimax/minimax-m2.7)"
            echo "  --n <num>       Number of tasks to run (default: all)"
            echo "  --concurrent <n> Concurrent tasks (default: 4)"
            echo ""
            echo "Supported models:"
            echo "  minimax/minimax-m2.7       (cheapest, ~\$0.001/task)"
            echo "  anthropic/claude-sonnet-4-5 (Claude Sonnet 4)"
            echo "  openai/gpt-4o             (GPT-4o)"
            echo "  google/gemini-2.0-flash-exp"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# Install dependencies if needed
if ! pip show harbor > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check API key based on provider
PROVIDER="${MODEL%%/*}"
case "$PROVIDER" in
    minimax)
        if [ -z "$MINIMAX_API_KEY" ]; then
            echo "Warning: MINIMAX_API_KEY not set"
        fi
        ;;
    anthropic)
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "Warning: ANTHROPIC_API_KEY not set"
        fi
        ;;
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "Warning: OPENAI_API_KEY not set"
        fi
        ;;
    google)
        if [ -z "$GOOGLE_API_KEY" ]; then
            echo "Warning: GOOGLE_API_KEY not set"
        fi
        ;;
esac

# Set up results directory
RESULTS_DIR="results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "============================================"
echo "AutoEvo-Agent Evaluation"
echo "============================================"
echo "Dataset:     $DATASET"
echo "Agent:      $AGENT"
echo "Model:      $MODEL"
echo "Concurrent: $N_CONCURRENT"
echo "Tasks:      ${N_TASKS:-all}"
echo "Results:    $RESULTS_DIR"
echo "============================================"

# Export model for agent
export AUTOEVO_MODEL="$MODEL"

# Run the evaluation
harbor run \
    --dataset "$DATASET" \
    --agent "$AGENT" \
    --agent-import-path "agent:AutoEvoAgentAdapter" \
    --model "$MODEL" \
    --n-concurrent "$N_CONCURRENT" \
    $N_TASKS \
    --output-dir "$RESULTS_DIR" \
    2>&1 | tee "$RESULTS_DIR/run.log"

# Calculate score
echo ""
echo "============================================"
echo "Results Summary"
echo "============================================"

if [ -f "$RESULTS_DIR/results.json" ]; then
    cat "$RESULTS_DIR/results.json"
elif [ -f "$RESULTS_DIR/summary.json" ]; then
    cat "$RESULTS_DIR/summary.json"
else
    echo "Results file not found. Check $RESULTS_DIR/"
fi
