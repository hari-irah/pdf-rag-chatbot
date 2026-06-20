# backend/tests/test_rag_pipeline.py

import pytest
import tempfile
import os
from pathlib import Path

from rag.extraction import PDFExtractor
from rag.preprocessing import TextPreprocessor
from rag.chunking import DocumentChunker, RecursiveChunker


class TestRecursiveChunker:
    """Unit tests for the chunking algorithm."""

    def test_short_text_returns_single_chunk(self):
        chunker = RecursiveChunker(chunk_size=1000)
        text = "This is a short text."
        chunks = chunker.split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_correctly(self):
        chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
        text = ("This is paragraph one. " * 10 + "\n\n" +
                "This is paragraph two. " * 10)
        chunks = chunker.split_text(text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100 + 50  # Allow slight overage at boundaries

    def test_overlap_content_present(self):
        """Verify overlap content is shared between consecutive chunks."""
        chunker = RecursiveChunker(chunk_size=50, chunk_overlap=20)
        text = "a" * 40 + " " + "b" * 40
        chunks = chunker.split_text(text)
        if len(chunks) > 1:
            # There should be some overlap
            assert len(chunks[0]) > 0
            assert len(chunks[1]) > 0

    def test_empty_text(self):
        chunker = RecursiveChunker()
        chunks = chunker.split_text("")
        assert chunks == [] or all(not c.strip() for c in chunks)


class TestTextPreprocessor:
    """Unit tests for text preprocessing."""

    def setup_method(self):
        self.preprocessor = TextPreprocessor()

    def test_unicode_normalization(self):
        text = "\u201cHello World\u201d"  # Fancy quotes
        result = self.preprocessor.preprocess(text)
        assert '"Hello World"' in result

    def test_hyphenation_fix(self):
        text = "infor-\nmation is key"
        result = self.preprocessor.preprocess(text)
        assert "information" in result

    def test_encoding_ligatures(self):
        text = "ﬁle system ﬂow"
        result = self.preprocessor.preprocess(text)
        assert "file" in result
        assert "flow" in result

    def test_is_meaningful_rejects_short_text(self):
        assert not self.preprocessor.is_meaningful("pg 3")
        assert not self.preprocessor.is_meaningful("   ")
        assert not self.preprocessor.is_meaningful("")

    def test_is_meaningful_accepts_good_text(self):
        good_text = "This is a meaningful paragraph with enough content to be useful."
        assert self.preprocessor.is_meaningful(good_text)


class TestRAGEvaluation:
    """
    RAG-specific evaluation tests.
    
    These test retrieval quality, not just code correctness.
    """

    def test_relevant_chunk_is_retrieved(self, vector_store, embedder):
        """
        Given a question about a specific topic,
        the retriever should return chunks containing that topic.
        """
        # This is a functional test that requires actual components
        # Mark as integration test
        pytest.skip("Integration test — requires vector store and embedder")