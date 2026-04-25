"""
LiRA Backend — Workflow Engine
Builds the LangGraph pipeline graph with SELECTIVE human-in-the-loop approval gates.

Only specific nodes get approval gates:
  - generate_initial_questions
  - select_framework, apply_framework (framework nodes)
  - parse_feasibility (feedback goes back to generate_initial_questions)
  - extract_keywords
  - build_search_queries
  - define_criteria
  - llm_classify (download asreview_import.csv)
  - asreview_screen (upload ASReview export file)

All other nodes execute and auto-continue without user review.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so we can import from the existing pipeline code
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from langchain_core.messages import AIMessage, HumanMessage

# Import from existing pipeline code (preserved, no modifications)
from State.state import LiRAState
from agents.agent_1 import (
    generate_initial_questions_node,
    select_framework_node,
    apply_framework_node,
    parse_feasibility_node,
    parse_originality_node,
    generate_final_ranked_questions_node,
)
from agents.agent_2 import (
    extract_keywords_node,
    select_databases_node,
    build_search_queries_node,
    define_criteria_node,
    prepare_search_node,
    save_papers_node,
)
from agents.agent_3 import (
    deduplicate_node,
    llm_classify_node,
    asreview_screen_node,
)
from agents.agent_4 import (
    metadata_insights_node,
    thematic_augmentation_node,
    augmented_analysis_node,
)
from agents.agent_5 import (
    generate_outline_node,
    draft_sections_node,
    proofread_draft_node,
)
from tools.serpapi_tool import tools as search_tools
from llm.llm import get_llm
from app.workflow.message_guard import guard_node


# ── Node name → step label mapping ──────────────────────────

NODE_STEP_MAP = {
    "generate_initial_questions": "Step 1.a",
    "select_framework": "Step 1.a",
    "apply_framework": "Step 1.a",
    "feasibility_llm_call": "Step 1.b",
    "tool_node": "Step 1.b",
    "parse_feasibility": "Step 1.b",
    "originality_llm_call": "Step 1.c",
    "tool_node_2": "Step 1.c",
    "parse_originality": "Step 1.c",
    "rank_questions_llm_call": "Step 1.d",
    "generate_final_ranked_questions": "Step 1.d",
    "extract_keywords": "Step 2.a",
    "select_databases": "Step 2.b",
    "build_search_queries": "Step 2.c",
    "define_criteria": "Step 2.d",
    "prepare_search": "Step 2.e",
    "save_papers": "Step 2.f",
    "deduplicate": "Step 3.a",
    "llm_classify": "Step 3.b",
    "asreview_screen": "Step 3.c",
    "metadata_insights": "Step 4.a",
    "thematic_augmentation": "Step 4.b",
    "augmented_analysis": "Step 4.c",
    "generate_outline": "Step 5.a",
    "draft_sections": "Step 5.b",
    "proofread_draft": "Step 5.c",
}

NODE_DESCRIPTIONS = {
    "generate_initial_questions": "Generating initial research questions",
    "select_framework": "Selecting research framework",
    "apply_framework": "Applying framework to reframe question",
    "feasibility_llm_call": "Assessing feasibility via search",
    "tool_node": "Executing search tools",
    "parse_feasibility": "Parsing feasibility assessment",
    "originality_llm_call": "Checking originality via surveys",
    "tool_node_2": "Executing search tools",
    "parse_originality": "Parsing originality assessment",
    "rank_questions_llm_call": "Generating final ranked questions",
    "generate_final_ranked_questions": "Parsing ranked questions",
    "extract_keywords": "Extracting search keywords",
    "select_databases": "Selecting databases",
    "build_search_queries": "Building Boolean search queries",
    "define_criteria": "Defining inclusion/exclusion criteria",
    "prepare_search": "Executing searches across databases",
    "save_papers": "Processing and saving papers",
    "deduplicate": "Removing duplicate papers",
    "llm_classify": "LLM screening papers",
    "asreview_screen": "ASReview manual screening (human-in-the-loop)",
    "metadata_insights": "Generating metadata insights",
    "thematic_augmentation": "LLM thematic extraction per paper",
    "augmented_analysis": "Analysis + visualizations",
    "generate_outline": "Generating literature review outline",
    "draft_sections": "Drafting review sections with ChatPDF",
    "proofread_draft": "Proofreading and refining draft",
}


# ── Approval Gate Definitions ───────────────────────────────
# SELECTIVE GATES — only these nodes pause for user review.
# Each tuple: (gate_node_name, gated_real_node, improve_target, continue_target)
# improve_target: where to route on "improve_result" (re-run)
# continue_target: where to route on "continue" (next step)

APPROVAL_GATES = [
    # Step 1 — Research Question
    ("gate_gen_questions",   "generate_initial_questions",      "generate_initial_questions",  "select_framework"),
    ("gate_sel_framework",   "select_framework",                "select_framework",            "apply_framework"),
    ("gate_apply_framework", "apply_framework",                 "apply_framework",             "feasibility_llm_call"),
    # parse_feasibility: feedback sends user back to generate_initial_questions
    ("gate_feasibility",     "parse_feasibility",               "generate_initial_questions",   "originality_llm_call"),
    # Step 2 — Keywords, Queries, Criteria
    ("gate_keywords",        "extract_keywords",                "extract_keywords",            "select_databases"),
    ("gate_queries",         "build_search_queries",            "build_search_queries",        "define_criteria"),
    ("gate_criteria",        "define_criteria",                 "define_criteria",             "prepare_search"),
    # Step 3 — After LLM screening (download asreview_import.csv) and ASReview upload
    ("gate_llm_screen",      "llm_classify",                   "llm_classify",                "asreview_screen"),
    ("gate_asreview",        "asreview_screen",                 "asreview_screen",             "metadata_insights"),
]

# Set of gate node names (for runner to distinguish from real nodes)
GATE_NODE_NAMES = {g[0] for g in APPROVAL_GATES}

# Populate step maps for gate nodes (inherit from their parent)
for gate_name, gated_node, _, _ in APPROVAL_GATES:
    NODE_STEP_MAP[gate_name] = NODE_STEP_MAP.get(gated_node, "")
    NODE_DESCRIPTIONS[gate_name] = f"Approval: {NODE_DESCRIPTIONS.get(gated_node, gated_node)}"


DEFAULT_WEB_MODEL_NAME = (
    os.getenv("LLM_MODEL_1")
    or os.getenv("LLM_MODEL")
    or "llama-3.3-70b-versatile"
)
TOOL_ENABLED_WEB_MODEL_NAME = f"{DEFAULT_WEB_MODEL_NAME}::tools"
TOOL_ENABLED_INTERNAL_NODES = {
    "feasibility_llm_call",
    "originality_llm_call",
    "tool_node",
    "tool_node_2",
}


def _select_web_model_name(node_name: str, _state: LiRAState) -> str:
    if node_name in TOOL_ENABLED_INTERNAL_NODES:
        return TOOL_ENABLED_WEB_MODEL_NAME
    return DEFAULT_WEB_MODEL_NAME


def _feedback_inject_wrapper(node_name: str, node_fn):
    """
    Wraps a node function so that when user_feedback is present in state,
    a complete revision prompt (using FEEDBACK_REVISION_PROMPT) is injected
    into the topic field — because agent nodes build their own prompts
    from state fields (topic, keywords, etc.), NOT from the messages list.
    """
    import json as _json
    from Prompts.prompts import (
        FEEDBACK_REVISION_PROMPT,
        PROMPT_1_INITIAL_GENERATION,
        PROMPT_2_FRAMEWORK_SELECTION,
        PROMPT_3_FRAMEWORK_APPLICATION,
        KEYWORD_EXTRACTION_PROMPT,
        QUERY_BUILDER_PROMPT,
        CRITERIA_PROMPT,
    )

    # Map each node to its original prompt template and the state keys it needs
    _NODE_PROMPT_MAP = {
        "generate_initial_questions": {
            "template": PROMPT_1_INITIAL_GENERATION,
            "vars": lambda s: {"topic": s.get("topic", "")},
            "output_keys": ["initial_questions"],
        },
        "select_framework": {
            "template": PROMPT_2_FRAMEWORK_SELECTION,
            "vars": lambda s: {"topic": s.get("topic", "")},
            "output_keys": ["selected_framework", "framework_justification"],
        },
        "apply_framework": {
            "template": PROMPT_3_FRAMEWORK_APPLICATION,
            "vars": lambda s: {
                "question": (s.get("initial_questions", [None]) or [None])[0] or s.get("topic", ""),
                "framework": s.get("selected_framework", "PICO"),
            },
            "output_keys": ["framework_breakdown", "reframed_question"],
        },
        "extract_keywords": {
            "template": KEYWORD_EXTRACTION_PROMPT,
            "vars": lambda s: {
                "question": (s.get("final_ranked_questions", [{}]) or [{}])[0].get("question", "")
                             if s.get("final_ranked_questions")
                             else s.get("reframed_question", s.get("topic", "")),
            },
            "output_keys": ["keywords"],
        },
        "build_search_queries": {
            "template": QUERY_BUILDER_PROMPT,
            "vars": lambda s: {
                "keywords": ", ".join(s.get("keywords", [])),
                "databases": ", ".join(s.get("databases", [])),
            },
            "output_keys": ["search_queries"],
        },
        "define_criteria": {
            "template": CRITERIA_PROMPT,
            "vars": lambda s: {
                "question": (s.get("final_ranked_questions", [{}]) or [{}])[0].get("question", "")
                             if s.get("final_ranked_questions")
                             else s.get("reframed_question", s.get("topic", "")),
            },
            "output_keys": ["inclusion_criteria", "exclusion_criteria"],
        },
    }

    def wrapped(state: LiRAState):
        user_feedback = state.get("user_feedback")
        if not user_feedback:
            return node_fn(state)

        prompt_info = _NODE_PROMPT_MAP.get(node_name)
        if not prompt_info:
            # Node not in the map — run without feedback injection
            return node_fn(state)

        # 1. Render the ORIGINAL PROMPT (what the LLM received the first time)
        try:
            template_vars = prompt_info["vars"](state)
            original_prompt = prompt_info["template"].format(**template_vars)
        except Exception:
            original_prompt = prompt_info["template"]

        # 2. Collect the LLM RESULT (what the LLM produced)
        output_keys = prompt_info["output_keys"]
        result_parts = []
        for key in output_keys:
            val = state.get(key)
            if val is not None:
                if isinstance(val, (list, dict)):
                    result_parts.append(f"{key}: {_json.dumps(val, default=str)}")
                else:
                    result_parts.append(f"{key}: {val}")
        llm_result = "\n".join(result_parts) if result_parts else "(no previous output)"

        # 3. Build the full FEEDBACK_REVISION_PROMPT with all three sections
        revision_prompt = FEEDBACK_REVISION_PROMPT.format(
            original_prompt=original_prompt,
            llm_result=llm_result,
            user_feedback=user_feedback,
        )

        # 4. Inject the revision prompt into the topic field
        injected_state = dict(state)
        injected_state["topic"] = revision_prompt

        # Also inject into final_ranked_questions if the node reads those
        if node_name in ("extract_keywords", "define_criteria"):
            questions = state.get("final_ranked_questions")
            if questions and isinstance(questions, list) and len(questions) > 0:
                q = questions[0]
                if isinstance(q, dict) and "question" in q:
                    injected_state["final_ranked_questions"] = [
                        {"question": revision_prompt, **{k: v for k, v in q.items() if k != "question"}}
                    ] + questions[1:]

        # 5. Run the node and clear user_feedback so it doesn't loop
        result = node_fn(injected_state)
        if isinstance(result, dict):
            result["user_feedback"] = None
        return result

    wrapped.__name__ = getattr(node_fn, "__name__", f"feedback_wrapped_{node_name}")
    return wrapped


# Nodes that have feedback-capable prompts (from _NODE_PROMPT_MAP inside the wrapper)
_FEEDBACK_CAPABLE_NODES = {
    "generate_initial_questions", "select_framework", "apply_framework",
    "extract_keywords", "build_search_queries", "define_criteria",
}


def _add_guarded_node(graph: StateGraph, node_name: str, node_fn):
    if node_name in _FEEDBACK_CAPABLE_NODES:
        wrapped_fn = _feedback_inject_wrapper(node_name, node_fn)
        graph.add_node(node_name, guard_node(node_name, wrapped_fn, _select_web_model_name))
    else:
        graph.add_node(node_name, guard_node(node_name, node_fn, _select_web_model_name))


# ── Gate Factory Functions ──────────────────────────────────

def _make_approval_gate(node_name: str, step_label: str, description: str):
    """
    Create an approval gate node function.
    When executed, it calls interrupt() to pause the graph.
    Includes the output_summary from the gated node so the frontend can display it.
    """
    # Map each node to which state keys hold its output
    NODE_OUTPUT_KEYS = {
        "generate_initial_questions": ["initial_questions"],
        "select_framework": ["selected_framework", "framework_justification"],
        "apply_framework": ["framework_breakdown", "reframed_question"],
        "parse_feasibility": ["feasibility_estimation", "feasibility_status"],
        "parse_originality": ["survey_summaries", "overlap", "gaps"],
        "generate_final_ranked_questions": ["final_ranked_questions"],
        "extract_keywords": ["keywords"],
        "select_databases": ["databases"],
        "build_search_queries": ["search_queries"],
        "define_criteria": ["inclusion_criteria", "exclusion_criteria"],
        "prepare_search": ["search_metadata"],
        "save_papers": ["raw_dataset_csv"],
        "deduplicate": ["deduplicated_csv"],
        "llm_classify": ["screened_llm_csv"],
        "asreview_screen": ["asreview_screened_csv", "initial_dataset_csv"],
        "metadata_insights": ["metadata_insights"],
        "thematic_augmentation": ["thematic_summary"],
        "augmented_analysis": ["analysis_report"],
        "generate_outline": ["outline"],
        "draft_sections": ["draft_sections"],
        "proofread_draft": ["final_draft_markdown"],
    }

    # Determine approval_type based on which node this gate is for
    def _get_approval_type():
        if node_name == "llm_classify":
            return "download_and_continue"
        if node_name == "asreview_screen":
            return "asreview_upload"
        return "node_approval"

    def gate_fn(state: LiRAState):
        # Build output summary for the interrupt payload
        output_keys = NODE_OUTPUT_KEYS.get(node_name, [])
        output_summary = {}
        for key in output_keys:
            val = state.get(key)
            if val is not None:
                output_summary[key] = val

        approval_type = _get_approval_type()

        # Extra data for special approval types
        extra_data = {}
        if approval_type == "download_and_continue":
            extra_data["download_file"] = "asreview_import.csv"
            extra_data["download_description"] = "Download the ASReview import file with LLM screening results"
        elif approval_type == "asreview_upload":
            asreview_port = os.getenv("ASREVIEW_PORT", "5001")
            extra_data["asreview_url"] = f"http://localhost:{asreview_port}"
            extra_data["upload_description"] = "Upload the exported ASReview result CSV file"

        # Pause the graph
        resume_action = interrupt({
            "type": "node_approval",
            "node_name": node_name,
            "step_label": step_label,
            "description": description,
            "approval_type": approval_type,
            "output_summary": output_summary,
            **extra_data,
        })

        # Parse the resume action
        action = "continue"
        feedback = None
        uploaded_file = None
        if isinstance(resume_action, dict):
            action = resume_action.get("action", "continue")
            feedback = resume_action.get("feedback")
            uploaded_file = resume_action.get("uploaded_file")

        if action == "improve_result" and feedback:
            # Store feedback so the _feedback_inject_wrapper picks it up
            # when the target node re-runs
            return {
                "user_feedback": feedback,
                "current_approval_node": node_name,
            }

        # For asreview_upload: pass the uploaded file path through state
        if approval_type == "asreview_upload" and uploaded_file:
            return {
                "user_feedback": None,
                "current_approval_node": None,
                "_asreview_uploaded_file": uploaded_file,
            }

        # Continue: clear feedback state
        return {
            "user_feedback": None,
            "current_approval_node": None,
        }

    gate_fn.__name__ = f"gate_{node_name}"
    return gate_fn


def _make_gate_router(gated_node: str, improve_target: str, continue_target: str):
    """
    Create a conditional router for an approval gate.
    Routes back to improve_target on revision, or forward to continue_target.
    """
    def router(state: LiRAState) -> str:
        if state.get("current_approval_node") == gated_node:
            return improve_target
        return continue_target

    router.__name__ = f"route_gate_{gated_node}"
    return router


# ── Conditional Edge Functions (unchanged) ──────────────────

def _should_continue_feasibility(state: LiRAState) -> str:
    """Route: if the LLM made a tool call, go to tool_node; else parse."""
    last = state["messages"][-1] if state.get("messages") else None
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tool_node"
    return "parse_feasibility"


def _should_continue_originality(state: LiRAState) -> str:
    """Route: if the LLM made a tool call, go to tool_node_2; else parse."""
    last = state["messages"][-1] if state.get("messages") else None
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tool_node_2"
    return "parse_originality"





# ── Graph Builder ───────────────────────────────────────────

def build_lira_graph() -> StateGraph:
    """
    Build the full LiRA pipeline graph with SELECTIVE approval gates.

    Only specific nodes get approval gates. All other nodes connect
    directly without pausing for user review.
    """
    llm = get_llm()
    llm_with_tools = get_llm(tools=search_tools)

    # ── Internal LLM call nodes (not gated — internal routing) ──

    def feasibility_llm_call(state: LiRAState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def originality_llm_call(state: LiRAState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def rank_questions_llm_call(state: LiRAState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools=search_tools)
    tool_node_2 = ToolNode(tools=search_tools)

    graph = StateGraph(LiRAState)

    # ── Register all real nodes ─────────────────────────────

    # Step 1
    _add_guarded_node(graph, "generate_initial_questions", generate_initial_questions_node)
    _add_guarded_node(graph, "select_framework", select_framework_node)
    _add_guarded_node(graph, "apply_framework", apply_framework_node)
    _add_guarded_node(graph, "feasibility_llm_call", feasibility_llm_call)
    _add_guarded_node(graph, "tool_node", tool_node)
    _add_guarded_node(graph, "parse_feasibility", parse_feasibility_node)
    _add_guarded_node(graph, "originality_llm_call", originality_llm_call)
    _add_guarded_node(graph, "tool_node_2", tool_node_2)
    _add_guarded_node(graph, "parse_originality", parse_originality_node)
    _add_guarded_node(graph, "rank_questions_llm_call", rank_questions_llm_call)
    _add_guarded_node(graph, "generate_final_ranked_questions", generate_final_ranked_questions_node)

    # Step 2
    _add_guarded_node(graph, "extract_keywords", extract_keywords_node)
    _add_guarded_node(graph, "select_databases", select_databases_node)
    _add_guarded_node(graph, "build_search_queries", build_search_queries_node)
    _add_guarded_node(graph, "define_criteria", define_criteria_node)
    _add_guarded_node(graph, "prepare_search", prepare_search_node)
    _add_guarded_node(graph, "save_papers", save_papers_node)

    # Step 3
    _add_guarded_node(graph, "deduplicate", deduplicate_node)
    _add_guarded_node(graph, "llm_classify", llm_classify_node)
    _add_guarded_node(graph, "asreview_screen", asreview_screen_node)

    # Step 4
    _add_guarded_node(graph, "metadata_insights", metadata_insights_node)
    _add_guarded_node(graph, "thematic_augmentation", thematic_augmentation_node)
    _add_guarded_node(graph, "augmented_analysis", augmented_analysis_node)

    # Step 5
    _add_guarded_node(graph, "generate_outline", generate_outline_node)
    _add_guarded_node(graph, "draft_sections", draft_sections_node)
    _add_guarded_node(graph, "proofread_draft", proofread_draft_node)

    # ── Register SELECTIVE approval gate nodes ──────────────

    for gate_name, gated_node, _, _ in APPROVAL_GATES:
        step_label = NODE_STEP_MAP.get(gated_node, "")
        description = NODE_DESCRIPTIONS.get(gated_node, gated_node)
        gate_fn = _make_approval_gate(gated_node, step_label, description)
        # Gates must NOT be wrapped with _feedback_inject_wrapper — they are
        # approval infrastructure, not agent nodes that call the LLM.
        graph.add_node(gate_name, guard_node(gate_name, gate_fn, _select_web_model_name))

    # ── Edges ───────────────────────────────────────────────

    # START → first node
    graph.add_edge(START, "generate_initial_questions")

    # ── GATED nodes → their approval gates ──────────────────
    for gate_name, gated_node, _, _ in APPROVAL_GATES:
        graph.add_edge(gated_node, gate_name)

    # ── Approval gates → conditional routing (improve or continue) ──
    for gate_name, gated_node, improve_target, continue_target in APPROVAL_GATES:
        router = _make_gate_router(gated_node, improve_target, continue_target)
        graph.add_conditional_edges(gate_name, router)

    # ── NON-GATED direct edges (auto-continue) ──────────────

    # parse_originality → rank_questions_llm_call (no gate)
    graph.add_edge("parse_originality", "rank_questions_llm_call")

    # generate_final_ranked_questions → extract_keywords (no gate)
    graph.add_edge("generate_final_ranked_questions", "extract_keywords")

    # select_databases → build_search_queries (no gate after select_databases)
    graph.add_edge("select_databases", "build_search_queries")

    # prepare_search → save_papers (no gate)
    graph.add_edge("prepare_search", "save_papers")

    # save_papers → deduplicate (no gate)
    graph.add_edge("save_papers", "deduplicate")

    # deduplicate → llm_classify (no gate)
    graph.add_edge("deduplicate", "llm_classify")

    # Step 4 — all auto-continue (no gates)
    graph.add_edge("metadata_insights", "thematic_augmentation")
    graph.add_edge("thematic_augmentation", "augmented_analysis")

    # Step 5 — all auto-continue (no gates)
    graph.add_edge("augmented_analysis", "generate_outline")
    graph.add_edge("generate_outline", "draft_sections")
    graph.add_edge("draft_sections", "proofread_draft")
    graph.add_edge("proofread_draft", END)

    # ── Tool loop edges (unchanged internal routing) ────────

    # Feasibility: llm_call → [tool_node | parse_feasibility]
    graph.add_conditional_edges("feasibility_llm_call", _should_continue_feasibility)
    graph.add_edge("tool_node", "feasibility_llm_call")

    # Originality: llm_call → [tool_node_2 | parse_originality]
    graph.add_conditional_edges("originality_llm_call", _should_continue_originality)
    graph.add_edge("tool_node_2", "originality_llm_call")

    # Ranking: direct edge (no tools, matches main.py)
    graph.add_edge("rank_questions_llm_call", "generate_final_ranked_questions")

    return graph
