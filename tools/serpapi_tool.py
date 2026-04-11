import requests
import time
import re
import xml.etree.ElementTree as ET
from typing import List
from langchain_core.tools import tool
from langchain_community.utilities import SerpAPIWrapper


def _is_real_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return False
        if v.upper() == "N/A":
            return False
        if v.lower() in {"unknown", "none", "null", "no abstract available", "no title"}:
            return False
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return False
    return True


def _safe_join(values, sep=", "):
    return sep.join([str(v).strip() for v in values if _is_real_value(v)])


def _clean_text(text: str) -> str:
    if not text:
        return ""
    return str(text).replace("\n", " ").replace("\r", " ").strip()


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return _clean_text(text)


def _add_if_present(lines: list, label: str, value):
    if _is_real_value(value):
        lines.append(f"{label}: {value}")


def _format_paper_entry(fields: dict) -> str:
    """
    Format one paper result.
    Only includes keys that truly exist.
    """
    ordered_keys = [
        ("Title", "title"),
        ("Year", "year"),
        ("Authors", "authors"),
        ("Journal", "journal"),
        ("Publisher", "publisher"),
        ("Publication Date", "publication_date"),
        ("Document Type", "document_type"),
        ("Keywords", "keywords"),
        ("Institutions", "institutions"),
        ("Countries", "countries"),
        ("Citation Count", "citation_count"),
        ("Language", "language"),
        ("PMID", "pmid"),
        ("Funding Info", "funding_info"),
        ("URL", "url"),
        ("DOI", "doi"),
        ("Abstract", "abstract"),
    ]

    lines = []
    for label, key in ordered_keys:
        _add_if_present(lines, label, fields.get(key))

    return "\n".join(lines)


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct plain text from OpenAlex abstract_inverted_index."""
    if not inverted_index:
        return ""
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort(key=lambda x: x[0])
    return " ".join(w for _, w in words)


def _parse_google_scholar_pub_info(pub_info: str) -> dict:
    """
    Best-effort extraction from Google Scholar publication summary.
    This is heuristic only.
    """
    result = {}
    text = _clean_text(pub_info)
    if not text:
        return result

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if year_match:
        result["year"] = year_match.group(1)

    parts = [p.strip() for p in text.split(" - ") if p.strip()]
    if parts:
        if parts[0]:
            result["authors"] = parts[0]

        for chunk in parts[1:]:
            if not _is_real_value(chunk):
                continue
            if "journal" in chunk.lower() or "conference" in chunk.lower():
                result.setdefault("journal", chunk)
            elif not result.get("journal") and len(chunk.split()) <= 12:
                result.setdefault("journal", chunk)

    return result


def _extract_countries_from_affiliations(affiliations: List[str]) -> str:
    """
    Very light heuristic from affiliation text.
    """
    countries = []
    blacklist = {"department", "faculty", "university", "hospital", "school", "institute", "center", "centre"}

    for aff in affiliations:
        parts = [p.strip() for p in aff.split(",") if p.strip()]
        if not parts:
            continue
        candidate = parts[-1]
        cand_lower = candidate.lower()
        if len(candidate) >= 2 and cand_lower not in blacklist and candidate not in countries:
            countries.append(candidate)

    return _safe_join(countries[:10])


COUNTRY_CODE_MAP = {
    "HK": "Hong Kong",
    "IT": "Italy",
    "US": "United States",
    "GB": "United Kingdom",
    "FR": "France",
    "DE": "Germany",
    "CN": "China",
    "IN": "India",
    "BR": "Brazil",
    "ES": "Spain",
    "CA": "Canada",
    "AU": "Australia",
    "JP": "Japan",
    "KR": "South Korea",
}


@tool
def google_scholar_search(query: str) -> str:
    """
    Search Google Scholar for a given query.
    Returns only fields that truly exist in the result.
    """
    try:
        search = SerpAPIWrapper(params={"engine": "google_scholar", "num": 20})
        res = search.results(query)
        papers = res.get("organic_results", [])
        output = []

        for p in papers:
            title = _clean_text(p.get("title", ""))
            url = _clean_text(p.get("link", ""))
            snippet = _clean_text(p.get("snippet", ""))
            pub_info = _clean_text(p.get("publication_info", {}).get("summary", ""))

            pub_meta = _parse_google_scholar_pub_info(pub_info)

            paper = {}
            if _is_real_value(title):
                paper["title"] = title
            if _is_real_value(url):
                paper["url"] = url
            if _is_real_value(snippet):
                paper["abstract"] = snippet

            for key in ["year", "authors", "journal"]:
                if _is_real_value(pub_meta.get(key)):
                    paper[key] = pub_meta[key]

            formatted = _format_paper_entry(paper)
            if formatted:
                output.append(formatted)

        return "\n---\n".join(output) if output else "No results found on Google Scholar."
    except Exception as e:
        return f"Google Scholar HTTP Error: {str(e)}. Try a simpler or shorter query."


@tool
def arxiv_search(query: str) -> str:
    """
    Search arXiv for free papers.
    Returns only fields that truly exist.
    """
    import urllib.request
    import urllib.parse

    try:
        q = urllib.parse.quote(query)
        url = f"http://export.arxiv.org/api/query?search_query=all:{q}&start=0&max_results=15"
        data = urllib.request.urlopen(url, timeout=15).read()
        root = ET.fromstring(data)

        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        results = []

        for entry in root.findall("atom:entry", ns):
            paper = {}

            title_node = entry.find("atom:title", ns)
            if title_node is not None and title_node.text:
                paper["title"] = _clean_text(title_node.text)

            pub_node = entry.find("atom:published", ns)
            if pub_node is not None and pub_node.text:
                paper["year"] = pub_node.text[:4]
                paper["publication_date"] = _clean_text(pub_node.text)

            id_node = entry.find("atom:id", ns)
            if id_node is not None and id_node.text:
                paper["url"] = _clean_text(id_node.text)

            doi_node = entry.find("arxiv:doi", ns)
            if doi_node is not None and doi_node.text:
                paper["doi"] = _clean_text(doi_node.text)

            authors = []
            affiliations = []
            for author in entry.findall("atom:author", ns):
                name_node = author.find("atom:name", ns)
                if name_node is not None and name_node.text:
                    authors.append(_clean_text(name_node.text))
                aff_node = author.find("arxiv:affiliation", ns)
                if aff_node is not None and aff_node.text:
                    aff = _clean_text(aff_node.text)
                    if aff and aff not in affiliations:
                        affiliations.append(aff)

            if authors:
                paper["authors"] = _safe_join(authors)
            if affiliations:
                paper["institutions"] = _safe_join(affiliations)

            sum_node = entry.find("atom:summary", ns)
            if sum_node is not None and sum_node.text:
                paper["abstract"] = _clean_text(sum_node.text)

            category_terms = []
            for cat in entry.findall("atom:category", ns):
                term = cat.attrib.get("term")
                if _is_real_value(term) and term not in category_terms:
                    category_terms.append(term)
            if category_terms:
                paper["keywords"] = _safe_join(category_terms)

            paper["document_type"] = "preprint"

            formatted = _format_paper_entry(paper)
            if formatted:
                results.append(formatted)

        return "\n---\n".join(results) if results else "No results found on arXiv."
    except Exception as e:
        return f"arXiv API Error: {str(e)}. Try simplifying or shortening your boolean search query."


@tool
def openalex_search(query: str) -> str:
    """
    Search OpenAlex for academic papers.
    Returns richer metadata only when those fields truly exist.
    """
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": 20,
            "select": ",".join([
                "title",
                "publication_year",
                "publication_date",
                "doi",
                "type",
                "language",
                "abstract_inverted_index",
                "authorships",
                "concepts",
                "primary_location",
                "cited_by_count",
                "ids"
            ])
        }
        response = requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"}
        )

        if response.status_code == 200:
            data = response.json()
            results = []

            for work in data.get("results", []):
                paper = {}

                title = work.get("title")
                if _is_real_value(title):
                    paper["title"] = _clean_text(title)

                year = work.get("publication_year")
                if year:
                    paper["year"] = str(year)

                publication_date = work.get("publication_date")
                if _is_real_value(publication_date):
                    paper["publication_date"] = publication_date

                doi = work.get("doi")
                if _is_real_value(doi):
                    if doi.startswith("https://doi.org/"):
                        doi = doi.split("doi.org/")[-1]
                    paper["doi"] = doi
                    paper["url"] = f"https://doi.org/{doi}"

                work_type = work.get("type")
                if _is_real_value(work_type):
                    paper["document_type"] = work_type

                language = work.get("language")
                if _is_real_value(language):
                    paper["language"] = language

                authorships = work.get("authorships", [])
                authors = []
                institutions = []
                countries = []

                for auth in authorships:
                    name = auth.get("author", {}).get("display_name")
                    if _is_real_value(name):
                        authors.append(name)

                    for inst in auth.get("institutions", []):
                        inst_name = inst.get("display_name")
                        if _is_real_value(inst_name) and inst_name not in institutions:
                            institutions.append(inst_name)

                        country = inst.get("country_code")
                        if _is_real_value(country):
                            country_name = COUNTRY_CODE_MAP.get(country, country)
                            if country_name not in countries:
                                countries.append(country_name)

                if authors:
                    paper["authors"] = _safe_join(authors[:10])
                if institutions:
                    paper["institutions"] = _safe_join(institutions)
                if countries:
                    paper["countries"] = _safe_join(countries)

                inv_idx = work.get("abstract_inverted_index")
                abstract = _reconstruct_abstract(inv_idx) if inv_idx else ""
                if _is_real_value(abstract):
                    paper["abstract"] = _clean_text(abstract)

                concepts = []
                for c in work.get("concepts", [])[:10]:
                    name = c.get("display_name")
                    if _is_real_value(name):
                        concepts.append(name)
                if concepts:
                    paper["keywords"] = _safe_join(concepts)

                primary_location = work.get("primary_location") or {}
                source = primary_location.get("source") or {}
                journal = source.get("display_name")
                publisher = source.get("host_organization_name")

                if _is_real_value(journal):
                    paper["journal"] = journal
                if _is_real_value(publisher):
                    paper["publisher"] = publisher

                cited_by_count = work.get("cited_by_count")
                if cited_by_count is not None:
                    paper["citation_count"] = str(cited_by_count)

                ids = work.get("ids") or {}
                pmid = ids.get("pmid")
                if isinstance(pmid, str) and "pubmed.ncbi.nlm.nih.gov/" in pmid:
                    pmid = pmid.rstrip("/").split("/")[-1]
                if _is_real_value(pmid):
                    paper["pmid"] = pmid

                formatted = _format_paper_entry(paper)
                if formatted:
                    results.append(formatted)

            return "\n---\n".join(results) if results else "No results found on OpenAlex."

        return f"OpenAlex API error: {response.status_code}"
    except Exception as e:
        return f"Error querying OpenAlex: {str(e)}"


@tool
def pubmed_search(query: str) -> str:
    """
    Search PubMed.
    Returns richer metadata only when those fields truly exist.
    """
    try:
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": 15,
            "retmode": "json",
            "tool": "LiRA-Pipeline",
            "email": "research@example.com"
        }
        search_resp = requests.get(esearch_url, params=params, timeout=15)
        if search_resp.status_code != 200:
            return f"PubMed search error: {search_resp.status_code}"

        pmids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return "No results found on PubMed."

        efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": "LiRA-Pipeline",
            "email": "research@example.com"
        }
        time.sleep(0.5)
        fetch_resp = requests.get(efetch_url, params=fetch_params, timeout=20)
        if fetch_resp.status_code != 200:
            return f"PubMed fetch error: {fetch_resp.status_code}"

        root = ET.fromstring(fetch_resp.text)
        results = []

        for article in root.findall(".//PubmedArticle"):
            paper = {}

            title_el = article.find(".//ArticleTitle")
            if title_el is not None:
                title = "".join(title_el.itertext()).strip()
                if _is_real_value(title):
                    paper["title"] = _clean_text(title)

            year_el = article.find(".//PubDate/Year")
            if year_el is None:
                year_el = article.find(".//PubDate/MedlineDate")
            if year_el is not None and year_el.text:
                paper["year"] = year_el.text[:4]
                paper["publication_date"] = _clean_text(year_el.text)

            authors = []
            affiliations = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None and last.text:
                    name = last.text
                    if fore is not None and fore.text:
                        name = f"{fore.text} {name}"
                    authors.append(_clean_text(name))

                for aff in author.findall(".//AffiliationInfo/Affiliation"):
                    aff_text = "".join(aff.itertext()).strip()
                    if _is_real_value(aff_text) and aff_text not in affiliations:
                        affiliations.append(_clean_text(aff_text))

            if authors:
                paper["authors"] = _safe_join(authors[:10])
            if affiliations:
                paper["institutions"] = _safe_join(affiliations[:10])

            countries = _extract_countries_from_affiliations(affiliations)
            if _is_real_value(countries):
                paper["countries"] = countries

            abstract_parts = []
            for abs_text in article.findall(".//AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext()).strip()
                if _is_real_value(text):
                    if _is_real_value(label):
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            if abstract_parts:
                paper["abstract"] = _clean_text(" ".join(abstract_parts))

            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            if _is_real_value(pmid):
                paper["pmid"] = pmid
                paper["url"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            doi = ""
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi" and article_id.text:
                    doi = article_id.text
                    break
            if _is_real_value(doi):
                paper["doi"] = doi

            journal_el = article.find(".//Journal/Title")
            if journal_el is not None and journal_el.text:
                paper["journal"] = _clean_text(journal_el.text)

            pub_types = []
            for pt in article.findall(".//PublicationType"):
                text = "".join(pt.itertext()).strip()
                if _is_real_value(text) and text not in pub_types:
                    pub_types.append(text)
            if pub_types:
                paper["document_type"] = _safe_join(pub_types)

            keywords = []
            for kw in article.findall(".//Keyword"):
                text = "".join(kw.itertext()).strip()
                if _is_real_value(text) and text not in keywords:
                    keywords.append(text)
            if keywords:
                paper["keywords"] = _safe_join(keywords[:10])

            formatted = _format_paper_entry(paper)
            if formatted:
                results.append(formatted)

        return "\n---\n".join(results) if results else "No results found on PubMed."
    except Exception as e:
        return f"PubMed API Error: {str(e)}"


@tool
def crossref_search(query: str) -> str:
    """
    Search CrossRef.
    Returns richer metadata only when those fields truly exist.
    """
    try:
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": 15
        }
        headers = {"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"}
        response = requests.get(url, params=params, headers=headers, timeout=20)

        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            results = []

            for item in items:
                paper = {}

                title_arr = item.get("title", [])
                if title_arr:
                    title = _clean_text(title_arr[0])
                    if _is_real_value(title):
                        paper["title"] = title

                doi = item.get("DOI")
                if _is_real_value(doi):
                    paper["doi"] = doi
                    paper["url"] = f"https://doi.org/{doi}"

                year = ""
                publication_date = ""
                for date_field in ["published-print", "published-online", "issued"]:
                    date_parts = item.get(date_field, {}).get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        parts = date_parts[0]
                        if len(parts) >= 1:
                            year = str(parts[0])
                        publication_date = "-".join(str(x) for x in parts)
                        break

                if _is_real_value(year):
                    paper["year"] = year
                if _is_real_value(publication_date):
                    paper["publication_date"] = publication_date

                authors = []
                institutions = []
                for a in item.get("author", [])[:10]:
                    family = a.get("family", "")
                    given = a.get("given", "")
                    full = f"{given} {family}".strip()
                    if _is_real_value(full):
                        authors.append(full)

                    for aff in a.get("affiliation", []):
                        name = aff.get("name")
                        if _is_real_value(name) and name not in institutions:
                            institutions.append(name)

                if authors:
                    paper["authors"] = _safe_join(authors)
                if institutions:
                    paper["institutions"] = _safe_join(institutions)

                abstract = _clean_html(item.get("abstract", ""))
                if _is_real_value(abstract):
                    paper["abstract"] = abstract

                journal_titles = item.get("container-title", [])
                if journal_titles:
                    journal = _clean_text(journal_titles[0])
                    if _is_real_value(journal):
                        paper["journal"] = journal

                publisher = item.get("publisher")
                if _is_real_value(publisher):
                    paper["publisher"] = publisher

                doc_type = item.get("type")
                if _is_real_value(doc_type):
                    paper["document_type"] = doc_type

                language = item.get("language")
                if _is_real_value(language):
                    paper["language"] = language

                subjects = item.get("subject", [])
                if subjects:
                    paper["keywords"] = _safe_join(subjects[:10])

                funders = []
                for funder in item.get("funder", []) or []:
                    name = funder.get("name")
                    if _is_real_value(name) and name not in funders:
                        funders.append(name)
                if funders:
                    paper["funding_info"] = _safe_join(funders)

                formatted = _format_paper_entry(paper)
                if formatted:
                    results.append(formatted)

            return "\n---\n".join(results) if results else "No results found on CrossRef."

        return f"CrossRef API error: {response.status_code}"
    except Exception as e:
        return f"CrossRef API Error: {str(e)}"


tools = [google_scholar_search, arxiv_search, openalex_search, pubmed_search, crossref_search]