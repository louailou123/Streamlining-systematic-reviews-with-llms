"""
Step 5 — Reading & Drafting Agent Nodes (LangGraph)
  5.a  generate_outline_node   — LLM-generated literature review outline
  5.b  draft_sections_node     — ChatPDF + LLM reading and section drafting
  5.c  proofread_draft_node    — LLM-based proofreading and refinement
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from llm.llm import get_llm
from llm.structured_parser import invoke_structured
from State.state import LiRAState
from Schemas.schemas import (
    OutlineResult,
    DraftedSection,
    ProofreadResult,
)
from Prompts.prompts import (
    STEP5_OUTLINE_PROMPT,
    STEP5_DRAFT_SECTION_PROMPT,
    STEP5_PROOFREAD_PROMPT,
)


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


def _read_csv(path: str) -> Tuple[List[str], List[dict]]:
    import csv

    with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _write_json(path: str, payload: Dict[str, Any]) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _write_markdown(path: str, content: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _top_n_keys(d: dict, n: int = 8) -> str:
    """Return top N keys from a dict as a comma-separated string."""
    if not d:
        return "N/A"
    items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]
    return ", ".join(k for k, _ in items)


def _build_paper_summary_text(
    row: dict,
    chatpdf_summary: Optional[str] = None,
) -> str:
    """
    Build a summary block for a single paper.
    Uses ChatPDF summary if available, otherwise falls back to title+abstract.
    """
    title = _pick_first_nonempty(row, ["title", "Title"]) or "Untitled"
    year = _pick_first_nonempty(row, ["year", "Year"]) or "N/A"
    authors = _pick_first_nonempty(row, ["authors", "Authors"]) or "Unknown"
    abstract = _pick_first_nonempty(row, ["abstract", "Abstract"]) or ""

    # Thematic fields from augmented dataset
    domain = _pick_first_nonempty(row, ["application_domain"]) or ""
    challenges = _pick_first_nonempty(row, ["challenges_addressed"]) or ""
    findings = _pick_first_nonempty(row, ["key_findings"]) or ""
    methods = _pick_first_nonempty(row, ["algorithm_families"]) or ""
    limitations = _pick_first_nonempty(row, ["limitations"]) or ""

    lines = [f"### {title} ({authors}, {year})"]

    if chatpdf_summary:
        lines.append(f"**Full-text summary (ChatPDF):**\n{chatpdf_summary}")
    elif abstract:
        lines.append(f"**Abstract:** {abstract[:500]}")

    if domain:
        lines.append(f"**Domain:** {domain}")
    if methods:
        lines.append(f"**Methods:** {methods}")
    if challenges:
        lines.append(f"**Challenges:** {challenges}")
    if findings:
        lines.append(f"**Key Findings:** {findings}")
    if limitations:
        lines.append(f"**Limitations:** {limitations}")

    return "\n".join(lines)


def _is_relevant_to_section(row: dict, relevant_themes: List[str]) -> bool:
    """Check if a paper is relevant to a section's themes (fuzzy match)."""
    if not relevant_themes:
        return True  # if no themes specified, include all

    # Collect all searchable text from the paper
    searchable_fields = [
        _pick_first_nonempty(row, ["application_domain"]),
        _pick_first_nonempty(row, ["challenges_addressed"]),
        _pick_first_nonempty(row, ["algorithm_families"]),
        _pick_first_nonempty(row, ["key_findings"]),
        _pick_first_nonempty(row, ["title", "Title"]),
        _pick_first_nonempty(row, ["abstract", "Abstract"]),
    ]
    searchable = " ".join(searchable_fields).lower()

    # Check if any theme keyword appears in the paper's text
    for theme in relevant_themes:
        theme_words = theme.lower().split()
        if any(word in searchable for word in theme_words if len(word) > 3):
            return True

    return False


# ============================================================
# Step 5.a — LLM-Generated Outline
# ============================================================

def generate_outline_node(state: LiRAState) -> Dict[str, Any]:
    """
    Generate a structured literature review outline using the LLM.
    Uses analysis results to inform section design.
    """
    logs = list(state.get("logs", []))

    research_question = (
        state.get("reframed_question")
        or state.get("topic", "")
    )

    # Gather analysis data for context
    analysis = state.get("analysis_report", {})
    thematic = state.get("thematic_summary", {})

    total_papers = analysis.get("total_papers", thematic.get("total_papers", 0))
    application_domains = _top_n_keys(
        analysis.get("top_application_domains") or thematic.get("application_domains", {})
    )
    challenges = _top_n_keys(
        analysis.get("top_challenges") or thematic.get("challenges_addressed", {})
    )
    algorithms = _top_n_keys(
        analysis.get("top_algorithm_families") or thematic.get("algorithm_families", {})
    )
    experimental_settings = _top_n_keys(
        analysis.get("top_experimental_settings") or thematic.get("experimental_settings", {})
    )

    prompt = STEP5_OUTLINE_PROMPT.format(
        research_question=research_question,
        total_papers=total_papers,
        application_domains=application_domains,
        challenges=challenges,
        algorithms=algorithms,
        experimental_settings=experimental_settings,
    )

    llm = get_llm()
    result = invoke_structured(llm, prompt, OutlineResult)

    # Store outline as list of section titles (for backward compat)
    outline_titles = [s.title for s in result.sections]

    # Save full outline to JSON
    outline_data = [s.model_dump() for s in result.sections]
    outline_json_path = _write_json("literature_review_outline.json", {
        "research_question": research_question,
        "total_papers": total_papers,
        "sections": outline_data,
    })

    logs.append(f"[Step5-Outline] Generated outline with {len(result.sections)} sections.")
    print(f"[Step5-Outline] Outline sections: {', '.join(outline_titles)}")

    return {
        "outline": outline_titles,
        "outline_json": outline_json_path,
        "logs": logs,
        "current_step": "Step 5.a complete",
    }


