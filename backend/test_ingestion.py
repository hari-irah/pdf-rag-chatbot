# backend/test_ingestion.py
# Run with: python test_ingestion.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv('../.env')

from rag.embeddings import get_embedder
from rag.vectorstore import VectorStore
from rag.pipeline import RAGPipeline

def test_pipeline(pdf_path: str, question: str):
    print(f"\n{'='*60}")
    print(f"Testing with: {pdf_path}")
    print(f"Question: {question}")
    print('='*60)

    embedder = get_embedder("local")
    vector_store = VectorStore(
        persist_directory="../vector_db/chroma_db",
        embedder=embedder
    )
    pipeline = RAGPipeline(
        embedder=embedder,
        vector_store=vector_store,
        llm_provider="gemini",
        llm_api_key=os.getenv("GEMINI_API_KEY")
    )

    # Ingest
    print("\n--- Ingesting PDF ---")
    stats = pipeline.ingest_pdf(pdf_path, session_id="test-session")
    print(f"Pages: {stats['total_pages']}")
    print(f"Chunks: {stats['chunks_created']}")
    print(f"Time: {stats['processing_time_seconds']}s")

    # Query
    print("\n--- Asking Question ---")
    response = pipeline.query(
        question=question,
        session_id="test-session"
    )
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSources:")
    for src in response.sources:
        print(f"  → {src['source_file']} | Page {src['page_number']}")
    print(f"\nTime: {response.processing_time_ms}ms")

if __name__ == "__main__":
    # Change this path to your downloaded PDF
    test_pipeline(
        pdf_path="../data/raw/test/rag_original_paper.pdf",
        question="What is the main idea of retrieval augmented generation?"
    )