from pathlib import Path
from typing import Sequence, Tuple

from src.common.config import AgentProfile, load_config
from src.common.orchestrator import run_discussion


class StubLLM:
    def generate(
        self,
        agent: AgentProfile,
        topic: str,
        prior_points: Sequence[str],
        round_index: int = 0,
    ) -> Tuple[str, str]:
        return "share_opinion", f"{agent.name} view on {topic} after {len(prior_points)} points"


def test_discussion_runs_and_persists(tmp_path: Path) -> None:
    config = load_config("configs/example.yaml")
    transcript, summary, output_dir = run_discussion(
        config=config,
        topic_override="Sample topic",
        max_rounds_override=2,
        output_dir_override=str(tmp_path),
        run_name="test_run",
        llm=StubLLM(),
    )

    assert transcript, "Transcript should not be empty"
    assert summary.stance in {"bullish", "neutral", "cautious"}

    expected_files = {"transcript.json", "summary.json", "config_snapshot.json", "summary.md"}
    found = {p.name for p in output_dir.iterdir()}
    assert expected_files.issubset(found)