# ============================================================
# Step 5.b — ChatPDF Reading + Section Drafting
# ============================================================

def draft_sections_node(state: LiRAState) -> Dict[str, Any]:
    """
    Draft literature review sections using ChatPDF summaries + LLM.
    
    For each paper:
    - If ChatPDF API key is available and paper has a URL → upload to ChatPDF and get summary
    - Otherwise → use title + abstract + augmented fields
    
    Then draft each outline section using relevant paper summaries.
    """
    logs = list(state.get("logs", []))

    research_question = (
        state.get("reframed_question")
        or state.get("topic", "")
    )

    # Load outline
    outline_json_path = state.get("outline_json", "literature_review_outline.json")
    if not outline_json_path or not Path(outline_json_path).exists():
        logs.append("[Step5-Draft] ERROR: outline JSON not found.")
        return {"logs": logs}

    with open(outline_json_path, "r", encoding="utf-8") as f:
        outline_data = json.load(f)

    sections = outline_data.get("sections", [])
    if not sections:
        logs.append("[Step5-Draft] ERROR: outline has no sections.")
        return {"logs": logs}

    # Load augmented dataset
    augmented_csv = state.get("augmented_dataset_csv", "augmented_dataset.csv")
    if not augmented_csv or not Path(augmented_csv).exists():
        logs.append(f"[Step5-Draft] ERROR: {augmented_csv} not found.")
        return {"logs": logs}

    _, rows = _read_csv(augmented_csv)

    # ── ChatPDF Integration ──────────────────────────────────
    from tools.chatpdf_tool import ChatPDFClient
    chatpdf = ChatPDFClient()
    chatpdf_summaries: Dict[str, str] = dict(state.get("chatpdf_summaries", {}))
    source_ids_to_cleanup: List[str] = []

    if chatpdf.is_configured:
        print(f"[Step5-Draft] ChatPDF API is configured. Attempting full-text reading...")
        logs.append("[Step5-Draft] ChatPDF API configured — attempting full-text reading.")

        for idx, row in enumerate(rows):
            row_id = _pick_first_nonempty(row, ["row_id"]) or str(idx)
            if row_id in chatpdf_summaries:
                continue  # already have a summary

            url = _pick_first_nonempty(row, ["url", "URL", "link", "Link"])
            if not url or not url.startswith("http"):
                continue

            # Check if URL likely points to a PDF
            title = _pick_first_nonempty(row, ["title", "Title"]) or "Untitled"
            print(f"  [{idx + 1}/{len(rows)}] ChatPDF: {title[:60]}...")

            try:
                source_id = chatpdf.add_pdf_url(url)
                if source_id:
                    source_ids_to_cleanup.append(source_id)
                    time.sleep(1.5)  # rate limiting

                    summary = chatpdf.summarize(source_id, research_question)
                    if summary:
                        chatpdf_summaries[row_id] = summary
                        print(f"    ✓ Got ChatPDF summary ({len(summary)} chars)")
                    else:
                        print(f"    ✗ ChatPDF returned no summary")
                else:
                    print(f"    ✗ Could not upload to ChatPDF")
            except Exception as e:
                print(f"    ✗ ChatPDF error: {e}")

            time.sleep(1.0)  # rate limiting between papers

        # Cleanup uploaded sources
        if source_ids_to_cleanup:
            chatpdf.delete_sources(source_ids_to_cleanup)

        logs.append(f"[Step5-Draft] ChatPDF: Got summaries for {len(chatpdf_summaries)} papers.")
    else:
        print("[Step5-Draft] ChatPDF not configured — using title+abstract only.")
        logs.append("[Step5-Draft] ChatPDF not configured — using title+abstract fallback.")

    # ── Draft Each Section ───────────────────────────────────
    llm = get_llm()
    draft_sections: Dict[str, str] = {}
    all_draft_parts: List[str] = []

    for sec_idx, section in enumerate(sections):
        section_title = section.get("title", f"Section {sec_idx + 1}")
        section_desc = section.get("description", "")
        relevant_themes = section.get("relevant_themes", [])

        print(f"\n[Step5-Draft] Drafting section {sec_idx + 1}/{len(sections)}: {section_title}")

        # Find relevant papers for this section
        relevant_papers = []
        for idx, row in enumerate(rows):
            if _is_relevant_to_section(row, relevant_themes):
                row_id = _pick_first_nonempty(row, ["row_id"]) or str(idx)
                chatpdf_summary = chatpdf_summaries.get(row_id)
                paper_text = _build_paper_summary_text(row, chatpdf_summary)
                relevant_papers.append(paper_text)

        # If no papers matched, use all papers for intro/conclusion sections
        if not relevant_papers:
            for idx, row in enumerate(rows):
                row_id = _pick_first_nonempty(row, ["row_id"]) or str(idx)
                chatpdf_summary = chatpdf_summaries.get(row_id)
                paper_text = _build_paper_summary_text(row, chatpdf_summary)
                relevant_papers.append(paper_text)

        paper_summaries_text = "\n\n---\n\n".join(relevant_papers[:15])  # cap at 15 papers per section

        prompt = STEP5_DRAFT_SECTION_PROMPT.format(
            research_question=research_question,
            section_title=section_title,
            section_description=section_desc,
            relevant_themes=", ".join(relevant_themes) if relevant_themes else "General",
            paper_summaries=paper_summaries_text,
        )

        try:
            result = invoke_structured(llm, prompt, DraftedSection)
            draft_sections[section_title] = result.content
            all_draft_parts.append(f"## {section_title}\n\n{result.content}")
            print(f"  ✓ Drafted ({len(result.content)} chars)")
        except Exception as e:
            error_msg = f"[Section drafting failed: {e}]"
            draft_sections[section_title] = error_msg
            all_draft_parts.append(f"## {section_title}\n\n{error_msg}")
            print(f"  ✗ Draft error: {e}")

    # Combine into full draft markdown
    header = (
        f"# Literature Review\n\n"
        f"**Research Question:** {research_question}\n\n"
        f"**Papers Analyzed:** {len(rows)}\n\n"
        f"---\n\n"
    )
    full_draft = header + "\n\n".join(all_draft_parts)
    draft_path = _write_markdown("literature_review_draft.md", full_draft)

    logs.append(f"[Step5-Draft] Drafted {len(draft_sections)} sections → {draft_path}")

    return {
        "draft_sections": draft_sections,
        "draft_markdown": draft_path,
        "chatpdf_summaries": chatpdf_summaries,
        "logs": logs,
        "current_step": "Step 5.b complete",
    }


