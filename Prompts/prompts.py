# =========================
# STEP 1 — RESEARCH QUESTION DESIGN
# =========================

PROMPT_1_INITIAL_GENERATION = """
You are an expert researcher in systematic literature reviews.

Generate 3 to 5 high-quality research questions on the topic:
{topic}

The questions should:
- Be clear, specific, and researchable
- Be suitable for a systematic literature review
- Avoid being too broad or too vague
- Focus on concrete and analyzable aspects

Ensure diversity in perspective (e.g., performance, scalability, methodology, application).
"""

PROMPT_2_FRAMEWORK_SELECTION = """
You are an expert in research methodology.

Based on the topic:
{topic}

Select the most appropriate framework among:
PICO, PICOC, SPIDER, SPICE, PEO

Explain your choice briefly by considering:
- The nature of the research (quantitative, qualitative, or mixed)
- The type of problem being studied
- Suitability for structuring a systematic literature review question
"""

PROMPT_3_FRAMEWORK_APPLICATION = """
You are an expert in systematic literature reviews.

Reframe the following research question using the {framework} framework:

{question}

Respect the structure of the selected framework:

- PICO: Population, Intervention, Comparison, Outcome
- PICOC: Population, Intervention, Comparison, Outcome, Context
- SPIDER: Sample, Phenomenon of Interest, Design, Evaluation, Research type
- SPICE: Setting, Perspective, Intervention, Comparison, Evaluation
- PEO: Population, Exposure, Outcome

Use precise and domain-specific wording.
"""

PROMPT_4_FEASIBILITY_SEARCH = """
You are evaluating the feasibility of conducting a systematic literature review.

Research question:
{question}

Timeframe:
{timeframe}

Use the provided tools (e.g., Google Scholar) to estimate the volume of relevant publications and assess if the topic is too broad, balanced, or too narrow for the given timeframe.
Summarize your findings clearly once you have enough information.
"""

PROMPT_4_FEASIBILITY_PARSE = """
Based on the research findings, provide a structured feasibility assessment.
Research question: {question}
Timeframe: {timeframe}

IMPORTANT: Do not invent exact publication counts (e.g., \"734 papers\"). Give broad estimates based ONLY on what you retrieved from the tools (e.g., \"100+\", \"Hundreds\"). Explicitly state your uncertainty if the complete number is hidden or unclear due to tool truncations.
"""

PROMPT_5_ORIGINALITY_SURVEYS_SEARCH = """
You are assessing the originality of a research topic.

Research question:
{question}

Use the provided tools (e.g., Google Scholar) to identify several recent survey or review papers related to this topic.
Focus on identifying themes, overlaps, and underexplored aspects.
Summarize your findings once you have identified 3-5 relevant surveys.

IMPORTANT: You must ONLY use tools that are explicitly provided in your tools list. DO NOT attempt to call 'open_file', 'python', or any imaginary tool.
"""

PROMPT_5_ORIGINALITY_SURVEYS_PARSE = """
Based on the identified surveys, provide a structured originality assessment.
Research question: {question}

Provide clear and thoughtful analysis.
"""

PROMPT_6_ORIGINALITY_RANKED = """
You are an expert in identifying novel research directions.

Research question:
{question}

Timeframe:
{timeframe}

Known research gaps:
{gaps}

Generate three research questions that:
- Address the identified gaps
- Are feasible within the given timeframe
- Offer meaningful academic contribution

Rank them by novelty, feasibility, and potential impact.
"""

# =========================================
# STEP 2 — SEARCH STRATEGY PROMPTS
# =========================================

KEYWORD_EXTRACTION_PROMPT = """
You are an expert in academic research and systematic literature reviews.

Given the following research question:

{question}

Extract a comprehensive set of relevant academic keywords.

Your output should include:
- Core technical terms directly related to the topic
- Key concepts and domain-specific terminology
- Synonyms, abbreviations, and alternative phrasings
- Variants using plural/singular forms and common lexical differences

Ensure that:
- Keywords are suitable for querying academic databases (e.g., IEEE Xplore, Scopus, ACM Digital Library)
- Redundant or overly generic terms are avoided
- Terms are grouped logically where appropriate
just 20 keywords
"""

