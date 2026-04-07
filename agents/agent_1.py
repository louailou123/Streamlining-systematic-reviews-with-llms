from typing import Dict, Any
from llm.llm import get_llm
from llm.structured_parser import invoke_structured
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, RemoveMessage

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
    PROMPT_4_FEASIBILITY_SEARCH,
    PROMPT_4_FEASIBILITY_PARSE,
    PROMPT_5_ORIGINALITY_SURVEYS_SEARCH,
    PROMPT_5_ORIGINALITY_SURVEYS_PARSE,
    PROMPT_6_ORIGINALITY_RANKED
)





def generate_initial_questions_node(state: LiRAState) -> Dict[str, Any]:
    topic = state.get("topic", "")
    llm = get_llm()
    # Explicitly creating the template and ensuring it only has 'topic'
    template = PromptTemplate(template=PROMPT_1_INITIAL_GENERATION, input_variables=["topic"])
    prompt_val = template.invoke({"topic": topic})
    result = invoke_structured(llm, prompt_val, InitialQuestions)
    print(result)
    
    return {
        "initial_questions": result.questions,
        "logs": state.get("logs", []) + [f"Generated {len(result.questions)} initial research questions."]
    }


def select_framework_node(state: LiRAState) -> Dict[str, Any]:
    topic = state.get("topic", "")
    llm = get_llm()
    # Explicitly creating the template and ensuring it only has 'topic'
    template = PromptTemplate(template=PROMPT_2_FRAMEWORK_SELECTION, input_variables=["topic"])
    prompt_val = template.invoke({"topic": topic})
    result = invoke_structured(llm, prompt_val, FrameworkSelectionResult)
    
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
    # Explicitly creating the template and ensuring it only has 'question' and 'framework'
    template = PromptTemplate(template=PROMPT_3_FRAMEWORK_APPLICATION, input_variables=["question", "framework"])
    prompt_val = template.invoke({"question": candidate, "framework": framework})
    result = invoke_structured(llm, prompt_val, FrameworkApplicationResult)
    
    # Setup search prompt for next node
    timeframe = state.get("timeframe", "3 months")
    feasibility_search_prompt = PROMPT_4_FEASIBILITY_SEARCH.format(question=result.reframed_question, timeframe=timeframe)
    
    print(f"Reframed question: {result.reframed_question}")
    
    return {
        "framework_breakdown": result.breakdown,
        "reframed_question": result.reframed_question,
        "messages": [HumanMessage(content=feasibility_search_prompt)],
        "logs": state.get("logs", []) + ["Applied framework to reframe question."]
    }


def parse_feasibility_node(state: LiRAState) -> Dict[str, Any]:
    llm = get_llm()
    # Adding PARSE instruction to messages for structured extraction
    question = state.get("reframed_question", state.get("topic", ""))
    timeframe = state.get("timeframe", "3 months")
    parse_instruction = PROMPT_4_FEASIBILITY_PARSE.format(question=question, timeframe=timeframe)
    
    messages = state["messages"] + [HumanMessage(content=parse_instruction)]
    parsed = invoke_structured(llm, messages, FeasibilityAssessment)
    
    originality_search_prompt = PROMPT_5_ORIGINALITY_SURVEYS_SEARCH.format(question=question)
    
    print(f"Feasibility Status: {parsed.feasibility_status}")
    print(f"Estimated Publications: {parsed.estimated_publications}")

    return {
        "feasibility_estimation": parsed.estimated_publications,
        "feasibility_status": parsed.feasibility_status,
        "messages": [RemoveMessage(id=m.id) for m in state["messages"] if hasattr(m, "id") and m.id] + [HumanMessage(content=originality_search_prompt)],
        "logs": state.get("logs", []) + [f"Feasibility: {parsed.feasibility_status}"]
    }


def parse_originality_node(state: LiRAState) -> Dict[str, Any]:
    llm = get_llm()
    # Adding PARSE instruction to messages for structured extraction
    question = state.get("reframed_question", state.get("topic", ""))
    parse_instruction = PROMPT_5_ORIGINALITY_SURVEYS_PARSE.format(question=question)
    
    messages = state["messages"] + [HumanMessage(content=parse_instruction)]
    parsed = invoke_structured(llm, messages, OriginalityAssessment)

    # Setup prompt 6 for final Ranked Questions
    timeframe = state.get("timeframe", "3 months")
    gaps_str = parsed.gaps
    
    final_prompt = PROMPT_6_ORIGINALITY_RANKED.format(question=question, timeframe=timeframe, gaps=gaps_str)
    
    print(f"Originality Overlap: {parsed.overlap}")
    
    return {
        "survey_summaries": [{"title": s.title, "summary": s.summary} for s in parsed.surveys],
        "overlap": parsed.overlap,
        "gaps": parsed.gaps,
        "messages": [RemoveMessage(id=m.id) for m in state["messages"] if hasattr(m, "id") and m.id] + [HumanMessage(content=final_prompt)],
        "logs": state.get("logs", []) + ["Parsed originality assessment (overlap/gaps)."]
    }


def generate_final_ranked_questions_node(state: LiRAState) -> Dict[str, Any]:
    llm = get_llm()
    # Now passing the full history (state["messages"]) instead of just the last message
    parsed = invoke_structured(llm, state["messages"], FinalRankedQuestions)
    
    return {
        "final_ranked_questions": [{"novelty_level": q.novelty_level, "question": q.question} for q in parsed.questions],
        "current_step": "Step 1 Complete",
        "messages": [RemoveMessage(id=m.id) for m in state["messages"] if hasattr(m, "id") and m.id],
        "logs": state.get("logs", []) + ["Generated final ranked questions."]
    }

