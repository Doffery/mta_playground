import os
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from src.common.config import AgentProfile

DEFAULT_MODEL_NAME = "vertex_ai/gemini-3.1-flash-lite"
os.environ.setdefault("VERTEXAI_PROJECT", "gen-lang-client-0986610697")
os.environ.setdefault("VERTEXAI_LOCATION", "us-central1")


def complete(model: str, messages: List[Dict[str, Any]]) -> object:
    from litellm import completion

    return completion(model=model, messages=messages)


AgentSystemPrompt = """
Your name is {agent_name}. You are professional financial analyst.
Your investment perspective is:
{agent_persona}

You are given a conversation history between you and other analysts on a given topic.
You should decide your next action based on the conversation history and your investment perspective.
You should output your next action in the following markdown format:
Action: [action]
Your Opinion:
[your opinion]

The possible actions are:
- share_opinion: share your opinion on the topic.
- ask_question: ask a question to the other analysts.
- request_research: ask the research helper to look something up; put your research question in the "Your Opinion" field. You may use this at most 2 times consecutively — after that you must choose a different action.
- conclude: conclude the discussion and share your final opinion on the topic.
- none: do nothing and wait for the other analysts to speak.

When using "request_research", write a concise, specific question (e.g. "What was Google's cloud revenue growth in Q1 2025?"). After the research helper responds, you will get another turn to react to the findings.

Topic:
{topic}

Existing conversation history:
{conversation_history}

Output:
Action:
"""


@dataclass
class LiteLLMAnalyst:
    """Analyst response generator backed by LiteLLM."""

    model_name: str = DEFAULT_MODEL_NAME

    def generate(
        self,
        agent: AgentProfile,
        topic: str,
        prior_points: Sequence[str],
        round_index: int = 0,
    ) -> Tuple[str, str]:
        prompt = AgentSystemPrompt.format(
            agent_name=agent.name,
            agent_persona=agent.persona,
            topic=topic,
            conversation_history="\n".join(prior_points),
        )
        response = complete(
            model=self.model_name,
            messages=[{"role": "system", "content": prompt}],
        )

        response_str = response.choices[0].message.content
        if "Your Opinion:" not in response_str:
            return "share_opinion", response_str.strip()

        action, opinion = response_str.split("Your Opinion:", maxsplit=1)
        return action.split()[-1].strip(), opinion.strip()
