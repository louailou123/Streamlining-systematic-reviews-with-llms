from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

from State.state import LiRAState
from llm.llm import get_llm
from agents.agent_1 import (
    generate_initial_questions_node,
    select_framework_node,
    apply_framework_node,
    parse_feasibility_node,
    parse_originality_node,
    generate_final_ranked_questions_node
)
from agents.agent_2 import (
    extract_keywords_node,
    select_databases_node,
    build_search_queries_node,
    define_criteria_node,
    prepare_search_node,
    save_papers_node
)
from agents.agent_3 import (
    deduplicate_node,
    llm_classify_node,
    asreview_screen_node
)
from agents.agent_4 import (
    metadata_insights_node,
    thematic_augmentation_node,
    augmented_analysis_node,
)
from tools.serpapi_tool import tools

# Define toolsets
from tools.serpapi_tool import google_scholar_search
tools_step_1 = [google_scholar_search]

# Bind tools
llm = get_llm()
model_step_1 = llm.bind_tools(tools_step_1, parallel_tool_calls=False)
model_all = llm.bind_tools(tools, parallel_tool_calls=False)


def llm_call_tools_step_1(state: LiRAState):
    """LLM for feasibility/originality checks (Google Scholar Only)."""
    return {"messages": [model_step_1.invoke(state["messages"])]}


def llm_call_tools_all(state: LiRAState):
    """LLM for general search execution (All available tools)."""
    return {"messages": [model_all.invoke(state["messages"])]}


def llm_call_no_tools(state: LiRAState):
    """LLM completes the final task without tools."""
    model = get_llm()
    return {"messages": [model.invoke(state["messages"])]}


def truncated_tool_node_factory(tools_):
    """
    Wrap ToolNode and truncate very large ToolMessage payloads before they
    keep growing the visible state too much.
    """
    node = ToolNode(tools_)

    def wrapped(state: LiRAState):
        result = node.invoke(state)
        new_messages = []

        for msg in result.get("messages", []):
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                if len(msg.content) > 12000:
                    truncated_content = msg.content[:12000] + "\n...[TRUNCATED FOR DISPLAY]"
                    new_msg = ToolMessage(
                        content=truncated_content,
                        tool_call_id=msg.tool_call_id,
                        name=getattr(msg, "name", None)
                    )
                    new_messages.append(new_msg)
                else:
                    new_messages.append(msg)
            else:
                new_messages.append(msg)

        return {"messages": new_messages}

    return wrapped


MAX_ITERATIONS = 3
MAX_SEARCH_ITERATIONS = 5  # separate budget for search phase


def should_continue_feasibility(state) -> Literal["tool_node", "parse_feasibility"]:
    messages = state["messages"]
    last_message = messages[-1]

    if getattr(last_message, "tool_calls", None):
        tool_count = sum(1 for m in messages if isinstance(m, ToolMessage))
        if tool_count < MAX_ITERATIONS:
            return "tool_node"

    return "parse_feasibility"


def should_continue_originality(state) -> Literal["tool_node_2", "parse_originality"]:
    messages = state["messages"]
    last_message = messages[-1]

    if getattr(last_message, "tool_calls", None):
        tool_count = sum(1 for m in messages if isinstance(m, ToolMessage))
        if tool_count < MAX_ITERATIONS:
            return "tool_node_2"

    return "parse_originality"


