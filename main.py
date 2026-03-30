from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from State.state import LiRAState
from llm.llm import get_llm
from tools.serpapi_tool import tools
from agents.agent_1 import (
    generate_initial_questions_node,
    select_framework_node,
    apply_framework_node,
    parse_feasibility_node,
    parse_originality_node,
    generate_final_ranked_questions_node
)

# Bind tools
model_with_tools = get_llm().bind_tools(tools)

def llm_call_tools(state: LiRAState):
    """LLM decides whether to call a tool or not."""
    return {"messages": [model_with_tools.invoke(state["messages"])]}

def llm_call_no_tools(state: LiRAState):
    """LLM completes the final task without tools."""
    model = get_llm()
    return {"messages": [model.invoke(state["messages"])]}

def should_continue_feasibility(state) -> Literal["tool_node", "parse_feasibility"]:
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return "parse_feasibility"

def should_continue_originality(state) -> Literal["tool_node_2", "parse_originality"]:
    if state["messages"][-1].tool_calls:
        return "tool_node_2"
    return "parse_originality"

def build_lira_graph():
    workflow = StateGraph(LiRAState)

    # 1.a Nodes
    workflow.add_node("generate_initial_questions", generate_initial_questions_node)
    workflow.add_node("select_framework", select_framework_node)
    workflow.add_node("apply_framework", apply_framework_node)

    # 1.b Nodes
    workflow.add_node("feasibility_llm_call", llm_call_tools)
    workflow.add_node("tool_node", ToolNode(tools))
    workflow.add_node("parse_feasibility", parse_feasibility_node)
    
    # 1.c Nodes
    workflow.add_node("originality_llm_call", llm_call_tools)
    workflow.add_node("tool_node_2", ToolNode(tools))
    workflow.add_node("parse_originality", parse_originality_node)
    
    # Final Rank Nodes
    workflow.add_node("rank_questions_llm_call", llm_call_no_tools)
    workflow.add_node("generate_final_ranked_questions", generate_final_ranked_questions_node)

    # Edges - 1.a
    workflow.add_edge(START, "generate_initial_questions")
    workflow.add_edge("generate_initial_questions", "select_framework")
    workflow.add_edge("select_framework", "apply_framework")
    
    # Edges - 1.b
    workflow.add_edge("apply_framework", "feasibility_llm_call")
    workflow.add_conditional_edges("feasibility_llm_call", should_continue_feasibility)
    workflow.add_edge("tool_node", "feasibility_llm_call")
    
    # Edges - 1.c (Originality)
    workflow.add_edge("parse_feasibility", "originality_llm_call")
    workflow.add_conditional_edges("originality_llm_call", should_continue_originality)
    workflow.add_edge("tool_node_2", "originality_llm_call")
    
    # Edges - 1.c (Final Ranked Questions)
    workflow.add_edge("parse_originality", "rank_questions_llm_call")
    workflow.add_edge("rank_questions_llm_call", "generate_final_ranked_questions")
    workflow.add_edge("generate_final_ranked_questions", END)

    return workflow.compile()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    graph = build_lira_graph()

    print("\n=== Framework Graph Structure ===\n")
    graph.get_graph().print_ascii()
    print("\n=================================\n")

    print("Executing LiRA Pipeline Step 1...\n")
    
    initial_input = {
        "topic": "challenges of using MADRL in highly dynamic communication networks for IoT",
        "timeframe": "3 months",
        "messages": [],
        "logs": []
    }

    final_state = None
    # Stream the execution to show each step clearly in the console
    for event in graph.stream(initial_input):
        for node_name, state_update in event.items():
            print(f"--- Finished Node: {node_name} ---")
            
            if "logs" in state_update and state_update["logs"]:
                print(f"Log: {state_update['logs'][-1]}")
                
            if node_name == "generate_initial_questions":
                print("Generated Questions:")
                for i, q in enumerate(state_update.get("initial_questions", [])):
                    print(f"  {i+1}. {q}")
            elif node_name == "select_framework":
                print(f"Framework Selected: {state_update.get('selected_framework')}")
                print(f"Justification: {state_update.get('framework_justification')}")
            elif node_name == "apply_framework":
                print("Framework Breakdown:")
                breakdown = state_update.get('framework_breakdown', {})
                for k, v in breakdown.items():
                    print(f"  {k.upper()}: {v}")
                print(f"Reframed Question: {state_update.get('reframed_question')}")
            elif node_name == "parse_feasibility":
                print(f"Feasibility Status: {state_update.get('feasibility_status')}")
                print(f"Estimated Publications: {state_update.get('feasibility_estimation')}")
            elif node_name == "parse_originality":
                print(f"Originality Overlap: {state_update.get('overlap')}")
                print(f"Gaps Identified: {state_update.get('gaps')}")
            elif node_name == "generate_final_ranked_questions":
                final_state = state_update
            
            print() # empty line for readability

    print("\n=== FINAL RESULTS ===")
    print("Top Ranked Questions:")
    if final_state and 'final_ranked_questions' in final_state:
        for idx, q in enumerate(final_state['final_ranked_questions']):
            print(f"[{q['novelty_level']}] {q['question']}")
    else:
        print("Final ranked questions not found in state.")
