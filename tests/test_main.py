from pathlib import Path
from typing import Sequence, Tuple

from src.agents.research_helper import NAME as RESEARCH_HELPER_NAME
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


class RequestResearchLLM:
    """Agent 0 requests research; agent 1+ share opinion (same round)."""

    def __init__(self) -> None:
        self._call_count: int = 0

    def generate(
        self,
        agent: AgentProfile,
        topic: str,
        prior_points: Sequence[str],
        round_index: int = 0,
    ) -> Tuple[str, str]:
        n = self._call_count
        self._call_count += 1
        if n == 0:
            # First agent requests research.
            return "request_research", f"{topic} latest earnings"
        # All subsequent agents (and all future rounds) share an opinion.
        return "share_opinion", f"{agent.name} view (prior={len(prior_points)})"


class StubResearchHelper:
    def proactive_research(self, topic: str, conversation: list) -> None:
        return None  # no proactive output by default

    def research(self, question: str) -> str:
        return f"Stub research on: {question}"


class ProactiveStubHelper:
    """Emits a proactive briefing every round; ignores reactive requests."""

    def proactive_research(self, topic: str, conversation: list) -> str:
        return f"Proactive briefing for: {topic}"

    def research(self, question: str) -> str:
        return f"Stub research on: {question}"


class StubFinalSynthesizer:
    def generate(self, topic: str, transcript: Sequence) -> str:
        return (
            "## Verdict\n"
            "- Stance: neutral\n"
            "- Confidence: medium\n"
            "- Time horizon: medium-term\n\n"
            "## Core Thesis\n"
            "1. Stub final thesis.\n"
        )


def test_discussion_runs_and_persists(tmp_path: Path) -> None:
    config = load_config("configs/example.yaml")
    transcript, summary, output_dir = run_discussion(
        config=config,
        topic_override="Sample topic",
        max_rounds_override=2,
        output_dir_override=str(tmp_path),
        run_name="test_run",
        llm=StubLLM(),
        research_helper=StubResearchHelper(),
        final_synthesizer=StubFinalSynthesizer(),
    )

    assert transcript, "Transcript should not be empty"
    assert summary.stance in {"bullish", "neutral", "cautious"}
    assert "## Verdict" in summary.final_report

    expected_files = {"transcript.json", "summary.json", "config_snapshot.json", "summary.md"}
    found = {p.name for p in output_dir.iterdir()}
    assert expected_files.issubset(found)
    assert "## Verdict" in (output_dir / "summary.md").read_text(encoding="utf-8")


def test_analyst_gets_follow_up_turn_after_research(tmp_path: Path) -> None:
    """After request_research the same analyst gets another generate() call."""
    config = load_config("configs/example.yaml")
    config.agents = config.agents[:1]
    call_log: list = []

    class FollowUpLLM:
        def generate(self, agent, topic, prior_points, round_index=0):
            call_log.append(len(prior_points))
            if len(call_log) == 1:
                return "request_research", f"{topic} earnings"
            return "share_opinion", f"{agent.name} reacts to research"

    transcript, _, _ = run_discussion(
        config=config,
        topic_override="Google",
        max_rounds_override=1,
        output_dir_override=str(tmp_path),
        run_name="followup_test",
        llm=FollowUpLLM(),
        research_helper=StubResearchHelper(),
        final_synthesizer=StubFinalSynthesizer(),
    )

    # generate() should have been called twice for the single analyst
    assert len(call_log) == 2, "Analyst should get a follow-up turn after requesting research"
    # Second call should see more prior_points (the request + result were appended)
    assert call_log[1] > call_log[0], "Follow-up turn should see research result in prior_points"

    opinion_msgs = [m for m in transcript if m.agent != RESEARCH_HELPER_NAME
                    and not m.content.startswith("[Research request]")]
    assert any("reacts to research" in m.content for m in opinion_msgs)


def test_consecutive_research_limit_enforced(tmp_path: Path) -> None:
    """After 2 consecutive request_research calls the analyst is cut off."""
    config = load_config("configs/example.yaml")
    config.agents = config.agents[:2]
    greedy_name = config.agents[0].name
    greedy_calls: list = []

    class GreedyAndNormalLLM:
        def generate(self, agent, topic, prior_points, round_index=0):
            if agent.name == greedy_name:
                greedy_calls.append(1)
                # Always requests research — should be capped at 2
                return "request_research", f"{topic} query {len(greedy_calls)}"
            # Second analyst shares opinion so the run can complete
            return "share_opinion", f"{agent.name} view"

    transcript, _, _ = run_discussion(
        config=config,
        topic_override="Google",
        max_rounds_override=1,
        output_dir_override=str(tmp_path),
        run_name="limit_test",
        llm=GreedyAndNormalLLM(),
        research_helper=StubResearchHelper(),
        final_synthesizer=StubFinalSynthesizer(),
    )

    requests = [m for m in transcript
                if m.content.startswith("[Research request]") and m.agent == greedy_name]
    helper_msgs = [m for m in transcript
                   if m.agent == RESEARCH_HELPER_NAME and greedy_name in m.content]

    # Exactly 2 requests fulfilled, not more
    assert len(requests) == 2, f"Expected 2 research requests, got {len(requests)}"
    assert len(helper_msgs) == 2, f"Expected 2 research results, got {len(helper_msgs)}"
    # generate() called 3 times for the greedy analyst: request, request, capped (treated as none)
    assert len(greedy_calls) == 3


def test_proactive_research_posted_before_analysts_speak(tmp_path: Path) -> None:
    config = load_config("configs/example.yaml")
    config.agents = config.agents[:1]

    first_prior_count: list = []

    class RecordingLLM:
        def generate(self, agent, topic, prior_points, round_index=0):
            first_prior_count.append(len(prior_points))
            return "share_opinion", f"{agent.name} view"

    transcript, _, _ = run_discussion(
        config=config,
        topic_override="Google",
        max_rounds_override=1,
        output_dir_override=str(tmp_path),
        run_name="proactive_test",
        llm=RecordingLLM(),
        research_helper=ProactiveStubHelper(),
        final_synthesizer=StubFinalSynthesizer(),
    )

    proactive_msgs = [
        m for m in transcript
        if m.agent == RESEARCH_HELPER_NAME and m.content.startswith("[Proactive]")
    ]
    assert proactive_msgs, "Proactive briefing should appear in transcript"
    assert "Proactive briefing for: Google" in proactive_msgs[0].content

    # The analyst must have seen the proactive message in prior_points.
    assert first_prior_count[0] >= 1, (
        "Analyst's prior_points should include the proactive briefing"
    )
