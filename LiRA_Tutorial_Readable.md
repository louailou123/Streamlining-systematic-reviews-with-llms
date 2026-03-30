# LiRA: A Tutorial for LLM-Accelerated Literature Review

**Author:** Prof. Mustapha Reda Senouci  
**Date:** March 16, 2026  
**Version:** v2026.03.16

---

## Introduction

The process of conducting a comprehensive literature review is often time-consuming and labor-intensive. **LiRA (Literature Review Assistant)** is a system designed to accelerate this task by strategically integrating the capabilities of Large Language Models (LLMs) with traditional literature review methodologies and specialized tools.

### LiRA Workflow (6 Steps)

1. Generate a good research question
2. Build a search strategy and execute it
3. Screening using tools
4. Automatic extraction of insights
5. Reading + Drafting
6. Synthesis and gaps identification

---

## Step 1: Generate a Good Research Question

The foundation of a successful literature review is a clear, well-scoped research question.

### 1.a: Leveraging LLMs and Structuring Frameworks

LLMs can assist in brainstorming and refining research questions using frameworks:

- **PICO** (Population, Intervention, Comparison, Outcome)
- **PICOC** (Population, Intervention, Comparison, Outcome, Context)
- **SPIDER** (Sample, Phenomenon of Interest, Design, Evaluation, Research type)
- **SPICE** (Setting, Perspective, Intervention, Comparison, Evaluation)
- **PEO** (Population, Exposure, Outcome)

#### Selecting the Right Framework

| Framework | Best For |
|-----------|----------|
| **PICO** | Quantitative, experimental comparisons (e.g., performance of algorithms/systems) |
| **PICOC** | Systematic reviews where context matters (environment, hardware, protocol) |
| **SPIDER** | Qualitative or design-based research (user experiences, development practices) |
| **SPICE** | Applied settings with user roles and interventions |
| **PEO** | Observational or causal questions (e.g., network conditions effect on protocols) |

#### Example Prompts

**Prompt #1: Initial Question Generation**
```
Generate 3-5 research questions about the challenges of using MADRL in highly 
dynamic communication networks, focusing on the scalability and robustness aspects. 
Consider the context of resource-constrained IoT devices.
```

**Expected Output:**
- How does MADRL scale in decentralized routing for low-power IoT networks under fluctuating connectivity?
- What strategies improve the robustness of MADRL-based decision-making in volatile mesh network topologies?
- How do resource constraints in IoT devices affect the learning stability of MADRL agents in real-time communication tasks?

**Prompt #2: Framework Selection**
```
Based on the research topic 'challenges of MADRL in dynamic IoT networks', which 
framework (PICO, SPIDER, SPICE, etc.) is most suitable for structuring a research 
question for a systematic review? Justify your answer.
```

**Expected Output:**
> PICOC is appropriate because the research question involves comparing MADRL variants (Intervention/Comparison) in IoT environments (Context), focusing on outcomes like scalability and robustness (Outcome).

**Prompt #3: Framework Application**
```
Reframe the question 'How robust is MADRL in dynamic IoT environments?' using the 
SPIDER framework.
```

**Expected Output:**
```
SPIDER Breakdown:
- Sample: Studies using MADRL in IoT networks
- Phenomenon: Robustness of decision-making under dynamic topology
- Design: Simulation-based experiments
- Evaluation: Success rate, message delivery ratio, convergence time
- Research Type: Quantitative empirical studies

Reframed Question: "How is robustness evaluated in MADRL-based routing algorithms 
for dynamic IoT networks in simulation studies?"
```

### 1.b: Ensure Feasibility of the LR

**Manual Check:** Conduct preliminary searches on Google Scholar or Scopus to assess available literature volume.

**LLM-Assisted Estimation:**

**Prompt #4:**
```
Based on this research question [RQ], estimate the number of relevant publications 
likely available and the feasibility of reviewing them within a 3-month timeframe. 
Consider the broadness/narrowness of the topic.
```

### 1.c: Ensure Originality of the LR

Confirm your research question hasn't been addressed by existing surveys.

**Manual Check:** Search for existing survey papers on platforms like Google Scholar.

