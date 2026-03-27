from typing import TypedDict, List, Dict, Optional, Literal
from datetime import datetime

class LiRAState(TypedDict):
    """State for LiRA Literature Review Assistant workflow"""
    
    # ===== Workflow Control =====
    current_step: Literal["step1", "step2", "step3", "step4", "step5", "step6"]
    workflow_status: Literal["initialized", "in_progress", "paused", "completed", "failed"]
    step_history: List[Dict[str, any]]  # Track completed steps and decisions
    
    # ===== Step 1: Research Question Generation =====
    research_topic: str  # Initial broad topic from user
    research_questions: List[str]  # Generated candidate questions
    selected_framework: Optional[Literal["PICO", "PICOC", "SPIDER", "SPICE", "PEO"]]
    structured_question: Optional[Dict[str, str]]  # Framework-structured components
    final_research_question: Optional[str]
    feasibility_assessment: Optional[Dict[str, any]]  # {estimated_papers, timeframe, is_feasible}
    originality_check: Optional[Dict[str, any]]  # {existing_surveys, gaps_identified, is_novel}
    
    # ===== Step 2: Search Strategy =====
    core_concepts: List[str]  # Main concepts and synonyms
    search_queries: Dict[str, str]  # {database_name: query_string}
    selected_databases: List[str]  # ["IEEE Xplore", "Scopus", "ACM DL", etc.]
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    search_results: Dict[str, Dict]  # {database: {count, date, results}}
    raw_dataset_path: Optional[str]  # Path to exported raw results
    raw_dataset_count: int
    
    # ===== Step 3: Screening =====
    deduplicated_count: int
    llm_screening_config: Optional[Dict[str, any]]  # Prompt template, model, criteria
    llm_screening_results: Optional[Dict[str, any]]  # {included: int, excluded: int}
    asreview_session_id: Optional[str]
    manual_screening_progress: Optional[Dict[str, int]]  # {reviewed, included, excluded}
    initial_dataset_path: Optional[str]  # Curated dataset after screening
    initial_dataset_count: int
    
    # ===== Step 4: Insight Extraction =====
    metadata_insights: Optional[Dict[str, any]]  # {top_authors, top_journals, keywords, etc.}
    thematic_dimensions: List[str]  # ["country", "algorithm_type", "network_type", etc.]
    augmentation_prompts: Dict[str, str]  # {dimension: prompt_template}
    augmented_dataset_path: Optional[str]
    augmented_insights: Optional[Dict[str, any]]  # Charts, trends, patterns
    visualization_paths: List[str]  # Paths to generated charts/graphs
    
    # ===== Step 5: Reading & Drafting =====
    review_outline: Optional[Dict[str, List[str]]]  # {section: [subsections]}
    draft_sections: Dict[str, str]  # {section_name: draft_content}
    papers_read: List[str]  # Paper IDs that have been read
    reading_notes: Dict[str, str]  # {paper_id: summary/notes}
    draft_version: int
    
    # ===== Step 6: Synthesis & Gaps =====
    synthesis: Optional[str]
    identified_gaps: List[Dict[str, str]]  # [{gap_description, importance, future_work}]
    final_report_path: Optional[str]
    
    # ===== Configuration & Settings =====
    llm_config: Dict[str, any]  # {model, api_key, temperature, etc.}
    user_preferences: Dict[str, any]  # Timeframe, depth, focus areas
    export_format: Literal["docx", "pdf", "latex", "markdown"]
    
    # ===== Human-in-the-Loop =====
    pending_user_input: Optional[Dict[str, any]]  # What decision is needed from user
    user_feedback: List[Dict[str, any]]  # User corrections/refinements
    
    # ===== Error Handling & Metadata =====
    errors: List[Dict[str, str]]  # {step, error_message, timestamp}
    warnings: List[Dict[str, str]]
    session_id: str
    created_at: str
    updated_at: str
    
    # ===== Optional: Multi-agent coordination =====
    agent_messages: List[Dict[str, any]]  # For multi-agent feedback loops
    active_agents: List[str]  # ["reviewer", "critic", "verifier"]