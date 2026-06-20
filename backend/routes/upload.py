# backend/routes/upload.py

import os
import uuid
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from utils.file_validator import validate_pdf_file

logger = logging.getLogger(__name__)
upload_bp = Blueprint("upload", __name__)

# Global pipeline — loaded ONCE when server starts, reused for every request
_pipeline = None


def init_pipeline(app):
    """
    Call this ONCE at app startup to pre-load the embedding model.
    This prevents the 20-second delay on the first upload request.
    """
    global _pipeline
    with app.app_context():
        logger.info("Initializing RAG pipeline at startup...")

        from rag.embeddings import get_embedder
        from rag.vectorstore import VectorStore
        from rag.pipeline import RAGPipeline

        embedder = get_embedder(
            app.config.get("EMBEDDING_PROVIDER", "local")
        )

        vector_store = VectorStore(
            persist_directory=app.config["VECTOR_DB_PATH"],
            embedder=embedder,
        )

        _pipeline = RAGPipeline(
            embedder=embedder,
            vector_store=vector_store,
            llm_provider="gemini",
            llm_api_key=app.config.get("GEMINI_API_KEY"),
        )

        logger.info("RAG pipeline ready.")


def get_pipeline():
    """Return the already-initialized pipeline."""
    if _pipeline is None:
        raise RuntimeError(
            "Pipeline not initialized. "
            "Make sure init_pipeline() was called at startup."
        )
    return _pipeline


@upload_bp.route("/upload", methods=["POST"])
def upload_pdf():
    """
    POST /api/upload
    Accepts multipart/form-data with 'files' field.
    """
    session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())

    if "files" not in request.files:
        return jsonify({
            "error": "No files provided",
            "detail": "Include PDF files in the 'files' field"
        }), 400

    files = request.files.getlist("files")

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected"}), 400

    if len(files) > 10:
        return jsonify({
            "error": "Too many files",
            "detail": "Maximum 10 files per upload"
        }), 400

    pipeline = get_pipeline()
    results = []
    errors = []

    for file in files:
        if file.filename == "":
            continue

        filename = secure_filename(file.filename)

        # Validate file
        validation_error = validate_pdf_file(file)
        if validation_error:
            errors.append({"filename": filename, "error": validation_error})
            continue

        try:
            # Save file to disk
            upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / session_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / filename
            file.save(str(file_path))

            logger.info(f"Saved file: {file_path}")

            # Run ingestion pipeline
            stats = pipeline.ingest_pdf(str(file_path), session_id=session_id)
            results.append(stats)

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}", exc_info=True)
            errors.append({"filename": filename, "error": str(e)})

    if not results and errors:
        return jsonify({
            "error": "All files failed to process",
            "errors": errors
        }), 400

    return jsonify({
        "session_id": session_id,
        "documents": results,
        "total_processed": len(results),
        "errors": errors,
    }), 200