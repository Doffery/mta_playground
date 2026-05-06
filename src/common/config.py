import dataclasses
from pathlib import Path
from typing import List, Optional

import yaml


@dataclasses.dataclass
class AgentProfile:
    name: str
    persona: str
    risk_appetite: str = "balanced"


@dataclasses.dataclass
class RunSettings:
    max_rounds: int = 3
    convergence_threshold: float = 0.15
    output_dir: str = "runs"
    seed: int = 123


@dataclasses.dataclass
class RunConfig:
    topic: str
    model_name: str
    agents: List[AgentProfile]
    run: RunSettings


def _parse_agents(raw_agents: List[dict]) -> List[AgentProfile]:
    return [
        AgentProfile(
            name=agent["name"],
            persona=agent.get("persona", ""),
            risk_appetite=agent.get("risk_appetite", "balanced"),
        )
        for agent in raw_agents
    ]


def load_config(path: str) -> RunConfig:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    agents = _parse_agents(data.get("agents", []))
    run_settings = data.get("run", {}) or {}

    run = RunSettings(
        max_rounds=int(run_settings.get("max_rounds", 3)),
        convergence_threshold=float(run_settings.get("convergence_threshold", 0.15)),
        output_dir=str(run_settings.get("output_dir", "runs")),
        seed=int(run_settings.get("seed", 123)),
    )

    return RunConfig(
        topic=str(data.get("topic", "Unnamed topic")),
        model_name=str(data.get("model_name", "fake-llm")),
        agents=agents,
        run=run,
    )


def resolve_output_dir(base: str, run_name: Optional[str]) -> Path:
    root = Path(base)
    run_id = run_name or ""
    return root / run_id if run_id else root