def build_lira_graph():
    workflow = StateGraph(LiRAState)

    # Step 1.a
    workflow.add_node("generate_initial_questions", generate_initial_questions_node)
    workflow.add_node("select_framework", select_framework_node)
    workflow.add_node("apply_framework", apply_framework_node)

    # Step 1.b
    workflow.add_node("feasibility_llm_call", llm_call_tools_step_1)
    workflow.add_node("tool_node", truncated_tool_node_factory(tools_step_1))
    workflow.add_node("parse_feasibility", parse_feasibility_node)

    # Step 1.c
    workflow.add_node("originality_llm_call", llm_call_tools_step_1)
    workflow.add_node("tool_node_2", truncated_tool_node_factory(tools_step_1))
    workflow.add_node("parse_originality", parse_originality_node)

    # Final ranking
    workflow.add_node("rank_questions_llm_call", llm_call_no_tools)
    workflow.add_node("generate_final_ranked_questions", generate_final_ranked_questions_node)

    # Step 2
    workflow.add_node("extract_keywords", extract_keywords_node)
    workflow.add_node("select_databases", select_databases_node)
    workflow.add_node("build_search_queries", build_search_queries_node)
    workflow.add_node("define_criteria", define_criteria_node)
    workflow.add_node("prepare_search", prepare_search_node)
    workflow.add_node("save_papers", save_papers_node)

    # Step 3 — Screening
    workflow.add_node("deduplicate", deduplicate_node)
    workflow.add_node("llm_classify", llm_classify_node)
    workflow.add_node("asreview_screen", asreview_screen_node)

    # Step 4 — Insights Extraction
    workflow.add_node("metadata_insights", metadata_insights_node)
    workflow.add_node("thematic_augmentation", thematic_augmentation_node)
    workflow.add_node("augmented_analysis", augmented_analysis_node)

    # Edges - Step 1.a
    workflow.add_edge(START, "generate_initial_questions")
    workflow.add_edge("generate_initial_questions", "select_framework")
    workflow.add_edge("select_framework", "apply_framework")

    # Edges - Step 1.b
    workflow.add_edge("apply_framework", "feasibility_llm_call")
    workflow.add_conditional_edges("feasibility_llm_call", should_continue_feasibility)
    workflow.add_edge("tool_node", "feasibility_llm_call")

    # Edges - Step 1.c
    workflow.add_edge("parse_feasibility", "originality_llm_call")
    workflow.add_conditional_edges("originality_llm_call", should_continue_originality)
    workflow.add_edge("tool_node_2", "originality_llm_call")

    # Final ranking
    workflow.add_edge("parse_originality", "rank_questions_llm_call")
    workflow.add_edge("rank_questions_llm_call", "generate_final_ranked_questions")

    # Step 2
    workflow.add_edge("generate_final_ranked_questions", "extract_keywords")
    workflow.add_edge("extract_keywords", "select_databases")
    workflow.add_edge("select_databases", "build_search_queries")
    workflow.add_edge("build_search_queries", "define_criteria")
    workflow.add_edge("define_criteria", "prepare_search")
    workflow.add_edge("prepare_search", "save_papers")

    # Step 3
    workflow.add_edge("save_papers", "deduplicate")
    workflow.add_edge("deduplicate", "llm_classify")
    workflow.add_edge("llm_classify", "asreview_screen")

    # Step 4 starts after ASReview confirms included studies
    workflow.add_edge("asreview_screen", "metadata_insights")
    workflow.add_edge("metadata_insights", "thematic_augmentation")
    workflow.add_edge("thematic_augmentation", "augmented_analysis")
    workflow.add_edge("augmented_analysis", END)

    # Checkpointer required for interrupt() / human-in-the-loop
    from langgraph.checkpoint.memory import MemorySaver
    return workflow.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    import os
    import sys
    import json
    import traceback

    # Try enabling ANSI on Windows terminals that support it.
    os.system("")

    # Restore original std streams in case they were redirected previously.
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    USE_COLOR = sys.stdout.isatty()

    class C:
        RESET = "\033[0m" if USE_COLOR else ""
        BOLD = "\033[1m" if USE_COLOR else ""
        DIM = "\033[2m" if USE_COLOR else ""
        RED = "\033[91m" if USE_COLOR else ""
        GREEN = "\033[92m" if USE_COLOR else ""
        YELLOW = "\033[93m" if USE_COLOR else ""
        BLUE = "\033[94m" if USE_COLOR else ""
        MAGENTA = "\033[95m" if USE_COLOR else ""
        CYAN = "\033[96m" if USE_COLOR else ""

    def safe_text(value, max_len=300):
        """Convert any value to a compact ASCII-safe display string."""
        try:
            if value is None:
                text = ""
            elif isinstance(value, str):
                text = value
            else:
                text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)

        text = text.replace("\r", " ").replace("\n", " ").strip()
        text = " ".join(text.split())

        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text

    def safe_print(*args, sep=" ", end="\n", flush=True):
        """Print without crashing if stdout has encoding/closure issues."""
        try:
            if sys.stdout is None or sys.stdout.closed:
                return
            text = sep.join(str(a) for a in args)
            try:
                print(text, end=end, flush=flush)
            except UnicodeEncodeError:
                ascii_text = text.encode("ascii", errors="replace").decode("ascii")
                print(ascii_text, end=end, flush=flush)
            except ValueError:
                pass
        except Exception:
            pass

    def hr(char="=", width=78):
        return char * width

    def section(title, color=C.CYAN):
        safe_print()
        safe_print(f"{color}{C.BOLD}{hr()}{C.RESET}")
        safe_print(f"{color}{C.BOLD}{title}{C.RESET}")
        safe_print(f"{color}{C.BOLD}{hr()}{C.RESET}")

    def subheader(title, color=C.CYAN):
        safe_print(f"{color}{C.BOLD}>> {title}{C.RESET}")

    def kv(label, value, color=C.GREEN):
        safe_print(f"{color}{label}:{C.RESET} {value}")

    def print_graph_structure(graph):
        section("LiRA GRAPH STRUCTURE", C.MAGENTA)
        try:
            graph.get_graph().print_ascii()
        except Exception:
            safe_print("[Graph structure unavailable for console display]")

    def print_tool_calls(tool_calls):
        subheader("Tool Calls", C.YELLOW)
        for idx, tc in enumerate(tool_calls, 1):
            name = safe_text(tc.get("name", "unknown_tool"), max_len=80)
            args_text = safe_text(tc.get("args", {}), max_len=220)
            safe_print(f"  {idx}. {name}")
            safe_print(f"     args: {args_text}")

    def print_message(msg):
        msg_type = msg.__class__.__name__
        content = getattr(msg, "content", "")

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            safe_print(f"{C.BLUE}[{msg_type}]{C.RESET} model requested tool calls")
            print_tool_calls(msg.tool_calls)
            return

        snippet = safe_text(content, max_len=350)
        if isinstance(msg, ToolMessage):
            safe_print(f"{C.YELLOW}[{msg_type}]{C.RESET} {snippet}")
        else:
            safe_print(f"{C.BLUE}[{msg_type}]{C.RESET} {snippet}")

    def print_node_summary(node_name, state_update):
        if node_name == "generate_initial_questions":
            questions = state_update.get("initial_questions", [])
            if questions:
                subheader("Generated Questions", C.GREEN)
                for i, q in enumerate(questions, 1):
                    safe_print(f"  {i}. {q}")

        elif node_name == "select_framework":
            kv("Framework Selected", state_update.get("selected_framework"), C.GREEN)
            kv("Justification", safe_text(state_update.get("framework_justification"), 800), C.GREEN)

        elif node_name == "apply_framework":
            breakdown = state_update.get("framework_breakdown", {})
            if breakdown:
                subheader("Framework Breakdown", C.GREEN)
                for k, v in breakdown.items():
                    safe_print(f"  - {k}: {v}")
            kv("Reframed Question", state_update.get("reframed_question"), C.GREEN)

        elif node_name == "parse_feasibility":
            kv("Feasibility Status", state_update.get("feasibility_status"), C.GREEN)
            kv("Estimated Publications", state_update.get("feasibility_estimation"), C.GREEN)

        elif node_name == "parse_originality":
            kv("Originality Overlap", safe_text(state_update.get("overlap"), 500), C.GREEN)
            kv("Gaps Identified", safe_text(state_update.get("gaps"), 500), C.GREEN)

        elif node_name == "extract_keywords":
            kv("Keywords Extracted", ", ".join(state_update.get("keywords", [])), C.GREEN)

        elif node_name == "select_databases":
            kv("Databases Selected", ", ".join(state_update.get("databases", [])), C.GREEN)

        elif node_name == "build_search_queries":
            queries = state_update.get("search_queries", {})
            if queries:
                subheader("Search Queries", C.GREEN)
                for db, query in queries.items():
                    safe_print(f"  - {db}: {safe_text(query, 300)}")

        elif node_name == "define_criteria":
            inclusion = state_update.get("inclusion_criteria", [])
            exclusion = state_update.get("exclusion_criteria", [])

            if inclusion:
                subheader("Inclusion Criteria", C.GREEN)
                for c in inclusion:
                    safe_print(f"  + {c}")

            if exclusion:
                subheader("Exclusion Criteria", C.RED)
                for c in exclusion:
                    safe_print(f"  - {c}")

        elif node_name == "search_llm_call":
            safe_print(f"{C.YELLOW}Search agent is preparing or requesting retrieval...{C.RESET}")

        elif node_name == "tool_node_search":
            safe_print(f"{C.YELLOW}Retrieving papers from external sources...{C.RESET}")

        # Step 3 — Screening
        elif node_name == "deduplicate":
            section("STEP 3.a — DEDUPLICATION", C.MAGENTA)
            dedup_csv = state_update.get("deduplicated_csv", "N/A")
            kv("Output File", dedup_csv, C.GREEN)

        elif node_name == "llm_classify":
            section("STEP 3.b — LLM SCREENING", C.MAGENTA)
            screened_csv = state_update.get("screened_llm_csv", "N/A")
            kv("Output File", screened_csv, C.GREEN)

        elif node_name == "asreview_screen":
            section("STEP 3.c — ASREVIEW MANUAL SCREENING", C.MAGENTA)
            asreview_csv = state_update.get("asreview_screened_csv", "N/A")
            kv("Output File", asreview_csv, C.GREEN)

        # Step 4 — Insights Extraction
        elif node_name == "metadata_insights":
            section("STEP 4.a — METADATA INSIGHTS", C.MAGENTA)
            metadata = state_update.get("metadata_insights", {})
            kv("Total Papers", metadata.get("total_papers", "N/A"), C.GREEN)
            kv("DOI Coverage %", metadata.get("doi_coverage_pct", "N/A"), C.GREEN)
            kv("Abstract Coverage %", metadata.get("abstract_coverage_pct", "N/A"), C.GREEN)
            if metadata.get("top_journals"):
                kv("Top Journals Found", len(metadata.get("top_journals", {})), C.GREEN)
            if metadata.get("top_keywords"):
                kv("Top Keywords Found", len(metadata.get("top_keywords", {})), C.GREEN)

        elif node_name == "thematic_augmentation":
            section("STEP 4.b — THEMATIC AUGMENTATION", C.MAGENTA)
            kv("Augmented CSV", state_update.get("augmented_dataset_csv", "N/A"), C.GREEN)
            kv("Average Confidence", state_update.get("step4_average_confidence", "N/A"), C.GREEN)

        elif node_name == "augmented_analysis":
            section("STEP 4.c — AUGMENTED ANALYSIS", C.MAGENTA)
            analysis = state_update.get("analysis_report", {})
            kv("Total Papers", analysis.get("total_papers", "N/A"), C.GREEN)
            kv("Review Needed Count", analysis.get("review_needed_count", "N/A"), C.GREEN)
            kv("Analysis JSON", state_update.get("analysis_report_json", "N/A"), C.GREEN)

    # Initialize logger
    from logger import LiRALogger
    plog = LiRALogger()

    graph = build_lira_graph()
    plog.log_graph_structure(graph)

    print_graph_structure(graph)
    section("EXECUTING LIRA PIPELINE", C.CYAN)

    initial_input = {
        "topic": "The role of renewable energy in sustainable development",
        "timeframe": "1 month",
        "databases": ["Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"],
        "messages": [],
        "logs": []
    }

    plog.log_initial_input(initial_input)

    # Thread config required for checkpointer (needed by interrupt())
    thread_config = {"configurable": {"thread_id": f"lira_run_{plog.run_id}"}}

    final_state = None

    try:
        for event in graph.stream(initial_input, config=thread_config):
            for node_name, state_update in event.items():
                if node_name == "__interrupt__":
                    continue
                plog.node_start(node_name)

                section(f"NODE: {node_name}", C.CYAN)

                if "messages" in state_update:
                    subheader("Messages", C.BLUE)
                    for msg in state_update["messages"]:
                        print_message(msg)

                if "logs" in state_update and state_update["logs"]:
                    kv("Latest Log", state_update["logs"][-1], C.GREEN)

                print_node_summary(node_name, state_update)
                plog.node_end(node_name, state_update)

                if node_name in {
                    "generate_final_ranked_questions",
                    "metadata_insights",
                    "thematic_augmentation",
                    "augmented_analysis",
                }:
                    final_state = state_update

        # Handle interrupt (ASReview human-in-the-loop)
        from langgraph.types import Command
        graph_state = graph.get_state(thread_config)
        while graph_state.next:
            section("PIPELINE PAUSED — HUMAN-IN-THE-LOOP", C.MAGENTA)
            safe_print(f"{C.YELLOW}The pipeline is waiting for you to complete ASReview screening.{C.RESET}")
            safe_print(f"{C.YELLOW}Follow the instructions above, then press ENTER to resume...{C.RESET}")

            user_input = input("\nEnter the FULL PATH to your ASReview result CSV file: ").strip()

            resume_value = user_input if user_input else "asreview_export.csv"
            section("RESUMING PIPELINE", C.CYAN)

            for event in graph.stream(Command(resume=resume_value), config=thread_config):
                for node_name, state_update in event.items():
                    if node_name == "__interrupt__":
                        continue
                    plog.node_start(node_name)
                    section(f"NODE: {node_name}", C.CYAN)

                    if "messages" in state_update:
                        subheader("Messages", C.BLUE)
                        for msg in state_update["messages"]:
                            print_message(msg)

                    if "logs" in state_update and state_update["logs"]:
                        kv("Latest Log", state_update["logs"][-1], C.GREEN)

                    print_node_summary(node_name, state_update)
                    plog.node_end(node_name, state_update)

                    if node_name in {
                        "generate_final_ranked_questions",
                        "metadata_insights",
                        "thematic_augmentation",
                        "augmented_analysis",
                    }:
                        final_state = state_update

            graph_state = graph.get_state(thread_config)

    except Exception as e:
        section("PIPELINE ERROR", C.RED)
        kv("Error Type", type(e).__name__, C.RED)
        kv("Error Message", str(e), C.RED)
        safe_print()
        safe_print(f"{C.DIM}{traceback.format_exc()}{C.RESET}")
        plog.log_error(e)

    section("FINAL RESULTS", C.GREEN)

    if final_state and "analysis_report" in final_state:
        subheader("Step 4 Analysis Outputs", C.GREEN)
        analysis = final_state.get("analysis_report", {})
        safe_print(f"  Total Papers: {analysis.get('total_papers', 'N/A')}")
        safe_print(f"  Average Extraction Confidence: {analysis.get('average_extraction_confidence', 'N/A')}")
        safe_print(f"  Review Needed Count: {analysis.get('review_needed_count', 'N/A')}")
        safe_print(f"  Analysis JSON: {final_state.get('analysis_report_json', 'N/A')}")
    elif final_state and "final_ranked_questions" in final_state:
        subheader("Top Ranked Questions", C.GREEN)
        for idx, q in enumerate(final_state["final_ranked_questions"], 1):
            novelty = q.get("novelty_level", "Unknown Novelty")
            question = q.get("question", "")
            safe_print(f"  {idx}. [{novelty}] {question}")
    else:
        safe_print("No final results found in state.")

    plog.log_final_state(final_state)
    plog.log_summary()

    safe_print()
    safe_print(f"{C.GREEN}Detailed log: {plog.log_file}{C.RESET}")