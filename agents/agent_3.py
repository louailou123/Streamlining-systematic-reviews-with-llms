"""
Step 3 — Screening Agent Nodes (LangGraph)
  3.a  deduplicate_node    — removes duplicate papers from raw_dataset.csv
  3.b  llm_classify_node   — classifies each paper using the project LLM + state criteria
  3.c  asreview_screen_node — pauses for human screening in ASReview and generates initial_dataset.csv
"""

import csv
import re
import time
import subprocess
import sys
import os
from typing import Dict, Any, List, Tuple
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
    """Lowercase, strip trailing year parens, remove punctuation."""
    if not title:
        return ""
    title = re.sub(r"\s*\(.*?\)\s*$", "", title)
    title = re.sub(r"[^\w\s]", "", title.lower())
    return " ".join(title.split())


def _normalize_doi(doi: str) -> str:
    """Normalize a DOI string for comparison."""
    if not doi or doi.strip() in ("", "N/A", "None"):
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://doi\.org/", "", doi)
    return doi


def _titles_similar(t1: str, t2: str, threshold: float = 0.90) -> bool:
    """Fuzzy title match."""
    return SequenceMatcher(None, t1, t2).ratio() >= threshold


def _read_csv(path: str) -> Tuple[List[str], List[dict]]:
    """Return (fieldnames, rows) from a CSV file."""
    rows: List[dict] = []
    with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            rows.append(row)
    return fieldnames, rows


def _write_csv(path: str, fieldnames: List[str], rows: List[dict]) -> None:
    """Write rows to a CSV file with full quoting for robust parsing."""
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)


def _pick_first_nonempty(row: dict, keys: List[str]) -> str:
    """Return first non-empty value from a list of candidate keys."""
    for key in keys:
        value = row.get(key, "")
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_binary_label(value: Any) -> str:
    """
    Normalize label values like 1, 1.0, '1', '1.0', True into '1'
    and 0, 0.0, '0', '0.0', False into '0'. Otherwise ''.
    """
    if value is None:
        return ""

    s = str(value).strip().lower()
    if s in {"1", "1.0", "true", "yes"}:
        return "1"
    if s in {"0", "0.0", "false", "no"}:
        return "0"
    return ""


def _is_real_value(value: Any) -> bool:
    """True only for values worth keeping in exported CSVs."""
    if value is None:
        return False
    s = str(value).strip()
    if not s:
        return False
    if s.lower() in {"n/a", "none", "null", "nan", "unknown"}:
        return False
    return True


def _clean_row_keep_real_values(row: dict) -> dict:
    """Keep only keys with real values."""
    cleaned = {}
    for k, v in row.items():
        if _is_real_value(v):
            cleaned[k] = str(v).strip()
    return cleaned


def _collect_existing_headers(rows: List[dict], preferred_order: List[str] | None = None) -> List[str]:
    """Build headers only from fields that truly exist."""
    preferred_order = preferred_order or []
    seen = set()
    headers: List[str] = []

    for key in preferred_order:
        for row in rows:
            if key in row and _is_real_value(row[key]):
                if key not in seen:
                    seen.add(key)
                    headers.append(key)
                break

    for row in rows:
        for key, value in row.items():
            if key not in seen and _is_real_value(value):
                seen.add(key)
                headers.append(key)

    return headers


def _normalize_match_key(title: str, doi: str) -> str:
    """Stable key for matching ASReview rows back to richer source rows."""
    clean_title = _normalize_title(title or "")
    clean_doi = _normalize_doi(doi or "")
    return f"{clean_doi}||{clean_title}"


