# backend/rag/pipeline.py
import os
import logging
import time
from typing import Optional
from pathlib import Path

from .extraction import PDFExtractor
from .preprocessing import TextPreprocessor
from .chunking import DocumentChunker
from .embeddings import BaseEmbedder, get_embedder
from .vectorstore import VectorStore
from .retriever import Retriever
from .prompt_builder import PromptBuilder
from .models import ConversationMessage, RAGResponse   # ← import from models now


logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Orchestrates the complete RAG pipeline.

    INGESTION FLOW:
    PDF → Extract → Preprocess → Chunk → Embed → Store

    QUERY FLOW:
    Query → Embed → Search → Build Prompt → LLM → Response
    """

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[VectorStore] = None,
        llm_provider: str = "gemini",
        llm_api_key: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        top_k: int = 5,
    ):
        self.extractor = PDFExtractor(enable_ocr=True)
        self.preprocessor = TextPreprocessor()
        self.chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedder = embedder or get_embedder("local")
        self.vector_store = vector_store or VectorStore(embedder=self.embedder)
        self.retriever = Retriever(vector_store=self.vector_store, top_k=top_k)
        self.prompt_builder = PromptBuilder()
        self.top_k = top_k
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key

        self._llm_client = self._initialize_llm()

        logger.info(
            f"RAG Pipeline initialized | "
            f"Embedder: {self.embedder.model_name} | "
            f"LLM: {llm_provider}"
        )

    '''  def _initialize_llm(self):
        """Initialize the LLM client based on provider."""
        if self.llm_provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.llm_api_key)
            return genai.GenerativeModel("gemini-1.5-flash")
        elif self.llm_provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=self.llm_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")'''

    def _initialize_llm(self):
        """Initialize the LLM client based on provider."""
        if self.llm_provider == "gemini":
            from google import genai

            if not self.llm_api_key:
                raise ValueError(
                    "GEMINI_API_KEY is missing. Check your .env file in the project root."
            )

            # Some versions of google-genai read GOOGLE_API_KEY from env directly
            os.environ["GOOGLE_API_KEY"] = self.llm_api_key

            client = genai.Client(api_key=self.llm_api_key)
            return client

        elif self.llm_provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=self.llm_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        
    def ingest_pdf(
        self,
        pdf_path: str,
        session_id: Optional[str] = None
    ) -> dict:
        """Complete ingestion pipeline for a single PDF."""
        start_time = time.time()
        pdf_path = Path(pdf_path)

        logger.info(f"Starting ingestion: {pdf_path.name}")

        # STEP 1: Extract
        logger.info("Step 1/4: Extracting text...")
        document = self.extractor.extract(str(pdf_path))

        # STEP 2: Preprocess
        logger.info("Step 2/4: Preprocessing text...")
        for page in document.pages:
            page.text = self.preprocessor.preprocess(
                page.text,
                source_info={"file": pdf_path.name, "page": page.page_number}
            )

        meaningful_pages = [
            p for p in document.pages
            if self.preprocessor.is_meaningful(p.text)
        ]

        logger.info(f"Pages after filtering: {len(meaningful_pages)}/{len(document.pages)}")

        # STEP 3: Chunk
        logger.info("Step 3/4: Chunking...")
        chunks = self.chunker.chunk_document(
            pages=meaningful_pages,
            filename=pdf_path.name
        )

        # STEP 4: Embed and store
        logger.info("Step 4/4: Embedding and storing...")
        chunks_added = self.vector_store.add_chunks(chunks, session_id=session_id)

        elapsed = time.time() - start_time

        stats = {
            "filename": pdf_path.name,
            "total_pages": document.total_pages,
            "meaningful_pages": len(meaningful_pages),
            "chunks_created": len(chunks),
            "chunks_stored": chunks_added,
            "processing_time_seconds": round(elapsed, 2),
            "total_characters": document.total_chars,
            "metadata": document.metadata,
            "extraction_errors": document.extraction_errors,
        }

        logger.info(
            f"Ingestion complete: {pdf_path.name} | "
            f"Time: {elapsed:.2f}s | Chunks: {chunks_added}"
        )

        return stats

    def query(
        self,
        question: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        source_filter: Optional[str] = None,
    ) -> RAGResponse:
        """Complete query pipeline."""
        start_time = time.time()
        conversation_history = conversation_history or []

        logger.info(f"Processing query: '{question[:100]}'")

        # STEP 1: Retrieve
        retrieved_chunks = self.retriever.retrieve(
            query=question,
            session_id=session_id,
            source_file=source_filter,
        )

        if not retrieved_chunks:
            return RAGResponse(
                answer=(
                    "I couldn't find relevant information in the uploaded documents "
                    "to answer your question. Please make sure you have uploaded "
                    "the relevant PDF files."
                ),
                sources=[],
                query=question,
                processing_time_ms=int((time.time() - start_time) * 1000),
                retrieved_chunks_count=0,
                model_used=self.llm_provider,
            )

        # STEP 2: Build prompt
        prompt = self.prompt_builder.build(
            question=question,
            retrieved_chunks=retrieved_chunks,
            conversation_history=conversation_history,
        )

        # STEP 3: Call LLM
        answer = self._call_llm(prompt)

        # STEP 4: Format sources
        sources = self._format_sources(retrieved_chunks)

        elapsed_ms = int((time.time() - start_time) * 1000)

        return RAGResponse(
            answer=answer,
            sources=sources,
            query=question,
            processing_time_ms=elapsed_ms,
            retrieved_chunks_count=len(retrieved_chunks),
            model_used=self.llm_provider,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM with the prompt."""
        try:
            if self.llm_provider == "gemini":
                response = self._llm_client.models.generate_content(
                    model="models/gemini-2.5-flash",
                    contents=prompt,
                )
                return response.text

            elif self.llm_provider == "openai":
                response = self._llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1024,
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"Failed to generate response: {str(e)}")

    def _format_sources(self, chunks: list) -> list:
        """Format retrieved chunks as source citations."""
        seen = set()
        sources = []
        for chunk in chunks:
            key = (chunk["source_file"], chunk["page_number"])
            if key not in seen:
                seen.add(key)
                sources.append({
                    "source_file": chunk["source_file"],
                    "page_number": chunk["page_number"],
                    "section_title": chunk.get("section_title"),
                    "relevance_score": chunk["similarity_score"],
                    "preview": chunk["text"][:200] + "...",
                })
        return sources