# ============================================================
# Step 5.c — Proofreading & Refinement
# ============================================================

def proofread_draft_node(state: LiRAState) -> Dict[str, Any]:
    """
    Proofread the full literature review draft using the LLM.
    Produces a refined final version.
    """
    logs = list(state.get("logs", []))

    draft_path = state.get("draft_markdown", "literature_review_draft.md")
    if not draft_path or not Path(draft_path).exists():
        logs.append("[Step5-Proofread] ERROR: draft markdown not found.")
        return {"logs": logs}

    with open(draft_path, "r", encoding="utf-8") as f:
        draft_content = f.read()

    if not draft_content.strip():
        logs.append("[Step5-Proofread] ERROR: draft is empty.")
        return {"logs": logs}

    print(f"[Step5-Proofread] Proofreading draft ({len(draft_content)} chars)...")

    # If draft is very long, proofread in chunks (LLM token limits)
    MAX_CHUNK = 12000
    if len(draft_content) > MAX_CHUNK:
        # Split by sections and proofread each
        sections = draft_content.split("\n## ")
        header = sections[0]
        body_sections = sections[1:] if len(sections) > 1 else []

        proofread_parts = [header]
        llm = get_llm()

        for i, section in enumerate(body_sections):
            section_text = f"## {section}"
            print(f"  Proofreading section {i + 1}/{len(body_sections)}...")

            prompt = STEP5_PROOFREAD_PROMPT.format(draft_content=section_text)
            try:
                result = invoke_structured(llm, prompt, ProofreadResult)
                proofread_parts.append(result.content)
            except Exception as e:
                print(f"  ✗ Proofread error for section {i + 1}: {e}")
                proofread_parts.append(section_text)

        final_content = "\n\n".join(proofread_parts)
        improvements = ["Proofread in sections due to length"]
    else:
        llm = get_llm()
        prompt = STEP5_PROOFREAD_PROMPT.format(draft_content=draft_content)

        try:
            result = invoke_structured(llm, prompt, ProofreadResult)
            final_content = result.content
            improvements = result.improvements_made
        except Exception as e:
            logs.append(f"[Step5-Proofread] ERROR: {e} — using original draft as final.")
            final_content = draft_content
            improvements = []

    final_path = _write_markdown("literature_review_final.md", final_content)

    # Update draft_sections with proofread content
    updated_sections = dict(state.get("draft_sections", {}))

    if improvements:
        logs.append(f"[Step5-Proofread] Improvements: {'; '.join(improvements[:5])}")

    logs.append(f"[Step5-Proofread] Final review saved → {final_path}")
    print(f"[Step5-Proofread] ✓ Final draft saved to {final_path}")

    return {
        "draft_sections": updated_sections,
        "final_draft_markdown": final_path,
        "logs": logs,
        "current_step": "Step 5 complete",
    }
