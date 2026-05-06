from src.agents.research_helper import ResearchHelper, SearchTool, _parse_response


# --- _parse_response unit tests ---

def test_parse_response_report() -> None:
    text = "Action: report\nContent:\nRevenue grew 12% YoY."
    action, content = _parse_response(text)
    assert action == "report"
    assert content == "Revenue grew 12% YoY."


def test_parse_response_search() -> None:
    text = "Action: search\nContent:\nGoogle Q1 2025 cloud revenue"
    action, content = _parse_response(text)
    assert action == "search"
    assert content == "Google Q1 2025 cloud revenue"


def test_parse_response_no_content_marker() -> None:
    action, content = _parse_response("Some raw text with no markers.")
    assert action == "report"
    assert "Some raw text" in content


# --- ResearchHelper agentic loop tests ---

class StubLLMResponses:
    """Returns a fixed sequence of (action, content) pairs."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0

    def __call__(self, model, messages):
        action, content = self._responses[self._idx % len(self._responses)]
        self._idx += 1

        class _Msg:
            pass

        msg = _Msg()
        msg.content = f"Action: {action}\nContent:\n{content}"

        class _Choice:
            message = msg

        class _Resp:
            choices = [_Choice()]

        return _Resp()


def make_helper(llm_responses, fake_search="Fake search result."):
    stub_tool = SearchTool(searcher=lambda q: fake_search)
    helper = ResearchHelper(model_name="stub-model", tools=[stub_tool], max_iterations=5)
    # Patch complete at import site inside _step
    import src.common.llm as llm_mod
    llm_mod._stub_complete = StubLLMResponses(llm_responses)
    original = llm_mod.complete

    def patched(model, messages):
        return llm_mod._stub_complete(model, messages)

    llm_mod.complete = patched
    return helper, original, llm_mod


def test_helper_reports_immediately(monkeypatch) -> None:
    fake_responses = [("report", "Google cloud revenue grew 28%.")]
    stub = StubLLMResponses(fake_responses)
    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: "unused")],
    )
    report = helper.research("Google cloud growth Q1 2025")
    assert "28%" in report


def test_helper_searches_then_reports(monkeypatch) -> None:
    search_results = "Revenue: $12B, up 28% YoY."
    fake_responses = [
        ("search", "Google Q1 2025 cloud revenue"),
        ("report", "Based on search: cloud revenue up 28%."),
    ]
    stub = StubLLMResponses(fake_responses)
    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: search_results)],
    )
    report = helper.research("Google cloud growth")
    assert "28%" in report


def test_helper_force_reports_at_max_iterations(monkeypatch) -> None:
    # Always returns search — should hit max_iterations and then force report
    call_count = {"n": 0}

    def stub(model, messages):
        call_count["n"] += 1
        is_force = "tool call limit" in messages[0]["content"]

        class _Msg:
            content = (
                "Action: report\nContent:\nForced report."
                if is_force
                else "Action: search\nContent:\nsome query"
            )

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()

    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: "result")],
        max_iterations=3,
    )
    report = helper.research("anything")
    assert "Forced report" in report
    # 3 search iterations + 1 forced report call
    assert call_count["n"] == 4


def test_helper_unknown_tool_skipped(monkeypatch) -> None:
    fake_responses = [
        ("unknown_tool", "some input"),
        ("report", "Final report despite unknown tool."),
    ]
    stub = StubLLMResponses(fake_responses)
    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: "unused")],
    )
    report = helper.research("test question")
    assert "Final report" in report


# --- proactive_research tests ---

def test_proactive_returns_none_when_done_immediately(monkeypatch) -> None:
    def stub(model, messages):
        class _Msg:
            content = "Action: done\nContent:\n"
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
        return _Resp()

    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: "unused")],
    )
    result = helper.proactive_research("Google", [])
    assert result is None


def test_proactive_searches_then_summarizes(monkeypatch) -> None:
    search_result = "Revenue: $90B, up 12% YoY."
    summary_text = "Google Q1 2025: revenue up 12%, cloud strong."

    responses = [
        "Action: search\nContent:\nGoogle Q1 2025 earnings",  # first: search
        "Action: done\nContent:\n",                           # second: done
        summary_text,                                          # third: summary (no Content: marker)
    ]
    call_count = {"n": 0}

    def stub(model, messages):
        text = responses[call_count["n"] % len(responses)]
        call_count["n"] += 1
        class _Msg:
            content = text
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
        return _Resp()

    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: search_result)],
    )
    result = helper.proactive_research("Google", ["prior: some conversation"])
    assert result is not None
    assert summary_text in result


def test_proactive_stops_at_max_iterations(monkeypatch) -> None:
    call_count = {"n": 0}

    def stub(model, messages):
        call_count["n"] += 1
        # Always search — proactive loop should stop at max_iterations
        class _Msg:
            content = "Action: search\nContent:\nsome query"
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
        return _Resp()

    monkeypatch.setattr("src.common.llm.complete", stub)

    helper = ResearchHelper(
        model_name="stub",
        tools=[SearchTool(searcher=lambda q: "result")],
        max_iterations=2,
    )
    # Should not loop forever; summary call may return raw text but must terminate
    result = helper.proactive_research("Google", [])
    # max_iterations=2 proactive steps + 1 summary call
    assert call_count["n"] == 3
    assert result is not None
