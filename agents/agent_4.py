from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Tuple

from llm.llm import get_llm
from llm.structured_parser import invoke_structured
from State.state import LiRAState
from Schemas.schemas import (
    MetadataInsightsSummary,
    ThematicPaperExtraction,
    ThematicSummary,
    Step4AnalysisReport,
)
from Prompts.prompts import STEP4_THEMATIC_EXTRACTION_PROMPT


# ============================================================
# Helpers
# ============================================================

def _pick_first_nonempty(row: dict, keys: List[str]) -> str:
    for key in keys:
        value = row.get(key, "")
        if value is not None and str(value).strip() and str(value).strip() not in {"N/A", "None", "nan"}:
            return str(value).strip()
    return ""


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split()).strip()


def _split_multi(value: str, split_commas: bool = False) -> List[str]:
    if not value:
        return []

    text = str(value).replace("|", ";")
    if split_commas:
        text = text.replace(",", ";")

    items: List[str] = []
    for part in text.split(";"):
        clean = _normalize_text(part)
        if clean and clean.lower() not in {"unknown", "n/a", "none"} and clean not in items:
            items.append(clean)

    return items


def _join_multi(values: List[str]) -> str:
    clean: List[str] = []
    for value in values:
        value = _normalize_text(value)
        if value and value.lower() not in {"unknown", "n/a", "none"} and value not in clean:
            clean.append(value)
    return "; ".join(clean)


def _safe_year(row: dict) -> str:
    year = _pick_first_nonempty(row, ["year", "Year", "publication_year", "Publication Year"])
    return year if year.isdigit() and len(year) == 4 else "Unknown"


def _stable_row_id(row: dict, idx: int) -> str:
    import hashlib

    base = "|".join([
        _pick_first_nonempty(row, ["doi", "DOI"]),
        _pick_first_nonempty(row, ["title", "Title"]),
        str(idx),
    ])
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:12]


