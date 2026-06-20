# backend/routes/history.py

import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)
history_bp = Blueprint("history", __name__)

# In-memory store — same one used by chat.py
# Import it from chat so both share the same dictionary
def get_conversation_store():
    """Lazy import to avoid circular imports."""
    from routes.chat import _conversation_store
    return _conversation_store


@history_bp.route("/history/<session_id>", methods=["GET"])
def get_history(session_id: str):
    """
    GET /api/history/:session_id
    Returns full conversation history for a session.
    """
    try:
        store = get_conversation_store()
        history = store.get(session_id, [])

        return jsonify({
            "session_id": session_id,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in history
            ],
            "total_messages": len(history),
        }), 200

    except Exception as e:
        logger.error(f"Error fetching history for {session_id}: {e}")
        return jsonify({"error": "Could not fetch history"}), 500


@history_bp.route("/history/<session_id>", methods=["DELETE"])
def clear_history(session_id: str):
    """
    DELETE /api/history/:session_id
    Clears conversation history for a session.
    """
    try:
        store = get_conversation_store()
        if session_id in store:
            del store[session_id]
            message = "History cleared successfully"
        else:
            message = "No history found for this session"

        return jsonify({
            "message": message,
            "session_id": session_id,
        }), 200

    except Exception as e:
        logger.error(f"Error clearing history for {session_id}: {e}")
        return jsonify({"error": "Could not clear history"}), 500