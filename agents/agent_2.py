from typing import Dict, Any, List
import re
from llm.llm import get_llm
from llm.structured_parser import invoke_structured
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from State.state import LiRAState
from Schemas.schemas import (
    Keywords,
    SearchQuery,
    Criteria
)
from Prompts.prompts import (
    KEYWORD_EXTRACTION_PROMPT,
    QUERY_BUILDER_PROMPT,
    CRITERIA_PROMPT
)


def extract_keywords_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.a: Extract core technical keywords from the research question."""
    target_q = (
        state.get("final_ranked_questions")[0]["question"]
        if state.get("final_ranked_questions")
        else state.get("reframed_question", state.get("topic", ""))
    )

    llm = get_llm()
    template = PromptTemplate(template=KEYWORD_EXTRACTION_PROMPT, input_variables=["question"])
    prompt_val = template.invoke({"question": target_q})
    result = invoke_structured(llm, prompt_val, Keywords)

    return {
        "keywords": result.keywords,
        "logs": state.get("logs", []) + [f"Extracted {len(result.keywords)} keywords for search strategy."]
    }


def select_databases_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.b: Databases are pre-configured from available search tools."""
    databases = state.get("databases", [])

    selected_databases = [
        {"name": db, "justification": "Available as a search tool in the pipeline"}
        for db in databases
    ]

    return {
        "selected_databases": selected_databases,
        "logs": state.get("logs", []) + [
            f"Using {len(databases)} pre-configured databases: {', '.join(databases)}"
        ]
    }


def build_search_queries_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.a: Construct optimized Boolean queries for each database."""
    keywords = state.get("keywords", [])
    databases = state.get("databases", [])
    llm = get_llm()

    template = PromptTemplate(template=QUERY_BUILDER_PROMPT, input_variables=["keywords", "databases"])
    prompt_val = template.invoke({
        "keywords": ", ".join(keywords),
        "databases": ", ".join(databases)
    })
    result = invoke_structured(llm, prompt_val, SearchQuery)

    return {
        "search_queries": result.query,
        "logs": state.get("logs", []) + [f"Constructed queries for {len(result.query)} databases."]
    }


def define_criteria_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.c: Define Inclusion and Exclusion criteria."""
    target_q = (
        state.get("final_ranked_questions")[0]["question"]
        if state.get("final_ranked_questions")
        else state.get("reframed_question", state.get("topic", ""))
    )

    llm = get_llm()
    template = PromptTemplate(template=CRITERIA_PROMPT, input_variables=["question"])
    prompt_val = template.invoke({"question": target_q})
    result = invoke_structured(llm, prompt_val, Criteria)

    return {
        "inclusion_criteria": result.inclusion,
        "exclusion_criteria": result.exclusion,
        "logs": state.get("logs", []) + ["Defined Inclusion and Exclusion criteria."]
    }


def prepare_search_node(state: LiRAState) -> Dict[str, Any]:
    """Execute search queries programmatically using tools/serpapi_tool.py functions."""
    queries = state.get("search_queries", {})
    from langchain_core.messages import AIMessage, ToolMessage
    import uuid

    db_to_tool = {
        "Google Scholar": "google_scholar_search",
        "arXiv": "arxiv_search",
        "OpenAlex": "openalex_search",
        "PubMed": "pubmed_search",
        "CrossRef": "crossref_search",
    }

    from tools.serpapi_tool import (
        google_scholar_search, arxiv_search, openalex_search, pubmed_search, crossref_search
    )

    tools_map = {
        "google_scholar_search": google_scholar_search,
        "arxiv_search": arxiv_search,
        "openalex_search": openalex_search,
        "pubmed_search": pubmed_search,
        "crossref_search": crossref_search,
    }

    tool_calls = []
    tool_messages = []

    for db_name, query in queries.items():
        tool_name = db_to_tool.get(db_name)
        if not tool_name or tool_name not in tools_map:
            continue

        tool_func = tools_map[tool_name]
        tool_call_id = str(uuid.uuid4())

        tool_calls.append({
            "name": tool_name,
            "args": {"query": query},
            "id": tool_call_id
        })

        try:
            result = tool_func.invoke({"query": query})
        except Exception as e:
            result = f"{tool_name} Error: {str(e)}"

        tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call_id, name=tool_name))

    ai_msg = AIMessage(content="I have executed the searches programmatically.", tool_calls=tool_calls)

    return {
        "messages": [ai_msg] + tool_messages,
        "logs": state.get("logs", []) + [f"Programmatically executed search across {len(tool_calls)} databases."]
    }


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct plain text from OpenAlex's abstract_inverted_index format."""
    if not inverted_index:
        return ""
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort(key=lambda x: x[0])
    return " ".join(w for _, w in words)


