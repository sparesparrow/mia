"""
CLI entry point for the AI Self-Improvement Orchestrator.

Usage examples
──────────────
# Run up to 20 cycles autonomously until convergence
python -m orchestration.ai_self_improvement run --max-cycles 20

# Run exactly one cycle
python -m orchestration.ai_self_improvement run --max-cycles 1

# Show current status (no cycles run)
python -m orchestration.ai_self_improvement status

# Reset state (keep knowledge base)
python -m orchestration.ai_self_improvement reset

# Full reset including knowledge base
python -m orchestration.ai_self_improvement reset --wipe-kb
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from .orchestrator import AISelfImprovementOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m orchestration.ai_self_improvement",
        description="AI Self-Improvement Orchestrator — autonomous firmware compliance loop",
    )
    parser.add_argument(
        "--kb",
        metavar="PATH",
        type=Path,
        default=None,
        help="Override knowledge base JSON path",
    )
    parser.add_argument(
        "--state",
        metavar="PATH",
        type=Path,
        default=None,
        help="Override orchestrator state JSON path",
    )
    parser.add_argument(
        "--no-intelligent-routing",
        action="store_true",
        default=False,
        help="Disable intelligent worst-metric routing; use fixed target rotation",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ──────────────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Run improvement cycles autonomously")
    run_p.add_argument(
        "--max-cycles",
        metavar="N",
        type=int,
        default=50,
        help="Maximum number of cycles to run (default: 50)",
    )
    run_p.add_argument(
        "--patience",
        metavar="N",
        type=int,
        default=5,
        help="Consecutive converged cycles before stopping (default: 5)",
    )
    run_p.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress per-cycle template output",
    )
    run_p.add_argument(
        "--save-history",
        metavar="PATH",
        type=Path,
        default=None,
        help="Write full cycle history JSON to this file after run",
    )

    # ── status ───────────────────────────────────────────────────────
    sub.add_parser("status", help="Print current orchestrator status and exit")

    # ── reset ────────────────────────────────────────────────────────
    reset_p = sub.add_parser("reset", help="Reset orchestrator state")
    reset_p.add_argument(
        "--wipe-kb",
        action="store_true",
        default=False,
        help="Also erase the knowledge base (all learned patterns)",
    )

    return parser


def _make_orchestrator(args: argparse.Namespace) -> AISelfImprovementOrchestrator:
    kwargs: dict = {
        "intelligent_routing": not args.no_intelligent_routing,
    }
    if args.kb:
        kwargs["knowledge_base_path"] = args.kb
    if args.state:
        kwargs["state_path"] = args.state
    return AISelfImprovementOrchestrator(**kwargs)


async def _cmd_run(args: argparse.Namespace) -> int:
    orchestrator = _make_orchestrator(args)
    print(
        f"\n🚀 Starting autonomous loop — "
        f"max_cycles={args.max_cycles}, patience={args.patience}, "
        f"intelligent_routing={not args.no_intelligent_routing}\n"
    )

    history = await orchestrator.run_autonomous(
        max_cycles=args.max_cycles,
        convergence_patience=args.patience,
        verbose=not args.quiet,
    )

    # Summary
    final = history[-1] if history else None
    if final:
        m = final.metrics_after
        converged = m.meets_all_targets()
        print("\n" + "═" * 60)
        print(f"  Cycles completed : {len(history)}")
        print(f"  Converged        : {'✅ YES' if converged else '❌ not yet'}")
        print(f"  Success Rate     : {m.success_rate * 100:.1f}%  (target ≥90%)")
        print(f"  Coverage         : {m.coverage * 100:.1f}%  (target ≥95%)")
        print(f"  Quality Score    : {m.quality_score:.1f}/100  (target ≥85)")
        print(f"  Efficiency       : {m.efficiency * 100:.1f}%  (target ≥90%)")
        print(f"  Error Rate       : {m.error_rate * 100:.1f}%  (target ≤5%)")
        print(f"  KB Patterns      : {orchestrator.kb.get_statistics()['total_patterns']}")
        print("═" * 60 + "\n")

    if args.save_history:
        args.save_history.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_history, "w") as fh:
            json.dump([c.to_dict() for c in history], fh, indent=2)
        print(f"History saved → {args.save_history}")

    return 0 if (final and final.metrics_after.meets_all_targets()) else 1


def _cmd_status(args: argparse.Namespace) -> int:
    orchestrator = _make_orchestrator(args)
    s = orchestrator.status()
    print(json.dumps(s, indent=2))
    return 0


def _cmd_reset(args: argparse.Namespace) -> int:
    orchestrator = _make_orchestrator(args)
    orchestrator.reset(reset_knowledge_base=args.wipe_kb)
    kb_msg = " + knowledge base" if args.wipe_kb else ""
    print(f"✅ Orchestrator state{kb_msg} reset.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return asyncio.run(_cmd_run(args))
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "reset":
        return _cmd_reset(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
