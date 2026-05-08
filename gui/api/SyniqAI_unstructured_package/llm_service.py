"""
LLM Service
===========
Provides language-model-powered analysis for unstructured media records.

Capabilities
------------
  - Sentiment analysis on transcript / text segments
  - Keyword / keyphrase extraction
  - Named-entity recognition (NER) for document fields
  - Language detection
  - Summary generation

Configuration (environment variables)
--------------------------------------
  LLM_PROVIDER      : "openai" | "azure_openai" | "local" | "none"  (default: "none")
  LLM_API_URL       : base URL for OpenAI-compatible API
  LLM_API_KEY       : API key
  LLM_MODEL         : model name (e.g. "gpt-4o-mini", "llama3")
  LLM_TEMPERATURE   : float (default 0.0 for deterministic outputs)

When LLM_PROVIDER=none (default) the service uses lightweight rule-based
fallbacks that require no external dependencies — so the rest of the
system keeps working without any LLM configuration.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Load .env from SYNIQ root so vars are available regardless of import order
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = Path(__file__).parent.parent.parent.parent / ".env"
    _load_dotenv(_env_path, override=False)  # override=False keeps shell vars supreme
except ImportError:
    pass  # python-dotenv not installed — rely on shell env

logger = logging.getLogger(__name__)


def _llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "none").lower()


def _llm_api_url() -> str:
    return os.getenv("LLM_API_URL", "")


def _llm_api_key() -> str:
    return os.getenv("LLM_API_KEY", "")


def _llm_model() -> str:
    return os.getenv("LLM_MODEL", "gpt-4o-mini")


def _llm_temp() -> float:
    return float(os.getenv("LLM_TEMPERATURE", "0.0"))

# ---------------------------------------------------------------------------
# Rule-based fallback helpers
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = {"thank", "great", "excellent", "good", "happy", "glad","found", "helpful", "appreciate", "wonderful", "pleased"}
_NEGATIVE_WORDS = {"problem", "issue", "error", "failed", "broken", "missing","lost", "frustrated", "unhappy", "sorry", "apologize", "wrong"}
_STOP_WORDS = {
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they",
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "not", "and", "or",
    "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "up", "about", "into", "through", "during", "that", "this", "these",
    "those", "so", "just", "if", "then", "than", "too", "very", "s", "t",
    "ll", "d", "m", "re", "ve", "ain", "no", "yes", "there", "here",
}

def _rule_based_sentiment(text: str) -> Tuple[str, float]:
    words = re.findall(r"\w+", text.lower())
    pos = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = pos + neg or 1
    score = (pos - neg) / total
    if score > 0.3:
        return "positive", round(min(0.95, 0.65 + score * 0.3), 2)
    if score < -0.3:
        return "negative", round(max(0.05, 0.35 + score * 0.3), 2)
    return "neutral", round(0.5 + score * 0.15, 2)


def _rule_based_keywords(text: str, top_n: int = 10) -> List[Dict[str, Any]]:
    words = re.findall(r"\b[a-z]{4,}\b", text.lower())
    freq: Dict[str, int] = {}
    for w in words:
        if w not in _STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:top_n]
    max_freq = max((v for _, v in top), default=1)
    return [
        {"word": w, "count": c, "relevance": round(0.6 + (c / max_freq) * 0.4, 2)}
        for w, c in top
    ]


def _rule_based_entities(text: str) -> Dict[str, Any]:
    """Very lightweight entity extraction via regex patterns."""
    fields: Dict[str, str] = {}
    # Dates
    date_m = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})\b", text)
    if date_m:
        fields["Date"] = date_m.group(1)
    # Currency amounts
    amount_m = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
    if amount_m:
        fields["Amount"] = amount_m.group(0)
    # Invoice / order numbers
    inv_m = re.search(r"\b(?:INV|ORDER|REF|CASE|TICKET)[#\-]?[\w\-]{4,}\b", text, re.IGNORECASE)
    if inv_m:
        fields["Reference Number"] = inv_m.group(0)
    # Email
    email_m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_m:
        fields["Email"] = email_m.group(0)
    return fields


def _rule_based_language(text: str) -> str:
    """Stub language detection (extend with langdetect if installed)."""
    try:
        from langdetect import detect  # type: ignore
        return detect(text)
    except ImportError:
        pass
    # Very rough heuristic
    if re.search(r"[^\x00-\x7F]", text):
        return "non-english"
    return "en"


# ---------------------------------------------------------------------------
# LLM Client (OpenAI-compatible)
# ---------------------------------------------------------------------------

def _call_llm(system_prompt: str, user_content: str) -> str:
    """Call an OpenAI-compatible chat completion endpoint. Returns the reply text."""
    api_url = _llm_api_url()
    api_key = _llm_api_key()
    model   = _llm_model()
    temp    = _llm_temp()
    try:
        import httpx  # type: ignore
        url = api_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "sk-YOUR_OPENAI_API_KEY_HERE":
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "temperature": temp,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning(f"LLM call failed: {exc}")
        raise


# ---------------------------------------------------------------------------
# Public Service
# ---------------------------------------------------------------------------

class LLMService:
    """
    Unified language intelligence service.

    Methods return structured dicts regardless of whether an LLM is
    configured or the rule-based fallback is being used.
    """

    def __init__(self):
        self._provider = _llm_provider()
        self._api_url  = _llm_api_url()
        logger.info(f"LLMService: provider={self._provider}, api_url={self._api_url or '(none)'}")

    # ------------------------------------------------------------------
    def analyse_transcript(self, text: str) -> Dict[str, Any]:
        """
        Given raw transcript text return:
          - overall_sentiment  : positive | negative | neutral
          - sentiment_score    : 0.0-1.0
          - keywords           : [{word, count, relevance}]
          - summary            : short prose summary
          - language           : ISO 639-1 code
        """
        if not text:
            return {"overall_sentiment": "neutral", "sentiment_score": 0.5, "keywords": [], "summary": "", "language": "en"}

        if self._provider in ("openai", "azure_openai", "local") and self._api_url:
            try:
                import json as _json
                prompt = (
                    "Analyse the following transcript. "
                    "Return a JSON object with keys: "
                    "overall_sentiment (positive|negative|neutral), "
                    "sentiment_score (0-1 float), "
                    "keywords (array of {word,count,relevance}), "
                    "summary (1-2 sentence string), "
                    "language (ISO 639-1). "
                    "Return ONLY valid JSON."
                )
                raw = _call_llm(prompt, text[:4000])
                # Extract JSON from the response (handle code blocks)
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    return _json.loads(m.group(0))
            except Exception as exc:
                logger.warning(f"LLM transcript analysis failed, using fallback: {exc}")

        # Rule-based fallback
        sentiment, score = _rule_based_sentiment(text)
        keywords = _rule_based_keywords(text)
        language = _rule_based_language(text)
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 20]
        summary = " ".join(sentences[:2]) if sentences else text[:200]
        return {"overall_sentiment": sentiment, "sentiment_score": score,
                "keywords": keywords, "summary": summary, "language": language}

    def analyse_speaker_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Given segments [{speaker, timestamp, text}] enrich each segment with
        per-segment sentiment.
        """
        enriched = []
        for seg in segments:
            text = seg.get("text", "")
            sentiment, _ = _rule_based_sentiment(text)
            enriched.append({**seg, "sentiment": seg.get("sentiment") or sentiment})
        return enriched

    def extract_document_fields(self, text: str, doc_type: str = "general") -> List[Dict[str, Any]]:
        """
        Extract structured key-value fields from document text.
        Returns [{field, value, confidence}].
        """
        if not text:
            return []

        if self._provider in ("openai", "azure_openai", "local") and self._api_url:
            try:
                import json as _json
                prompt = (
                    f"Extract key structured fields from this {doc_type} document. "
                    "Return a JSON array of objects with keys: field, value, confidence (0-1). "
                    "Focus on dates, amounts, names, IDs, references. Return ONLY valid JSON array."
                )
                raw = _call_llm(prompt, text[:4000])
                m = re.search(r"\[.*\]", raw, re.DOTALL)
                if m:
                    return _json.loads(m.group(0))
            except Exception as exc:
                logger.warning(f"LLM entity extraction failed, using fallback: {exc}")

        # Rule-based fallback
        entities = _rule_based_entities(text)
        return [{"field": k, "value": v, "confidence": 0.75} for k, v in entities.items()]

    def detect_language(self, text: str) -> str:
        """Return ISO 639-1 language code."""
        return _rule_based_language(text)

    def summarise(self, text: str, max_sentences: int = 2) -> str:
        """Return a short summary of the text."""
        if not text:
            return ""
        if self._provider in ("openai", "azure_openai", "local") and self._api_url:
            try:
                prompt = f"Summarise the following text in at most {max_sentences} sentences."
                return _call_llm(prompt, text[:4000]).strip()
            except Exception:
                pass
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 20]
        return " ".join(sentences[:max_sentences])