def _is_real_value(value) -> bool:
    """True only for values worth saving."""
    if value is None:
        return False
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return False
        if v.upper() == "N/A":
            return False
        if v.lower() in {"unknown", "none", "null", "no abstract available"}:
            return False
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return False
    return True


def _safe_join(values, sep=", ") -> str:
    cleaned = [str(v).strip() for v in values if _is_real_value(v)]
    return sep.join(cleaned)


def _clean_html(text: str) -> str:
    import re
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\n", " ").replace("\r", " ").strip()


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("\n", " ").replace("\r", " ").strip()


def _clean_paper_dict(paper: dict) -> dict:
    """Remove empty/fake values before saving."""
    cleaned = {}
    for k, v in paper.items():
        if _is_real_value(v):
            if isinstance(v, (list, tuple, set)):
                joined = _safe_join(v)
                if _is_real_value(joined):
                    cleaned[k] = joined
            else:
                cleaned[k] = _normalize_text(v) if isinstance(v, str) else v
    return cleaned


def _collect_existing_headers(papers: list, preferred_order: list | None = None) -> list:
    """Build CSV headers using only keys that really exist in the saved papers."""
    preferred_order = preferred_order or []
    seen = set()
    headers = []

    for key in preferred_order:
        for p in papers:
            if key in p and _is_real_value(p[key]):
                if key not in seen:
                    seen.add(key)
                    headers.append(key)
                break

    for p in papers:
        for key, value in p.items():
            if key not in seen and _is_real_value(value):
                seen.add(key)
                headers.append(key)

    return headers


def _extract_openalex_authors(authorships: list) -> str:
    authors = []
    for auth in authorships[:10]:
        name = auth.get("author", {}).get("display_name")
        if name:
            authors.append(name)
    return _safe_join(authors)


def _extract_openalex_institutions(authorships: list) -> str:
    institutions = []
    for auth in authorships or []:
        for inst in auth.get("institutions", []):
            name = inst.get("display_name")
            if name and name not in institutions:
                institutions.append(name)
    return _safe_join(institutions)


def _extract_openalex_countries(authorships: list) -> str:
    countries = []
    for auth in authorships or []:
        for inst in auth.get("institutions", []):
            country = inst.get("country_code")
            if country and country not in countries:
                countries.append(country)
    return _safe_join(countries)


def _extract_openalex_keywords(concepts: list) -> str:
    if not concepts:
        return ""
    keywords = []
    for c in concepts[:10]:
        name = c.get("display_name")
        if name:
            keywords.append(name)
    return _safe_join(keywords)


def _extract_crossref_authors(author_list: list) -> str:
    authors = []
    for a in (author_list or [])[:10]:
        family = a.get("family", "")
        given = a.get("given", "")
        full = f"{given} {family}".strip()
        if full:
            authors.append(full)
    return _safe_join(authors)


def _extract_crossref_institutions(author_list: list) -> str:
    institutions = []
    for a in author_list or []:
        for aff in a.get("affiliation", []):
            name = aff.get("name")
            if name and name not in institutions:
                institutions.append(name)
    return _safe_join(institutions)


def _extract_crossref_keywords(item: dict) -> str:
    return _safe_join((item.get("subject") or [])[:10])


def _extract_crossref_funders(item: dict) -> str:
    funders = []
    for funder in item.get("funder", []) or []:
        name = funder.get("name")
        if name and name not in funders:
            funders.append(name)
    return _safe_join(funders)


def _maybe_set(target: dict, key: str, value):
    if _is_real_value(value):
        target[key] = value


