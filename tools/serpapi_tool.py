import requests
import time
import re
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.utilities.arxiv import ArxivAPIWrapper

@tool
def google_scholar_search(query: str) -> str:
    """
    Search Google Scholar for a given query.
    Excellent starting point for systematic reviews across all publishers (ACM, IEEE, Springer…).
    """
    try:
        search = SerpAPIWrapper(params={"engine": "google_scholar", "num": 20})
        res = search.results(query)
        papers = res.get("organic_results", [])
        output = []
        for p in papers:
            title = p.get("title", "No Title")
            url = p.get("link", "N/A")
            snippet = p.get("snippet", "No Abstract available")
            pub_info = p.get("publication_info", {}).get("summary", "N/A")
            
            # Extract year from pub_info (usually a 4 digit number)
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', pub_info)
            year = year_match.group(1) if year_match else "N/A"
            
            # Extract authors from pub_info (usually everything before the first " - ")
            authors = pub_info.split(" - ")[0] if " - " in pub_info else "Unknown"
            
            # Google Scholar has no DOI
            output.append(f"Title: {title} ({year})\nAuthors: {authors}\nURL: {url}\nDOI: N/A\nAbstract: {snippet}")
        return "\n---\n".join(output) if output else "No results found on Google Scholar."
    except Exception as e:
        return f"Google Scholar HTTP Error: {str(e)}. Try a simpler or shorter query."

@tool
def arxiv_search(query: str) -> str:
    """
    Search arXiv for 100% free papers.
    Strong in AI, Reinforcement Learning, and Networking.
    """
    import urllib.request
    import xml.etree.ElementTree as ET
    import urllib.parse
    try:
        q = urllib.parse.quote(query)
        url = f"http://export.arxiv.org/api/query?search_query=all:{q}&start=0&max_results=15"
        data = urllib.request.urlopen(url, timeout=15).read()
        root = ET.fromstring(data)
        
        # XML namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        
        results = []
        for entry in root.findall("atom:entry", ns):
            title_node = entry.find("atom:title", ns)
            if title_node is None:
                continue
            title = title_node.text.strip().replace("\n", " ").replace("\r", "")
            
            pub_node = entry.find("atom:published", ns)
            year = pub_node.text[:4] if pub_node is not None else "N/A"
            
            id_node = entry.find("atom:id", ns)
            url_link = id_node.text if id_node is not None else "N/A"
            
            # Arxiv DOI
            doi = "N/A"
            doi_node = entry.find("arxiv:doi", ns)
            if doi_node is not None:
                doi = doi_node.text
            
            authors = []
            for author in entry.findall("atom:author", ns):
                name_node = author.find("atom:name", ns)
                if name_node is not None:
                    authors.append(name_node.text)
            authors_str = ", ".join(authors) if authors else "Unknown"
            
            sum_node = entry.find("atom:summary", ns)
            abstract = sum_node.text.strip().replace("\n", " ").replace("\r", "") if sum_node is not None else "No Abstract available"
            
            results.append(f"Title: {title} ({year})\nAuthors: {authors_str}\nURL: {url_link}\nDOI: {doi}\nAbstract: {abstract}")
            
        return "\n---\n".join(results) if results else "No results found on arXiv."
    except Exception as e:
        return f"arXiv API Error: {str(e)}. Try simplifying or shortening your boolean search query."

@tool
def openalex_search(query: str) -> str:
    """
    Search OpenAlex for academic papers. Free, no API key required.
    Returns full abstracts, titles, URLs, and publication years.
    Excellent coverage across all disciplines.
    """
    try:
        url = f"https://api.openalex.org/works?search={query}&per_page=20&select=title,publication_year,doi,abstract_inverted_index,authorships"
        response = requests.get(url, timeout=15, headers={"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"})
        if response.status_code == 200:
            data = response.json()
            results = []
            for work in data.get("results", []):
                title = work.get("title") or "No Title"
                title = title.replace("\n", " ").replace("\r", "")
                year = work.get("publication_year") or "N/A"
                doi = work.get("doi") or "N/A"
                if doi != "N/A" and doi.startswith("https://doi.org/"):
                    doi = doi.split("doi.org/")[-1]
                
                # Extract Authors
                authorships = work.get("authorships", [])
                authors = []
                for auth in authorships[:5]:
                    name = auth.get("author", {}).get("display_name")
                    if name: authors.append(name)
                if len(authorships) > 5: authors.append("et al.")
                authors_str = ", ".join(authors) if authors else "Unknown"

                inv_idx = work.get("abstract_inverted_index")
                if inv_idx:
                    words = []
                    for word, positions in inv_idx.items():
                        for pos in positions:
                            words.append((pos, word))
                    words.sort(key=lambda x: x[0])
                    abstract = " ".join(w for _, w in words)
                else:
                    abstract = "No Abstract available"
                abstract = abstract.replace("\n", " ").replace("\r", "")
                
                doi_url = f"https://doi.org/{doi}" if doi != "N/A" else "N/A"
                results.append(f"Title: {title} ({year})\nAuthors: {authors_str}\nURL: {doi_url}\nDOI: {doi}\nAbstract: {abstract}")
            return "\n---\n".join(results) if results else "No results found on OpenAlex."
        return f"OpenAlex API error: {response.status_code}"
    except Exception as e:
        return f"Error querying OpenAlex: {str(e)}"

