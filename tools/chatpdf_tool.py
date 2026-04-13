"""
ChatPDF API Client — Wrapper for the ChatPDF REST API.

Provides methods to upload PDFs (by URL or file), chat with them,
get structured summaries, and extract key findings.

API docs: https://www.chatpdf.com/docs/api/backend
"""

import os
import time
import requests
from typing import List, Dict, Optional, Any


class ChatPDFClient:
    """Wrapper for the ChatPDF REST API."""

    BASE_URL = "https://api.chatpdf.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CHATPDF_API_KEY", "")
        self._headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        """Returns True if a valid-looking API key is set."""
        return bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key not in {"your_chatpdf_api_key_here", ""}
        )

    # ─── Source Management ─────────────────────────────────────

    def add_pdf_url(self, url: str) -> Optional[str]:
        """
        Upload a PDF by its publicly accessible URL.
        Returns the sourceId, or None on failure.
        """
        if not self.is_configured:
            return None

        try:
            response = requests.post(
                f"{self.BASE_URL}/sources/add-url",
                json={"url": url},
                headers=self._headers,
                timeout=60,
            )
            if response.status_code == 200:
                return response.json().get("sourceId")
            else:
                print(f"[ChatPDF] add_pdf_url failed ({response.status_code}): {response.text[:200]}")
                return None
        except Exception as e:
            print(f"[ChatPDF] add_pdf_url error: {e}")
            return None

    def add_pdf_file(self, filepath: str) -> Optional[str]:
        """
        Upload a local PDF file.
        Returns the sourceId, or None on failure.
        """
        if not self.is_configured:
            return None

        try:
            headers = {"x-api-key": self.api_key}
            with open(filepath, "rb") as f:
                response = requests.post(
                    f"{self.BASE_URL}/sources/add-file",
                    files={"file": (os.path.basename(filepath), f, "application/pdf")},
                    headers=headers,
                    timeout=120,
                )
            if response.status_code == 200:
                return response.json().get("sourceId")
            else:
                print(f"[ChatPDF] add_pdf_file failed ({response.status_code}): {response.text[:200]}")
                return None
        except Exception as e:
            print(f"[ChatPDF] add_pdf_file error: {e}")
            return None

    def delete_sources(self, source_ids: List[str]) -> bool:
        """Delete uploaded PDF sources from ChatPDF."""
        if not self.is_configured or not source_ids:
            return False

        try:
            response = requests.post(
                f"{self.BASE_URL}/sources/delete",
                json={"sources": source_ids},
                headers=self._headers,
                timeout=30,
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[ChatPDF] delete_sources error: {e}")
            return False

    # ─── Chat ─────────────────────────────────────────────────

    def chat(
        self,
        source_id: str,
        messages: List[Dict[str, str]],
        reference_sources: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Send messages to a PDF source.

        Args:
            source_id: The ChatPDF sourceId.
            messages: List of {"role": "user"|"assistant", "content": "..."}.
            reference_sources: If True, include page references in response.

        Returns:
            {"content": "...", "references": [...]} or None on failure.
        """
        if not self.is_configured:
            return None

        payload = {
            "sourceId": source_id,
            "messages": messages,
            "referenceSources": reference_sources,
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/chats/message",
                json=payload,
                headers=self._headers,
                timeout=90,
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ChatPDF] chat failed ({response.status_code}): {response.text[:200]}")
                return None
        except Exception as e:
            print(f"[ChatPDF] chat error: {e}")
            return None

    # ─── Convenience Methods ──────────────────────────────────

    def summarize(self, source_id: str, research_question: str = "") -> Optional[str]:
        """
        Ask ChatPDF for a structured summary of the paper.
        Returns the summary text, or None on failure.
        """
        from Prompts.prompts import STEP5_CHATPDF_SUMMARY_PROMPT

        prompt = STEP5_CHATPDF_SUMMARY_PROMPT.format(
            research_question=research_question or "the research topic"
        )

        result = self.chat(
            source_id=source_id,
            messages=[{"role": "user", "content": prompt}],
            reference_sources=True,
        )

        if result and result.get("content"):
            return result["content"]
        return None

    def extract_findings(self, source_id: str, research_question: str) -> Optional[str]:
        """
        Extract key findings relevant to the research question.
        Returns the findings text, or None on failure.
        """
        prompt = (
            f"Extract the key findings from this paper that are specifically relevant to "
            f"the following research question: {research_question}\n\n"
            f"For each finding, provide:\n"
            f"1. The finding itself\n"
            f"2. The methodology that produced this finding\n"
            f"3. Any quantitative results or metrics\n"
            f"4. Limitations or caveats\n\n"
            f"Be specific and cite page numbers where possible."
        )

        result = self.chat(
            source_id=source_id,
            messages=[{"role": "user", "content": prompt}],
            reference_sources=True,
        )

        if result and result.get("content"):
            return result["content"]
        return None

    def summarize_from_url(
        self,
        url: str,
        research_question: str = "",
        delay: float = 1.0,
    ) -> Optional[str]:
        """
        End-to-end: upload PDF by URL, summarize, then clean up.
        Returns the summary text, or None if any step fails.
        """
        source_id = self.add_pdf_url(url)
        if not source_id:
            return None

        time.sleep(delay)

        try:
            summary = self.summarize(source_id, research_question)
            return summary
        finally:
            self.delete_sources([source_id])
