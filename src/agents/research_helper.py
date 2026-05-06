"""
ResearchHelper: an agentic loop that uses registered tools to investigate a
question and produce a concise evidence-based report for the analyst panel.

Two entry points:
- proactive_research(topic, conversation): called at the start of each round;
  the helper autonomously decides what gaps to fill and surfaces context before
  analysts speak.
- research(question): called inline when an analyst issues request_research;
  the helper answers the specific question and returns a report.
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, Tuple

from src.common.search import Searcher, web_search

NAME = "research_helper"

def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


_REACTIVE_PROMPT = """\
You are a financial research assistant supporting a panel of investment analysts.
Given a research question, use the available tools to gather evidence and then
write a clear, factual report that the analysts can reason from.

Current time: {current_time}

Available tools:
{tools}

Research question:
{question}

Findings so far:
{findings}

Decide your next step. If you need more data, call a tool. If you have enough
evidence, write a final report.

Output format (follow exactly):
Action: [tool_name|report]
Content:
[tool input OR final report text]
"""

_PROACTIVE_PROMPT = """\
You are a proactive financial research assistant embedded in an analyst panel discussion.

At the start of each round, review the topic and conversation so far. Identify any
facts, recent news, earnings data, or market context that the analysts would benefit
from having before they speak. If you find something worth looking up, use a tool.
When you have gathered enough (or if nothing useful is needed), use "done".

Current time: {current_time}

Available tools:
{tools}

Topic: {topic}

Conversation so far:
{conversation}

Findings gathered this round:
{findings}

Output format (follow exactly):
Action: [tool_name|done]
Content:
[search query, or leave blank if done]
"""

_PROACTIVE_SUMMARY_PROMPT = """\
You are a financial research assistant. Summarize the following search findings into a
concise briefing for an analyst panel. Focus on facts, numbers, and recent developments
most relevant to the topic. Be direct — no fluff.

Current time: {current_time}

Topic: {topic}

Findings:
{findings}

Write the briefing now:
"""


class Tool(Protocol):
    name: str
    description: str

    def run(self, query: str) -> str: ...


@dataclass
class SearchTool:
    name: str = "search"
    description: str = (
        "Search the web. Input: a concise, specific query "
        "(e.g. 'Google Q1 2025 cloud revenue growth')."
    )
    searcher: Searcher = field(default_factory=lambda: web_search)

    def run(self, query: str) -> str:
        return self.searcher(query)


@dataclass
class ResearchHelper:
    model_name: str = ""  # inherits from RunConfig when left empty
    tools: List[Any] = field(default_factory=list)
    max_iterations: int = 5

    def __post_init__(self) -> None:
        if not self.tools:
            self.tools = [SearchTool()]

    # ------------------------------------------------------------------
    # Proactive: called at the start of each round before analysts speak
    # ------------------------------------------------------------------

    def proactive_research(self, topic: str, conversation: List[str]) -> Optional[str]:
        """
        Autonomously surface context before analysts speak.
        Returns a formatted briefing string if any research was done, None otherwise.
        """
        findings: List[str] = []
        tool_map = {t.name: t for t in self.tools}
        conv_text = "\n".join(conversation) if conversation else "None yet."

        for _ in range(self.max_iterations):
            action, content = self._proactive_step(topic, conv_text, findings)
            if action == "done":
                break
            tool = tool_map.get(action)
            if tool is None:
                break
            result = tool.run(content.strip())
            findings.append(f'{action}("{content.strip()}"):\n{result}')

        if not findings:
            return None

        return self._summarize_proactive(topic, findings)

    def _proactive_step(
        self, topic: str, conversation: str, findings: List[str]
    ) -> Tuple[str, str]:
        from src.common.llm import complete

        tools_text = "\n".join(f"- {t.name}: {t.description}" for t in self.tools)
        findings_text = "\n\n".join(findings) if findings else "None yet."
        prompt = _PROACTIVE_PROMPT.format(
            current_time=_now(),
            tools=tools_text,
            topic=topic,
            conversation=conversation,
            findings=findings_text,
        )
        response = complete(
            model=self.model_name,
            messages=[{"role": "system", "content": prompt}],
        )
        return _parse_response(response.choices[0].message.content)

    def _summarize_proactive(self, topic: str, findings: List[str]) -> str:
        from src.common.llm import complete

        findings_text = "\n\n".join(findings)
        prompt = _PROACTIVE_SUMMARY_PROMPT.format(
            current_time=_now(), topic=topic, findings=findings_text
        )
        response = complete(
            model=self.model_name,
            messages=[{"role": "system", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Reactive: called inline when an analyst issues request_research
    # ------------------------------------------------------------------

    def research(self, question: str) -> str:
        """Run the agentic loop and return a final research report."""
        findings: List[str] = []
        tool_map = {t.name: t for t in self.tools}

        for _ in range(self.max_iterations):
            action, content = self._step(question, findings)
            if action == "report":
                return content
            tool = tool_map.get(action)
            if tool is None:
                findings.append(f"[Unknown tool '{action}' — skipping]")
                continue
            result = tool.run(content)
            findings.append(f'{action}("{content}"):\n{result}')

        # Max iterations exhausted — force a report from whatever was gathered.
        _, report = self._step(question, findings, force_report=True)
        return report

    def _step(
        self,
        question: str,
        findings: List[str],
        force_report: bool = False,
    ) -> Tuple[str, str]:
        from src.common.llm import complete

        tools_text = "\n".join(f"- {t.name}: {t.description}" for t in self.tools)
        findings_text = "\n\n".join(findings) if findings else "None yet."
        prompt = _REACTIVE_PROMPT.format(
            current_time=_now(),
            tools=tools_text,
            question=question,
            findings=findings_text,
        )
        if force_report:
            prompt += (
                "\n\nYou have reached the tool call limit. "
                "Summarize your findings into a final report now."
            )
        response = complete(
            model=self.model_name,
            messages=[{"role": "system", "content": prompt}],
        )
        return _parse_response(response.choices[0].message.content)


def _parse_response(text: str) -> Tuple[str, str]:
    if "Content:" not in text:
        return "report", text.strip()
    action_part, content_part = text.split("Content:", maxsplit=1)
    action = action_part.split()[-1].strip().lower()
    return action, content_part.strip()
