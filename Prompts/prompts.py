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

# =========================
# STEP 5 — READING & DRAFTING
# =========================

STEP5_OUTLINE_PROMPT = """
You are an expert academic writer specializing in systematic literature reviews.

Research question:
{research_question}

Based on the analysis of {total_papers} papers, generate a structured outline for a comprehensive literature review.

Key thematic data to consider when designing sections:
- Top application domains: {application_domains}
- Top challenges addressed: {challenges}
- Top algorithm/method families: {algorithms}
- Experimental settings: {experimental_settings}

Requirements:
- Include an Introduction section
- Include a Methodology section (briefly describing the systematic review process)
- Create 3-6 thematic body sections based on the data above
- Include a Discussion section covering cross-cutting themes
- Include a Conclusion and Future Directions section
- Each section should have a clear title, description, and list of relevant themes it covers
- The outline must be logically organized and flow naturally

Return ONLY valid JSON.
"""

STEP5_CHATPDF_SUMMARY_PROMPT = """Provide a structured summary of this paper with the following sections:
1. **Objective**: What is the main goal of this study?
2. **Methods**: What methodology or approach was used?
3. **Key Findings**: What are the main results?
4. **Relevance**: How does this relate to: {research_question}
5. **Limitations**: What limitations are acknowledged?

Be concise but thorough. Use direct quotes where helpful."""

STEP5_DRAFT_SECTION_PROMPT = """
You are an expert academic writer drafting a section of a systematic literature review.

Research question:
{research_question}

Section title: {section_title}
Section description: {section_description}
Relevant themes: {relevant_themes}

Below are summaries of papers relevant to this section. Use them to write a well-structured, analytical section.

Paper summaries:
{paper_summaries}

Requirements:
- Write in formal academic style suitable for a peer-reviewed journal
- Synthesize findings across papers — do NOT just list paper-by-paper summaries
- Identify patterns, trends, agreements, and contradictions
- Cite papers by referencing their titles in parentheses, e.g., (Author et al., Year) or (Paper Title, Year)
- Include critical analysis, not just description
- Use smooth transitions between paragraphs
- Length: 400-800 words per section
- Format in Markdown

Return ONLY valid JSON.
"""

STEP5_PROOFREAD_PROMPT = """
You are an expert academic editor and proofreader specializing in literature reviews.

Proofread and refine the following literature review draft. Focus on:

1. **Grammar and spelling**: Fix any errors
2. **Clarity**: Ensure sentences are clear and unambiguous
3. **Coherence**: Ensure logical flow between paragraphs and sections
4. **Argumentation**: Strengthen analytical claims and evidence connections
5. **Academic tone**: Ensure formal, scholarly language throughout
6. **Consistency**: Uniform formatting, terminology, and citation style
7. **Transitions**: Improve connections between sections
8. **Redundancy**: Remove repetitive content

Draft to proofread:
{draft_content}

Return the COMPLETE improved draft in Markdown format, plus a list of key improvements made.
Return ONLY valid JSON.
"""


# =========================
# FEEDBACK / REVISION PROMPT
# =========================

FEEDBACK_REVISION_PROMPT = """You are an expert research assistant helping a user refine the output of a systematic literature review pipeline.

The user has reviewed a step in the pipeline and is asking you to revise the output based on their feedback.

Below you will find three clearly separated sections. Read each one carefully and understand its purpose:

---

## SECTION 1: ORIGINAL PROMPT (context — what was the task)
This is the original instruction that was given to the LLM to produce the output.
It describes the task, the constraints, and the expected output format.
Use this to understand what the task was about and what the expected output should look like.

{original_prompt}

---

## SECTION 2: LLM RESULT (current output — what was produced)
This is the output that the LLM generated in response to the original prompt above.
The user has reviewed this result and wants changes.
Use this as the baseline — keep what is good, and revise only what the user asks for.

{llm_result}

---

## SECTION 3: USER FEEDBACK (top priority — what the user wants changed)
This is the user's feedback. It is your PRIMARY DIRECTIVE.
You MUST address every single point the user raises.
The user's instructions take absolute priority over any other consideration.
Do NOT ignore, skip, or partially address any part of this feedback.

{user_feedback}

---

## YOUR TASK
1. Re-read the original prompt to understand the task requirements and output format.
2. Look at the previous LLM result to understand what was already produced.
3. Apply ALL of the user's feedback to revise the output.
4. Produce the revised output in the SAME FORMAT as the original result.
5. Keep everything the user did not mention — only change what they asked for.
"""
