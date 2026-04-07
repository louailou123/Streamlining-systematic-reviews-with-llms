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

class MetadataInsights(BaseModel):
    topics: List[str]
    trends: List[str]

class ThematicExtraction(BaseModel):
    method: str
    network_type: str
    challenge: str

# =========================
# STEP 5 — DRAFTING
# =========================

class Outline(BaseModel):
    sections: List[str]

class SectionDraft(BaseModel):
    content: str

# =========================
# STEP 6 — SYNTHESIS
# =========================

class FinalReport(BaseModel):
    summary: str

class Gaps(BaseModel):
    gaps: List[str]