@tool
def pubmed_search(query: str) -> str:
    """
    Search PubMed (NCBI) for biomedical and life sciences papers.
    Free, no API key required. Returns full abstracts.
    Gold standard database for medical/clinical research.
    """
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    import time
    try:
        # Step 1: ESearch — get PMIDs
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

        # Step 2: EFetch — get full metadata + abstracts
        efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": "LiRA-Pipeline",
            "email": "research@example.com"
        }
        time.sleep(0.5)  # Be polite, max 3 req/s without key
        fetch_resp = requests.get(efetch_url, params=fetch_params, timeout=20)
        if fetch_resp.status_code != 200:
            return f"PubMed fetch error: {fetch_resp.status_code}"

        # Parse XML response
        root = ET.fromstring(fetch_resp.text)
        results = []

        for article in root.findall(".//PubmedArticle"):
            # Title
            title_el = article.find(".//ArticleTitle")
            title = title_el.text.replace("\n", " ").replace("\r", "") if title_el is not None and title_el.text else "No Title"

            # Year
            year_el = article.find(".//PubDate/Year")
            if year_el is None:
                year_el = article.find(".//PubDate/MedlineDate")
            year = year_el.text[:4] if year_el is not None and year_el.text else "N/A"

            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None and last.text:
                    name = last.text
                    if fore is not None and fore.text:
                        name += f" {fore.text}"
                    authors.append(name)
            authors_str = ", ".join(authors[:5])
            if len(authors) > 5:
                authors_str += " et al."
            if not authors_str: authors_str = "Unknown"

            # Abstract
            abstract_parts = []
            for abs_text in article.findall(".//AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext()).strip().replace("\n", " ").replace("\r", "")
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts) if abstract_parts else "No Abstract available"

            # PMID / URL / DOI
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else "N/A"
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid != "N/A" else "N/A"
            
            doi = "N/A"
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi" and article_id.text:
                    doi = article_id.text
                    break

            results.append(f"Title: {title} ({year})\nAuthors: {authors_str}\nURL: {url}\nDOI: {doi}\nAbstract: {abstract}")

        return "\n---\n".join(results) if results else "No results found on PubMed."
    except Exception as e:
        return f"PubMed API Error: {str(e)}"

@tool
def crossref_search(query: str) -> str:
    """
    Search CrossRef for scholarly articles across all publishers.
    Free, no API key required. Returns DOIs, titles, authors, and abstracts.
    Broad coverage: Springer, Elsevier, Wiley, IEEE, ACM, etc.
    """
    try:
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": 15,
            "filter": "has-abstract:true",
            "select": "DOI,title,author,abstract,published-print,published-online"
        }
        headers = {"User-Agent": "LiRA-Pipeline/1.0 (mailto:research@example.com)"}
        response = requests.get(url, params=params, headers=headers, timeout=20)

        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            results = []

            for item in items:
                title_arr = item.get("title", [])
                title = title_arr[0].replace("\n", " ") if title_arr else "No Title"
                doi = item.get("DOI", "N/A")
                doi_url = f"https://doi.org/{doi}" if doi != "N/A" else "N/A"

                # Year
                year = "N/A"
                for date_field in ["published-print", "published-online"]:
                    date_parts = item.get(date_field, {}).get("date-parts", [[]])
                    if date_parts and date_parts[0] and date_parts[0][0]:
                        year = str(date_parts[0][0])
                        break

                # Authors
                authors = []
                for a in item.get("author", [])[:5]:
                    family = a.get("family", "")
                    given = a.get("given", "")
                    authors.append(f"{family} {given}".strip())
                if len(item.get("author", [])) > 5:
                    authors.append("et al.")
                authors_str = ", ".join(authors) if authors else "Unknown"

                # Abstract
                abstract = item.get("abstract", "No Abstract available")
                abstract = re.sub(r'<[^>]+>', '', abstract).replace("\n", " ").replace("\r", " ").strip()

                results.append(f"Title: {title} ({year})\nAuthors: {authors_str}\nURL: {doi_url}\nDOI: {doi}\nAbstract: {abstract}")

            return "\n---\n".join(results) if results else "No results found on CrossRef."
        return f"CrossRef API error: {response.status_code}"
    except Exception as e:
        return f"CrossRef API Error: {str(e)}"

tools = [google_scholar_search, arxiv_search, openalex_search, pubmed_search, crossref_search]