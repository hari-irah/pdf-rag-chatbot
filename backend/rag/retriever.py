# backend/rag/retriever.py

import logging
from typing import Optional
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """
    Handles similarity search and result ranking.
    
    Advanced features:
    - MMR (Maximal Marginal Relevance) to reduce redundancy
    - Score filtering
    - Metadata-based filtering
    """

    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 5,
        min_similarity_score: float = 0.0,
    ):
        self.vector_store = vector_store
        self.top_k = top_k
        self.min_similarity_score = min_similarity_score

    def retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.
        
        Retrieves top_k * 2 candidates, then applies MMR
        to select the final top_k with diversity.
        """
        # Get more candidates than needed for MMR to work with
        candidates = self.vector_store.similarity_search(
            query=query,
            top_k=self.top_k * 2,
            session_id=session_id,
            source_file=source_file,
            min_score=self.min_similarity_score,
        )

        if not candidates:
            logger.warning(f"No relevant chunks found for: '{query[:50]}'")
            return []

        # Apply MMR for diversity (avoid returning very similar chunks)
        selected = self._maximal_marginal_relevance(candidates, self.top_k)

        logger.info(
            f"Retrieved {len(selected)} chunks | "
            f"Best score: {selected[0]['similarity_score']:.3f}"
        )

        return selected

    def _maximal_marginal_relevance(
        self,
        candidates: list[dict],
        k: int,
        lambda_mult: float = 0.7,
    ) -> list[dict]:
        """
        Select k diverse results using Maximal Marginal Relevance.
        
        MMR balances relevance and diversity:
        - lambda_mult=1.0: Pure relevance (no diversity)
        - lambda_mult=0.0: Pure diversity (no relevance)
        - lambda_mult=0.7: Good balance (industry default)
        
        This prevents the retriever from returning 5 nearly-identical chunks.
        """
        if len(candidates) <= k:
            return candidates

        selected = [candidates[0]]  # Always include most relevant
        remaining = candidates[1:]

        while len(selected) < k and remaining:
            best_score = -float("inf")
            best_candidate = None
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # Relevance score
                relevance = candidate["similarity_score"]

                # Redundancy: max similarity to already selected chunks
                # (simple text overlap as proxy when we don't have embeddings)
                max_redundancy = max(
                    self._text_overlap(candidate["text"], sel["text"])
                    for sel in selected
                )

                # MMR score
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_redundancy

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate
                    best_idx = i

            selected.append(best_candidate)
            remaining.pop(best_idx)

        return selected

    def _text_overlap(self, text1: str, text2: str) -> float:
        """Simple word overlap similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)