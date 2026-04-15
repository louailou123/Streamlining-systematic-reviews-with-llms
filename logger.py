"""
LiRA Pipeline Logger — Rich HTML Output
Creates beautiful, color-coded HTML log files for every pipeline execution.
Open the .html file in any browser to explore the full execution log.
"""

import os
import json
import time
import html
import sys
import traceback
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────────────────────────
# HTML TEMPLATE
# ──────────────────────────────────────────────────────────────

HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LiRA Run — {run_id}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

  :root {{
    --bg: #0d1117;
    --surface: #161b22;
    --surface-2: #1c2333;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --orange: #d29922;
    --purple: #bc8cff;
    --cyan: #39d2c0;
    --pink: #f778ba;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    line-height: 1.6;
    padding: 24px;
    max-width: 1400px;
    margin: 0 auto;
  }}

  h1 {{
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}

  .header-meta {{
    color: var(--text-dim);
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 24px;
    padding: 12px 16px;
    background: var(--surface);
    border-radius: 8px;
    border: 1px solid var(--border);
  }}
  .header-meta span {{ color: var(--cyan); }}

  /* Node sections */
  .node-section {{
    margin: 16px 0;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    overflow: hidden;
    transition: box-shadow 0.2s;
  }}
  .node-section:hover {{
    box-shadow: 0 0 20px rgba(88, 166, 255, 0.08);
  }}

  .node-header {{
    padding: 12px 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 12px;
    user-select: none;
    font-weight: 600;
  }}
  .node-header:hover {{ background: var(--surface-2); }}

  .node-header .arrow {{
    transition: transform 0.2s;
    color: var(--text-dim);
    font-size: 0.8rem;
  }}
  .node-header.open .arrow {{ transform: rotate(90deg); }}

  .node-number {{
    background: var(--accent);
    color: var(--bg);
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
  }}

  .node-name {{
    font-size: 1rem;
    color: var(--text);
  }}

  .node-time {{
    margin-left: auto;
    font-size: 0.78rem;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
  }}

  .node-body {{
    display: none;
    padding: 16px 20px;
    border-top: 1px solid var(--border);
  }}
  .node-section.open .node-body {{ display: block; }}

  /* Color-coded badges for steps */
  .step1 .node-number {{ background: var(--green); }}
  .step2 .node-number {{ background: var(--orange); }}
  .step3 .node-number {{ background: var(--purple); }}
  .step4 .node-number {{ background: var(--cyan); }}
  .step5 .node-number {{ background: var(--pink); }}
  .tool-node .node-number {{ background: var(--pink); }}

  /* Sub-sections inside nodes */
  .sub-section {{
    margin: 10px 0;
    padding: 10px 14px;
    background: var(--surface-2);
    border-radius: 6px;
    border-left: 3px solid var(--border);
  }}
  .sub-section.messages {{ border-left-color: var(--accent); }}
  .sub-section.state {{ border-left-color: var(--green); }}
  .sub-section.tools {{ border-left-color: var(--orange); }}
  .sub-section.error {{ border-left-color: var(--red); background: rgba(248,81,73,0.08); }}
  .sub-section.timing {{ border-left-color: var(--cyan); }}
  .sub-section.metadata {{ border-left-color: var(--purple); }}

  .sub-title {{
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-dim);
    margin-bottom: 8px;
  }}

  /* Code / content blocks */
  .content-block {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text);
  }}

  .field-name {{ color: var(--cyan); font-weight: 600; }}
  .field-value {{ color: var(--text); }}
  .msg-type {{ color: var(--purple); font-weight: 600; }}
  .tool-name {{ color: var(--orange); font-weight: 600; }}
  .label-inc {{ color: var(--green); font-weight: 600; }}
  .label-exc {{ color: var(--red); font-weight: 600; }}
  .dim {{ color: var(--text-dim); }}

  /* Message card */
  .msg-card {{
    margin: 8px 0;
    padding: 10px 12px;
    background: var(--bg);
    border-radius: 6px;
    border: 1px solid var(--border);
  }}
  .msg-card .msg-header {{
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  /* Summary table */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    margin: 12px 0;
  }}
  th {{
    text-align: left;
    padding: 8px 12px;
    background: var(--surface-2);
    color: var(--accent);
    font-weight: 600;
    border-bottom: 2px solid var(--border);
  }}
  td {{
    padding: 6px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }}
  tr:hover td {{ background: var(--surface-2); }}

  /* Expand all button */
  .controls {{
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }}
  .btn {{
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
    font-size: 0.8rem;
    cursor: pointer;
    font-family: 'Inter', sans-serif;
  }}
  .btn:hover {{ background: var(--surface-2); border-color: var(--accent); }}
