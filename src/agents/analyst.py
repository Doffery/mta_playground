from dataclasses import dataclass
from typing import Sequence

from src.common.config import AgentProfile
from src.common.llm import LiteLLMAnalyst


@dataclass
class AnalystAgent:
    profile: AgentProfile
    llm: LiteLLMAnalyst

    def respond(self, topic: str, prior_points: Sequence[str], round_index: int) -> str:
        return self.llm.generate(
            agent=self.profile,
            topic=topic,
            round_index=round_index,
            prior_points=prior_points,
        )
