# prompts.py

# =========================
# STEP 1
# =========================

RQ_GENERATION_PROMPT = """
Generate three research questions about:
{topic}
Focus on scalability, robustness, and IoT.
"""

FRAMEWORK_SELECTION_PROMPT = """
Given the topic:
{topic}

Select the most appropriate research framework.
"""

REFINE_QUESTION_PROMPT = """
Improve and clarify the following research question using the framework.

Question:
{question}

Framework:
{framework}
"""

FEASIBILITY_PROMPT = """
Evaluate feasibility of this research question for a short literature review:

{question}
"""

ORIGINALITY_PROMPT = """
Assess whether this research question is already well covered:

{question}
"""

# =========================
# STEP 2
# =========================

KEYWORD_EXTRACTION_PROMPT = """
Extract important keywords from:

{question}
"""

QUERY_BUILDER_PROMPT = """
Build a search query using these keywords:

{keywords}
"""

DATABASE_SELECTION_PROMPT = """
Select the most relevant academic databases for:

{topic}
"""

CRITERIA_PROMPT = """
Define inclusion and exclusion criteria for:

{question}
"""

# =========================
# STEP 3
# =========================

LLM_CLASSIFICATION_PROMPT = """
Evaluate whether this paper is relevant to MADRL in communication networks.

Title:
{title}

Abstract:
{abstract}
"""

# =========================
# STEP 4
# =========================

METADATA_SUMMARY_PROMPT = """
Analyze the following metadata and identify main topics and trends:

{data}
"""

THEMATIC_EXTRACTION_PROMPT = """
Analyze this paper:

Title:
{title}

Abstract:
{abstract}

Identify method, network type, and main challenge.
"""

# =========================
# STEP 5
# =========================

OUTLINE_PROMPT = """
Create a structured outline for a literature review on:

{question}
"""

SECTION_WRITING_PROMPT = """
Write a section of a literature review.

Section:
{section}

Context:
{insights}
"""

# =========================
# STEP 6
# =========================

SYNTHESIS_PROMPT = """
Synthesize the following sections into a coherent literature review:

{sections}
"""

GAP_IDENTIFICATION_PROMPT = """
Identify research gaps based on:

{insights}
"""