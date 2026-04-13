"""
LiRA Backend — Workflow Engine
Builds the LangGraph pipeline graph, preserving the exact same structure
from the original main.py but adapted for web execution.

Imports agent code from the project root (../agents/, ../llm/, ../tools/, etc.)
to avoid duplicating the pipeline logic.
"""

import sys
from pathlib import Path

# Add project root to sys.path so we can import from the existing pipeline code
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage

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


def _should_continue_ranking(state: LiRAState) -> str:
    last = state["messages"][-1] if state.get("messages") else None
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tool_node"
    return "generate_final_ranked_questions"


def build_lira_graph() -> StateGraph:
    """
    Build the full LiRA pipeline graph.
    This is the exact same graph structure as the original main.py,
    preserving all node semantics, edges, and conditional routing.
    """
    llm = get_llm()
    llm_with_tools = get_llm(tools=search_tools)

    def feasibility_llm_call(state: LiRAState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def originality_llm_call(state: LiRAState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def rank_questions_llm_call(state: LiRAState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools=search_tools)
    tool_node_2 = ToolNode(tools=search_tools)

    graph = StateGraph(LiRAState)

    # ── Step 1 nodes ─────────────────────────────────────────
    graph.add_node("generate_initial_questions", generate_initial_questions_node)
    graph.add_node("select_framework", select_framework_node)
    graph.add_node("apply_framework", apply_framework_node)
    graph.add_node("feasibility_llm_call", feasibility_llm_call)
    graph.add_node("tool_node", tool_node)
    graph.add_node("parse_feasibility", parse_feasibility_node)
    graph.add_node("originality_llm_call", originality_llm_call)
    graph.add_node("tool_node_2", tool_node_2)
    graph.add_node("parse_originality", parse_originality_node)
    graph.add_node("rank_questions_llm_call", rank_questions_llm_call)
    graph.add_node("generate_final_ranked_questions", generate_final_ranked_questions_node)

    # ── Step 2 nodes ─────────────────────────────────────────
    graph.add_node("extract_keywords", extract_keywords_node)
    graph.add_node("select_databases", select_databases_node)
    graph.add_node("build_search_queries", build_search_queries_node)
    graph.add_node("define_criteria", define_criteria_node)
    graph.add_node("prepare_search", prepare_search_node)
    graph.add_node("save_papers", save_papers_node)

    # ── Step 3 nodes ─────────────────────────────────────────
    graph.add_node("deduplicate", deduplicate_node)
    graph.add_node("llm_classify", llm_classify_node)
    graph.add_node("asreview_screen", asreview_screen_node)

    # ── Step 4 nodes ─────────────────────────────────────────
    graph.add_node("metadata_insights", metadata_insights_node)
    graph.add_node("thematic_augmentation", thematic_augmentation_node)
    graph.add_node("augmented_analysis", augmented_analysis_node)

    # ── Step 5 nodes ─────────────────────────────────────────
    graph.add_node("generate_outline", generate_outline_node)
    graph.add_node("draft_sections", draft_sections_node)
    graph.add_node("proofread_draft", proofread_draft_node)

    # ── Edges: Step 1 ────────────────────────────────────────
    graph.add_edge(START, "generate_initial_questions")
    graph.add_edge("generate_initial_questions", "select_framework")
    graph.add_edge("select_framework", "apply_framework")
    graph.add_edge("apply_framework", "feasibility_llm_call")

    graph.add_conditional_edges("feasibility_llm_call", _should_continue_feasibility)
    graph.add_edge("tool_node", "feasibility_llm_call")
    graph.add_edge("parse_feasibility", "originality_llm_call")

    graph.add_conditional_edges("originality_llm_call", _should_continue_originality)
    graph.add_edge("tool_node_2", "originality_llm_call")
    graph.add_edge("parse_originality", "rank_questions_llm_call")

    graph.add_conditional_edges("rank_questions_llm_call", _should_continue_ranking)
    graph.add_edge("generate_final_ranked_questions", "extract_keywords")

    # ── Edges: Step 2 ────────────────────────────────────────
    graph.add_edge("extract_keywords", "select_databases")
    graph.add_edge("select_databases", "build_search_queries")
    graph.add_edge("build_search_queries", "define_criteria")
    graph.add_edge("define_criteria", "prepare_search")
    graph.add_edge("prepare_search", "save_papers")

    # ── Edges: Step 3 ────────────────────────────────────────
    graph.add_edge("save_papers", "deduplicate")
    graph.add_edge("deduplicate", "llm_classify")
    graph.add_edge("llm_classify", "asreview_screen")

    # ── Edges: Step 4 ────────────────────────────────────────
    graph.add_edge("asreview_screen", "metadata_insights")
    graph.add_edge("metadata_insights", "thematic_augmentation")
    graph.add_edge("thematic_augmentation", "augmented_analysis")

    # ── Edges: Step 5 ────────────────────────────────────────
    graph.add_edge("augmented_analysis", "generate_outline")
    graph.add_edge("generate_outline", "draft_sections")
    graph.add_edge("draft_sections", "proofread_draft")
    graph.add_edge("proofread_draft", END)

    return graph