**Prompt #5:**
```
Find and summarize 3–5 recent survey papers on 'Reinforcement Learning for Network 
Routing'. Identify coverage overlap and potential gaps for a new literature review 
focused on MADRL in dynamic environments.
```

**Prompt #6:**
```
Generate 3 research questions about MADRL in networks that are feasible for a 
literature review within 2 months and have not been extensively covered in recent 
survey papers. Rank them by novelty and potential impact.
```

**Expected Output:**
- **High Novelty:** How do meta-learning strategies influence the adaptability of MADRL agents to abrupt topology changes in low-latency networks?
- **Moderate Novelty:** What role do attention mechanisms play in improving coordination in multi-agent routing across heterogeneous IoT layers?
- **Low Novelty:** How does MADRL compare to centralized DQN approaches in mobile ad hoc networks?

**Summary:**
- Use LLMs to rapidly iterate on question ideas
- Match your question to a framework based on research type
- Validate feasibility manually and simulate with LLMs
- Check originality through surveys and summaries

---

## Step 2: Build a Search Strategy and Execute It

A strong search strategy ensures you capture relevant, high-impact, and recent work while minimizing irrelevant noise.

### 2.a: Define the Search Query

Your search query should include:
- Core concepts and synonyms
- Boolean operators (AND, OR, NOT)
- Specific fields (Title, Abstract, Keywords)
- Filters (publication year, document type)

**Prompt #7: Term Expansion**
```
List relevant synonyms and domain-specific variations for the concepts:
(1) Multi-agent deep reinforcement learning
(2) Network routing
(3) Future network architectures (e.g., ICN, UAV, etc.)
```

#### Example Search Queries

**Scopus/Web of Science:**
```
TITLE-ABS-KEY((("Multi-Agent Deep Reinforcement Learning" OR "MADRL") AND 
("IoT" OR "IIoT" OR "ICN" OR "NDN" OR "SDN" OR "UAV" OR "5G" OR "6G" OR 
"MANET*" OR "VANET*" OR "FANET*" OR "network*")))
```

**IEEE Xplore:**
```
TITLE-ABS-KEY ( ( "multiagent deep reinforcement learning" OR "MADRL" OR 
"multi-agent RL" OR "MARL" ) AND ( "network routing" OR "packet routing" OR 
"routing protocol" OR "traffic engineering" ) AND ( "communication network*" OR 
"wireless network*" OR "6G" OR "O-RAN" OR "NDN" OR "satellite network*" ) ) AND 
PUBYEAR > 2019 AND PUBYEAR < 2026
```

**ACM Digital Library:**
```
[[All: "multiagent deep reinforcement learning"] OR [All: "MADRL"]] AND 
[[All: "network routing"] OR [All: "traffic engineering"]] AND 
[[All: "wireless network*"] OR [All: "6G"] OR [All: "O-RAN"] OR [All: "ICN"]] AND 
[E-Publication Date: (01/01/2019 TO 12/31/2025)]
```

#### Tips for Query Design
- Start broad, then refine
- Use wildcards (*) cautiously (IEEE limits wildcard count)
- Adapt query logic to each platform's syntax

**Prompt #8: Query Translation**
```
Translate this IEEE Xplore query to be compatible with Scopus and ACMDL syntax, 
while preserving field targeting and Boolean logic.
```

### 2.b: Where to Search

Common databases:
- Google Scholar
- ACM Digital Library
- ScienceDirect (Elsevier)
- SpringerLink
- Web of Science
- Scopus

**Prompt #9:**
```
Given a research question on 'MADRL for dynamic routing in IoT and 6G networks', 
rank IEEE Xplore, Scopus, Web of Science, and ACMDL based on coverage and relevance. 
Explain the criteria.
```

### 2.c: Define Inclusion and Exclusion Criteria

| Inclusion Criteria | Exclusion Criteria |
|-------------------|-------------------|
| Peer-reviewed conference/journal papers | Studies not using RL or DRL |
| Publications between 2019 and 2025 | Non-English papers |
| Directly related to research question | Not aligned with research question |

**Prompt #10:**
```
Suggest initial inclusion and exclusion criteria for a systematic review using the 
PICO framework, focusing on MADRL for resource-constrained IoT network routing.
```

