# backend/rag/prompt_builder.py

from .models import ConversationMessage   # ← changed this line


class PromptBuilder:
    """
    Builds structured prompts for the RAG pipeline.
    """

    SYSTEM_PROMPT = """You are an intelligent PDF assistant. Your role is to answer questions 
based EXCLUSIVELY on the document excerpts provided below. 

CRITICAL RULES:
1. ONLY use information from the provided context. Do NOT use external knowledge.
2. If the answer is not in the context, say: "The provided documents don't contain information about this topic."
3. Always cite your sources using the format: [Source: filename, Page X]
4. Be concise and precise. Prefer bullet points for lists.
5. If multiple documents contain relevant information, synthesize them coherently.
6. Do not make up page numbers or information.

Context from documents:
{context}

Conversation history:
{history}

Question: {question}

Answer (with citations):"""

    def build(
        self,
        question: str,
        retrieved_chunks: list,
        conversation_history: list = None,
        max_context_chars: int = 4000,
    ) -> str:
        """Build the complete prompt."""
        context = self._build_context(retrieved_chunks, max_context_chars)
        history = self._build_history(conversation_history or [])

        return self.SYSTEM_PROMPT.format(
            context=context,
            history=history,
            question=question,
        )

    def _build_context(self, chunks: list, max_chars: int) -> str:
        """Format retrieved chunks as numbered context blocks."""
        context_parts = []
        total_chars = 0

        for i, chunk in enumerate(chunks, 1):
            chunk_text = (
                f"[Excerpt {i}] "
                f"Source: {chunk['source_file']}, "
                f"Page {chunk['page_number']}\n"
                f"{chunk['text']}\n"
            )

            if total_chars + len(chunk_text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(chunk_text[:remaining] + "...[truncated]")
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n---\n".join(context_parts) if context_parts else "No relevant context found."

    def _build_history(self, history: list, max_turns: int = 5) -> str:
        """Format conversation history, keeping only recent turns."""
        if not history:
            return "No previous conversation."

        recent_history = history[-(max_turns * 2):]
        parts = []
        for msg in recent_history:
            role = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{role}: {msg.content}")

        return "\n".join(parts)