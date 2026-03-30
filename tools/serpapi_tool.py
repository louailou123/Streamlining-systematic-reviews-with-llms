from langchain_core.tools import tool
from langchain_community.utilities import SerpAPIWrapper

@tool
def google_scholar_search(query: str) -> str:
    """
    Search Google Scholar for a given query.
    Use this to get the amount of papers, surveys, or reviews.
    """
    search = SerpAPIWrapper(params={"engine": "google_scholar"})
    return search.run(query)

tools = [google_scholar_search]