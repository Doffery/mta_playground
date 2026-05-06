import dataclasses
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.agents.research_helper import NAME as RESEARCH_HELPER_NAME, ResearchHelper
from src.common.config import AgentProfile, RunConfig, resolve_output_dir
from src.common.llm import LiteLLMAnalyst


@dataclass
class AgentMessage:
    agent: str
    round_index: int
    content: str


@dataclass
class RoundSummary:
    round_index: int
    stance: str
    key_points: Dict
    final_report: str = ""


def _derive_stance(topic: str, round_index: int) -> str:
    labels = ["bullish", "neutral", "cautious"]
    return labels[(len(topic) + round_index) % len(labels)]


def _aggregate_round(topic: str, round_index: int, messages: Sequence[AgentMessage]) -> RoundSummary:
    stance = _derive_stance(topic, round_index)
    key_points = {msg.agent: msg.content for msg in messages}
    return RoundSummary(round_index=round_index, stance=stance, key_points=key_points)


def _has_converged(history: Sequence[RoundSummary]) -> bool:
    if len(history) < 2:
        return False
    return history[-1].stance == history[-2].stance


def _timestamp_slug() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


_MAX_CONSECUTIVE_RESEARCH = 2


FINAL_REPORT_PROMPT = """\
You are the final synthesizer for a multi-agent financial analysis discussion.
Read the full transcript and produce a concise structured markdown report.

Topic:
{topic}

Transcript:
{transcript}

Use exactly this structure:

## Verdict
- Stance: bullish | neutral | cautious | bearish
- Confidence: low | medium | high
- Time horizon: short-term | medium-term | long-term

## Core Thesis
1. Main reason supporting the verdict.
2. Second most important reason.
3. Third most important reason.

## Where Analysts Agree
- Shared point 1
- Shared point 2

## Where Analysts Disagree
- Disagreement 1: who disagreed and why
- Disagreement 2: who disagreed and why

## Evidence Used
- Research/helper finding or metric 1
- Research/helper finding or metric 2
- Important caveat about evidence quality

## Key Risks
- Risk 1
- Risk 2
- Risk 3

## Watch Items
- Upcoming event, metric, or condition to monitor
- Trigger that would change the view

## Analyst Takeaways
- `analyst_name`: one-sentence takeaway
"""


class FinalSynthesizer:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def generate(self, topic: str, transcript: Sequence[AgentMessage]) -> str:
        from src.common.llm import complete

        transcript_text = "\n\n".join(
            f"[Round {message.round_index + 1}] {message.agent}: {message.content}"
            for message in transcript
        )
        response = complete(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": FINAL_REPORT_PROMPT.format(
                        topic=topic,
                        transcript=transcript_text,
                    ),
                }
            ],
        )
        return response.choices[0].message.content.strip()


