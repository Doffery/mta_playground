import dataclasses
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

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


def run_discussion(
    config: RunConfig,
    topic_override: str = "",
    max_rounds_override: Optional[int] = None,
    output_dir_override: Optional[str] = None,
    run_name: Optional[str] = None,
    llm: Optional[Any] = None,
    on_message: Optional[Callable[[AgentMessage], None]] = None,
) -> Tuple[List[AgentMessage], RoundSummary, Path]:
    topic = topic_override or config.topic
    max_rounds = max_rounds_override or config.run.max_rounds
    run_label = run_name or _timestamp_slug()
    output_root = resolve_output_dir(output_dir_override or config.run.output_dir, run_label)
    output_root.mkdir(parents=True, exist_ok=True)

    llm = llm or LiteLLMAnalyst(model_name=config.model_name)
    agents = list(config.agents)

    transcript: List[AgentMessage] = []
    summaries: List[RoundSummary] = []

    for round_index in range(max_rounds):
        round_messages: List[AgentMessage] = []
        all_actions = []
        for agent in agents:
            prior_points = [f"{msg.agent}: {msg.content}" for msg in transcript]
            action, content = llm.generate(
                agent=agent,
                topic=topic,
                prior_points=prior_points,
                round_index=round_index,
            )
            all_actions.append(action)
            if action != "none":
                message = AgentMessage(agent=agent.name, round_index=round_index, content=content)
                round_messages.append(message)
                if on_message is not None:
                    on_message(message)
        if not round_messages:
            break
        transcript.extend(round_messages)

        round_summary = _aggregate_round(topic, round_index, round_messages)
        summaries.append(round_summary)
        if "share_opinion" not in all_actions:
            break

    if not summaries:
        raise RuntimeError("No analyst messages were generated.")
    final_summary = summaries[-1]
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
        handle.write("## Key Points\n")
        for agent, point in summary.key_points.items():
            handle.write(f"### {agent}\n")
            handle.write(f"{point}\n")
