# backend/utils/file_validator.py

from werkzeug.datastructures import FileStorage

ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_pdf_file(file: FileStorage) -> str | None:
    """
    Validate an uploaded file.
    Returns error message string if invalid, None if valid.
    """
    # Check extension
    if not file.filename.lower().endswith(".pdf"):
        return "File must have .pdf extension"

    # Check MIME type (if provided)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        return f"Invalid file type: {file.content_type}. Only PDF files are allowed."

    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)     # Reset to beginning

    if file_size == 0:
        return "File is empty"

    if file_size > MAX_FILE_SIZE:
        return f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum is 50MB."

    # Check PDF magic bytes
    header = file.read(4)
    file.seek(0)
    if header != b"%PDF":
        return "File does not appear to be a valid PDF"

    return None  # Valid