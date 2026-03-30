# prompts.py

# =========================
# STEP 1
# =========================

PROMPT_1_INITIAL_GENERATION = """
Generate 3-5 research questions about {topic}.
"""

PROMPT_2_FRAMEWORK_SELECTION = """
Based on the research topic '{topic}', which framework (PICO, PICOC, SPIDER, SPICE, PEO) is most suitable for structuring a research question for a systematic review? Justify your answer.
"""

PROMPT_3_FRAMEWORK_APPLICATION = """
Reframe the question '{question}' using the {framework} framework. 

The framework letters correspond strictly in this order to:
- PICO: Population, Intervention, Comparison, Outcome
- PICOC: Population, Intervention, Comparison, Outcome, Context
- SPIDER: Sample, Phenomenon of Interest, Design, Evaluation, Research type
- SPICE: Setting, Perspective, Intervention, Comparison, Evaluation
- PEO: Population, Exposure, Outcome

Provide the framework breakdown as a dictionary where the keys are the exact full words from the framework (e.g., "Population", "Intervention", "Comparison", "Outcome") IN THE EXACT ORDER of the framework acronym. Give specific context from the question for each. Also provide the final reframed question.
"""

PROMPT_4_FEASIBILITY = """
Based on this research question '{question}', estimate the number of relevant publications likely available and the feasibility of reviewing them within a {timeframe} timeframe. Consider the broadness/narrowness of the topic.
"""

PROMPT_5_ORIGINALITY_SURVEYS = """
Find and summarize 3–5 recent survey papers on '{topic}'. Identify coverage overlap and potential gaps for a new literature review focused on {topic}.
"""

PROMPT_6_ORIGINALITY_RANKED = """
Generate 3 research questions about {topic} that are feasible for a literature review within {timeframe} and have not been extensively covered in recent survey papers (considering these gaps: {gaps}). Rank them by novelty and potential impact.
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