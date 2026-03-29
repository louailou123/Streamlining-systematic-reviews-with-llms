from typing import TypedDict, List, Dict, Optional

class LiRAState(TypedDict):
    # =========================
    # SYSTEM INPUT
    # =========================
    topic: str  # initial user input

    # =========================
    # STEP 1 — RESEARCH QUESTION
    # =========================
    research_questions: List[str]
    selected_framework: List[str]
    selected_framework_reason:str
    final_research_question: Dict[str,str]
    feasibility_score: int
    originality_score: int

    # =========================
    # STEP 2 — SEARCH STRATEGY
    # =========================
    keywords: List[str]
    search_queries: Dict[str, str]  # db_name -> query
    databases: List[str]
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]

    # =========================
    # DATA STORAGE (CSV PIPELINE)
    # =========================
    raw_dataset_csv: Optional[str]          # initial collected papers
    deduplicated_csv: Optional[str]         # after duplicate removal
    screened_llm_csv: Optional[str]           # optional separate labels file
    screened_human_csv:Optional[str]# after LLM/human screening
    augmented_csv: Optional[str]            # enriched dataset (LLM features)

    # =========================
    # LLM SCREENING
    # =========================


    # =========================
    # STEP 4 — INSIGHTS
    # =========================
    metadata_insights: Dict                 # stats (authors, years, trends)
    thematic_insights: Dict                # semantic insights (LLM extracted)

    # =========================
    # STEP 5 — DRAFTING
    # =========================
    outline: List[str]
    draft_sections: Dict[str, str]         # section -> content

    # =========================
    # STEP 6 — SYNTHESIS
    # =========================
    final_report: Optional[str]
    gaps_identified: List[str]

    # =========================
    # SYSTEM / ENGINEERING
    # =========================
    current_step: Optional[str]            # for tracking execution
    logs: List[str]                       # execution logs
    errors: List[str]                     # error tracking