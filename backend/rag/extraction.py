# backend/rag/extraction.py

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import re

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Structured representation of a single PDF page."""
    page_number: int
    text: str
    tables: list[list] = field(default_factory=list)
    images_count: int = 0
    char_count: int = 0
    extraction_method: str = "pymupdf"

    def __post_init__(self):
        self.char_count = len(self.text)


@dataclass
class DocumentContent:
    """Complete extracted content from a PDF."""
    filename: str
    total_pages: int
    pages: list[PageContent]
    metadata: dict
    total_chars: int = 0
    extraction_errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.total_chars = sum(p.char_count for p in self.pages)

    def get_full_text(self) -> str:
        """Concatenate all pages with page markers."""
        parts = []
        for page in self.pages:
            parts.append(f"\n--- Page {page.page_number} ---\n{page.text}")
        return "\n".join(parts)


class PDFExtractor:
    """
    Production-grade PDF text extractor.
    
    Strategy:
    1. Try PyMuPDF (fast, accurate for digital PDFs)
    2. Fall back to pdfplumber (better for complex layouts)
    3. Fall back to OCR (for scanned PDFs)
    """

    # Minimum characters to consider a page "text-rich"
    # Below this threshold, we assume the page is scanned
    MIN_CHARS_THRESHOLD = 50

    def __init__(
        self,
        enable_ocr: bool = True,
        ocr_language: str = "eng",
        extract_tables: bool = True,
        max_pages: Optional[int] = None
    ):
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.extract_tables = extract_tables
        self.max_pages = max_pages

        if enable_ocr:
            self._check_ocr_availability()

    def _check_ocr_availability(self):
        """Verify tesseract is installed and accessible."""
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            logger.warning(
                "Tesseract OCR not found. OCR fallback will be disabled. "
                "Install tesseract-ocr for scanned PDF support."
            )
            self.enable_ocr = False

    def extract(self, pdf_path: str) -> DocumentContent:
        """
        Main extraction method.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentContent with all extracted information
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        if not path.suffix.lower() == ".pdf":
            raise ValueError(f"File is not a PDF: {pdf_path}")

        logger.info(f"Starting extraction: {path.name}")

        # Extract metadata and pages using PyMuPDF
        doc = fitz.open(pdf_path)
        metadata = self._extract_metadata(doc)
        total_pages = len(doc)
        pages_to_process = (
            min(self.max_pages, total_pages)
            if self.max_pages
            else total_pages
        )

        pages = []
        errors = []

        for page_num in range(pages_to_process):
            try:
                page_content = self._extract_page(
                    doc, pdf_path, page_num + 1
                )
                pages.append(page_content)
            except Exception as e:
                error_msg = f"Error on page {page_num + 1}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                # Add empty page to maintain page numbering
                pages.append(PageContent(
                    page_number=page_num + 1,
                    text="[Error: Could not extract this page]"
                ))

        doc.close()

        document = DocumentContent(
            filename=path.name,
            total_pages=total_pages,
            pages=pages,
            metadata=metadata,
            extraction_errors=errors
        )

        logger.info(
            f"Extraction complete: {path.name} | "
            f"Pages: {len(pages)} | "
            f"Total chars: {document.total_chars} | "
            f"Errors: {len(errors)}"
        )

        return document

    def _extract_page(
        self,
        doc: fitz.Document,
        pdf_path: str,
        page_number: int
    ) -> PageContent:
        """Extract content from a single page."""
        page = doc[page_number - 1]

        # Attempt 1: PyMuPDF direct text extraction
        text = page.get_text("text")
        text = text.strip()

        tables = []
        extraction_method = "pymupdf"

        # Check if the page has meaningful text
        if len(text) < self.MIN_CHARS_THRESHOLD:
            # Attempt 2: Try pdfplumber for complex layouts
            text_plumber = self._extract_with_pdfplumber(
                pdf_path, page_number
            )
            if len(text_plumber) > len(text):
                text = text_plumber
                extraction_method = "pdfplumber"

        # If still minimal text, try OCR
        if len(text) < self.MIN_CHARS_THRESHOLD and self.enable_ocr:
            text = self._extract_with_ocr(page)
            extraction_method = "ocr"

        # Extract tables if enabled
        if self.extract_tables:
            tables = self._extract_tables_from_page(pdf_path, page_number)

        # Get image count
        images_count = len(page.get_images())

        return PageContent(
            page_number=page_number,
            text=text,
            tables=tables,
            images_count=images_count,
            extraction_method=extraction_method
        )

    def _extract_with_pdfplumber(
        self, pdf_path: str, page_number: int
    ) -> str:
        """Use pdfplumber as fallback extractor."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_number - 1]
                text = page.extract_text() or ""
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed on page {page_number}: {e}")
            return ""

    def _extract_with_ocr(self, page: fitz.Page) -> str:
        """Convert page to image and apply OCR."""
        try:
            # Render page at 300 DPI for good OCR quality
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))

            # Apply OCR
            text = pytesseract.image_to_string(
                img,
                lang=self.ocr_language,
                config="--psm 6"  # Assume uniform text block
            )
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    def _extract_tables_from_page(
        self, pdf_path: str, page_number: int
    ) -> list[list]:
        """Extract tables using pdfplumber."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_number - 1]
                tables = page.extract_tables()
                return tables or []
        except Exception as e:
            logger.warning(f"Table extraction failed on page {page_number}: {e}")
            return []

    def _extract_metadata(self, doc: fitz.Document) -> dict:
        """Extract PDF metadata."""
        metadata = doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(doc),
            "encrypted": doc.is_encrypted,
        }