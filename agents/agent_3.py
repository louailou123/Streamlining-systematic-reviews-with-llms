"""
Step 3 — Screening Agent Nodes (LangGraph)
  3.a  deduplicate_node    — removes duplicate papers from raw_dataset.csv
  3.b  llm_classify_node   — classifies each paper using the project LLM + state criteria
"""

import csv
import re
import time
from typing import Dict, Any, List
from pathlib import Path
from difflib import SequenceMatcher

from llm.llm import get_llm
from llm.structured_parser import invoke_structured
from State.state import LiRAState
from Schemas.schemas import ScreeningResult
from Prompts.prompts import LLM_SCREENING_PROMPT


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_title(title: str) -> str:
    """Lowercase, strip year parens, remove punctuation."""
    title = re.sub(r'\s*\(.*?\)\s*$', '', title)
    title = re.sub(r'[^\w\s]', '', title.lower())
    return ' '.join(title.split())


def _normalize_doi(doi: str) -> str:
    """Normalize a DOI string for comparison."""
    if not doi or doi.strip() in ('', 'N/A'):
        return ''
    doi = doi.strip().lower()
    doi = re.sub(r'^https?://doi\.org/', '', doi)
    return doi


def _titles_similar(t1: str, t2: str, threshold: float = 0.90) -> bool:
    return SequenceMatcher(None, t1, t2).ratio() >= threshold


def _read_csv(path: str) -> tuple:
    """Return (fieldnames, rows) from a CSV file."""
    rows = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(row)
    return fieldnames, rows


def _write_csv(path: str, fieldnames: list, rows: list):
    """Write rows to a CSV file."""
    with open(path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ═══════════════════════════════════════════════════════════════
# NODE 3.a — DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

def deduplicate_node(state: LiRAState) -> Dict[str, Any]:
    """
    Reads raw_dataset.csv, removes duplicates on DOI (exact) and
    Title (≥90 % fuzzy match), writes deduplicated_dataset.csv.
    """
    input_file = state.get("raw_dataset_csv", "raw_dataset.csv")
    output_file = "deduplicated_dataset.csv"
    logs = list(state.get("logs", []))

    if not Path(input_file).exists():
        logs.append(f"[Dedup] ERROR: {input_file} not found — skipping.")
        return {"logs": logs}

    fieldnames, papers = _read_csv(input_file)
    total_before = len(papers)

    # Pass 1 — exact DOI dedup
    seen_dois: set = set()
    doi_dups = 0
    after_doi: List[dict] = []
    for p in papers:
        doi = _normalize_doi(p.get('DOI', ''))
        if doi:
            if doi in seen_dois:
                doi_dups += 1
                continue
            seen_dois.add(doi)
        after_doi.append(p)

    # Pass 2 — fuzzy title dedup
    seen_titles: List[str] = []
    title_dups = 0
    unique: List[dict] = []
    for p in after_doi:
        norm = _normalize_title(p.get('Title', ''))
        if not norm:
            unique.append(p)
            continue
        is_dup = False
        for existing in seen_titles:
            if _titles_similar(norm, existing):
                is_dup = True
                title_dups += 1
                break
        if not is_dup:
            seen_titles.append(norm)
            unique.append(p)

    total_removed = total_before - len(unique)
    _write_csv(output_file, fieldnames, unique)

    msg = (
        f"[Dedup] {total_before} papers → {len(unique)} unique "
        f"(DOI dups:{doi_dups}, title dups:{title_dups}, total removed:{total_removed})"
    )
    print(msg)
    logs.append(msg)

    return {
        "deduplicated_csv": output_file,
        "logs": logs,
    }


# ═══════════════════════════════════════════════════════════════
# NODE 3.b — LLM CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

def llm_classify_node(state: LiRAState) -> Dict[str, Any]:
    """
    For each paper in deduplicated_dataset.csv, calls the project LLM
    with the inclusion/exclusion criteria from state.
    Uses invoke_structured to parse into ScreeningResult schema.
    Writes screened_llm_dataset.csv with 'included', 'excluded', and 'justification' columns.
    """
    # Resolve input file
    dedup_csv = state.get("deduplicated_csv", "deduplicated_dataset.csv")
    raw_csv = state.get("raw_dataset_csv", "raw_dataset.csv")
    input_file = dedup_csv if Path(dedup_csv).exists() else raw_csv
    output_file = "screened_llm_dataset.csv"
    logs = list(state.get("logs", []))

    if not Path(input_file).exists():
        logs.append(f"[Screen] ERROR: {input_file} not found — skipping.")
        return {"logs": logs}

    # Format criteria from state (populated by define_criteria_node in Step 2)
    inclusion = state.get("inclusion_criteria", [])
    exclusion = state.get("exclusion_criteria", [])
    inclusion_str = "\n".join(f"  - {c}" for c in inclusion) if inclusion else "  - Directly related to MADRL in communication networks"
    exclusion_str = "\n".join(f"  - {c}" for c in exclusion) if exclusion else "  - Not related to deep reinforcement learning or networking"

    # Get the research question from state
    question = ""
    if state.get("final_ranked_questions"):
        question = state["final_ranked_questions"][0].get("question", "")
    if not question:
        question = state.get("reframed_question", state.get("topic", ""))

    fieldnames, papers = _read_csv(input_file)
    new_cols = []
    for col in ['included', 'excluded', 'justification']:
        if col not in fieldnames:
            new_cols.append(col)
    out_fields = fieldnames + new_cols

    llm = get_llm()
    stats = {'included': 0, 'excluded': 0, 'both': 0}
    delay = 2.0

    print(f"\n[Screen] Screening {len(papers)} papers from {input_file} ...")

    for i, paper in enumerate(papers):
        title = paper.get('Title', '')
        abstract = paper.get('Abstract', '')

        # Skip papers without an abstract
        if not abstract or abstract.strip() in ('N/A', ''):
            paper['included'] = '0'
            paper['excluded'] = '1'
            paper['justification'] = 'No abstract available for screening.'
            stats['excluded'] += 1
            print(f"  [{i+1}/{len(papers)}] SKIP (no abstract): {title[:60]}...")
            continue

        # Build prompt from the shared template
        prompt_text = LLM_SCREENING_PROMPT.format(
            title=title,
            abstract=abstract,
            question=question,
            inclusion_criteria=inclusion_str,
            exclusion_criteria=exclusion_str,
        )

        try:
            result = invoke_structured(llm, prompt_text, ScreeningResult)
            inc = '1' if result.included == 1 else '0'
            exc = '1' if result.excluded == 1 else '0'
            justification = result.justification or 'No justification provided.'
        except Exception as e:
            print(f"    Error on paper {i+1}: {e} — defaulting to excluded.")
            inc = '0'
            exc = '1'
            justification = f'Classification error: {e}'

        paper['included'] = inc
        paper['excluded'] = exc
        paper['justification'] = justification

        if inc == '1':
            stats['included'] += 1
        if exc == '1':
            stats['excluded'] += 1

        status = 'INCLUDED' if inc == '1' and exc == '0' else 'EXCLUDED'
        print(f"  [{i+1}/{len(papers)}] {status}: {title[:60]}...")

        # Rate-limit
        if i < len(papers) - 1:
            time.sleep(delay)

    _write_csv(output_file, out_fields, papers)

    msg = (
        f"[Screen] Done — included:{stats['included']}, excluded:{stats['excluded']} "
        f"out of {len(papers)} → {output_file}"
    )
    print(msg)
    logs.append(msg)

    return {
        "screened_llm_csv": output_file,
        "logs": logs,
    }

