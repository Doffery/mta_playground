"""
Local web UI for UX V2.
Run: python -m src.web --config configs/example.yaml --port 8000
"""

import argparse
import dataclasses
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple, Type
from urllib.parse import urlparse

from src.common.config import AgentProfile, RunConfig, load_config
from src.common.orchestrator import run_discussion


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MTA Playground UX V2</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #16202a;
      --muted: #647282;
      --line: #d9e0e7;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --warn: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 18px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 20px; font-weight: 700; }
    h2 { font-size: 15px; font-weight: 700; margin-bottom: 12px; }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
      gap: 18px;
      padding: 18px;
      max-width: 1320px;
      margin: 0 auto;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    label {
      display: block;
      font-weight: 650;
      margin: 14px 0 6px;
    }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      font: inherit;
      background: #fff;
      color: var(--ink);
    }
    textarea {
      min-height: 104px;
      resize: vertical;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 10px 14px;
      font: inherit;
      font-weight: 700;
      background: var(--accent);
      color: white;
      cursor: pointer;
    }
    button:hover { background: var(--accent-strong); }
    button:disabled { opacity: .65; cursor: wait; }
    .stack { display: grid; gap: 12px; }
    .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .muted { color: var(--muted); }
    .pill {
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
    }
    .agent {
      display: grid;
      gap: 8px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    .agent-head {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 10px;
      align-items: center;
    }
    .agent input[type="checkbox"] { width: auto; margin: 0; }
    .agent button,
    .ghost-button {
      background: #fff;
      color: var(--ink);
      border: 1px solid var(--line);
      padding: 7px 10px;
    }
    .agent button:hover,
    .ghost-button:hover { background: #f2f5f7; }
    .agent-editor {
      display: none;
      gap: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
    }
    .agent.open .agent-editor { display: grid; }
    .agent-editor textarea { min-height: 86px; }
    .agent-editor label { margin: 0; font-size: 12px; color: var(--muted); }
    .result-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfd;
    }
    .metric strong { display: block; font-size: 18px; }
    .message {
      border-top: 1px solid var(--line);
      padding: 14px 0;
    }
    .message:first-child { border-top: 0; }
    .message h3 {
      font-size: 14px;
      margin-bottom: 5px;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .message p { white-space: pre-wrap; }
    .md { line-height: 1.55; }
    .md p,
    .md ul,
    .md ol,
    .md pre { margin: 0 0 10px; }
    .md p:last-child,
    .md ul:last-child,
    .md ol:last-child,
    .md pre:last-child { margin-bottom: 0; }
    .md ul,
    .md ol { padding-left: 22px; }
    .md code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      background: #eef2f6;
      border: 1px solid #dce3ea;
      border-radius: 4px;
      padding: 1px 4px;
    }
    .md pre {
      background: #111827;
      color: #f9fafb;
      border-radius: 6px;
      padding: 10px 12px;
      overflow-x: auto;
    }
    .md pre code {
      background: transparent;
      border: 0;
      color: inherit;
      padding: 0;
    }
    .md blockquote {
      margin: 0 0 10px;
      padding-left: 12px;
      border-left: 3px solid var(--line);
      color: var(--muted);
    }
    .md p { margin: 0 0 8px; }
    .md p:last-child { margin-bottom: 0; }
    .md ul, .md ol { margin: 6px 0 8px 18px; padding: 0; }
    .md li { margin-bottom: 2px; }
    .md strong { font-weight: 700; }
    .md em { font-style: italic; }
    .md a { color: var(--accent); }
    .md code { font-family: ui-monospace, monospace; font-size: 12px; background: #f1f3f5; padding: 1px 4px; border-radius: 3px; }
    .md pre { background: #f1f3f5; border-radius: 5px; padding: 10px; overflow-x: auto; margin: 8px 0; }
    .md pre code { background: none; padding: 0; }
    .md h1, .md h2, .md h3 { font-weight: 700; margin: 10px 0 4px; }
    .md blockquote { border-left: 3px solid var(--line); margin: 0; padding-left: 10px; color: var(--muted); }
    .message.research {
      background: #f0f7ff;
      border-left: 3px solid #0369a1;
      border-top: none;
      border-radius: 4px;
      padding: 12px 14px;
      margin: 8px 0;
    }
    .message.research + .message { border-top: 1px solid var(--line); }
    .pill.research-badge { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }
    .message.research-request {
      background: #fefce8;
      border-left: 3px solid #ca8a04;
      border-top: none;
      border-radius: 4px;
      padding: 10px 14px;
      margin: 6px 0;
      font-style: italic;
    }
    .message.research-request + .message { border-top: 1px solid var(--line); }
    .pill.request-badge { background: #fef9c3; color: #854d0e; border-color: #fde68a; }
    .live {
      border: 1px solid var(--line);
      border-radius: 6px;
      margin-bottom: 14px;
      padding: 0 12px;
      background: #fbfcfd;
    }
    .tabs {
      display: flex;
      gap: 6px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 12px;
    }
    .tab-button {
      background: transparent;
      color: var(--muted);
      border: 0;
      border-bottom: 2px solid transparent;
      border-radius: 0;
      padding: 8px 10px;
    }
    .tab-button:hover { background: #f2f5f7; }
    .tab-button.active {
      color: var(--ink);
      border-bottom-color: var(--accent);
    }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .error {
      border-color: #f2c38b;
      background: #fff7ed;
      color: var(--warn);
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; padding: 12px; }
      header { padding: 14px 16px; align-items: flex-start; flex-direction: column; }
      .summary { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>MTA Playground</h1>
      <p class="muted">UX V2 local web analysis</p>
    </div>
    <span class="pill" id="modelName">Loading config</span>
  </header>
  <main>
    <section>
      <h2>Run Analysis</h2>
      <form id="analysisForm" class="stack">
        <div>
          <label for="topic">Topic</label>
          <textarea id="topic" name="topic" required></textarea>
        </div>
        <div>
          <label for="maxRounds">Max rounds</label>
          <input id="maxRounds" name="maxRounds" type="number" min="1" max="8" value="3">
        </div>
        <div>
          <label for="model">Model</label>
          <input id="model" name="model" list="modelList" autocomplete="off" spellcheck="false">
          <datalist id="modelList">
            <option value="vertex_ai/gemini-3.1-flash-lite">
            <option value="vertex_ai/gemini-3-flash">
            <option value="vertex_ai/gemini-2.5-flash">
            <option value="vertex_ai/gemini-2.5-pro">
            <option value="vertex_ai/gemini-2.0-flash">
            <option value="anthropic/claude-opus-4-7">
            <option value="anthropic/claude-sonnet-4-6">
            <option value="anthropic/claude-haiku-4-5">
            <option value="openai/gpt-4o">
            <option value="openai/gpt-4o-mini">
            <option value="openai/o3-mini">
          </datalist>
        </div>
        <div>
          <label>Analyst profiles</label>
          <div id="agents" class="stack"></div>
          <button class="ghost-button" id="addAgentButton" type="button">Add analyst</button>
        </div>
        <button id="submitButton" type="submit">Analyze</button>
      </form>
    </section>
    <section>
      <div class="result-head">
        <h2>Output</h2>
        <span class="pill" id="runPath">No run yet</span>
      </div>
      <div id="status" class="muted">Submit a topic to generate the debate and final stance.</div>
      <div id="output"></div>
    </section>
  </main>
  <script>
    const state = { config: null, agents: [] };
    const form = document.querySelector("#analysisForm");
    const output = document.querySelector("#output");
    const statusBox = document.querySelector("#status");
    const submitButton = document.querySelector("#submitButton");
    const addAgentButton = document.querySelector("#addAgentButton");

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);
    }

    function renderConfig(config) {
      state.config = config;
      state.agents = config.agents.map((agent, index) => ({
        id: `agent-${index}-${Date.now()}`,
        selected: true,
        open: false,
        name: agent.name,
        persona: agent.persona,
        risk_appetite: agent.risk_appetite || "balanced"
      }));
      document.querySelector("#topic").value = config.topic;
      document.querySelector("#maxRounds").value = config.max_rounds;
      document.querySelector("#model").value = config.model_name;
      document.querySelector("#modelName").textContent = config.model_name;
      renderAgentProfiles();
    }

    function renderAgentProfiles() {
      document.querySelector("#agents").innerHTML = state.agents.map((agent, index) => `
        <div class="agent${agent.open ? " open" : ""}" data-agent-id="${escapeHtml(agent.id)}">
          <div class="agent-head">
            <input type="checkbox" data-agent-field="selected" ${agent.selected ? "checked" : ""}>
            <button type="button" data-agent-action="toggle">
              <strong>${escapeHtml(agent.name || "Untitled analyst")}</strong>
              <span class="muted"> ${escapeHtml(agent.risk_appetite || "balanced")}</span>
            </button>
            <button type="button" data-agent-action="remove">Remove</button>
          </div>
          <div class="muted">${escapeHtml(agent.persona || "No persona set.")}</div>
          <div class="agent-editor">
            <label>Name</label>
            <input data-agent-field="name" value="${escapeHtml(agent.name)}">
            <label>Risk appetite</label>
            <select data-agent-field="risk_appetite">
              ${["low", "balanced", "high"].map(value => `
                <option value="${value}" ${agent.risk_appetite === value ? "selected" : ""}>${value}</option>
              `).join("")}
            </select>
            <label>Persona</label>
            <textarea data-agent-field="persona">${escapeHtml(agent.persona)}</textarea>
          </div>
        </div>
      `).join("");
    }

    function updateAgent(id, patch) {
      state.agents = state.agents.map(agent => agent.id === id ? { ...agent, ...patch } : agent);
    }

    function collectAgents() {
      return state.agents
        .filter(agent => agent.selected)
        .map(agent => ({
          name: agent.name.trim(),
          persona: agent.persona.trim(),
          risk_appetite: agent.risk_appetite || "balanced"
        }))
        .filter(agent => agent.name);
    }

    function showTab(name) {
      document.querySelectorAll(".tab-button").forEach(button => {
        button.classList.toggle("active", button.dataset.tab === name);
      });
      document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.classList.toggle("active", panel.dataset.panel === name);
      });
    }

    function renderResult(data) {
      document.querySelector("#runPath").textContent = data.output_dir;
      statusBox.textContent = "";
      output.innerHTML = `
        <div class="tabs">
          <button class="tab-button active" data-tab="final" type="button">Final Key Points</button>
          <button class="tab-button" data-tab="transcript" type="button">Transcript</button>
        </div>
        <div class="summary">
          <div class="metric"><span class="muted">Final stance</span><strong>${escapeHtml(data.summary.stance)}</strong></div>
          <div class="metric"><span class="muted">Rounds</span><strong>${escapeHtml(data.rounds_executed)}</strong></div>
          <div class="metric"><span class="muted">Messages</span><strong>${escapeHtml(data.transcript.length)}</strong></div>
        </div>
        <div class="tab-panel active" data-panel="final">
          <h2>Final Key Points</h2>
          ${finalReportHtml(data.summary)}
        </div>
        <div class="tab-panel" data-panel="transcript">
          <h2>Transcript</h2>
          <div>${data.transcript.map(messageHtml).join("")}</div>
        </div>
      `;
    }

    function startLiveRun() {
      document.querySelector("#runPath").textContent = "Running";
      output.innerHTML = `
        <div class="tabs">
          <button class="tab-button active" data-tab="transcript" type="button">Transcript</button>
          <button class="tab-button" data-tab="final" type="button">Final Key Points</button>
        </div>
        <div class="tab-panel active" data-panel="transcript">
          <div id="liveTranscript" class="live"></div>
        </div>
        <div class="tab-panel" data-panel="final">
          <div id="finalResult"></div>
        </div>
      `;
    }

    function renderMd(text) {
      const source = String(text || "").replace(/\\r\\n/g, "\\n");
      const lines = source.split("\\n");
      const html = [];
      let paragraph = [];
      let listType = null;
      let inCode = false;
      let codeLines = [];

      function flushParagraph() {
        if (!paragraph.length) return;
        html.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
        paragraph = [];
      }

      function closeList() {
        if (!listType) return;
        html.push(`</${listType}>`);
        listType = null;
      }

      function openList(type) {
        if (listType === type) return;
        closeList();
        flushParagraph();
        listType = type;
        html.push(`<${type}>`);
      }

      for (const line of lines) {
        if (line.trim().startsWith("```")) {
          if (inCode) {
            html.push(`<pre><code>${escapeHtml(codeLines.join("\\n"))}</code></pre>`);
            codeLines = [];
            inCode = false;
          } else {
            flushParagraph();
            closeList();
            inCode = true;
          }
          continue;
        }

        if (inCode) {
          codeLines.push(line);
          continue;
        }

        if (!line.trim()) {
          flushParagraph();
          closeList();
          continue;
        }

        const heading = line.match(/^(#{1,3})\\s+(.+)$/);
        if (heading) {
          flushParagraph();
          closeList();
          const level = heading[1].length + 2;
          html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
          continue;
        }

        const quote = line.match(/^>\\s?(.+)$/);
        if (quote) {
          flushParagraph();
          closeList();
          html.push(`<blockquote>${renderInline(quote[1])}</blockquote>`);
          continue;
        }

        const unordered = line.match(/^[-*]\\s+(.+)$/);
        if (unordered) {
          openList("ul");
          html.push(`<li>${renderInline(unordered[1])}</li>`);
          continue;
        }

        const ordered = line.match(/^\\d+\\.\\s+(.+)$/);
        if (ordered) {
          openList("ol");
          html.push(`<li>${renderInline(ordered[1])}</li>`);
          continue;
        }

        closeList();
        paragraph.push(line.trim());
      }

      if (inCode) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\\n"))}</code></pre>`);
      }
      flushParagraph();
      closeList();
      return html.join("");
    }

    function renderInline(text) {
      let html = escapeHtml(text);
      html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
      html = html.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>");
      html = html.replace(/\\*([^*]+)\\*/g, "<em>$1</em>");
      html = html.replace(
        /\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
      );
      return html;
    }

    function keyPointsHtml(keyPoints) {
      return Object.entries(keyPoints).map(([agent, point]) => `
        <div class="message">
          <h3>${escapeHtml(agent)}</h3>
          <div class="md">${renderMd(point)}</div>
        </div>
      `).join("");
    }

    function finalReportHtml(summary) {
      if (summary.final_report) {
        return `<div class="message"><div class="md">${renderMd(summary.final_report)}</div></div>`;
      }
      return `<div class="stack">${keyPointsHtml(summary.key_points)}</div>`;
    }

    function messageHtml(message) {
      const isResearch = message.agent === "research_helper";
      const isRequest = message.content.startsWith("[Research request]");

      let cssClass = "";
      let badge = `<span class="pill">Round ${message.round_index + 1}</span>`;

      if (isResearch) {
        cssClass = " research";
        badge = `<span class="pill research-badge">research</span>`;
      } else if (isRequest) {
        cssClass = " research-request";
        badge = `<span class="pill request-badge">requesting research</span>`;
      }

      const rawBody = isRequest
        ? message.content.replace("[Research request] ", "")
        : message.content;

      return `
        <div class="message${cssClass}">
          <h3>${escapeHtml(message.agent)} ${badge}</h3>
          <div class="md">${renderMd(rawBody)}</div>
        </div>`;
    }

    function appendTurn(message) {
      document.querySelector("#liveTranscript").insertAdjacentHTML("beforeend", messageHtml(message));
    }

    function renderFinal(data) {
      document.querySelector("#runPath").textContent = data.output_dir;
      statusBox.textContent = "";
      document.querySelector("#finalResult").innerHTML = `
        <div class="summary">
          <div class="metric"><span class="muted">Final stance</span><strong>${escapeHtml(data.summary.stance)}</strong></div>
          <div class="metric"><span class="muted">Rounds</span><strong>${escapeHtml(data.rounds_executed)}</strong></div>
          <div class="metric"><span class="muted">Messages</span><strong>${escapeHtml(data.transcript.length)}</strong></div>
        </div>
        <h2>Final Key Points</h2>
        ${finalReportHtml(data.summary)}
      `;
      showTab("final");
    }

    async function readAnalysisStream(response) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === "turn") {
            appendTurn(event.message);
            statusBox.textContent = `Round ${event.message.round_index + 1}: ${event.message.agent} responded`;
          } else if (event.type === "complete") {
            renderFinal(event.result);
          } else if (event.type === "error") {
            throw new Error(event.error);
          }
        }
      }
    }

    async function loadConfig() {
      const response = await fetch("/api/config");
      renderConfig(await response.json());
    }

    document.querySelector("#agents").addEventListener("click", event => {
      const card = event.target.closest(".agent");
      if (!card) return;
      const id = card.dataset.agentId;
      const action = event.target.closest("[data-agent-action]")?.dataset.agentAction;
      if (action === "toggle") {
        updateAgent(id, { open: !state.agents.find(agent => agent.id === id).open });
        renderAgentProfiles();
      } else if (action === "remove") {
        state.agents = state.agents.filter(agent => agent.id !== id);
        renderAgentProfiles();
      }
    });

    document.querySelector("#agents").addEventListener("input", event => {
      const card = event.target.closest(".agent");
      const field = event.target.dataset.agentField;
      if (!card || !field) return;
      const value = field === "selected" ? event.target.checked : event.target.value;
      updateAgent(card.dataset.agentId, { [field]: value });
    });

    document.querySelector("#agents").addEventListener("change", event => {
      const card = event.target.closest(".agent");
      const field = event.target.dataset.agentField;
      if (!card || !field) return;
      const value = field === "selected" ? event.target.checked : event.target.value;
      updateAgent(card.dataset.agentId, { [field]: value });
      renderAgentProfiles();
    });

    addAgentButton.addEventListener("click", () => {
      state.agents.push({
        id: `custom-${Date.now()}`,
        selected: true,
        open: true,
        name: `custom_analyst_${state.agents.length + 1}`,
        persona: "Describe this analyst's investment perspective.",
        risk_appetite: "balanced"
      });
      renderAgentProfiles();
    });

    output.addEventListener("click", event => {
      const tab = event.target.closest(".tab-button")?.dataset.tab;
      if (tab) showTab(tab);
    });

    document.querySelector("#model").addEventListener("input", event => {
      document.querySelector("#modelName").textContent = event.target.value || "—";
    });

    form.addEventListener("submit", async event => {
      event.preventDefault();
      startLiveRun();
      statusBox.className = "muted";
      statusBox.textContent = "Starting analysis...";
      submitButton.disabled = true;
      const selectedAgents = collectAgents();
      try {
        if (!selectedAgents.length) {
          throw new Error("Select or add at least one analyst profile.");
        }
        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            topic: document.querySelector("#topic").value,
            max_rounds: Number(document.querySelector("#maxRounds").value),
            model_name: document.querySelector("#model").value.trim(),
            agent_profiles: selectedAgents
          })
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "Analysis failed");
        }
        await readAnalysisStream(response);
      } catch (error) {
        statusBox.className = "error";
        statusBox.textContent = error.message;
      } finally {
        submitButton.disabled = false;
      }
    });

    loadConfig().catch(error => {
      statusBox.className = "error";
      statusBox.textContent = error.message;
    });
  </script>