</style>
</head>
<body>
<h1>🔬 LiRA Pipeline — Execution Log</h1>
<div class="header-meta">
  <span>Run ID:</span> {run_id} &nbsp;|&nbsp;
  <span>Started:</span> {start_time} &nbsp;|&nbsp;
  <span>Python:</span> {python_ver} &nbsp;|&nbsp;
  <span>CWD:</span> {cwd}
</div>
<div class="controls">
  <button class="btn" onclick="toggleAll(true)">▼ Expand All</button>
  <button class="btn" onclick="toggleAll(false)">▲ Collapse All</button>
</div>
<div id="log-body">
"""

HTML_TAIL = """
</div>
<script>
function toggleNode(el) {
  const section = el.closest('.node-section');
  section.classList.toggle('open');
  el.classList.toggle('open');
}
function toggleAll(expand) {
  document.querySelectorAll('.node-section').forEach(s => {
    if (expand) s.classList.add('open');
    else s.classList.remove('open');
  });
  document.querySelectorAll('.node-header').forEach(h => {
    if (expand) h.classList.add('open');
    else h.classList.remove('open');
  });
}
</script>
</body>
</html>
"""


# ──────────────────────────────────────────────────────────────
# NODE STEP CLASSIFICATION
# ──────────────────────────────────────────────────────────────

STEP1_NODES = {
    "generate_initial_questions", "select_framework", "apply_framework",
    "feasibility_llm_call", "tool_node", "parse_feasibility",
    "originality_llm_call", "tool_node_2", "parse_originality",
    "rank_questions_llm_call", "generate_final_ranked_questions",
}
STEP2_NODES = {
    "extract_keywords", "select_databases", "build_search_queries",
    "define_criteria", "prepare_search", "search_llm_call",
    "tool_node_search", "save_papers",
}
STEP3_NODES = {"deduplicate", "llm_classify", "asreview_screen"}
STEP4_NODES = {"metadata_insights", "thematic_augmentation", "augmented_analysis"}
STEP5_NODES = {"generate_outline", "draft_sections", "proofread_draft"}
TOOL_NODES = {"tool_node", "tool_node_2", "tool_node_search"}


def _node_css_class(name: str) -> str:
    if name in TOOL_NODES:
        return "tool-node"
    if name in STEP1_NODES:
        return "step1"
    if name in STEP2_NODES:
        return "step2"
    if name in STEP3_NODES:
        return "step3"
    if name in STEP4_NODES:
        return "step4"
    if name in STEP5_NODES:
        return "step5"
    return ""


# ──────────────────────────────────────────────────────────────
# LOGGER CLASS
# ──────────────────────────────────────────────────────────────

class LiRALogger:
    """Generates a rich HTML execution log."""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.logs_dir = os.path.join(self.base_dir, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)

        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.logs_dir, f"lira_run_{self.run_id}.html")

        # Timing
        self.pipeline_start = time.time()
        self.node_timings = []
        self.node_counter = 0
        self._current_node_start = None

        # Open file and write header
        self._file = open(self.log_file, "w", encoding="utf-8")
        self._file.write(HTML_HEAD.format(
            run_id=self.run_id,
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            python_ver=html.escape(sys.version.split()[0]),
            cwd=html.escape(os.getcwd()),
        ))
        self._file.flush()

    def _w(self, text: str):
        self._file.write(text)

    def _esc(self, text) -> str:
        if text is None:
            return ""
        return html.escape(str(text))

    def _json_pretty(self, obj, max_len: int = 10000) -> str:
        try:
            text = json.dumps(obj, ensure_ascii=False, default=str, indent=2)
        except Exception:
            text = str(obj)
        if len(text) > max_len:
            text = text[:max_len] + f"\n... [TRUNCATED — {len(text)} total chars]"
        return self._esc(text)

    # ──────────────────────────────────────────────────────────────
    # PIPELINE LIFECYCLE
    # ──────────────────────────────────────────────────────────────

    def log_initial_input(self, initial_input: dict):
        self._w('<div class="node-section open">')
        self._w('<div class="node-header open" onclick="toggleNode(this)">')
        self._w('<span class="arrow">▶</span>')
        self._w('<span class="node-name">📋 Initial Input</span>')
        self._w('</div>')
        self._w('<div class="node-body">')
        self._w('<div class="sub-section state">')
        self._w('<div class="sub-title">Pipeline Input</div>')
        self._w('<div class="content-block">')
        for key, value in initial_input.items():
            if key == "messages":
                self._w(f'<span class="field-name">{self._esc(key)}</span>: [{len(value)} messages]\n')
            else:
                self._w(f'<span class="field-name">{self._esc(key)}</span>: {self._esc(str(value))}\n')
        self._w('</div></div></div></div>')

    def log_graph_structure(self, graph):
        self._w('<div class="node-section">')
        self._w('<div class="node-header" onclick="toggleNode(this)">')
        self._w('<span class="arrow">▶</span>')
        self._w('<span class="node-name">🗺️ Graph Structure</span>')
        self._w('</div>')
        self._w('<div class="node-body">')
        self._w('<div class="sub-section state">')
        self._w('<div class="sub-title">Nodes &amp; Edges</div>')
        self._w('<div class="content-block">')
        try:
            g = graph.get_graph()
            nodes = list(g.nodes.keys())
            self._w(f'<span class="field-name">Nodes</span> ({len(nodes)}):\n')
            for n in nodes:
                css = _node_css_class(n)
                color = {"step1": "var(--green)", "step2": "var(--orange)", "step3": "var(--purple)", "tool-node": "var(--pink)"}.get(css, "var(--text)")
                self._w(f'  <span style="color:{color}">● {self._esc(n)}</span>\n')
            self._w(f'\n<span class="field-name">Edges</span>:\n')
            for edge in g.edges:
                self._w(f'  {self._esc(str(edge))}\n')
        except Exception as e:
            self._w(f'Could not extract graph: {self._esc(str(e))}')
        self._w('</div></div></div></div>')

    # ──────────────────────────────────────────────────────────────
    # NODE EXECUTION
    # ──────────────────────────────────────────────────────────────

    def node_start(self, node_name: str):
        self.node_counter += 1
        self._current_node_start = time.time()

    def node_end(self, node_name: str, state_update: dict):
        node_elapsed = time.time() - (self._current_node_start or time.time())
        total_elapsed = time.time() - self.pipeline_start

        self.node_timings.append({
            "order": self.node_counter,
            "node": node_name,
            "elapsed_s": round(node_elapsed, 2),
            "total_s": round(total_elapsed, 2),
        })

        css_class = _node_css_class(node_name)

        self._w(f'<div class="node-section {css_class}">')
        self._w(f'<div class="node-header" onclick="toggleNode(this)">')
        self._w(f'<span class="arrow">▶</span>')
        self._w(f'<span class="node-number">#{self.node_counter}</span>')
        self._w(f'<span class="node-name">{self._esc(node_name)}</span>')
        self._w(f'<span class="node-time">{node_elapsed:.2f}s  |  T+{total_elapsed:.1f}s</span>')
        self._w(f'</div>')
        self._w(f'<div class="node-body">')

        # Timing
        self._w('<div class="sub-section timing">')
        self._w('<div class="sub-title">⏱️ Timing</div>')
        self._w('<div class="content-block">')
        self._w(f'<span class="field-name">Node duration</span> : {node_elapsed:.3f}s\n')
        self._w(f'<span class="field-name">Total elapsed</span> : {total_elapsed:.2f}s\n')
        self._w('</div></div>')

        # State update — every field
        self._log_state_update(node_name, state_update)

        self._w('</div></div>')  # close node-body + node-section
        self._file.flush()

    def _log_state_update(self, node_name: str, state_update: dict):
        for key, value in state_update.items():
            if key == "messages":
                self._log_messages(value)
            elif key == "logs":
                self._w('<div class="sub-section state">')
                self._w(f'<div class="sub-title">📝 Logs ({len(value)} entries)</div>')
                self._w('<div class="content-block">')
                for i, entry in enumerate(value):
                    self._w(f'<span class="dim">[{i}]</span> {self._esc(str(entry))}\n')
                self._w('</div></div>')
            elif isinstance(value, list):
                self._w('<div class="sub-section state">')
                self._w(f'<div class="sub-title">📦 {self._esc(key)} ({len(value)} items)</div>')
                self._w('<div class="content-block">')
                for i, item in enumerate(value):
                    self._w(f'<span class="dim">[{i}]</span> {self._json_pretty(item, 2000)}\n')
                self._w('</div></div>')
            elif isinstance(value, dict):
                self._w('<div class="sub-section state">')
                self._w(f'<div class="sub-title">📦 {self._esc(key)}</div>')
                self._w(f'<div class="content-block">{self._json_pretty(value, 5000)}</div>')
                self._w('</div>')
            elif isinstance(value, str):
                self._w('<div class="sub-section state">')
                self._w(f'<div class="sub-title">📦 {self._esc(key)} ({len(value)} chars)</div>')
                self._w(f'<div class="content-block">{self._esc(value)}</div>')
                self._w('</div>')
            else:
                self._w('<div class="sub-section state">')
                self._w(f'<div class="sub-title">📦 {self._esc(key)}</div>')
                self._w(f'<div class="content-block">{self._esc(str(value))}</div>')
                self._w('</div>')

    # ──────────────────────────────────────────────────────────────
    # MESSAGES
    # ──────────────────────────────────────────────────────────────

    def _log_messages(self, messages: list):
        self._w(f'<div class="sub-section messages">')
        self._w(f'<div class="sub-title">💬 Messages ({len(messages)})</div>')

        for i, msg in enumerate(messages):
            msg_type = msg.__class__.__name__
            msg_id = getattr(msg, "id", "N/A")

            self._w('<div class="msg-card">')
            self._w(f'<div class="msg-header"><span class="msg-type">{self._esc(msg_type)}</span> <span class="dim">id={self._esc(str(msg_id))}</span></div>')

            # Content
            content = getattr(msg, "content", "")
            if isinstance(content, str) and content:
                self._w(f'<div class="content-block">{self._esc(content)}</div>')
            elif isinstance(content, list):
                self._w(f'<div class="content-block">{self._json_pretty(content, 5000)}</div>')

            # Tool Calls
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                self._w('<div style="margin-top:8px">')
                for j, tc in enumerate(tool_calls):
                    self._w(f'<div style="margin:4px 0; padding:6px 10px; background:var(--bg); border-radius:4px; border:1px solid var(--border)">')
                    self._w(f'<span class="tool-name">🔧 {self._esc(tc.get("name", "unknown"))}</span> ')
                    self._w(f'<span class="dim">id={self._esc(tc.get("id", "N/A"))}</span>\n')
                    self._w(f'<div class="content-block" style="margin-top:4px"><span class="field-name">args:</span>\n{self._json_pretty(tc.get("args", {}), 3000)}</div>')
                    self._w('</div>')
                self._w('</div>')

            # Tool Call ID (ToolMessage)
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id:
                self._w(f'<div class="content-block" style="margin-top:4px"><span class="field-name">tool_call_id:</span> {self._esc(tool_call_id)}</div>')

            # Response metadata
            resp_meta = getattr(msg, "response_metadata", None)
            if resp_meta:
                self._w(f'<div class="sub-section metadata" style="margin-top:8px">')
                self._w(f'<div class="sub-title">Response Metadata</div>')
                self._w(f'<div class="content-block">{self._json_pretty(resp_meta, 1500)}</div>')
                self._w('</div>')

            # Usage metadata
            usage = getattr(msg, "usage_metadata", None)
            if usage:
                self._w(f'<div class="sub-section metadata" style="margin-top:4px">')
                self._w(f'<div class="sub-title">Token Usage</div>')
                self._w(f'<div class="content-block">{self._json_pretty(usage, 500)}</div>')
                self._w('</div>')

            self._w('</div>')  # close msg-card

        self._w('</div>')  # close messages sub-section

    # ──────────────────────────────────────────────────────────────
    # ERROR
    # ──────────────────────────────────────────────────────────────

    def log_error(self, error: Exception):
        self._w('<div class="node-section open">')
        self._w('<div class="node-header open" onclick="toggleNode(this)">')
        self._w('<span class="arrow">▶</span>')
        self._w('<span class="node-name" style="color:var(--red)">❌ Pipeline Error</span>')
        self._w('</div>')
        self._w('<div class="node-body">')
        self._w('<div class="sub-section error">')
        self._w(f'<div class="sub-title">Error Details</div>')
        self._w(f'<div class="content-block">')
        self._w(f'<span class="field-name">Type</span>    : {self._esc(type(error).__name__)}\n')
        self._w(f'<span class="field-name">Message</span> : {self._esc(str(error))}\n\n')
        self._w(f'<span class="field-name">Traceback:</span>\n{self._esc(traceback.format_exc())}')
        self._w('</div></div></div></div>')
        self._file.flush()

    # ──────────────────────────────────────────────────────────────
    # FINAL STATE + SUMMARY
    # ──────────────────────────────────────────────────────────────

    def log_final_state(self, final_state: dict):
        self._w('<div class="node-section">')
        self._w('<div class="node-header" onclick="toggleNode(this)">')
        self._w('<span class="arrow">▶</span>')
        self._w('<span class="node-name">📊 Final State Snapshot</span>')
        self._w('</div>')
        self._w('<div class="node-body">')

        if not final_state:
            self._w('<div class="sub-section state"><div class="content-block dim">No final state captured.</div></div>')
        else:
            for key, value in final_state.items():
                if key == "messages":
                    self._w(f'<div class="sub-section state"><div class="sub-title">{self._esc(key)}</div>')
                    self._w(f'<div class="content-block dim">[{len(value)} messages — see above per node]</div></div>')
                elif isinstance(value, list):
                    self._w(f'<div class="sub-section state"><div class="sub-title">{self._esc(key)} ({len(value)} items)</div>')
                    self._w(f'<div class="content-block">{self._json_pretty(value, 10000)}</div></div>')
                elif isinstance(value, dict):
                    self._w(f'<div class="sub-section state"><div class="sub-title">{self._esc(key)}</div>')
                    self._w(f'<div class="content-block">{self._json_pretty(value, 5000)}</div></div>')
                else:
                    self._w(f'<div class="sub-section state"><div class="sub-title">{self._esc(key)}</div>')
                    self._w(f'<div class="content-block">{self._esc(str(value))}</div></div>')

        self._w('</div></div>')

    def log_summary(self):
        total_time = time.time() - self.pipeline_start

        self._w('<div class="node-section open">')
        self._w('<div class="node-header open" onclick="toggleNode(this)">')
        self._w('<span class="arrow">▶</span>')
        self._w(f'<span class="node-name">📈 Execution Summary</span>')
        self._w(f'<span class="node-time">{total_time:.2f}s total</span>')
        self._w('</div>')
        self._w('<div class="node-body">')

        self._w('<div class="sub-section timing">')
        self._w(f'<div class="sub-title">Overall</div>')
        self._w(f'<div class="content-block">')
        self._w(f'<span class="field-name">Finished at</span>    : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        self._w(f'<span class="field-name">Nodes executed</span> : {self.node_counter}\n')
        self._w(f'<span class="field-name">Total wall time</span>: {total_time:.2f}s ({total_time/60:.1f} min)\n')
        self._w('</div></div>')

        # Timing table
        self._w('<div class="sub-section timing">')
        self._w('<div class="sub-title">Node Timing Breakdown</div>')
        self._w('<table><thead><tr><th>#</th><th>Node</th><th>Duration</th><th>Cumulative</th></tr></thead><tbody>')
        for t in self.node_timings:
            css = _node_css_class(t["node"])
            color = {"step1": "var(--green)", "step2": "var(--orange)", "step3": "var(--purple)", "tool-node": "var(--pink)"}.get(css, "var(--text)")
            self._w(f'<tr><td>{t["order"]}</td>')
            self._w(f'<td style="color:{color}">{self._esc(t["node"])}</td>')
            self._w(f'<td>{t["elapsed_s"]:.2f}s</td>')
            self._w(f'<td>{t["total_s"]:.2f}s</td></tr>')
        self._w('</tbody></table>')
        self._w('</div>')

        self._w('</div></div>')

        # Write closing HTML
        self._w(HTML_TAIL)
        self._file.close()

    def close(self):
        """Alias for log_summary."""
        self.log_summary()
