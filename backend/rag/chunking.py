# backend/rag/chunking.py

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    HYBRID = "hybrid"


@dataclass
class ChunkMetadata:
    """Metadata attached to each chunk for retrieval and citation."""
    source_file: str
    page_number: int
    chunk_index: int
    total_chunks_in_doc: int
    start_char: int
    end_char: int
    extraction_method: str = "unknown"
    section_title: Optional[str] = None


@dataclass
class DocumentChunk:
    """A single chunk of text with metadata."""
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    token_estimate: int = 0

    def __post_init__(self):
        # Rough token estimate: ~4 chars per token
        self.token_estimate = len(self.text) // 4

    def to_dict(self) -> dict:
        """Serialize for storage in vector database."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.metadata.source_file,
            "page_number": self.metadata.page_number,
            "chunk_index": self.metadata.chunk_index,
            "section_title": self.metadata.section_title,
            "token_estimate": self.token_estimate,
        }


class RecursiveChunker:
    """
    Recursive character text splitter — the industry-standard choice.
    
    Algorithm:
    1. Try to split on double newlines (paragraphs)
    2. If chunks still too large, split on single newlines
    3. If still too large, split on sentence boundaries (. ! ?)
    4. If still too large, split on spaces (words)
    5. If still too large, split on characters (last resort)
    
    The overlap ensures continuity between chunks.
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[list[str]] = None,
        min_chunk_size: int = 100,
    ):
        """
        Args:
            chunk_size: Target maximum characters per chunk
            chunk_overlap: Characters to overlap between consecutive chunks
            separators: Custom split hierarchy
            min_chunk_size: Discard chunks smaller than this
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS
        self.min_chunk_size = min_chunk_size

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks using recursive strategy."""
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text, trying each separator in order."""
        chunks = []

        # Find the best separator that applies to this text
        separator = separators[-1]  # Default: character split
        for sep in separators:
            if sep == "" or sep in text:
                separator = sep
                break

        # Split the text
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # Merge splits back into proper-sized chunks
        current_chunk = []
        current_length = 0

        for split in splits:
            split_length = len(split)

            if current_length + split_length + len(separator) > self.chunk_size:
                # Current chunk would exceed size limit
                if current_chunk:
                    # Save current chunk
                    chunk_text = separator.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)

                    # Implement overlap: keep last portion
                    # Roll back to maintain overlap
                    overlap_text = chunk_text[-self.chunk_overlap:]
                    overlap_splits = self._find_overlap_splits(
                        overlap_text, separator
                    )
                    current_chunk = overlap_splits
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0

                # If split itself exceeds chunk size, recurse
                if split_length > self.chunk_size:
                    next_separators = separators[separators.index(separator) + 1:]
                    if next_separators:
                        sub_chunks = self._split_recursive(split, next_separators)
                        chunks.extend(sub_chunks)
                    else:
                        # Hard character split as last resort
                        for i in range(0, split_length, self.chunk_size - self.chunk_overlap):
                            chunks.append(split[i:i + self.chunk_size])
                    continue

            current_chunk.append(split)
            current_length += split_length + len(separator)

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = separator.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks

    def _find_overlap_splits(
        self, overlap_text: str, separator: str
    ) -> list[str]:
        """Find splits to keep for the overlap portion."""
        if not separator or separator not in overlap_text:
            return [overlap_text] if overlap_text else []
        splits = overlap_text.split(separator)
        # Only keep splits that form a meaningful start
        return [s for s in splits if s.strip()]


class DocumentChunker:
    """
    High-level chunker that processes full DocumentContent objects
    and produces DocumentChunk objects with rich metadata.
    """

    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._chunker = RecursiveChunker(chunk_size, chunk_overlap)

    def chunk_document(
        self,
        pages: list,  # List of PageContent from extraction
        filename: str,
    ) -> list[DocumentChunk]:
        """
        Convert extracted PDF pages into indexed, metadata-rich chunks.
        
        Args:
            pages: List of PageContent objects
            filename: Source PDF filename
            
        Returns:
            List of DocumentChunk objects ready for embedding
        """
        all_chunks = []
        chunk_index = 0

        for page in pages:
            if not page.text.strip():
                continue

            # Detect section title if present (first line that looks like a header)
            section_title = self._detect_section_title(page.text)

            # Split page text into chunks
            text_chunks = self._chunker.split_text(page.text)

            for local_idx, chunk_text in enumerate(text_chunks):
                if not chunk_text.strip():
                    continue

                chunk_id = f"{filename}_p{page.page_number}_c{chunk_index}"

                metadata = ChunkMetadata(
                    source_file=filename,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    total_chunks_in_doc=0,  # Updated after all chunks created
                    start_char=local_idx * self.chunk_size,
                    end_char=(local_idx + 1) * self.chunk_size,
                    section_title=section_title,
                )

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=metadata,
                )
                all_chunks.append(chunk)
                chunk_index += 1

        # Update total_chunks_in_doc now that we know the count
        total = len(all_chunks)
        for chunk in all_chunks:
            chunk.metadata.total_chunks_in_doc = total

        logger.info(
            f"Chunked '{filename}': {len(pages)} pages → {total} chunks | "
            f"Avg chunk size: {sum(len(c.text) for c in all_chunks) // max(total, 1)} chars"
        )

        return all_chunks

    def _detect_section_title(self, text: str) -> Optional[str]:
        """
        Heuristically detect if the first line is a section title.
        
        Indicators: ALL CAPS, short line, ends without period,
        numbered (e.g., "1.2 Introduction")
        """
        lines = text.strip().split("\n")
        if not lines:
            return None

        first_line = lines[0].strip()

        # Skip if too long (titles are usually short)
        if len(first_line) > 100:
            return None

        # Check if it looks like a title
        is_all_caps = first_line == first_line.upper() and len(first_line) > 3
        is_numbered = bool(re.match(r"^\d+[\.\d]*\s+\w+", first_line))
        ends_without_period = not first_line.endswith(".")
        is_short = len(first_line.split()) <= 10

        if (is_all_caps or is_numbered) and ends_without_period and is_short:
            return first_line

        return None