QUERY_BUILDER_PROMPT = """
You are an expert in constructing advanced academic search queries for systematic reviews.

Given the following set of keywords:

{keywords}

And the following target databases:

{databases}

Generate high-quality search queries tailored to each database.

Requirements:
- Use appropriate Boolean operators (AND, OR)
- Group synonyms using parentheses
- Balance between recall (broad coverage) and precision (relevance)

#### Tips for Query Design
- Start broad, then refine
- Use wildcards (*) cautiously
- Adapt query logic to each platform's syntax
- CRITICAL: arXiv, PubMed, and OpenAlex APIs strictly reject excessively long queries or crash. For these platforms ONLY use a maximum of 3 to 4 extremely core keywords without complex nested boolean logic. Google Scholar can handle full boolean queries.

Respond with EXACTLY this JSON structure:

{{
  \"query\": {{
    \"Database Name 1\": \"query string\",
    \"Database Name 2\": \"query string\"
  }}
}}

Make sure you include exactly the databases listed above.
DO NOT omit the top-level \"query\" field.
DO NOT return a bare dictionary.
"""

CRITERIA_PROMPT = """
You are an expert in systematic literature reviews following rigorous academic standards.

Based on the following research question:

{question}

Define clear and well-justified inclusion and exclusion criteria.

Inclusion criteria should specify:
- Relevant topics and scope
- Types of studies (e.g., empirical, experimental, review)
- Publication years (if applicable)
- Language and accessibility
- Methodological relevance

Exclusion criteria should specify:
- Irrelevant domains or off-topic studies
- Low-quality or non-peer-reviewed sources (if applicable)
- Duplicates or incomplete studies
- Non-accessible or non-English papers (if relevant)

Ensure that:
- Criteria are precise, non-overlapping, and actionable
- They support reproducibility and transparency of the review process
"""

# =========================
# STEP 3 — PAPER SCREENING
# =========================

LLM_SCREENING_PROMPT = """You are an expert researcher and systematic reviews specialist screening papers for a literature review.

**Paper Title:**
{title}

**Paper Abstract:**
{abstract}

**Research Question:**
{question}

**Inclusion Criteria:**
{inclusion_criteria}

**Exclusion Criteria:**
{exclusion_criteria}

**Task:**
You MUST classify this paper. Do NOT skip or leave any field empty.
- Evaluate whether it meets any of the **inclusion criteria** (set included = 1 if yes, 0 if no).
- Evaluate whether it matches any of the **exclusion criteria** (set excluded = 1 if yes, 0 if no).
- If the abstract is unavailable, base your decision on the title alone.
- Provide a brief justification explaining which specific criteria the paper matched and why.

CRITICAL RULE: You MUST set EXACTLY ONE of included or excluded to 1.
- If the paper is relevant → included=1, excluded=0
- If the paper is NOT relevant → included=0, excluded=1
- NEVER return included=0 AND excluded=0. You must make a decision."""

# =========================
# STEP 4 — AUTOMATIC EXTRACTION OF INSIGHTS
# =========================

STEP4_THEMATIC_EXTRACTION_PROMPT = """
You are an expert literature-review analyst extracting structured thematic information from academic papers.

Research question:
{research_question}

Paper row ID:
{row_id}

Title:
{title}

Abstract:
{abstract}

Your task is to extract topic-agnostic thematic metadata that can support downstream analysis for ANY research domain.

Rules:
- Use ONLY the title and abstract provided.
- If a field is not supported by the title/abstract, return an empty list or "Unknown".
- Keep confidence low when the evidence is weak.
- Countries must be extracted only if explicitly stated or strongly inferable from the text. Do not guess.
- Evidence snippets must be short phrases copied or tightly paraphrased from the title/abstract.
- The output must be valid JSON matching the schema exactly.

Field guidance:
- countries_of_study: country or countries where the study was conducted
- application_domain: the main application/problem area of the paper
- algorithm_families: method families, model families, or named technical approaches central to the paper
- baseline_methods: methods used for comparison
- challenges_addressed: core problems tackled by the study
- evaluation_metrics: explicit evaluation criteria or metrics
- experimental_setting: one short label such as simulation, experiment, case study, survey, benchmark, theoretical, real-world deployment, or Unknown
- dataset_simulator_testbed: named datasets, simulators, testbeds, benchmarks, or corpora
- key_findings: short factual findings supported by the abstract
- limitations: explicit or clearly signaled limitations only
- evidence_snippets: brief evidence snippets supporting the extraction
- extraction_confidence: number between 0 and 1
- needs_review: true if the abstract is too weak/ambiguous for reliable extraction
- review_reason: short reason if needs_review is true

Return ONLY valid JSON.
"""
