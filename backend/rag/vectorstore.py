# backend/rag/vectorstore.py

import logging
import uuid
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings

from .chunking import DocumentChunk
from .embeddings import BaseEmbedder

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB vector store wrapper.
    
    Handles:
    - Storing document chunks + embeddings
    - Similarity search
    - Document management (add, delete, list)
    - Persistence across restarts
    """

    def __init__(
        self,
        persist_directory: str = "./vector_db/chroma_db",
        collection_name: str = "pdf_documents",
        embedder: Optional[BaseEmbedder] = None,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedder = embedder

        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistence
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry for privacy
                allow_reset=True
            )
        )

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",  # Use cosine similarity
                "description": "PDF document chunks for RAG"
            }
        )

        logger.info(
            f"VectorStore initialized | "
            f"Collection: {collection_name} | "
            f"Existing vectors: {self._collection.count()}"
        )

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        session_id: Optional[str] = None,
    ) -> int:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects
            session_id: Optional session identifier for multi-user isolation
            
        Returns:
            Number of chunks added
        """
        if not chunks:
            logger.warning("No chunks provided to add_chunks")
            return 0

        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        texts_to_embed = [chunk.text for chunk in chunks]

        # Generate embeddings in batch (much faster than one at a time)
        if self.embedder:
            logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks...")
            batch_embeddings = self.embedder.embed_batch(texts_to_embed)
        else:
            batch_embeddings = None

        for i, chunk in enumerate(chunks):
            chunk_id = chunk.chunk_id
            if session_id:
                chunk_id = f"{session_id}_{chunk_id}"

            ids.append(chunk_id)
            documents.append(chunk.text)

            metadata = {
                "source_file": chunk.metadata.source_file,
                "page_number": chunk.metadata.page_number,
                "chunk_index": chunk.metadata.chunk_index,
                "token_estimate": chunk.token_estimate,
            }
            if chunk.metadata.section_title:
                metadata["section_title"] = chunk.metadata.section_title
            if session_id:
                metadata["session_id"] = session_id

            metadatas.append(metadata)

            if batch_embeddings:
                embeddings.append(batch_embeddings[i])

        # Add to ChromaDB
        # Handle deduplication: use upsert to avoid duplicate ID errors
        add_kwargs = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        if embeddings:
            add_kwargs["embeddings"] = embeddings

        self._collection.upsert(**add_kwargs)

        logger.info(f"Added {len(chunks)} chunks to vector store")
        return len(chunks)

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
        source_file: Optional[str] = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """
        Find the most relevant chunks for a query.
        
        Args:
            query: User's question
            top_k: Number of results to return
            session_id: Filter by session (multi-user isolation)
            source_file: Filter by specific document
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of dicts with text, metadata, and similarity score
        """
        # Build filter
        where_filter = {}
        if session_id and source_file:
            where_filter = {
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"source_file": {"$eq": source_file}}
                ]
            }
        elif session_id:
            where_filter = {"session_id": {"$eq": session_id}}
        elif source_file:
            where_filter = {"source_file": {"$eq": source_file}}

        # Generate query embedding
        if self.embedder:
            query_embedding = self.embedder.embed_text(query)
            query_kwargs = {"query_embeddings": [query_embedding]}
        else:
            # Let ChromaDB handle embedding (requires embedding function configured)
            query_kwargs = {"query_texts": [query]}

        # Perform search
        results = self._collection.query(
            **query_kwargs,
            n_results=min(top_k, max(1, self._collection.count())),
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                # ChromaDB returns distance (lower = more similar)
                # Convert to similarity score (higher = more similar)
                similarity = 1 - distance

                if similarity >= min_score:
                    formatted_results.append({
                        "text": doc,
                        "metadata": meta,
                        "similarity_score": round(similarity, 4),
                        "source_file": meta.get("source_file", "Unknown"),
                        "page_number": meta.get("page_number", 0),
                        "section_title": meta.get("section_title"),
                    })

                # DEBUG: show what was actually compared
        logger.info(f"Where filter used: {where_filter}")
        logger.info(f"Raw results count: {len(results['documents'][0]) if results['documents'] else 0}")
        if results["distances"] and results["distances"][0]:
            logger.info(f"Distances: {results['distances'][0][:5]}")

        logger.info(
            f"Similarity search: '{query[:50]}...' → {len(formatted_results)} results"
        )

        return formatted_results

    def delete_document(
        self,
        source_file: str,
        session_id: Optional[str] = None
    ) -> int:
        """Delete all chunks belonging to a specific document."""
        where_filter = {"source_file": {"$eq": source_file}}
        if session_id:
            where_filter = {
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"source_file": {"$eq": source_file}}
                ]
            }

        # Get IDs to delete
        results = self._collection.get(
            where=where_filter,
            include=[]
        )
        ids_to_delete = results["ids"]

        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} chunks for '{source_file}'")

        return len(ids_to_delete)

    def list_documents(self, session_id: Optional[str] = None) -> list[str]:
        """Get list of unique document names in the store."""
        where_filter = {}
        if session_id:
            where_filter = {"session_id": {"$eq": session_id}}

        results = self._collection.get(
            where=where_filter if where_filter else None,
            include=["metadatas"]
        )

        # Extract unique source files
        sources = set()
        for meta in results["metadatas"]:
            if meta.get("source_file"):
                sources.add(meta["source_file"])

        return sorted(list(sources))

    def get_collection_stats(self) -> dict:
        """Return statistics about the vector store."""
        return {
            "total_vectors": self._collection.count(),
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
        }