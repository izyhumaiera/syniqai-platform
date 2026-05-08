"""
SyniqAI Unstructured Processing Package
=========================================
Core business logic for the Unstructured Silver Layer.

Provides:
  - QualityRulesEngine  : PostgreSQL-backed quality + transform rules
  - MLModelRegistry     : ML model catalog (image, audio, video, document, text)
  - LLMService          : LLM-powered analysis (transcript, entity extraction, sentiment)
  - AnalysisService     : Per-file analysis dispatch (coordinates ML + LLM + Spark)
"""

from .rules_engine import QualityRulesEngine
from .ml_registry import MLModelRegistry
from .llm_service import LLMService
from .analysis_service import AnalysisService

__all__ = [
    "QualityRulesEngine",
    "MLModelRegistry",
    "LLMService",
    "AnalysisService",
]