**Prompt #11:**
```
According to PRISMA guidelines and based on this research question: '[insert]', 
what inclusion/exclusion criteria are most critical?
```

### 2.d: Execute, Refine, and Document

1. Run searches in selected databases
2. Refine queries and criteria if too many/too few results
3. Export results (CSV, RIS) into reference manager (e.g., Zotero)
4. De-duplicate and store as `raw_dataset`
5. Record search queries, filters, and results per PRISMA 2020 standards

**Prompt #12:**
```
Generate a PRISMA-style search strategy documentation table based on the following 
queries and database outputs: [insert queries + search metadata].
```

**Caveats:**
- ACMDL doesn't expose full abstracts in search exports
- IEEE has wildcard count limits
- arXiv includes non-peer-reviewed work

---

## Step 3: Screening Using Tools

Screening filters your `raw_dataset` based on inclusion/exclusion criteria.

### Tools Setup

```bash
conda create --name LIRA python=3.13
conda activate LIRA
pip install google-generativeai
conda install conda-forge::openai
conda install conda-forge::seaborn
```

**API Key:** Obtain a Gemini API key from Google AI Studio.

### 3.a: Data Deduplication

Run `clean_duplicate.py` to remove duplicate entries from `raw_dataset`.

### 3.b: LLM-based Pre-screening

**Prompt #13: Relevance Classification**
```
Determine if the paper [title + abstract] is relevant to the scope of research 
focused on Multi-Agent Deep Reinforcement Learning implemented in recent and 
emerging communication network environments. Output '1' if relevant, and '0' if 
not relevant.

Relevance Criteria: The paper must discuss the implementation or application of 
Multi-Agent Deep Reinforcement Learning in the context of communication networks 
that are considered recent or emerging (e.g., 5G/6G, IoT, VANETs, Satellite 
Networks, etc.). Papers focusing on theoretical MADRL or applications in 
non-networking domains are NOT considered relevant.
```

#### Two Approaches

**Option 1: Separate Relevance and Criteria Validation**
- First assess relevance
- Then evaluate alignment with specific criteria

**Option 2: Combined Prompt (Recommended)**

**Prompt #14:**
```
Given the following paper [title + abstract], classify it as relevant (1) or not 
relevant (0) to a literature review on the challenges of MADRL in dynamic 
communication networks. Relevant papers must address one or more of the following: 
[explicitly list key criteria from your inclusion criteria, e.g., 'scalability 
issues', 'robustness in dynamic environments', 'application to IoT or similar 
resource-constrained networks'].
```

#### Automated Classification Script

```python
import google.generativeai as genai
from llm_classifier import LLMClassifier, create_custom_config

# Setup Gemini
genai.configure(api_key="your-api-key-here")
model = genai.GenerativeModel('gemini-pro')

# Create classifier instance
classifier = LLMClassifier(model=model, delay_between_requests=3.0)

# Define custom configuration
cybersecurity_config = create_custom_config(
    name="cybersecurity_focus",
    description="Cybersecurity Research Classification",
    prompt_template="""You are a cybersecurity expert analyzing research papers.
    Determine if this paper is relevant to cybersecurity research.
    
    Paper Title: {title}
    Paper Abstract: {abstract}
    
    Relevance Criteria: The paper must address cybersecurity topics such as network
    security, encryption, threat detection, vulnerability assessment, security
    protocols, or cyber defense mechanisms. Papers that only mention security in
    passing or focus on other domains are NOT relevant.
    
    Is the paper relevant to cybersecurity research?
    - '1' for relevant (focuses on cybersecurity topics)
    - '0' for not relevant (does not focus on cybersecurity)
    
    Output your response as a single digit: '0' or '1'""",
    valid_responses=['0', '1'],
    default_response='0'
)

# Add configuration
classifier.add_config(cybersecurity_config)

# Define column mapping
column_mapping = {
    'Title': 'title',
    'Abstract': 'abstract'
}

# Classify papers
results = classifier.classify_papers(
    input_file="research_papers.csv",
    config_name="cybersecurity_focus",
    column_mapping=column_mapping,
    output_file="papers_with_cybersecurity_classification.csv"
)

print("Classification completed!")
print(f"Available configurations: {classifier.list_configs()}")
```

