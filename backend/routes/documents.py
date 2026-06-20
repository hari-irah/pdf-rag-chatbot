# backend/routes/documents.py

import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from routes.upload import get_pipeline          # ← get from upload

logger = logging.getLogger(__name__)
documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/documents", methods=["GET"])
def list_documents():
    session_id = request.args.get("session_id") or request.headers.get("X-Session-ID")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    pipeline  = get_pipeline()
    documents = pipeline.vector_store.list_documents(session_id=session_id)
    stats     = pipeline.vector_store.get_collection_stats()

    return jsonify({
        "session_id":        session_id,
        "documents":         documents,
        "total_documents":   len(documents),
        "vector_store_stats": stats,
    }), 200


@documents_bp.route("/documents/<filename>", methods=["DELETE"])
def delete_document(filename: str):
    session_id = request.args.get("session_id") or request.headers.get("X-Session-ID")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    pipeline      = get_pipeline()
    deleted_count = pipeline.vector_store.delete_document(
        source_file=filename,
        session_id=session_id,
    )

    file_path = (
        Path(current_app.config["UPLOAD_FOLDER"]) / session_id / filename
    )
    if file_path.exists():
        file_path.unlink()

    return jsonify({
        "message":       f"Deleted '{filename}'",
        "chunks_removed": deleted_count,
    }), 200