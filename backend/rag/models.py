# backend/rag/models.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConversationMessage:
    """A single turn in the conversation."""
    role: str   # "user" or "assistant"
    content: str


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    answer: str
    sources: list
    query: str
    processing_time_ms: int
    retrieved_chunks_count: int
    model_used: str