</body>
</html>
"""


class WebApp:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load_config(self) -> RunConfig:
        return load_config(str(self.config_path))

    def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        config, topic, max_rounds = self.prepare_run(payload)
        transcript, summary, output_dir = run_discussion(
            config=config,
            topic_override=topic,
            max_rounds_override=max_rounds,
        )
        return self.build_result(transcript, summary, output_dir)

    def prepare_run(self, payload: Dict[str, Any]) -> Tuple[RunConfig, str, int]:
        config = self.load_config()
        raw_profiles = payload.get("agent_profiles") or []
        if raw_profiles:
            config.agents = [
                AgentProfile(
                    name=str(agent.get("name", "")).strip(),
                    persona=str(agent.get("persona", "")).strip(),
                    risk_appetite=str(agent.get("risk_appetite", "balanced")).strip() or "balanced",
                )
                for agent in raw_profiles
                if str(agent.get("name", "")).strip()
            ]
        else:
            selected_agents = set(payload.get("agents") or [])
            if selected_agents:
                config.agents = [agent for agent in config.agents if agent.name in selected_agents]
        if not config.agents:
            raise ValueError("Select at least one analyst profile.")

        model_name = str(payload.get("model_name") or "").strip()
        if model_name:
            config.model_name = model_name

        topic = str(payload.get("topic") or config.topic).strip()
        if not topic:
            raise ValueError("Topic is required.")

        max_rounds = int(payload.get("max_rounds") or config.run.max_rounds)
        return config, topic, max_rounds

    def build_result(self, transcript: List[Any], summary: Any, output_dir: Path) -> Dict[str, Any]:
        return {
            "output_dir": str(output_dir),
            "rounds_executed": len({message.round_index for message in transcript}),
            "transcript": [dataclasses.asdict(message) for message in transcript],
            "summary": dataclasses.asdict(summary),
        }


def make_handler(app: WebApp) -> Type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                self._send(HTTPStatus.OK, HTML_PAGE, "text/html; charset=utf-8")
                return
            if path == "/api/config":
                config = app.load_config()
                payload = {
                    "topic": config.topic,
                    "model_name": config.model_name,
                    "max_rounds": config.run.max_rounds,
                    "agents": [dataclasses.asdict(agent) for agent in config.agents],
                }
                self._send_json(HTTPStatus.OK, payload)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/analyze":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                payload = json.loads(body or "{}")
                self._send_analysis_stream(payload)
            except Exception as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
            self._send(status, json.dumps(payload), "application/json")

        def _send_analysis_stream(self, payload: Dict[str, Any]) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def send_event(event: Dict[str, Any]) -> None:
                self.wfile.write((json.dumps(event) + "\n").encode("utf-8"))
                self.wfile.flush()

            try:
                config, topic, max_rounds = app.prepare_run(payload)
                transcript, summary, output_dir = run_discussion(
                    config=config,
                    topic_override=topic,
                    max_rounds_override=max_rounds,
                    on_message=lambda message: send_event(
                        {"type": "turn", "message": dataclasses.asdict(message)}
                    ),
                )
                send_event(
                    {
                        "type": "complete",
                        "result": app.build_result(transcript, summary, output_dir),
                    }
                )
            except Exception as exc:
                send_event({"type": "error", "error": str(exc)})

        def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local UX V2 web UI.")
    parser.add_argument("--config", default="configs/example.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = WebApp(config_path=Path(args.config))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"UX V2 web UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
