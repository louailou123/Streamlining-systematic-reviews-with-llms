# schemas.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# =========================
# STEP 1 — RESEARCH QUESTION
# =========================

class InitialQuestions(BaseModel):
    questions: List[str] = Field(description="List of 3-5 research questions")

class FrameworkSelectionResult(BaseModel):
    framework: str = Field(description="The selected framework (e.g., PICO, SPIDER, etc.)")
    justification: str = Field(description="Justification for why this framework is most suitable")

class FrameworkApplicationResult(BaseModel):
    breakdown: Dict[str, str] = Field(description="Framework breakdown mapping each letter to its description")
    reframed_question: str = Field(description="The reframed research question")

class FeasibilityAssessment(BaseModel):
    estimated_publications: str = Field(description="Estimated number of relevant publications")
    feasibility_status: str = Field(description="Assessment of feasibility (e.g., Feasible, Too broad, Too narrow)")

class SurveySummary(BaseModel):
    title: str = Field(description="Title of the survey paper")
    summary: str = Field(description="Brief summary of the survey paper")

class OriginalityAssessment(BaseModel):
    surveys: List[SurveySummary] = Field(description="List of 3-5 recent survey papers")
    overlap: str = Field(description="Coverage overlap with existing surveys")
    gaps: str = Field(description="Potential gaps for a new literature review")

class RankedQuestion(BaseModel):
    novelty_level: str = Field(description="Novelty level classification, e.g., 'High Novelty', 'Moderate Novelty', 'Low Novelty'")
    question: str = Field(description="The research question")

class FinalRankedQuestions(BaseModel):
    questions: List[RankedQuestion] = Field(description="List of 3 feasible and original research questions ranked by novelty")

# =========================
# STEP 2 — SEARCH STRATEGY
# =========================

class Keywords(BaseModel):
    keywords: List[str] = Field(description="list of relevant keywords")

class DatabaseItem(BaseModel):
    name: str = Field(description="Name of the database")
    justification: str = Field(description="Justification for why this database is relevant")

class DatabaseSelection(BaseModel):
    databases: List[DatabaseItem]

class SearchQuery(BaseModel):
    query: Dict[str,str] = Field(description="each database mapped with a search query")

class Criteria(BaseModel):
    inclusion: List[str]
    exclusion: List[str]

class Paper(BaseModel):
    title: str = Field(description="Title of the paper")
    year: str = Field(description="Year of publication")
    url: str = Field(description="Direct URL to the paper if it exists")
    source: str = Field(description="Database or API source (e.g., arXiv, Semantic Scholar)")
    abstract: str = Field(description="Brief abstract of the paper")

class PapersExtract(BaseModel):
    papers: List[Paper] = Field(description="List of all extracted papers")

# =========================
# STEP 3 — SCREENING
# =========================

class ScreeningResult(BaseModel):
    included: int = Field(description="1 if the paper meets at least one inclusion criterion, 0 otherwise")
    excluded: int = Field(description="1 if the paper matches at least one exclusion criterion, 0 otherwise")
    justification: str = Field(description="Brief reason explaining why the paper was included or excluded, citing which specific criteria matched")

# =========================
# STEP 4 — INSIGHTS
# =========================

class MetadataInsightsSummary(BaseModel):
    total_papers: int = Field(description="Number of papers in initial_dataset")
    doi_coverage_pct: float = Field(description="Percentage of papers with DOI")
    abstract_coverage_pct: float = Field(description="Percentage of papers with abstracts")
    funding_info_coverage_pct: float = Field(description="Percentage of papers with funding information")
    papers_by_year: Dict[str, int] = Field(description="Counts of papers by year")
    papers_by_source: Dict[str, int] = Field(description="Counts by source/database")
    top_authors: Dict[str, int] = Field(description="Top authors")
    top_institutions: Dict[str, int] = Field(description="Top institutions")
    top_keywords: Dict[str, int] = Field(description="Top keywords")
    top_journals: Dict[str, int] = Field(description="Top journals")
    document_types: Dict[str, int] = Field(description="Distribution of document types")
    top_funding_sources: Dict[str, int] = Field(description="Top funding sources")
    citation_statistics: Dict[str, float] = Field(description="Citation count summary statistics")
    collaboration_patterns: Dict[str, float] = Field(description="Co-authorship and co-institution patterns")


class ThematicPaperExtraction(BaseModel):
    row_id: str
    countries_of_study: List[str] = Field(default_factory=list)
    application_domain: str = Field(default="Unknown")
    algorithm_families: List[str] = Field(default_factory=list)
    baseline_methods: List[str] = Field(default_factory=list)
    challenges_addressed: List[str] = Field(default_factory=list)
    evaluation_metrics: List[str] = Field(default_factory=list)
    experimental_setting: str = Field(default="Unknown")
    dataset_simulator_testbed: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    evidence_snippets: List[str] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.5)
    needs_review: bool = Field(default=False)
    review_reason: str = Field(default="")


class ThematicSummary(BaseModel):
    total_papers: int
    countries_distribution: Dict[str, int]
    application_domains: Dict[str, int]
    algorithm_families: Dict[str, int]
    challenges_addressed: Dict[str, int]
    evaluation_metrics: Dict[str, int]
    experimental_settings: Dict[str, int]


class Step4AnalysisReport(BaseModel):
    total_papers: int
    average_extraction_confidence: float
    review_needed_count: int
    top_countries: Dict[str, int]
    top_application_domains: Dict[str, int]
    top_network_types: Dict[str, int]
    top_algorithm_families: Dict[str, int]
    top_challenges: Dict[str, int]
    top_metrics: Dict[str, int]
    top_experimental_settings: Dict[str, int]


# =========================
# STEP 5 — DRAFTING
# =========================

class OutlineSection(BaseModel):
    title: str = Field(description="Section title for the literature review")
    description: str = Field(description="Brief description of what this section should cover")
    relevant_themes: List[str] = Field(default_factory=list, description="Key themes/topics this section should address")

class OutlineResult(BaseModel):
    sections: List[OutlineSection] = Field(description="Ordered list of literature review sections")

class DraftedSection(BaseModel):
    title: str = Field(description="Section title")
    content: str = Field(description="Full drafted content for this section in Markdown")

class ProofreadResult(BaseModel):
    content: str = Field(description="The proofread and refined full literature review draft in Markdown")
    improvements_made: List[str] = Field(default_factory=list, description="List of key improvements made during proofreading")

# =========================
# STEP 6 — SYNTHESIS
# =========================

class FinalReport(BaseModel):
    summary: str

class Gaps(BaseModel):
    gaps: List[str]