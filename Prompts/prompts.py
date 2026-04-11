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

IMPORTANT: Do not invent exact publication counts (e.g., "734 papers"). Give broad estimates based ONLY on what you retrieved from the tools (e.g., "100+", "Hundreds"). Explicitly state your uncertainty if the complete number is hidden or unclear due to tool truncations.
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

# -----------------------------------------
# KEYWORD EXTRACTION
# -----------------------------------------
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


# -----------------------------------------
# QUERY BUILDER
# -----------------------------------------
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
  "query": {{
    "Database Name 1": "query string",
    "Database Name 2": "query string"
  }}
}}

Make sure you include exactly the databases listed above.
DO NOT omit the top-level "query" field.
DO NOT return a bare dictionary.
"""


# -----------------------------------------
# DATABASE SELECTION
# -----------------------------------------
DATABASE_SELECTION_PROMPT = """
You are an expert in academic publishing and research methodologies.

Given the following research topic:

{topic}

Identify the most relevant academic databases for conducting a systematic literature review, focusing on **Free & Open Access** sources.

Recommended sources to prioritize:
1. **Google Scholar**: Broad coverage across all publishers (ACM, IEEE, Springer).
2. **arXiv**: 100% free papers, strong in AI, RL, and Networking.
3. **DOAJ (Directory of Open Access Journals)**: Peer-reviewed open-access journals.
4. **CORE**: Aggregates millions of free papers from repositories and journals.
5. **Semantic Scholar**: Smart search with influential paper highlights.
"""

EXECUTE_SEARCH_PROMPT = """
You are an automated research assistant. Your task is to execute the following search queries across their respective databases:

{queries}

### Instructions:
1. Use the provided tools (google_scholar_search, arxiv_search, openalex_search, pubmed_search, crossref_search) to perform the searches.
2. If a specific tool for a database (like DOAJ or CORE) is not available, use Google Scholar search to capture papers from those repositories.
3. For arxiv_search, openalex_search, pubmed_search, and crossref_search you MUST use SHORT queries (2-5 keywords, NO boolean operators, NO parentheses). But make them SPECIFIC and targeted, not generic.
   - BAD (too generic): "deep learning breast cancer"
   - BAD (too long): "(deep learning OR machine learning) AND (breast cancer OR mammography) AND (sensitivity OR specificity)"
   - GOOD (specific + short): "mammography CNN diagnostic accuracy"
   - GOOD (specific + short): "explainable AI breast cancer detection"
4. For google_scholar_search only, you may use the full boolean query.
5. ALWAYS call openalex_search and pubmed_search — they provide the best full abstracts.
6. CRITICAL: Make at most 4 tool calls per round. You can make more calls in the next round.
7. REFINE STRATEGY: Analyze the volume and relevance of the returned results. 
   - If a query returns 0 results (too few), immediately formulate a broader, simpler query and search again using the tools in the next step.
   - If a query returns completely irrelevant/generic results (too many), formulate a stricter query using more precise keywords and search again.
8. Validate the results against the defined Inclusion/Exclusion criteria internally before deciding if you've found enough good papers.
9. Summarize the initial findings and the volume of results once you are satisfied.
"""

EXTRACT_PAPERS_PROMPT = """
You are a fastidious data extraction assistant.
Extract EVERY SINGLE academic paper mentioned in the following unstructured search results text.
DO NOT summarize or group them. You must create a distinct entry for each paper you find.

For each paper, find its Title, Year, URL, Abstract, and Database Source.
If a specific field is entirely missing, use "N/A".

It is CRITICAL that you do not skip any papers. You must extract all of them no matter how long the list is.
just 20 papers
Search Results to extract from:
{search_results}
"""


# -----------------------------------------
# INCLUSION / EXCLUSION CRITERIA
# -----------------------------------------
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
# STEP 4 — DATA EXTRACTION
# =========================

METADATA_SUMMARY_PROMPT = """
Analyze the following metadata collected from selected papers:

{data}

Identify:
- Main research themes
- Common methods used
- Emerging trends or patterns
"""


THEMATIC_EXTRACTION_PROMPT = """
Analyze the following paper:

Title:
{title}

Abstract:
{abstract}

Identify:
- The main method used
- The type of network or system studied
- The primary challenge addressed
- The key contribution
"""


# =========================
# STEP 5 — WRITING
# =========================

OUTLINE_PROMPT = """
Create a clear and logical outline for a systematic literature review based on:

{question}

The structure should follow academic standards and ensure a coherent flow.
"""


SECTION_WRITING_PROMPT = """
Write a section of a literature review.

Section:
{section}

Context:
{insights}

Requirements:
- Use a formal academic tone
- Base the content on the provided insights
- Avoid unsupported claims or fabricated references
- Ensure clarity and coherence
"""


# =========================
# STEP 6 — SYNTHESIS
# =========================

SYNTHESIS_PROMPT = """
Combine the following sections into a coherent and well-structured literature review:

{sections}

Ensure:
- Logical flow between sections
- No redundancy
- Consistent academic tone
"""


GAP_IDENTIFICATION_PROMPT = """
Based on the following insights:

{insights}

Identify:
- Key research gaps
- Promising directions for future work

Provide clear and thoughtful analysis.
"""