def _parse_structured_entry(entry: str, db_name: str) -> dict:
    """
    Parse one tool output entry with richer labeled fields.
    Supports the newer structured output emitted by serpapi_tool.py.
    """
    paper = {}

    def _extract(label: str) -> str:
        match = re.search(rf"{re.escape(label)}:\s*(.+?)(?:\n|$)", entry)
        return _normalize_text(match.group(1)) if match else ""

    title = _extract("Title")
    year = _extract("Year")
    authors = _extract("Authors")
    journal = _extract("Journal")
    publisher = _extract("Publisher")
    publication_date = _extract("Publication Date")
    document_type = _extract("Document Type")
    keywords = _extract("Keywords")
    institutions = _extract("Institutions")
    countries = _extract("Countries")
    citation_count = _extract("Citation Count")
    language = _extract("Language")
    pmid = _extract("PMID")
    funding_info = _extract("Funding Info")
    url = _extract("URL")
    doi = _extract("DOI")

    abs_match = re.search(r"Abstract:\s*(.+)", entry, re.DOTALL)
    abstract = _normalize_text(abs_match.group(1)) if abs_match else ""

    if "doi.org/" in url and not _is_real_value(doi):
        doi = url.split("doi.org/")[-1].strip()

    # Legacy fallback: if tool didn't emit Year but title still has "(2023)"
    if not _is_real_value(year):
        year_m = re.search(r"\((\d{4})\)", title)
        if year_m:
            year = year_m.group(1)

    _maybe_set(paper, "title", title)
    _maybe_set(paper, "year", year)
    _maybe_set(paper, "authors", authors)
    _maybe_set(paper, "journal", journal)
    _maybe_set(paper, "publisher", publisher)
    _maybe_set(paper, "publication_date", publication_date)
    _maybe_set(paper, "document_type", document_type)
    _maybe_set(paper, "keywords", keywords)
    _maybe_set(paper, "institutions", institutions)
    _maybe_set(paper, "countries", countries)
    _maybe_set(paper, "citation_count", citation_count)
    _maybe_set(paper, "language", language)
    _maybe_set(paper, "pmid", pmid)
    _maybe_set(paper, "funding_info", funding_info)
    _maybe_set(paper, "url", url)
    _maybe_set(paper, "doi", doi)
    _maybe_set(paper, "source", db_name)
    _maybe_set(paper, "abstract", abstract)

    return paper


def _enrich_paper(title: str) -> dict:
    """
    Look up a paper from OpenAlex and CrossRef and return only real fields.
    No fake keys, no N/A placeholders.
    """
    import requests
    import re

    clean_title = re.sub(r"\s*\(.*$", "", title).strip()

    # Try OpenAlex first
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": clean_title,
            "per_page": 1,
            "select": ",".join([
                "title",
                "doi",
                "publication_year",
                "publication_date",
                "type",
                "language",
                "primary_location",
                "authorships",
                "abstract_inverted_index",
                "concepts",
                "cited_by_count",
                "ids",
            ])
        }
        resp = requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"}
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                work = results[0]
                result = {}

                new_title = _normalize_text(work.get("title") or title)
                _maybe_set(result, "title", new_title)

                doi = work.get("doi")
                if doi and doi.startswith("https://doi.org/"):
                    doi = doi.split("doi.org/")[-1]
                _maybe_set(result, "doi", doi)

                if _is_real_value(doi):
                    _maybe_set(result, "url", f"https://doi.org/{doi}")

                inv_idx = work.get("abstract_inverted_index")
                abstract = _reconstruct_abstract(inv_idx) if inv_idx else ""
                _maybe_set(result, "abstract", _normalize_text(abstract))

                year = work.get("publication_year")
                _maybe_set(result, "year", str(year) if year else None)

                _maybe_set(result, "publication_date", work.get("publication_date"))
                _maybe_set(result, "document_type", work.get("type"))
                _maybe_set(result, "language", work.get("language"))

                authorships = work.get("authorships", [])
                _maybe_set(result, "authors", _extract_openalex_authors(authorships))
                _maybe_set(result, "institutions", _extract_openalex_institutions(authorships))
                _maybe_set(result, "countries", _extract_openalex_countries(authorships))
                _maybe_set(result, "keywords", _extract_openalex_keywords(work.get("concepts", [])))

                primary_location = work.get("primary_location") or {}
                source = primary_location.get("source") or {}
                _maybe_set(result, "journal", source.get("display_name"))
                _maybe_set(result, "publisher", source.get("host_organization_name"))

                cited_by_count = work.get("cited_by_count")
                if cited_by_count is not None:
                    _maybe_set(result, "citation_count", str(cited_by_count))

                ids = work.get("ids") or {}
                pmid = ids.get("pmid")
                if isinstance(pmid, str) and "pubmed.ncbi.nlm.nih.gov/" in pmid:
                    pmid = pmid.rstrip("/").split("/")[-1]
                _maybe_set(result, "pmid", pmid)

                return result
    except Exception:
        pass

    # Fallback to CrossRef
    try:
        url = "https://api.crossref.org/works"
        params = {
            "query.title": clean_title,
            "rows": 3
        }
        resp = requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"}
        )
        if resp.status_code == 200:
            items = resp.json().get("message", {}).get("items", [])
            for item in items:
                ref_title = (item.get("title", [""]) or [""])[0].lower()
                clean_lower = clean_title.lower()
                if clean_lower in ref_title or ref_title in clean_lower:
                    result = {}

                    new_title = _normalize_text((item.get("title", [title]) or [title])[0])
                    _maybe_set(result, "title", new_title)

                    doi = item.get("DOI")
                    _maybe_set(result, "doi", doi)
                    if _is_real_value(doi):
                        _maybe_set(result, "url", f"https://doi.org/{doi}")

                    abstract = _clean_html(item.get("abstract", ""))
                    _maybe_set(result, "abstract", abstract)

                    authors = item.get("author", [])
                    _maybe_set(result, "authors", _extract_crossref_authors(authors))
                    _maybe_set(result, "institutions", _extract_crossref_institutions(authors))
                    _maybe_set(result, "keywords", _extract_crossref_keywords(item))
                    _maybe_set(result, "funding_info", _extract_crossref_funders(item))

                    year = None
                    publication_date = None
                    for date_field in ["published-print", "published-online", "issued"]:
                        date_parts = item.get(date_field, {}).get("date-parts", [[]])
                        if date_parts and date_parts[0]:
                            parts = date_parts[0]
                            if len(parts) >= 1:
                                year = str(parts[0])
                            publication_date = "-".join(str(x) for x in parts)
                            break

                    _maybe_set(result, "year", year)
                    _maybe_set(result, "publication_date", publication_date)
                    _maybe_set(result, "document_type", item.get("type"))
                    _maybe_set(result, "publisher", item.get("publisher"))

                    container_title = item.get("container-title", [])
                    if container_title:
                        _maybe_set(result, "journal", container_title[0])

                    return result
    except Exception:
        pass

    return {}


