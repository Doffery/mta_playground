from src.common.config import AgentProfile
from src.common.llm import LiteLLMAnalyst


def test_litellm_analyst_parses_action_and_opinion(monkeypatch) -> None:
    def fake_completion(model, messages):
        class Message:
            content = "Action: share_opinion\nYour Opinion:\nMargins look resilient."

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]

        return Response()

    monkeypatch.setattr("src.common.llm.complete", fake_completion)
    profile = AgentProfile(name="growth_focus", persona="Growth", risk_appetite="high")
    llm = LiteLLMAnalyst(model_name="fake-model")

    out = llm.generate(
        agent=profile,
        topic="Tech rally",
        round_index=2,
        prior_points=["p1", "p2", "p3"],
    )
    assert out == ("share_opinion", "Margins look resilient.")
