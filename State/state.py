from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph.message import add_messages

class LiRAState(TypedDict):
    # =========================
    # SYSTEM INPUT
    # =========================
    topic: str  # initial user input
    timeframe: str # Review timeframe (e.g. '2 months')
    messages: Annotated[list, add_messages]  # Chat history / tool messages

    # =========================
    # STEP 1 — RESEARCH QUESTION
    # =========================
    initial_questions: List[str]
    selected_framework: str
    framework_justification: str
    framework_breakdown: Dict[str, str]
    reframed_question: str
    feasibility_estimation: str
    feasibility_status: str
    survey_summaries: List[Dict[str, str]]
    overlap: str
    gaps: str
    final_ranked_questions: List[Dict[str, str]]

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
    raw_dataset_ris: Optional[str]          # RIS export for Zotero
    prisma_doc: Optional[str]               # PRISMA search strategy doc
    search_metadata: List[Dict]             # per-database: query, count, date
    deduplicated_csv: Optional[str]         # after duplicate removal
    screened_llm_csv: Optional[str]           # optional separate labels file
    screened_human_csv:Optional[str]     # after LLM/human screening
    asreview_screened_csv: Optional[str]  # after ASReview manual screening
    initial_dataset_csv: Optional[str]            # enriched dataset (LLM features)

  # =========================
    # STEP 4 — INSIGHTS
    # =========================
    metadata_insights: Dict
    metadata_summary_json: Optional[str]
    thematic_summary: Dict
    thematic_summary_json: Optional[str]
    augmented_dataset_csv: Optional[str]
    analysis_report: Dict
    analysis_report_json: Optional[str]
    step4_average_confidence: Optional[float]

    visualization_paths: List[str]          # paths to generated chart PNGs

    # =========================
    # STEP 5 — DRAFTING
    # =========================
    outline: List[str]
    draft_sections: Dict[str, str]         # section -> content
    outline_json: Optional[str]            # path to saved outline JSON
    draft_markdown: Optional[str]          # path to draft markdown
    final_draft_markdown: Optional[str]    # path to proofread final draft
    chatpdf_summaries: Dict[str, str]      # row_id -> ChatPDF summary

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