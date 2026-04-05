# Benchmark Info

## Available Benchmarks

### SWE-bench Family
| Benchmark | Tasks | Cost/Task | Full Cost | Notes |
|-----------|-------|-----------|-----------|-------|
| SWE-bench Lite | 300 | ~$1.30 | ~$390 | Quick eval |
| SWE-bench Verified Mini | 100 | ~$3.00 | ~$300 | Faster |
| SWE-bench Verified (full) | ~500 | ~$1.00 | ~$500 | Comprehensive |
| SWE-bench (full) | ~1500 | ~$1.00 | ~$1500 | Complete |

### SpreadsheetBench
| Benchmark | Tasks | Cost/Task | Full Cost | Notes |
|-----------|-------|-----------|-----------|-------|
| SpreadsheetBench (full) | 912 | ~$0.50 | ~$456 | Excel manipulation |
| SpreadsheetBench (verified) | 400 | ~$0.50 | ~$200 | Human-validated subset |

### TerminalBench
| Benchmark | Tasks | Cost/Task | Full Cost | Notes |
|-----------|-------|-----------|-----------|-------|
| TerminalBench (core) | 80 | ~$1.00 | ~$80 | Terminal tasks |
| TerminalBench 2.0 | 89 | ~$1.00 | ~$89 | Updated version |

## kevinrgu's Original Run

From the [autoagent announcement](https://github.com/kevinrgu/autoagent):

| Metric | Value |
|--------|-------|
| Duration | 24 hours |
| Experiments | ~32 |
| SpreadsheetBench | 96.5% (first place) |
| TerminalBench | 55.1% (top GPT-5 score) |
| Estimated cost | ~$10,000-30,000 |

## Cost Optimization Tips

1. **Start with subsets** — Run 20-50 tasks first to validate, then scale
2. **Use concurrency** — Harbor runs tasks in parallel (`-n 100`)
3. **Cheaper meta-agent** — Use Sonnet for the meta-agent, save Opus for task execution
4. **Early stopping** — If score plateaus for 5+ experiments, stop
5. **Incremental eval** — Run only changed tasks after first baseline

## Realistic Experiment Budget

| Scope | Tasks | Experiments | Estimated Cost |
|-------|-------|-------------|----------------|
| Quick test | 20 | 5 | ~$200 |
| Medium eval | 100 | 10 | ~$1,500 |
| Full benchmark | 300+ | 20+ | ~$5,000+ |
| Production run | 500+ | 30+ | ~$10,000+ |
