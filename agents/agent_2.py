from typing import Dict, Any, List
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
    # We use the final ranked question if available, otherwise the reframed one
    target_q = state.get("final_ranked_questions")[0]["question"] if state.get("final_ranked_questions") else state.get("reframed_question", state.get("topic", ""))
    
    llm = get_llm()
    # Explicitly creating the template and ensuring it only has 'question'
    template = PromptTemplate(template=KEYWORD_EXTRACTION_PROMPT, input_variables=["question"])
    prompt_val = template.invoke({"question": target_q})
    result = invoke_structured(llm, prompt_val, Keywords)
    
    return {
        "keywords": result.keywords,
        "logs": state.get("logs", []) + [f"Extracted {len(result.keywords)} keywords for search strategy."]
    }

def select_databases_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.b: Databases are pre-configured from available search tools.
    This node just logs the selection — no LLM call needed."""
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
    target_q = state.get("final_ranked_questions")[0]["question"] if state.get("final_ranked_questions") else state.get("reframed_question", state.get("topic", ""))
    llm = get_llm()
    # Explicitly creating the template and ensuring it only has 'question'
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

    # Map our predefined databases to tool names
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

        # Execute the tool
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


def _enrich_paper(title: str) -> dict:
    """Look up a paper from OpenAlex and CrossRef to find its full metadata."""
    import requests
    import re
    
    clean_title = re.sub(r'\s*\(.*$', '', title).strip()
    
    # Try OpenAlex
    try:
        url = "https://api.openalex.org/works"
        params = {"search": clean_title, "per_page": 1, "select": "title,doi,abstract_inverted_index,authorships,publication_year"}
        resp = requests.get(url, params=params, timeout=10, headers={"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"})
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                work = results[0]
                doi = work.get("doi") or "N/A"
                if doi != "N/A" and doi.startswith("https://doi.org/"):
                    doi = doi.split("doi.org/")[-1]
                    
                abstract = ""
                inv_idx = work.get("abstract_inverted_index")
                if inv_idx:
                    abstract = _reconstruct_abstract(inv_idx)
                    abstract = abstract.replace("\n", " ").replace("\r", " ").strip()
                    
                year = str(work.get("publication_year")) if work.get("publication_year") else "N/A"
                
                authorships = work.get("authorships", [])
                authors = [a.get("author", {}).get("display_name") for a in authorships[:5] if a.get("author", {}).get("display_name")]
                if len(authorships) > 5: authors.append("et al.")
                authors_str = ", ".join(authors) if authors else "Unknown"
                
                new_title = work.get("title", title)
                if new_title: new_title = new_title.replace("\n", " ").replace("\r", " ")
                
                return {
                    "abstract": abstract, 
                    "doi": doi, 
                    "authors": authors_str, 
                    "year": year, 
                    "title": new_title or title,
                    "url": f"https://doi.org/{doi}" if doi != "N/A" else "N/A"
                }
    except Exception:
        pass
        
    # Fallback to CrossRef
    try:
        url = "https://api.crossref.org/works"
        params = {"query.title": clean_title, "rows": 3, "filter": "has-abstract:true"}
        resp = requests.get(url, params=params, timeout=10, headers={"User-Agent": "LiRA-Pipeline/1.0"})
        if resp.status_code == 200:
            items = resp.json().get("message", {}).get("items", [])
            for item in items:
                ref_title = item.get("title", [""])[0].lower()
                clean_lower = clean_title.lower()
                if clean_lower in ref_title or ref_title in clean_lower:
                    doi = item.get("DOI", "N/A")
                    
                    abstract = item.get("abstract", "")
                    if abstract:
                        abstract = re.sub(r'<[^>]+>', '', abstract).replace("\n", " ").replace("\r", " ").strip()
                        
                    authors = []
                    for a in item.get("author", [])[:5]:
                        family = a.get("family", "")
                        given = a.get("given", "")
                        authors.append(f"{family} {given}".strip())
                    if len(item.get("author", [])) > 5:
                        authors.append("et al.")
                    authors_str = ", ".join(authors) if authors else "Unknown"
                    
                    year = "N/A"
                    for date_field in ["published-print", "published-online"]:
                        date_parts = item.get(date_field, {}).get("date-parts", [[]])
                        if date_parts and date_parts[0] and date_parts[0][0]:
                            year = str(date_parts[0][0])
                            break
                            
                    new_title = item.get("title", [title])[0]
                    if new_title: new_title = new_title.replace("\n", " ").replace("\r", " ")
                    
                    return {
                        "abstract": abstract, 
                        "doi": doi, 
                        "authors": authors_str, 
                        "year": year, 
                        "title": new_title or title,
                        "url": f"https://doi.org/{doi}" if doi != "N/A" else "N/A"
                    }
    except Exception:
        pass

    return {}


def save_papers_node(state: LiRAState) -> Dict[str, Any]:
    """Step 2.d: Parse tool results directly into raw_dataset.csv, generate RIS, and write PRISMA doc."""
    from langchain_core.messages import ToolMessage, AIMessage
    import csv
    import re
    import time
    from datetime import datetime

    # 1. Build map of tool_call_id -> query & tool used (from AIMessages)
    tool_calls_map = {}
    for msg in state["messages"]:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_map[tc["id"]] = {
                    "tool": tc["name"],
                    "query": tc.get("args", {}).get("query", "Unknown query")
                }

    # Collect tool messages
    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage) and isinstance(m.content, str)]
    if not tool_messages:
        return {"logs": state.get("logs", []) + ["No tool search results to extract papers from."]}

    all_papers = []
    search_metadata = []

    for msg in tool_messages:
        raw = msg.content
        if raw.startswith(("arXiv API Error", "Semantic Scholar API error", "Google Scholar HTTP Error", "Error querying", "PubMed API Error", "PubMed search error", "PubMed fetch error", "CrossRef API error", "OpenAlex API error")):
            continue

        tool_info = tool_calls_map.get(msg.tool_call_id, {"tool": "Unknown", "query": "Unknown"})
        tool_name = tool_info["tool"]
        query_used = tool_info["query"]
        
        # Name formatting
        db_name = tool_name.replace("_search", "").replace("_", " ").title()
        if db_name == "Arxiv": db_name = "arXiv"
        
        papers_from_query = 0

        # -----------------------------------------------------------
        # FORMAT A: structured output
        # -----------------------------------------------------------
        if "Title:" in raw and ("Abstract:" in raw or "URL:" in raw):
            entries = re.split(r'\n---\n', raw)
            for entry in entries:
                if not entry.strip(): continue
                title_m = re.search(r'Title:\s*(.+?)(?:\n|$)', entry)
                url_m   = re.search(r'URL:\s*(.+?)(?:\n|$)', entry)
                doi_m   = re.search(r'DOI:\s*(.+?)(?:\n|$)', entry)
                abs_m   = re.search(r'Abstract:\s*(.+)', entry, re.DOTALL)
                authors_m = re.search(r'Authors:\s*(.+?)(?:\n|$)', entry)

                title = title_m.group(1).strip().replace("\n", " ").replace("\r", " ") if title_m else "N/A"
                url   = url_m.group(1).strip()   if url_m   else "N/A"
                doi   = doi_m.group(1).strip()   if doi_m   else "N/A"
                abstract = abs_m.group(1).strip().replace("\n", " ").replace("\r", " ") if abs_m else "N/A"
                authors = authors_m.group(1).strip().replace("\n", " ").replace("\r", " ") if authors_m else "Unknown"

                # Extract year
                year_m = re.search(r'\((\d{4})\)', title)
                year = year_m.group(1) if year_m else "N/A"
                
                # DOI Parsing
                if "doi.org/" in url and doi == "N/A":
                    doi = url.split("doi.org/")[-1].strip()

                if len(abstract) > 50:
                    all_papers.append({
                        "title": title, "year": year, "authors": authors, "url": url,
                        "doi": doi, "source": db_name, "abstract": abstract
                    })
                    papers_from_query += 1

        # -----------------------------------------------------------
        # FORMAT B: Arxiv API fallback
        # -----------------------------------------------------------
        elif "Published:" in raw and "Summary:" in raw:
            entries = raw.split("Published:")
            for entry in entries:
                entry = entry.strip()
                if not entry: continue
                title_m = re.search(r'Title:\s*(.+?)(?:\n|$)', entry)
                summ_m  = re.search(r'Summary:\s*(.+)', entry, re.DOTALL)
                pub_m   = re.search(r'^(\d{4})', entry)
                authors_m = re.search(r'Authors:\s*(.+?)(?:\n|$)', entry)

                title    = title_m.group(1).strip() if title_m else "N/A"
                abstract = summ_m.group(1).strip()  if summ_m  else "N/A"
                year     = pub_m.group(1)            if pub_m   else "N/A"
                authors  = authors_m.group(1).strip() if authors_m else "Unknown"

                if len(abstract) > 50:
                    all_papers.append({
                        "title": title, "year": year, "authors": authors, "url": "N/A", "doi": "N/A",
                        "source": "arXiv", "abstract": abstract
                    })
                    papers_from_query += 1
                    
        # Track PRISMA info
        search_metadata.append({
            "database": db_name,
            "query": query_used,
            "count": papers_from_query,
            "date": datetime.now().strftime("%Y-%m-%d")
        })

    print(f"\n[DEBUG save_papers_node] Directly parsed {len(all_papers)} papers from tool outputs.")

    # -----------------------------------------------------------
    # Enrichment Phase (Abstracts & DOIs & Metadata)
    # -----------------------------------------------------------
    enriched_count = 0
    total_needed = 0
    
    for p in all_papers:
        # Google Scholar returns truncated data. We flag the paper for full enrichment.
        needs_doi = p["doi"] == "N/A"
        needs_abstract = p["abstract"] in ("N/A", "No Abstract available", "") or p["source"] == "Google Scholar" or len(p["abstract"]) < 200 or p["abstract"].endswith("...")
        
        if needs_doi or needs_abstract:
            total_needed += 1
            enrich_data = _enrich_paper(p["title"])
            
            made_change = False
            
            if enrich_data:
                # Update DOI if found
                if enrich_data.get("doi") and enrich_data["doi"] != "N/A":
                    p["doi"] = enrich_data["doi"]
                    made_change = True
                    if p["url"] == "N/A" or "scholar.google.com" in p["url"] or p["source"] == "Google Scholar":
                         if enrich_data.get("url") and enrich_data["url"] != "N/A":
                              p["url"] = enrich_data["url"]
                
                # Update Abstract if found
                if enrich_data.get("abstract") and len(enrich_data["abstract"]) > 50:
                    p["abstract"] = enrich_data["abstract"]
                    made_change = True
                    
                # Overwrite dirty Google Scholar metadata
                if p["source"] == "Google Scholar" or needs_abstract:
                    if enrich_data.get("authors") and enrich_data["authors"] != "Unknown":
                        p["authors"] = enrich_data["authors"]
                    if enrich_data.get("year") and enrich_data["year"] != "N/A":
                        p["year"] = enrich_data["year"]
                    if enrich_data.get("title"):
                        p["title"] = enrich_data["title"]
                        
            if made_change:
                enriched_count += 1
            
            time.sleep(0.5)

        # STRICT VALIDATION: discard if abstract is still inadequate
        final_abs = p["abstract"]
        if final_abs in ("N/A", "No Abstract available", "") or len(final_abs) < 200 or "\u2026" in final_abs or "..." in final_abs:
            p["title"] = "MARK_FOR_DELETION"
            continue

    # Remove incomplete papers (deduplication is handled by agent_3 deduplicate_node)
    all_papers = [p for p in all_papers if p["title"] != "MARK_FOR_DELETION"]
    
    print(f"[DEBUG save_papers_node] Enriched {enriched_count}/{total_needed} papers missing DOIs or full abstracts.")

    # -----------------------------------------------------------
    # Exports
    # -----------------------------------------------------------
    csv_filename = "raw_dataset.csv"
    ris_filename = "raw_dataset.ris"
    prisma_filename = "prisma_search_strategy.md"
    logs = state.get("logs", [])

    try:
        # Write CSV
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, quoting=csv.QUOTE_ALL)
            writer.writerow(["Title", "Year", "Authors", "URL", "DOI", "Source", "Abstract"])
            for p in all_papers:
                writer.writerow([p["title"], p["year"], p["authors"], p["url"], p["doi"], p["source"], p["abstract"]])
        logs.append(f"Saved {len(all_papers)} papers to {csv_filename}.")
        
        # Write RIS
        with open(ris_filename, mode='w', encoding='utf-8') as ris_file:
            for p in all_papers:
                ris_file.write("TY  - JOUR\n")
                ris_file.write(f"TI  - {p['title']}\n")
                if p["authors"] != "Unknown":
                    for auth in p["authors"].split(","):
                        ris_file.write(f"AU  - {auth.strip()}\n")
                if p["year"] != "N/A": ris_file.write(f"PY  - {p['year']}\n")
                if p["abstract"] != "N/A": ris_file.write(f"AB  - {p['abstract']}\n")
                if p["url"] != "N/A": ris_file.write(f"UR  - {p['url']}\n")
                if p["doi"] != "N/A": ris_file.write(f"DO  - {p['doi']}\n")
                ris_file.write("ER  - \n\n")
        logs.append(f"Generated RIS export {ris_filename}.")
        
        # Write PRISMA Markdown
        with open(prisma_filename, mode='w', encoding='utf-8') as prisma_file:
            prisma_file.write(f"# PRISMA Search Strategy Documentation\n\n")
            prisma_file.write(f"**Date Generated:** {datetime.now().strftime('%Y-%m-%d')}\n")
            prisma_file.write(f"**Total Unique Papers Retained:** {len(all_papers)}\n\n")
            prisma_file.write("| Database | Search Query | Records Found | Retrieval Date |\n")
            prisma_file.write("|---|---|---|---|\n")
            
            # Combine searches with 0 results
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


