# backend/routes/chat.py

import logging
from flask import Blueprint, request, jsonify
from routes.upload import get_pipeline          # ← get from upload, not local
from rag.models import ConversationMessage

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)

_conversation_store: dict = {}


@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    question   = data.get("question", "").strip()
    session_id = data.get("session_id") or request.headers.get("X-Session-ID")
    source_filter = data.get("source_filter")

    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    if len(question) > 2000:
        return jsonify({"error": "Question too long. Maximum 2000 characters"}), 400

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    try:
        pipeline = get_pipeline()
        history  = _conversation_store.get(session_id, [])

        response = pipeline.query(
            question=question,
            session_id=session_id,
            conversation_history=history,
            source_filter=source_filter,
        )

        history.append(ConversationMessage(role="user",      content=question))
        history.append(ConversationMessage(role="assistant", content=response.answer))

        if len(history) > 20:
            history = history[-20:]
        _conversation_store[session_id] = history

        return jsonify({
            "answer":            response.answer,
            "sources":           response.sources,
            "processing_time_ms": response.processing_time_ms,
            "retrieved_chunks":  response.retrieved_chunks_count,
            "model":             response.model_used,
        }), 200

    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        return jsonify({"error": "AI generation failed", "detail": str(e)}), 503

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500