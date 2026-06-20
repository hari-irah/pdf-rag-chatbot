# backend/rag/preprocessing.py

import re
import unicodedata
import logging
from dataclasses import dataclass
from typing import Optional
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingConfig:
    """Configuration for text preprocessing pipeline."""
    # Minimum length of text to keep a chunk
    min_text_length: int = 50
    # Remove page numbers pattern
    remove_page_numbers: bool = True
    # Remove URLs
    remove_urls: bool = False  # URLs can be informative
    # Remove email addresses
    remove_emails: bool = False
    # Normalize whitespace
    normalize_whitespace: bool = True
    # Remove repeated punctuation (e.g., "....." -> "...")
    normalize_punctuation: bool = True
    # Language detection
    detect_language: bool = True
    # Languages to keep (None = keep all)
    allowed_languages: Optional[list[str]] = None


class TextPreprocessor:
    """
    Production-grade text preprocessor for RAG pipelines.
    
    Each cleaning step is separate and configurable.
    This makes debugging and testing each step independently easy.
    """

    # Common header/footer patterns in PDFs
    HEADER_FOOTER_PATTERNS = [
        r"^\s*page\s+\d+\s*of\s*\d+\s*$",
        r"^\s*\d+\s*$",  # Standalone page numbers
        r"^\s*confidential\s*$",
        r"^\s*all rights reserved\s*$",
        r"^\s*www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*$",  # URLs as headers
    ]

    # Patterns that indicate noise
    NOISE_PATTERNS = [
        r"\.{4,}",   # Four or more dots (table of contents leaders)
        r"-{3,}",    # Three or more dashes (separator lines)
        r"_{3,}",    # Three or more underscores (separator lines)
        r"={3,}",    # Three or more equals signs
        r"\*{3,}",   # Three or more asterisks
    ]

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        self.config = config or PreprocessingConfig()
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self._header_footer_re = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.HEADER_FOOTER_PATTERNS
        ]
        self._noise_re = [
            re.compile(p)
            for p in self.NOISE_PATTERNS
        ]
        self._url_re = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|"
            r"(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )
        self._email_re = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        self._whitespace_re = re.compile(r"\s+")
        self._multi_newline_re = re.compile(r"\n{3,}")

    def preprocess(self, text: str, source_info: dict = None) -> str:
        """
        Main preprocessing pipeline.
        
        Args:
            text: Raw extracted text
            source_info: Optional dict with filename, page_number for logging
            
        Returns:
            Cleaned, normalized text
        """
        if not text or not text.strip():
            return ""

        source = source_info or {}
        original_length = len(text)

        # Step 1: Unicode normalization (MUST be first)
        text = self._normalize_unicode(text)

        # Step 2: Fix encoding artifacts
        text = self._fix_encoding_artifacts(text)

        # Step 3: Remove headers and footers
        text = self._remove_headers_footers(text)

        # Step 4: Fix hyphenated words split across lines
        text = self._fix_hyphenation(text)

        # Step 5: Remove noise patterns
        text = self._remove_noise(text)

        # Step 6: Normalize URLs/emails
        if self.config.remove_urls:
            text = self._remove_urls(text)
        if self.config.remove_emails:
            text = self._remove_emails(text)

        # Step 7: Normalize whitespace (must be after other cleanups)
        if self.config.normalize_whitespace:
            text = self._normalize_whitespace(text)

        # Step 8: Normalize punctuation
        if self.config.normalize_punctuation:
            text = self._normalize_punctuation(text)

        final_length = len(text)
        reduction = (1 - final_length / original_length) * 100 if original_length > 0 else 0

        logger.debug(
            f"Preprocessing: {original_length} → {final_length} chars "
            f"({reduction:.1f}% reduction) | {source}"
        )

        return text.strip()

    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize unicode characters.
        
        NFC: Canonical decomposition + canonical composition.
        This ensures é is stored as a single character, not e + combining accent.
        """
        text = unicodedata.normalize("NFC", text)
        # Replace common unicode artifacts with ASCII equivalents
        replacements = {
            "\u2018": "'",   # Left single quote
            "\u2019": "'",   # Right single quote
            "\u201c": '"',   # Left double quote
            "\u201d": '"',   # Right double quote
            "\u2013": "-",   # En dash
            "\u2014": "-",   # Em dash
            "\u2026": "...", # Ellipsis
            "\u00a0": " ",   # Non-breaking space
            "\u00ad": "",    # Soft hyphen
            "\ufeff": "",    # BOM (byte order mark)
        }
        for unicode_char, replacement in replacements.items():
            text = text.replace(unicode_char, replacement)
        return text

    def _fix_encoding_artifacts(self, text: str) -> str:
        """Fix common PDF encoding artifacts."""
        # Fix fi, fl ligatures that often break in PDFs
        text = text.replace("ﬁ", "fi")
        text = text.replace("ﬂ", "fl")
        text = text.replace("ﬀ", "ff")
        text = text.replace("ﬃ", "ffi")
        text = text.replace("ﬄ", "ffl")
        # Remove null bytes
        text = text.replace("\x00", "")
        return text

    def _fix_hyphenation(self, text: str) -> str:
        """
        Fix words split with hyphen at end of line.
        
        Example: "infor-\nmation" → "information"
        This is critical because chunking will otherwise split mid-word.
        """
        # Match word-hyphen-newline-word pattern
        return re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    def _remove_headers_footers(self, text: str) -> str:
        """Remove repeating headers and footers."""
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            is_noise = False
            for pattern in self._header_footer_re:
                if pattern.match(stripped):
                    is_noise = True
                    break
            if not is_noise:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _remove_noise(self, text: str) -> str:
        """Remove table-of-contents leaders and separator lines."""
        for pattern in self._noise_re:
            text = pattern.sub("", text)
        return text

    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        return self._url_re.sub("[URL]", text)

    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        return self._email_re.sub("[EMAIL]", text)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph breaks."""
        # Normalize multiple newlines to max 2
        text = self._multi_newline_re.sub("\n\n", text)
        # Normalize spaces within lines
        lines = text.split("\n")
        normalized_lines = []
        for line in lines:
            # Replace multiple spaces with single space within each line
            normalized_line = re.sub(r"[ \t]+", " ", line)
            normalized_lines.append(normalized_line)
        return "\n".join(normalized_lines)

    def _normalize_punctuation(self, text: str) -> str:
        """Normalize repeated punctuation."""
        # Normalize multiple periods (but preserve ellipsis)
        text = re.sub(r"\.{4,}", "...", text)
        # Normalize multiple exclamation/question marks
        text = re.sub(r"!{2,}", "!", text)
        text = re.sub(r"\?{2,}", "?", text)
        return text

    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            lang = detect(text[:1000])  # Use first 1000 chars for speed
            return lang
        except LangDetectException:
            return "unknown"

    def is_meaningful(self, text: str) -> bool:
        """
        Check if text has enough content to be useful for RAG.
        
        Filters out pages that are:
        - Blank or near-blank
        - Only page numbers
        - Only images (no text extracted)
        """
        if len(text.strip()) < self.config.min_text_length:
            return False
        # Check that it's not all numbers/punctuation
        alpha_chars = sum(1 for c in text if c.isalpha())
        if alpha_chars < self.config.min_text_length // 2:
            return False
        return True


# Convenience function for quick use
def preprocess_text(text: str, config: PreprocessingConfig = None) -> str:
    """Convenience function to preprocess a single text string."""
    preprocessor = TextPreprocessor(config)
    return preprocessor.preprocess(text)