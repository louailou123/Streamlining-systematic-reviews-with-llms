from typing import Dict, Any
from llm.llm import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from tools.serpapi_tool import tools

from State.state import LiRAState
from Schemas.schemas import (
    InitialQuestions,
    FrameworkSelectionResult,
    FrameworkApplicationResult,
    FeasibilityAssessment,
    OriginalityAssessment,
    FinalRankedQuestions
)
from Prompts.prompts import (
    PROMPT_1_INITIAL_GENERATION,
    PROMPT_2_FRAMEWORK_SELECTION,
    PROMPT_3_FRAMEWORK_APPLICATION,
    PROMPT_4_FEASIBILITY,
    PROMPT_5_ORIGINALITY_SURVEYS,
    PROMPT_6_ORIGINALITY_RANKED
)


def _extract_text(msg) -> str:
    """Extracts plain text from a message, handling Gemini's block format."""
    content = msg.content
    if isinstance(content, str):
        return content or "No information available."
    if isinstance(content, list):
        # Gemini returns [{'type': 'text', 'text': '...', 'extras': ...}]
        texts = [block.get("text", "") for block in content if isinstance(block, dict)]
        return " ".join(texts) or "No information available."
    return str(content) or "No information available."


def generate_initial_questions_node(state: LiRAState) -> Dict[str, Any]:
    topic = state.get("topic", "")
    llm = get_llm()
    chain = PromptTemplate.from_template(PROMPT_1_INITIAL_GENERATION) | llm.with_structured_output(InitialQuestions)
    result = chain.invoke({"topic": topic})
    
    return {
        "initial_questions": result.questions,
        "logs": state.get("logs", []) + [f"Generated {len(result.questions)} initial research questions."]
    }


def select_framework_node(state: LiRAState) -> Dict[str, Any]:
    topic = state.get("topic", "")
    llm = get_llm()
    chain = PromptTemplate.from_template(PROMPT_2_FRAMEWORK_SELECTION) | llm.with_structured_output(FrameworkSelectionResult)
    result = chain.invoke({"topic": topic})
    
    return {
        "selected_framework": result.framework,
        "framework_justification": result.justification,
        "logs": state.get("logs", []) + [f"Selected framework: {result.framework}"]
    }


def apply_framework_node(state: LiRAState) -> Dict[str, Any]:
    # take the first generated question
    questions = state.get("initial_questions", [])
    candidate = questions[0] if questions else state.get("topic", "")
    framework = state.get("selected_framework", "PICO")
    
    llm = get_llm()
    chain = PromptTemplate.from_template(PROMPT_3_FRAMEWORK_APPLICATION) | llm.with_structured_output(FrameworkApplicationResult)
    result = chain.invoke({"question": candidate, "framework": framework})
    
    # Setup prompt for next node's initial Tool using HumanMessage
    timeframe = state.get("timeframe", "3 months")
    feasibility_prompt = PROMPT_4_FEASIBILITY.format(question=result.reframed_question, timeframe=timeframe)
    
    print(f"Reframed question: {result.reframed_question}")
    
    return {
        "framework_breakdown": result.breakdown,
        "reframed_question": result.reframed_question,
        "messages": [HumanMessage(content=feasibility_prompt)],
        "logs": state.get("logs", []) + ["Applied framework to reframe question."]
    }


def parse_feasibility_node(state: LiRAState) -> Dict[str, Any]:
    llm = get_llm()
    text = _extract_text(state["messages"][-1])
    parsed = llm.with_structured_output(FeasibilityAssessment).invoke([HumanMessage(content=text)])
    
    topic = state.get("topic", "")
    originality_prompt = PROMPT_5_ORIGINALITY_SURVEYS.format(topic=topic)
    
    print(f"Feasibility Status: {parsed.feasibility_status}")
    print(f"Estimated Publications: {parsed.estimated_publications}")

    return {
        "feasibility_estimation": parsed.estimated_publications,
        "feasibility_status": parsed.feasibility_status,
        "messages": [HumanMessage(content=originality_prompt)],
        "logs": state.get("logs", []) + [f"Feasibility: {parsed.feasibility_status}"]
    }


def parse_originality_node(state: LiRAState) -> Dict[str, Any]:
    llm = get_llm()
    text = _extract_text(state["messages"][-1])
    parsed = llm.with_structured_output(OriginalityAssessment).invoke([HumanMessage(content=text)])

    # Setup prompt 6 for final Ranked Questions
    topic = state.get("topic", "")
    timeframe = state.get("timeframe", "3 months")
    gaps_str = parsed.gaps
    
    final_prompt = PROMPT_6_ORIGINALITY_RANKED.format(topic=topic, timeframe=timeframe, gaps=gaps_str)
    
    print(f"Originality Overlap: {parsed.overlap}")
    
    return {
        "survey_summaries": [{"title": s.title, "summary": s.summary} for s in parsed.surveys],
        "overlap": parsed.overlap,
        "gaps": parsed.gaps,
        "messages": [HumanMessage(content=final_prompt)],
        "logs": state.get("logs", []) + ["Parsed originality assessment (overlap/gaps)."]
    }


def generate_final_ranked_questions_node(state: LiRAState) -> Dict[str, Any]:
    llm = get_llm()
    text = _extract_text(state["messages"][-1])
    parsed = llm.with_structured_output(FinalRankedQuestions).invoke([HumanMessage(content=text)])
    
    return {
        "final_ranked_questions": [{"novelty_level": q.novelty_level, "question": q.question} for q in parsed.questions],
        "current_step": "Step 1 Complete",
        "logs": state.get("logs", []) + ["Generated final ranked questions."]
    }