def _read_csv(path: str) -> Tuple[List[str], List[dict]]:
    import csv

    with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _write_csv(path: str, fieldnames: List[str], rows: List[dict]) -> str:
    import csv

    with open(path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_json(path: str, payload: Dict[str, Any]) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _top_authors(rows: List[dict], top_n: int = 20) -> Dict[str, int]:
    counter: Counter = Counter()
    for row in rows:
        authors = _pick_first_nonempty(row, ["authors", "Authors"])
        if not authors:
            continue
        for author in authors.replace(" et al.", "").split(","):
            name = _normalize_text(author)
            if name:
                counter[name] += 1
    return dict(counter.most_common(top_n))


def _count_multivalue(rows: List[dict], column: str) -> Dict[str, int]:
    counter: Counter = Counter()
    for row in rows:
        for item in _split_multi(row.get(column, "")):
            counter[item] += 1
    return dict(counter.most_common())


def _flatten_thematic_result(result: ThematicPaperExtraction) -> Dict[str, Any]:
    return {
        "row_id": result.row_id,
        "countries_of_study": _join_multi(result.countries_of_study),
        "application_domain": result.application_domain,
        "algorithm_families": _join_multi(result.algorithm_families),
        "baseline_methods": _join_multi(result.baseline_methods),
        "challenges_addressed": _join_multi(result.challenges_addressed),
        "evaluation_metrics": _join_multi(result.evaluation_metrics),
        "experimental_setting": result.experimental_setting,
        "dataset_simulator_testbed": _join_multi(result.dataset_simulator_testbed),
        "key_findings": _join_multi(result.key_findings),
        "limitations": _join_multi(result.limitations),
        "evidence_snippets": _join_multi(result.evidence_snippets),
        "extraction_confidence": float(result.extraction_confidence),
        "needs_review": bool(result.needs_review),
        "review_reason": result.review_reason,
    }


def _validate_extraction(result: ThematicPaperExtraction, has_abstract: bool) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    if not result.row_id:
        issues.append("Missing row_id")
    if not result.application_domain:
        issues.append("Missing application_domain")
    if not result.experimental_setting:
        issues.append("Missing experimental_setting")
    if not 0.0 <= float(result.extraction_confidence) <= 1.0:
        issues.append("extraction_confidence must be between 0 and 1")
    if has_abstract and not result.key_findings:
        issues.append("Expected key_findings when abstract is available")
    if float(result.extraction_confidence) >= 0.7 and not result.evidence_snippets:
        issues.append("High-confidence extraction should include evidence_snippets")
    return len(issues) == 0, issues

def _top_multivalue(
    rows: List[dict],
    keys: List[str],
    top_n: int = 20,
    split_commas: bool = False,
) -> Dict[str, int]:
    counter: Counter = Counter()
    for row in rows:
        raw = _pick_first_nonempty(row, keys)
        for item in _split_multi(raw, split_commas=split_commas):
            counter[item] += 1
    return dict(counter.most_common(top_n))


def _top_singlevalue(rows: List[dict], keys: List[str], top_n: int = 20) -> Dict[str, int]:
    counter: Counter = Counter()
    for row in rows:
        value = _pick_first_nonempty(row, keys)
        value = _normalize_text(value)
        if value and value.lower() not in {"unknown", "n/a", "none"}:
            counter[value] += 1
    return dict(counter.most_common(top_n))


def _citation_stats(rows: List[dict]) -> Dict[str, float]:
    values: List[int] = []
    for row in rows:
        raw = _pick_first_nonempty(row, ["citation_count", "Citation Count"])
        if raw:
            try:
                values.append(int(float(raw)))
            except Exception:
                pass

    if not values:
        return {
            "papers_with_citation_count": 0,
            "total_citations": 0,
            "average_citations": 0.0,
            "max_citations": 0,
        }

    return {
        "papers_with_citation_count": len(values),
        "total_citations": int(sum(values)),
        "average_citations": round(sum(values) / len(values), 2),
        "max_citations": int(max(values)),
    }


def _collaboration_patterns(rows: List[dict]) -> Dict[str, Any]:
    author_counts: List[int] = []
    institution_counts: List[int] = []
    multi_author_papers = 0
    multi_institution_papers = 0

    for row in rows:
        authors = _split_multi(_pick_first_nonempty(row, ["authors", "Authors"]))
        # fallback for comma-separated author strings
        if not authors:
            raw_authors = _pick_first_nonempty(row, ["authors", "Authors"])
            if raw_authors:
                authors = [
                    _normalize_text(a)
                    for a in raw_authors.replace(" et al.", "").split(",")
                    if _normalize_text(a)
                ]

        institutions = _split_multi(_pick_first_nonempty(row, ["institutions", "Institutions"]))

        if authors:
            author_counts.append(len(authors))
            if len(authors) > 1:
                multi_author_papers += 1

        if institutions:
            institution_counts.append(len(institutions))
            if len(institutions) > 1:
                multi_institution_papers += 1

    total = len(rows) if rows else 1

    return {
        "multi_author_papers": multi_author_papers,
        "multi_author_papers_pct": round((multi_author_papers / total) * 100, 2),
        "multi_institution_papers": multi_institution_papers,
        "multi_institution_papers_pct": round((multi_institution_papers / total) * 100, 2),
        "average_authors_per_paper": round(sum(author_counts) / len(author_counts), 2) if author_counts else 0.0,
        "average_institutions_per_paper": round(sum(institution_counts) / len(institution_counts), 2) if institution_counts else 0.0,
    }
# ============================================================
# Step 4.a — Metadata Analysis (deterministic)
# ============================================================

def metadata_insights_node(state: LiRAState) -> Dict[str, Any]:
    input_file = state.get("initial_dataset_csv", "initial_dataset.csv")
    logs = list(state.get("logs", []))

    if not input_file or not Path(input_file).exists():
        logs.append(f"[Step4-Metadata] ERROR: {input_file} not found.")
        return {"logs": logs}

    _, rows = _read_csv(input_file)
    total = len(rows)

    year_counts: Counter = Counter()
    source_counts: Counter = Counter()
    journal_counts: Counter = Counter()
    document_type_counts: Counter = Counter()

    doi_coverage = 0
    abstract_coverage = 0
    funding_coverage = 0

    for row in rows:
        year_counts[_safe_year(row)] += 1

        source = _pick_first_nonempty(row, ["source", "Source", "database", "Database"]) or "Unknown"
        source_counts[source] += 1

        journal = _pick_first_nonempty(row, ["journal", "Journal", "venue", "Venue", "conference", "Conference"])
        if not journal:
            journal = "Unknown"
        journal_counts[journal] += 1

        doc_type = _pick_first_nonempty(row, ["document_type", "Document Type", "type", "Type"])
        if not doc_type:
            doc_type = "Unknown"
        document_type_counts[doc_type] += 1

        if _pick_first_nonempty(row, ["doi", "DOI"]):
            doi_coverage += 1
        if _pick_first_nonempty(row, ["abstract", "Abstract"]):
            abstract_coverage += 1
        if _pick_first_nonempty(row, ["funding_info", "Funding Info"]):
            funding_coverage += 1

    metadata_payload = {
        "total_papers": total,
        "doi_coverage_pct": round((doi_coverage / total) * 100, 2) if total else 0.0,
        "abstract_coverage_pct": round((abstract_coverage / total) * 100, 2) if total else 0.0,
        "funding_info_coverage_pct": round((funding_coverage / total) * 100, 2) if total else 0.0,
        "papers_by_year": dict(year_counts),
        "papers_by_source": dict(source_counts),
        "top_authors": _top_authors(rows),
        "top_institutions": _top_multivalue(rows, ["institutions", "Institutions"], top_n=20),
        "top_keywords": _top_multivalue(rows, ["keywords", "Keywords"], top_n=30, split_commas=True),
        "top_journals": dict(journal_counts.most_common(20)),
        "document_types": dict(document_type_counts.most_common()),
        "top_funding_sources": _top_multivalue(rows, ["funding_info", "Funding Info"], top_n=20),
        "citation_statistics": _citation_stats(rows),
        "collaboration_patterns": _collaboration_patterns(rows),
    }

    metadata_json = _write_json("metadata_summary.json", metadata_payload)

    _write_csv(
        "chart_papers_by_year.csv",
        ["year", "count"],
        [{"year": year, "count": count} for year, count in sorted(year_counts.items())],
    )

    _write_csv(
        "chart_sources_distribution.csv",
        ["source", "count"],
        [{"source": src, "count": count} for src, count in source_counts.most_common()],
    )

    _write_csv(
        "chart_top_journals.csv",
        ["journal", "count"],
        [{"journal": j, "count": c} for j, c in journal_counts.most_common(20)],
    )

    _write_csv(
        "chart_top_institutions.csv",
        ["institution", "count"],
        [{"institution": k, "count": v} for k, v in _top_multivalue(rows, ["institutions", "Institutions"], top_n=50).items()],
    )

    _write_csv(
        "chart_top_keywords.csv",
        ["keyword", "count"],
        [{"keyword": k, "count": v} for k, v in _top_multivalue(rows, ["keywords", "Keywords"], top_n=50, split_commas=True).items()],
    )

    _write_csv(
        "chart_document_types.csv",
        ["document_type", "count"],
        [{"document_type": k, "count": v} for k, v in document_type_counts.items()],
    )

    logs.append(f"[Step4-Metadata] Generated enriched metadata insights for {total} papers.")
    return {
        "metadata_insights": metadata_payload,
        "metadata_summary_json": metadata_json,
        "logs": logs,
        "current_step": "Step 4.a complete",
    }

# ============================================================
# Step 4.b — LLM-driven thematic augmentation 
# ============================================================

def thematic_augmentation_node(state: LiRAState) -> Dict[str, Any]:
    input_file = state.get("initial_dataset_csv", "initial_dataset.csv")
    logs = list(state.get("logs", []))

    if not input_file or not Path(input_file).exists():
        logs.append(f"[Step4-Thematic] ERROR: {input_file} not found.")
        return {"logs": logs}

    fieldnames, rows = _read_csv(input_file)
    llm = get_llm()

    augmented_rows: List[dict] = []
    thematic_records: List[dict] = []
    confidence_values: List[float] = []

    for idx, row in enumerate(rows):
        row_id = _stable_row_id(row, idx)
        title = _pick_first_nonempty(row, ["title", "Title"])
        abstract = _pick_first_nonempty(row, ["abstract", "Abstract"])
        has_abstract = bool(abstract)
        abstract_for_prompt = abstract if has_abstract else "(No abstract available. Use the title only and keep confidence low if uncertain.)"

        prompt = STEP4_THEMATIC_EXTRACTION_PROMPT.format(
            research_question=state.get("reframed_question") or state.get("topic", ""),
            row_id=row_id,
            title=title or "Untitled",
            abstract=abstract_for_prompt,
        )

        parsed = invoke_structured(llm, prompt, ThematicPaperExtraction)
        valid, issues = _validate_extraction(parsed, has_abstract)

        if not valid:
            parsed.needs_review = True
            merged_reason = _normalize_text(parsed.review_reason)
            qc_reason = "; ".join(issues)
            parsed.review_reason = f"{merged_reason}; {qc_reason}".strip("; ")
            if not 0.0 <= float(parsed.extraction_confidence) <= 1.0:
                parsed.extraction_confidence = 0.3

        flat = _flatten_thematic_result(parsed)
        thematic_records.append(flat)
        confidence_values.append(float(flat["extraction_confidence"]))

        merged = dict(row)
        merged.update(flat)
        augmented_rows.append(merged)

    out_fields = list(fieldnames)
    for extra in [
        "row_id",
        "countries_of_study",
        "application_domain",
        "algorithm_families",
        "baseline_methods",
        "challenges_addressed",
        "evaluation_metrics",
        "experimental_setting",
        "dataset_simulator_testbed",
        "key_findings",
        "limitations",
        "evidence_snippets",
        "extraction_confidence",
        "needs_review",
        "review_reason",
    ]:
        if extra not in out_fields:
            out_fields.append(extra)

    augmented_csv = _write_csv("augmented_dataset.csv", out_fields, augmented_rows)

    thematic_summary = ThematicSummary(
        total_papers=len(augmented_rows),
        countries_distribution=_count_multivalue(augmented_rows, "countries_of_study"),
        application_domains=_count_multivalue(augmented_rows, "application_domain"),
        network_types=_count_multivalue(augmented_rows, "network_types"),
        algorithm_families=_count_multivalue(augmented_rows, "algorithm_families"),
        challenges_addressed=_count_multivalue(augmented_rows, "challenges_addressed"),
        evaluation_metrics=_count_multivalue(augmented_rows, "evaluation_metrics"),
        experimental_settings=_count_multivalue(augmented_rows, "experimental_setting"),
    )
    thematic_json = _write_json("thematic_summary.json", thematic_summary.model_dump())

    avg_conf = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0
    logs.append(f"[Step4-Thematic] Augmented {len(augmented_rows)} rows using the LLM.")

    return {
        "augmented_dataset_csv": augmented_csv,
        "thematic_summary": thematic_summary.model_dump(),
        "thematic_summary_json": thematic_json,
        "step4_average_confidence": avg_conf,
        "logs": logs,
        "current_step": "Step 4.b complete",
    }


# ============================================================
# Step 4.c — Analysis of augmented dataset (deterministic)
# ============================================================

def augmented_analysis_node(state: LiRAState) -> Dict[str, Any]:
    input_file = state.get("augmented_dataset_csv", "augmented_dataset.csv")
    logs = list(state.get("logs", []))

    if not input_file or not Path(input_file).exists():
        logs.append(f"[Step4-Analysis] ERROR: {input_file} not found.")
        return {"logs": logs}

    _, rows = _read_csv(input_file)
    total = len(rows)

    review_needed = sum(1 for r in rows if str(r.get("needs_review", "")).lower() == "true")
    analysis = Step4AnalysisReport(
        total_papers=total,
        average_extraction_confidence=round(
            sum(float(r.get("extraction_confidence", 0.0)) for r in rows) / total, 4
        ) if total else 0.0,
        review_needed_count=review_needed,
        top_countries=_count_multivalue(rows, "countries_of_study"),
        top_application_domains=_count_multivalue(rows, "application_domain"),
        top_network_types=_count_multivalue(rows, "network_types"),
        top_algorithm_families=_count_multivalue(rows, "algorithm_families"),
        top_challenges=_count_multivalue(rows, "challenges_addressed"),
        top_metrics=_count_multivalue(rows, "evaluation_metrics"),
        top_experimental_settings=_count_multivalue(rows, "experimental_setting"),
    )

    analysis_json = _write_json("analysis_report.json", analysis.model_dump())

    _write_csv(
        "chart_challenges.csv",
        ["challenge", "count"],
        [{"challenge": k, "count": v} for k, v in analysis.top_challenges.items()],
    )
    _write_csv(
        "chart_metrics.csv",
        ["metric", "count"],
        [{"metric": k, "count": v} for k, v in analysis.top_metrics.items()],
    )

    logs.append(f"[Step4-Analysis] Completed augmented analysis for {total} rows.")
    return {
        "analysis_report": analysis.model_dump(),
        "analysis_report_json": analysis_json,
        "logs": logs,
        "current_step": "Step 4 complete",
    }