def _pick_best_rich_source(state: LiRAState) -> str:
    """
    Prefer the richest available dataset as the source for final initial_dataset.csv,
    so we preserve added headers like journal, keywords, institutions, etc.
    """
    candidates = [
        state.get("screened_llm_csv", ""),
        state.get("deduplicated_csv", ""),
        state.get("raw_dataset_csv", ""),
        "screened_llm_dataset.csv",
        "deduplicated_dataset.csv",
        "raw_dataset.csv",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def build_initial_dataset_from_asreview_export(
    asreview_export_file: str,
    rich_source_file: str,
    output_file: str = "initial_dataset.csv",
) -> str:
    """
    Build initial_dataset.csv using ASReview inclusion decisions, but preserve
    the richer headers from the pre-ASReview dataset.

    - ASReview export decides which papers are kept (asreview_label == 1)
    - rich_source_file provides the full metadata columns
    """
    export_fields, export_rows = _read_csv(asreview_export_file)

    if "asreview_label" not in export_fields:
        raise ValueError(
            f"'asreview_label' column not found in {asreview_export_file}. "
            "Could not generate initial_dataset.csv."
        )

    if not rich_source_file or not Path(rich_source_file).exists():
        raise ValueError(
            f"Rich source file not found: {rich_source_file}. "
            "Could not preserve enriched headers in initial_dataset.csv."
        )

    rich_fields, rich_rows = _read_csv(rich_source_file)

    include_map = {}
    for row in export_rows:
        human_label = _normalize_binary_label(row.get("asreview_label", ""))
        if human_label == "1":
            key = _normalize_match_key(
                _pick_first_nonempty(row, ["title", "Title"]),
                _pick_first_nonempty(row, ["doi", "DOI"]),
            )
            include_map[key] = True

    kept: List[dict] = []
    seen_keys = set()

    for row in rich_rows:
        key = _normalize_match_key(
            _pick_first_nonempty(row, ["title", "Title"]),
            _pick_first_nonempty(row, ["doi", "DOI"]),
        )
        if include_map.get(key):
            kept.append(row)
            seen_keys.add(key)

    unmatched_titles = set()
    for row in export_rows:
        human_label = _normalize_binary_label(row.get("asreview_label", ""))
        if human_label == "1":
            key = _normalize_match_key(
                _pick_first_nonempty(row, ["title", "Title"]),
                _pick_first_nonempty(row, ["doi", "DOI"]),
            )
            if key not in seen_keys:
                unmatched_titles.add(_normalize_title(_pick_first_nonempty(row, ["title", "Title"])))

    if unmatched_titles:
        for row in rich_rows:
            norm_title = _normalize_title(_pick_first_nonempty(row, ["title", "Title"]))
            if norm_title in unmatched_titles:
                key = _normalize_match_key(
                    _pick_first_nonempty(row, ["title", "Title"]),
                    _pick_first_nonempty(row, ["doi", "DOI"]),
                )
                if key not in seen_keys:
                    kept.append(row)
                    seen_keys.add(key)

    _write_csv(output_file, rich_fields, kept)
    return output_file


# ═══════════════════════════════════════════════════════════════
# NODE 3.a — DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

def deduplicate_node(state: LiRAState) -> Dict[str, Any]:
    """
    Reads raw_dataset.csv, removes duplicates on DOI (exact) and
    Title (≥90% fuzzy match), writes deduplicated_dataset.csv.
    """
    input_file = state.get("raw_dataset_csv", "raw_dataset.csv")
    output_file = "deduplicated_dataset.csv"
    logs = list(state.get("logs", []))

    if not Path(input_file).exists():
        logs.append(f"[Dedup] ERROR: {input_file} not found — skipping.")
        return {"logs": logs}

    fieldnames, papers = _read_csv(input_file)
    total_before = len(papers)

    seen_dois: set = set()
    doi_dups = 0
    after_doi: List[dict] = []

    for paper in papers:
        doi = _normalize_doi(_pick_first_nonempty(paper, ["DOI", "doi"]))
        if doi:
            if doi in seen_dois:
                doi_dups += 1
                continue
            seen_dois.add(doi)
        after_doi.append(paper)

    seen_titles: List[str] = []
    title_dups = 0
    unique: List[dict] = []

    for paper in after_doi:
        title = _pick_first_nonempty(paper, ["Title", "title"])
        norm_title = _normalize_title(title)

        if not norm_title:
            unique.append(paper)
            continue

        is_dup = False
        for existing_title in seen_titles:
            if _titles_similar(norm_title, existing_title):
                is_dup = True
                title_dups += 1
                break

        if not is_dup:
            seen_titles.append(norm_title)
            unique.append(paper)

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
    For each paper in deduplicated_dataset.csv, call the project LLM
    with the inclusion/exclusion criteria from state.

    Writes screened_llm_dataset.csv with:
      - llm_included
      - llm_excluded
      - llm_justification
    """
    dedup_csv = state.get("deduplicated_csv", "deduplicated_dataset.csv")
    raw_csv = state.get("raw_dataset_csv", "raw_dataset.csv")
    input_file = dedup_csv if Path(dedup_csv).exists() else raw_csv
    output_file = "screened_llm_dataset.csv"
    logs = list(state.get("logs", []))

    if not Path(input_file).exists():
        logs.append(f"[Screen] ERROR: {input_file} not found — skipping.")
        return {"logs": logs}

    inclusion = state.get("inclusion_criteria", [])
    exclusion = state.get("exclusion_criteria", [])

    inclusion_str = (
        "\n".join(f"  - {c}" for c in inclusion)
        if inclusion
        else "  - Directly related to the research question"
    )
    exclusion_str = (
        "\n".join(f"  - {c}" for c in exclusion)
        if exclusion
        else "  - Not related to the research question"
    )

    question = ""
    if state.get("final_ranked_questions"):
        question = state["final_ranked_questions"][0].get("question", "")
    if not question:
        question = state.get("reframed_question", state.get("topic", ""))

    fieldnames, papers = _read_csv(input_file)

    required_cols = ["llm_included", "llm_excluded", "llm_justification"]
    out_fields = list(fieldnames)
    for col in required_cols:
        if col not in out_fields:
            out_fields.append(col)

    llm = get_llm()
    stats = {"included": 0, "excluded": 0, "errors": 0}
    delay = 2.0
    max_retries = 3

    print(f"\n[Screen] Screening {len(papers)} papers from {input_file} ...")

    for i, paper in enumerate(papers):
        title = _pick_first_nonempty(paper, ["Title", "title"])
        abstract = _pick_first_nonempty(paper, ["Abstract", "abstract"])

        if not abstract or abstract.strip() in ("N/A", ""):
            abstract = "(No abstract available — classify based on title only.)"

        prompt_text = LLM_SCREENING_PROMPT.format(
            title=title,
            abstract=abstract,
            question=question,
            inclusion_criteria=inclusion_str,
            exclusion_criteria=exclusion_str,
        )

        inc = "0"
        exc = "0"
        justification = ""

        for attempt in range(1, max_retries + 1):
            try:
                result = invoke_structured(llm, prompt_text, ScreeningResult)
                inc = "1" if result.included == 1 else "0"
                exc = "1" if result.excluded == 1 else "0"
                justification = result.justification or "No justification provided."
                break
            except Exception as e:
                if attempt < max_retries:
                    print(f"    Retry {attempt}/{max_retries} for paper {i+1}: {e}")
                    time.sleep(delay)
                else:
                    print(f"    FAILED after {max_retries} attempts for paper {i+1}: {e}")
                    inc = "0"
                    exc = "1"
                    justification = f"Classification failed after {max_retries} retries: {e}"
                    stats["errors"] += 1

        paper["llm_included"] = inc
        paper["llm_excluded"] = exc
        paper["llm_justification"] = justification

        if paper["llm_included"] == "0" and paper["llm_excluded"] == "0":
            paper["llm_excluded"] = "1"
            paper["llm_justification"] += " (Auto-excluded: LLM did not make a clear decision.)"

        if paper["llm_included"] == "1":
            stats["included"] += 1
        if paper["llm_excluded"] == "1":
            stats["excluded"] += 1

        status = "INCLUDED" if inc == "1" and exc != "1" else "EXCLUDED"
        print(f"  [{i+1}/{len(papers)}] {status}: {title[:60]}...")

        if i < len(papers) - 1:
            time.sleep(delay)

    _write_csv(output_file, out_fields, papers)

    msg = (
        f"[Screen] Done — LLM included:{stats['included']}, "
        f"LLM excluded:{stats['excluded']}, errors:{stats['errors']} "
        f"out of {len(papers)} → {output_file}"
    )
    print(msg)
    logs.append(msg)

    return {
        "screened_llm_csv": output_file,
        "logs": logs,
    }


# ═══════════════════════════════════════════════════════════════
# NODE 3.c — ASREVIEW MANUAL SCREENING (HUMAN-IN-THE-LOOP)
# ═══════════════════════════════════════════════════════════════

def asreview_screen_node(state: LiRAState) -> Dict[str, Any]:
    """
    ASReview human-in-the-loop screening step.

    Flow:
      1. Check if an uploaded ASReview export file exists (resume path).
         If yes, process it and create initial_dataset.csv.
      2. If no upload yet: Prepare the ASReview-compatible CSV import file,
         auto-launch ASReview LAB, and return state.
         The approval gate (gate_asreview) will pause the pipeline and show
         the upload UI. When resumed, this node runs again with the uploaded file.
    """
    import glob

    logs = list(state.get("logs", []))

    # ── RESUME PATH: Check if an ASReview export file was uploaded ──
    # Look for uploaded export files in the current directory
    uploaded_exports = [
        f for f in glob.glob("asreview_export*.*")
        if Path(f).exists() and Path(f).stat().st_size > 0
    ]
    # Also check for any CSV uploaded through the gate system
    if not uploaded_exports:
        uploaded_exports = [
            f for f in glob.glob("*.csv")
            if "asreview_export" in f.lower() or "asreview_result" in f.lower()
        ]

    if uploaded_exports:
        export_path = uploaded_exports[0]
        logs.append(f"[ASReview] Found uploaded export file: {export_path}")

        try:
            asreview_export_local = "asreview_export.csv"
            initial_dataset_file = "initial_dataset.csv"

            export_fields, export_rows = _read_csv(export_path)
            # If the uploaded file is not already named asreview_export.csv, copy it
            if export_path != asreview_export_local:
                _write_csv(asreview_export_local, export_fields, export_rows)

            rich_source_file = _pick_best_rich_source(state)

            initial_dataset_file = build_initial_dataset_from_asreview_export(
                asreview_export_file=asreview_export_local,
                rich_source_file=rich_source_file,
                output_file=initial_dataset_file,
            )

            _, initial_rows = _read_csv(initial_dataset_file)

            msg = (
                f"[ASReview] Processed export from {export_path}. "
                f"Generated {initial_dataset_file} with {len(initial_rows)} included papers "
                f"(asreview_label == 1), preserving enriched headers from {rich_source_file}."
            )
            print(msg)
            logs.append(msg)

            return {
                "screened_human_csv": asreview_export_local,
                "asreview_screened_csv": asreview_export_local,
                "initial_dataset_csv": initial_dataset_file,
                "logs": logs,
            }

        except Exception as e:
            msg = f"[ASReview] ERROR processing export file: {e}"
            print(msg)
            logs.append(msg)
            return {"logs": logs}

    # ── FIRST RUN: Prepare import file and launch ASReview ──

    # 1. Find the best available input CSV
    llm_csv = state.get("screened_llm_csv", "screened_llm_dataset.csv")
    dedup_csv = state.get("deduplicated_csv", "deduplicated_dataset.csv")
    raw_csv = state.get("raw_dataset_csv", "raw_dataset.csv")

    input_file = None
    for candidate in [llm_csv, dedup_csv, raw_csv]:
        if candidate and Path(candidate).exists():
            input_file = candidate
            break

    if not input_file:
        logs.append("[ASReview] ERROR: No input CSV found — skipping.")
        return {"logs": logs}

    # 2. Build ASReview-compatible import CSV, preserving rich metadata fields
    asreview_import = "asreview_import.csv"
    _, papers = _read_csv(input_file)

    asreview_rows: List[dict] = []

    for paper in papers:
        title = _pick_first_nonempty(paper, ["Title", "title"])
        abstract = _pick_first_nonempty(paper, ["Abstract", "abstract"])
        doi = _pick_first_nonempty(paper, ["DOI", "doi"])

        llm_included = _normalize_binary_label(paper.get("llm_included", ""))
        llm_excluded = _normalize_binary_label(paper.get("llm_excluded", ""))

        if llm_included == "1" and llm_excluded != "1":
            included_label = "1"
        elif llm_excluded == "1":
            included_label = "0"
        else:
            included_label = ""

        # Start from richer source row
        row = _clean_row_keep_real_values(dict(paper))

        # Canonical ASReview fields
        row["title"] = title
        row["abstract"] = abstract
        row["doi"] = doi

        # Screening helper columns
        if _is_real_value(included_label):
            row["included_label"] = included_label
        if _is_real_value(llm_included):
            row["llm_included"] = llm_included
        if _is_real_value(llm_excluded):
            row["llm_excluded"] = llm_excluded
        if _is_real_value(paper.get("llm_justification", "")):
            row["llm_justification"] = str(paper.get("llm_justification")).strip()

        # Remove duplicate alternate-case keys
        for redundant_key in ["Title", "Abstract", "DOI"]:
            row.pop(redundant_key, None)

        asreview_rows.append(row)

    preferred_asreview_fields = [
        "title",
        "abstract",
        "doi",
        "included_label",
        "llm_included",
        "llm_excluded",
        "llm_justification",
        "year",
        "authors",
        "source",
        "journal",
        "publisher",
        "publication_date",
        "document_type",
        "keywords",
        "institutions",
        "countries",
        "citation_count",
        "language",
        "pmid",
        "funding_info",
        "url",
    ]

    asreview_fields = _collect_existing_headers(asreview_rows, preferred_asreview_fields)
    _write_csv(asreview_import, asreview_fields, asreview_rows)

    total = len(asreview_rows)
    included_count = sum(1 for p in asreview_rows if p.get("included_label") == "1")
    excluded_count = sum(1 for p in asreview_rows if p.get("included_label") == "0")

    msg = (
        f"[ASReview] Prepared {asreview_import} with {total} papers "
        f"and {len(asreview_fields)} real columns "
        f"(LLM prior labels: {included_count} included, {excluded_count} excluded)"
    )
    print(msg)
    logs.append(msg)

    # 3. Auto-launch ASReview LAB
    asreview_port = os.environ.get("ASREVIEW_PORT", "5001")
    print(f"[ASReview] Starting ASReview LAB on port {asreview_port}...")
    try:
        subprocess.Popen(
            [sys.executable, "-m", "asreview", "lab", "--host", "0.0.0.0", "--port", asreview_port],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        asreview_url = f"http://localhost:{asreview_port}"
        logs.append(f"[ASReview] ASReview LAB launched at {asreview_url}")
    except Exception as e:
        warn = f"[ASReview] WARNING: Could not auto-start ASReview LAB: {e}"
        print(warn)
        logs.append(warn)
        asreview_url = f"http://localhost:{asreview_port}"

    import_path = str(Path(asreview_import).resolve())

    msg = (
        f"[ASReview] Import file ready at: {import_path}\n"
        f"  ASReview LAB: {asreview_url}\n"
        f"  Papers to screen: {total}\n"
        f"  LLM prior included: {included_count}\n"
        f"  LLM prior excluded: {excluded_count}"
    )
    print(msg)
    logs.append(msg)

    # Return state — the gate_asreview will pause the pipeline
    # and show the upload UI to the user
    return {
        "screened_llm_csv": state.get("screened_llm_csv"),
        "logs": logs,
        "current_step": "Step 3.c — ASReview Screening",
    }