### 3.c: Manual Screening using ASReview

**Why ASReview:** Uses active learning to prioritize the most informative papers.

**Steps:**
1. Install: `pip install asreview`
2. Start: `asreview lab`
3. Import `raw_dataset` (with LLM's "included_label")
4. Screen studies based on inclusion/exclusion criteria
5. Export as `initial_dataset`

---

## Step 4: Automatic Extraction of Insights

Transform `initial_dataset` into structured, actionable insights.

### 4.a: Python Script for Initial Insights (Metadata Analysis)

Use `insights_from_initial_dataset.py` to extract:
- Top authors
- Institutions
- Keywords
- Journals
- Citation counts
- Funding sources
- Collaboration patterns
- Document types

### 4.b: LLM-Driven Thematic Augmentation

**Prompt #15: Country Extraction**
```
Based on the title and abstract of the following paper, identify the country or 
countries where the study was conducted. If not explicitly stated, infer from 
author affiliations. Output only the country name(s).
```

Use `augment_initial_dataset_llms.py` to extract:
- Application domains
- Methods used
- Challenges addressed
- Experimental contexts

Output: `augmented_dataset`

### 4.c: Analysis of the Augmented Dataset

Use `insights_from_augmented_dataset.py` with libraries like:
- pandas
- matplotlib
- seaborn

Generate:
- Charts
- Tables
- Trend summaries

---

## Step 5: Reading + Drafting

In-depth reading of selected studies and drafting the literature review report.

### 5.a: LLM-Generated Initial Outline

**Prompt:**
```
Can you write an outline for a literature review on the challenges of using 
Multi-Agent Deep Reinforcement Learning in highly dynamic communication networks, 
focusing on scalability and robustness aspects, considering the context of 
resource-constrained IoT devices? Include potential themes and sub-themes.
```

### 5.b: Reading and Drafting with LLM Assistance

- Use ChatPDF and LLM-based summarization tools
- Get quick understanding of paper content
- Draft sections with LLM assistance

### 5.c: Proofreading

- Use Grammarly
- Use LLMs for clarity, coherence, and argumentation improvements

---

## Step 6: Synthesis and Gaps Identification

Use **Google NotebookLM** + prompts for synthesis and identifying research gaps.

---

## Suggestions for Improvement

1. **Data Format:** Define different mappings for `raw_dataset` to support other providers (IEEE, WoS)

2. **Prompt Engineering Repository:** Create a repository of well-tested prompts for consistency

3. **Feedback Loop:** Implement mechanism to provide feedback on LLM outputs for refinement

4. **Agent-Based Feedback:** Multi-agent system with reviewer, critic, and verifier roles

5. **Automated Workflow Management:** Use Apache Airflow or Prefect for automation

6. **Knowledge Graphs:** Explore LLM-generated knowledge graphs for structured representation

7. **Different Review Types:** Adapt LiRA for scoping reviews, meta-analyses, etc.

8. **Collaboration Features:** Integrate shared access, synchronized screening, collaborative drafting

9. **Evaluation Metrics:** Define metrics for time saved, comprehensiveness, and quality

---

## LiRA Workflow Diagram

```
Step 1: Generate Research Question (LLMs, Frameworks)
    ↓
Step 2: Build Search Strategy & Execute (Manual, LLM)
    ↓
Initial Dataset (from Databases)
    ↓
Step 3a: LLM Pre-screening (llm_relevance_classifier.py)
    ↓
Initial Dataset with "included_label"
    ↓
Step 3b: Manual Screening (ASReview)
    ↓
Raw Dataset (Relevant Studies)
    ↓
Step 4a: Initial Insights (insights_from_raw_dataset.py)
    ↓
Step 4b: Thematic Augmentation (augment_raw_dataset_llms.py)
    ↓
Augmented Dataset (with Thematic Info)
    ↓
Step 4c: Further Insights & Analysis (insights_from_augmented_dataset.py)
    ↓
Step 5: Reading & Drafting (LLM Assisted)
    ↓
Literature Review Report
```

---

*End of Tutorial*
