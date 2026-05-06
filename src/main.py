"""
Entry point for the multi-agent financial analysis demo.
Example: python -m src.main --config configs/example.yaml --topic "Acme Corp Q2 results"
"""

import argparse
from pathlib import Path

from src.common.config import load_config
from src.common.orchestrator import run_discussion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a multi-agent discussion over a topic.")
    parser.add_argument(
        "--config",
        default="configs/example.yaml",
        help="Path to a YAML config defining agents and run settings.",
    )
    parser.add_argument("--topic", default="", help="Override topic for this run.")
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Override max discussion rounds.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where to store run artifacts (transcript, summary).",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Optional run name; defaults to UTC timestamp.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = load_config(str(config_path))
    transcript, final_summary, output_dir = run_discussion(
        config=config,
        topic_override=args.topic,
        max_rounds_override=args.max_rounds,
        output_dir_override=args.output_dir,
        run_name=args.run_name,
    )

    print(f"Topic: {config.topic if not args.topic else args.topic}")
    print(f"Rounds executed: {1 + max(msg.round_index for msg in transcript)}")
    print(f"Final stance: {final_summary.stance}")
    print(f"Run artifacts saved to: {output_dir}")


if __name__ == "__main__":
    main()
