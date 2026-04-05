#!/usr/bin/env python3
"""
Plot progress from results.tsv

Generates a progress chart like autoagent's progress.png showing:
- Running best score over experiments
- Kept experiments (improved)
- Discarded experiments (didn't improve)

Usage:
    python plot_progress.py
    python plot_progress.py --benchmark spreadsheet
    python plot_progress.py --benchmark terminal
"""

import argparse
import csv
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Plot AutoEvo-Agent progress")
    parser.add_argument("--input", "-i", default="results.tsv", help="Input TSV file")
    parser.add_argument("--output", "-o", default="progress.png", help="Output PNG file")
    parser.add_argument(
        "--benchmark", "-b", 
        choices=["spreadsheet", "terminal", "swebench", "all"],
        default="all",
        help="Benchmark to plot"
    )
    return parser.parse_args()


def read_results(path: Path):
    """Read results from TSV file."""
    experiments = []
    if not path.exists():
        return experiments
    
    with open(path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("score"):
                experiments.append({
                    "num": int(row.get("experiment", 0)),
                    "score": float(row["score"]),
                    "change": row.get("change", ""),
                    "intervention": row.get("intervention", ""),
                    "kept": row.get("kept", "").lower() in ("yes", "true", "1", "y"),
                })
    return experiments


def plot_progress(experiments, output_path, benchmark_name="benchmark"):
    """Generate progress chart."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("Error: matplotlib required. Run: pip install matplotlib")
        sys.exit(1)
    
    if not experiments:
        print(f"No data found in {args.input}")
        print("Format expected:")
        print("experiment\tscore\tchange\tintervention\tkept")
        print("0\t0.45\tbaseline\tinitial config\tyes")
        return
    
    # Calculate running best
    scores = [e["score"] for e in experiments]
    running_best = []
    best = 0.0
    for s in scores:
        best = max(best, s)
        running_best.append(best)
    
    # Separate kept vs discarded
    kept_scores = [(i, e["score"]) for i, e in enumerate(experiments) if e.get("kept")]
    discarded_scores = [(i, e["score"]) for i, e in enumerate(experiments) if not e.get("kept")]
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = list(range(len(experiments)))
    ax.plot(x, running_best, color="darkgreen" if "spreadsheet" in benchmark_name else "darkblue", 
            linewidth=2, label="Running best", zorder=3)
    
    if kept_scores:
        xi, yi = zip(*kept_scores)
        ax.scatter(xi, yi, color="green", s=80, zorder=4, label="Kept")
    
    if discarded_scores:
        xi, yi = zip(*discarded_scores)
        ax.scatter(xi, yi, color="lightgray", s=60, zorder=2, alpha=0.7, label="Discarded")
    
    # Labels
    ax.set_xlabel("Experiment #")
    ax.set_ylabel("Score")
    ax.set_title(f"AutoEvo-Agent Progress: {benchmark_name.title()}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Annotate key experiments
    for i, e in enumerate(experiments):
        if e.get("kept") and i in [0, len(experiments)//2, len(experiments)-1]:
            intervention = e.get("intervention", "")[:30]
            ax.annotate(f"Ex {i}: {intervention}", 
                       xy=(i, e["score"]), 
                       xytext=(i+1, e["score"]+0.02),
                       fontsize=8, rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Saved progress chart to {output_path}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Experiments: {len(experiments)}")
    print(f"  Baseline: {scores[0]:.1%}")
    print(f"  Best: {max(scores):.1%}")
    print(f"  Improvement: {(max(scores) - scores[0]):.1%}")
    print(f"  Kept: {len(kept_scores)}")
    print(f"  Discarded: {len(discarded_scores)}")


if __name__ == "__main__":
    args = parse_args()
    experiments = read_results(Path(args.input))
    plot_progress(experiments, args.output, args.benchmark)
