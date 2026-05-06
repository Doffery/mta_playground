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

from src.common.config import RunConfig, load_config
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
      grid-template-columns: auto 1fr;
      gap: 10px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    .agent input { width: auto; margin-top: 3px; }
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
    .live {
      border: 1px solid var(--line);
      border-radius: 6px;
      margin-bottom: 14px;
      padding: 0 12px;
      background: #fbfcfd;
    }
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
          <label>Analyst profiles</label>
          <div id="agents" class="stack"></div>
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
    const state = { config: null };
    const form = document.querySelector("#analysisForm");
    const output = document.querySelector("#output");
    const statusBox = document.querySelector("#status");
    const submitButton = document.querySelector("#submitButton");

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);
    }

    function renderConfig(config) {
      state.config = config;
      document.querySelector("#topic").value = config.topic;
      document.querySelector("#maxRounds").value = config.max_rounds;
      document.querySelector("#modelName").textContent = config.model_name;
      document.querySelector("#agents").innerHTML = config.agents.map(agent => `
        <label class="agent">
          <input type="checkbox" name="agent" value="${escapeHtml(agent.name)}" checked>
          <span>
            <strong>${escapeHtml(agent.name)}</strong>
            <span class="muted"> ${escapeHtml(agent.risk_appetite)}</span><br>
            <span class="muted">${escapeHtml(agent.persona)}</span>
          </span>
        </label>
      `).join("");
    }

    function renderResult(data) {
      document.querySelector("#runPath").textContent = data.output_dir;
      statusBox.textContent = "";
      output.innerHTML = `
        <div class="summary">
          <div class="metric"><span class="muted">Final stance</span><strong>${escapeHtml(data.summary.stance)}</strong></div>
          <div class="metric"><span class="muted">Rounds</span><strong>${escapeHtml(data.rounds_executed)}</strong></div>
          <div class="metric"><span class="muted">Messages</span><strong>${escapeHtml(data.transcript.length)}</strong></div>
        </div>
        <h2>Key Points</h2>
        <div class="stack">
          ${Object.entries(data.summary.key_points).map(([agent, point]) => `
            <div class="message">
              <h3>${escapeHtml(agent)}</h3>
              <p>${escapeHtml(point)}</p>
            </div>
          `).join("")}
        </div>
        <h2 style="margin-top: 18px;">Transcript</h2>
        <div>
          ${data.transcript.map(message => `
            <div class="message">
              <h3>${escapeHtml(message.agent)} <span class="pill">Round ${message.round_index + 1}</span></h3>
              <p>${escapeHtml(message.content)}</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function startLiveRun() {
      document.querySelector("#runPath").textContent = "Running";
      output.innerHTML = `
        <div id="liveTranscript" class="live"></div>
        <div id="finalResult"></div>
      `;
    }

    function appendTurn(message) {
      const liveTranscript = document.querySelector("#liveTranscript");
      liveTranscript.insertAdjacentHTML("beforeend", `
        <div class="message">
          <h3>${escapeHtml(message.agent)} <span class="pill">Round ${message.round_index + 1}</span></h3>
          <p>${escapeHtml(message.content)}</p>
        </div>
      `);
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
        <h2>Key Points</h2>
        <div class="stack">
          ${Object.entries(data.summary.key_points).map(([agent, point]) => `
            <div class="message">
              <h3>${escapeHtml(agent)}</h3>
              <p>${escapeHtml(point)}</p>
            </div>
          `).join("")}
        </div>
      `;
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

    form.addEventListener("submit", async event => {
      event.preventDefault();
      startLiveRun();
      statusBox.className = "muted";
      statusBox.textContent = "Starting analysis...";
      submitButton.disabled = true;
      const selectedAgents = [...document.querySelectorAll("input[name='agent']:checked")].map(input => input.value);
      try {
        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            topic: document.querySelector("#topic").value,
            max_rounds: Number(document.querySelector("#maxRounds").value),
            agents: selectedAgents
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
        selected_agents = set(payload.get("agents") or [])
        if selected_agents:
            config.agents = [agent for agent in config.agents if agent.name in selected_agents]
        if not config.agents:
            raise ValueError("Select at least one analyst profile.")

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