def save_papers_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.d: Parse tool results into raw_dataset.csv, generate RIS, and write PRISMA doc."""
    from langchain_core.messages import ToolMessage, AIMessage
    import csv
    import re
    import time
    from datetime import datetime

    tool_calls_map = {}
    for msg in state["messages"]:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_map[tc["id"]] = {
                    "tool": tc["name"],
                    "query": tc.get("args", {}).get("query", "Unknown query")
                }

    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage) and isinstance(m.content, str)]
    if not tool_messages:
        return {"logs": state.get("logs", []) + ["No tool search results to extract papers from."]}

    all_papers = []
    search_metadata = []

    for msg in tool_messages:
        raw = msg.content
        if raw.startswith((
            "arXiv API Error",
            "Semantic Scholar API error",
            "Google Scholar HTTP Error",
            "Error querying",
            "PubMed API Error",
            "PubMed search error",
            "PubMed fetch error",
            "CrossRef API error",
            "OpenAlex API error"
        )):
            continue

        tool_info = tool_calls_map.get(msg.tool_call_id, {"tool": "Unknown", "query": "Unknown"})
        tool_name = tool_info["tool"]
        query_used = tool_info["query"]

        db_name = tool_name.replace("_search", "").replace("_", " ").title()
        if db_name == "Arxiv":
            db_name = "arXiv"

        papers_from_query = 0

        # New structured format from updated serpapi_tool.py
        if "Title:" in raw and ("Abstract:" in raw or "URL:" in raw):
            entries = re.split(r"\n---\n", raw)
            for entry in entries:
                if not entry.strip():
                    continue

                paper = _parse_structured_entry(entry, db_name)

                if len(paper.get("abstract", "")) > 50:
                    all_papers.append(paper)
                    papers_from_query += 1

        search_metadata.append({
            "database": db_name,
            "query": query_used,
            "count": papers_from_query,
            "date": datetime.now().strftime("%Y-%m-%d")
        })

    print(f"\n[DEBUG save_papers_node] Directly parsed {len(all_papers)} papers from tool outputs.")

    enriched_count = 0
    total_needed = 0

    for p in all_papers:
        needs_doi = not _is_real_value(p.get("doi"))
        abstract_text = p.get("abstract", "")
        needs_abstract = (
            not _is_real_value(abstract_text)
            or p.get("source") == "Google Scholar"
            or len(abstract_text) < 200
            or abstract_text.endswith("...")
        )

        if needs_doi or needs_abstract:
            total_needed += 1
            enrich_data = _enrich_paper(p.get("title", ""))
            if enrich_data:
                before_keys = set(p.keys())
                for k, v in enrich_data.items():
                    if _is_real_value(v):
                        if k not in p or not _is_real_value(p.get(k)):
                            p[k] = v
                        elif k in {
                            "title",
                            "authors",
                            "year",
                            "abstract",
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
                        } and p.get("source") == "Google Scholar":
                            p[k] = v
                if set(p.keys()) != before_keys:
                    enriched_count += 1
            time.sleep(0.5)

        final_abs = p.get("abstract", "")
        if (
            not _is_real_value(final_abs)
            or len(final_abs) < 200
            or "\u2026" in final_abs
            or "..." in final_abs
        ):
            p["__delete__"] = True

    all_papers = [p for p in all_papers if not p.get("__delete__")]
    all_papers = [_clean_paper_dict(p) for p in all_papers]
    all_papers = [p for p in all_papers if p]

    print(f"[DEBUG save_papers_node] Enriched {enriched_count}/{total_needed} papers missing DOIs or full abstracts.")

    csv_filename = "raw_dataset.csv"
    ris_filename = "raw_dataset.ris"
    prisma_filename = "prisma_search_strategy.md"
    logs = state.get("logs", [])

    try:
        preferred_headers = [
            "title",
            "year",
            "authors",
            "url",
            "doi",
            "source",
            "abstract",
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
        ]

        headers = _collect_existing_headers(all_papers, preferred_headers)

        with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=headers, quoting=csv.QUOTE_ALL, extrasaction="ignore")
            writer.writeheader()
            for p in all_papers:
                writer.writerow(p)

        logs.append(f"Saved {len(all_papers)} papers to {csv_filename} with {len(headers)} real columns.")

        with open(ris_filename, mode="w", encoding="utf-8") as ris_file:
            for p in all_papers:
                ris_file.write("TY  - JOUR\n")
                if p.get("title"):
                    ris_file.write(f"TI  - {p['title']}\n")
                if p.get("authors"):
                    for auth in str(p["authors"]).split(","):
                        auth = auth.strip()
                        if auth:
                            ris_file.write(f"AU  - {auth}\n")
                if p.get("year"):
                    ris_file.write(f"PY  - {p['year']}\n")
                if p.get("abstract"):
                    ris_file.write(f"AB  - {p['abstract']}\n")
                if p.get("url"):
                    ris_file.write(f"UR  - {p['url']}\n")
                if p.get("doi"):
                    ris_file.write(f"DO  - {p['doi']}\n")
                if p.get("journal"):
                    ris_file.write(f"JO  - {p['journal']}\n")
                if p.get("publisher"):
                    ris_file.write(f"PB  - {p['publisher']}\n")
                ris_file.write("ER  - \n\n")

        logs.append(f"Generated RIS export {ris_filename}.")

        with open(prisma_filename, mode="w", encoding="utf-8") as prisma_file:
            prisma_file.write("# PRISMA Search Strategy Documentation\n\n")
            prisma_file.write(f"**Date Generated:** {datetime.now().strftime('%Y-%m-%d')}\n")
            prisma_file.write(f"**Total Unique Papers Retained:** {len(all_papers)}\n\n")
            prisma_file.write("| Database | Search Query | Records Found | Retrieval Date |\n")
            prisma_file.write("|---|---|---|---|\n")
            for meta in search_metadata:
                prisma_file.write(f"| {meta['database']} | `{meta['query']}` | {meta['count']} | {meta['date']} |\n")

        logs.append(f"Generated PRISMA documentation {prisma_filename}.")

        return {
            "raw_dataset_csv": csv_filename,
            "raw_dataset_ris": ris_filename,
            "prisma_doc": prisma_filename,
            "search_metadata": search_metadata,
            "logs": logs,
            "messages": [m for m in state["messages"]]
        }

    except Exception as e:
        return {"logs": logs + [f"Failed to assemble exports: {e}"]}