def run_discussion(
    config: RunConfig,
    topic_override: str = "",
    max_rounds_override: Optional[int] = None,
    output_dir_override: Optional[str] = None,
    run_name: Optional[str] = None,
    llm: Optional[Any] = None,
    research_helper: Optional[Any] = None,
    final_synthesizer: Optional[Any] = None,
    on_message: Optional[Callable[[AgentMessage], None]] = None,
) -> Tuple[List[AgentMessage], RoundSummary, Path]:
    topic = topic_override or config.topic
    max_rounds = max_rounds_override or config.run.max_rounds
    run_label = run_name or _timestamp_slug()
    output_root = resolve_output_dir(output_dir_override or config.run.output_dir, run_label)
    output_root.mkdir(parents=True, exist_ok=True)

    llm = llm or LiteLLMAnalyst(model_name=config.model_name)
    _helper = research_helper or ResearchHelper(model_name=config.model_name)
    _synthesizer = final_synthesizer or FinalSynthesizer(model_name=config.model_name)
    agents = list(config.agents)

    transcript: List[AgentMessage] = []
    summaries: List[RoundSummary] = []

    for round_index in range(max_rounds):
        round_messages: List[AgentMessage] = []
        all_actions: List[str] = []
        any_research: bool = False

        # Proactive phase: research_helper surfaces context before analysts speak.
        conversation = [f"{msg.agent}: {msg.content}" for msg in transcript]
        proactive_report = _helper.proactive_research(topic=topic, conversation=conversation)
        if proactive_report:
            proactive_msg = AgentMessage(
                agent=RESEARCH_HELPER_NAME,
                round_index=round_index,
                content=f"[Proactive] {proactive_report}",
            )
            transcript.append(proactive_msg)
            any_research = True
            if on_message is not None:
                on_message(proactive_msg)

        for agent in agents:
            consecutive_research = 0

            while True:
                # Agent sees all messages committed so far, including results from
                # its own earlier requests in this same turn.
                prior_points = [f"{msg.agent}: {msg.content}" for msg in transcript]
                action, content = llm.generate(
                    agent=agent,
                    topic=topic,
                    prior_points=prior_points,
                    round_index=round_index,
                )

                if action == "request_research" and consecutive_research < _MAX_CONSECUTIVE_RESEARCH:
                    # Post the analyst's request so it is visible in the transcript.
                    request_msg = AgentMessage(
                        agent=agent.name,
                        round_index=round_index,
                        content=f"[Research request] {content.strip()}",
                    )
                    transcript.append(request_msg)
                    if on_message is not None:
                        on_message(request_msg)

                    # Fulfill immediately, then loop back to give the analyst another turn.
                    result = _helper.research(content.strip())
                    research_msg = AgentMessage(
                        agent=RESEARCH_HELPER_NAME,
                        round_index=round_index,
                        content=f"(Requested by {agent.name}) {result}",
                    )
                    transcript.append(research_msg)
                    any_research = True
                    if on_message is not None:
                        on_message(research_msg)

                    consecutive_research += 1
                    continue  # analyst gets another turn to react to findings

                # Final action for this analyst (or limit reached — treat excess as none).
                all_actions.append(action)
                if action not in ("none", "request_research"):
                    message = AgentMessage(agent=agent.name, round_index=round_index, content=content)
                    round_messages.append(message)
                    if on_message is not None:
                        on_message(message)
                break

        transcript.extend(round_messages)

        if not round_messages and not any_research:
            break

        if round_messages:
            round_summary = _aggregate_round(topic, round_index, round_messages)
            summaries.append(round_summary)

        if not {"share_opinion"}.intersection(all_actions) and not any_research:
            break

    if not summaries:
        if not transcript:
            raise RuntimeError("No analyst messages were generated.")
        last_round = max(msg.round_index for msg in transcript)
        final_messages = [msg for msg in transcript if msg.round_index == last_round]
        summaries.append(_aggregate_round(topic, last_round, final_messages))
    final_summary = summaries[-1]
    final_summary.final_report = _synthesizer.generate(topic=topic, transcript=transcript)
    _persist_outputs(output_root, config, topic, transcript, final_summary)
    return transcript, final_summary, output_root


def _persist_outputs(
    path: Path,
    config: RunConfig,
    topic: str,
    transcript: Sequence[AgentMessage],
    summary: RoundSummary,
) -> None:
    path.mkdir(parents=True, exist_ok=True)

    transcript_payload = [dataclasses.asdict(msg) for msg in transcript]  # type: ignore
    summary_payload = dataclasses.asdict(summary)  # type: ignore
    config_payload = {
        "topic": topic,
        "model_name": config.model_name,
        "agents": [dataclasses.asdict(agent) for agent in config.agents],  # type: ignore
        "run": dataclasses.asdict(config.run),  # type: ignore
    }

    with open(path / "transcript.json", "w", encoding="utf-8") as handle:
        json.dump(transcript_payload, handle, indent=2)

    with open(path / "summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary_payload, handle, indent=2)

    with open(path / "config_snapshot.json", "w", encoding="utf-8") as handle:
        json.dump(config_payload, handle, indent=2)

    with open(path / "summary.md", "w", encoding="utf-8") as handle:
        handle.write("# Run Summary\n\n")
        handle.write(f"**Topic:** {topic}\n\n")
        handle.write(f"**Stance:** {summary.stance}\n\n")
        if summary.final_report:
            handle.write(summary.final_report)
            handle.write("\n\n")
        handle.write("## Key Points\n")
        for agent, point in summary.key_points.items():
            handle.write(f"### {agent}\n")
            handle.write(f"{point}\n")
