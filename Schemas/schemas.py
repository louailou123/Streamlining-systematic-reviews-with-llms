# schemas.py

from pydantic import BaseModel, Field
from typing import List, Dict


# =========================
# STEP 1 — RESEARCH QUESTION
# =========================

class ResearchQuestions(BaseModel):
    questions: List[str] = Field(description="List of 3 research questions")


class FrameworkSelection(BaseModel):
    framework: List[str] = Field(description="a list of the first letters of the selected framework for example ['p','i','c','o']")
    reason: str = Field(description="Short justification")


class FinalQuestion(BaseModel):
    question: Dict[str,str] =Field(description="dict of each first letter of the selected framework mapped with a string for example 'p':'the population'")


class FeasibilityResult(BaseModel):
    feasibility: str  # Feasible | Too broad | Too narrow


class OriginalityResult(BaseModel):
    status: str  # Yes | Partial | No
    reason: str


# =========================
# STEP 2 — SEARCH STRATEGY
# =========================

class Keywords(BaseModel):
    keywords: List[str] = Field(description="list of relevant keywords")

class DatabaseSelection(BaseModel):
    databases: List[str]

class SearchQuery(BaseModel):
    query: Dict[str,str] = Field(description="each database mapped with a search query")


class Criteria(BaseModel):
    inclusion: List[str]
    exclusion: List[str]


# =========================
# STEP 3 — SCREENING
# =========================

class ClassificationResult(BaseModel):
    label: int  # 0 or 1


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