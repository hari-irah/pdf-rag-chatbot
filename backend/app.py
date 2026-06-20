# backend/app.py

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

print(f"Loading .env from: {env_path}")
print(f"GEMINI_API_KEY found: {'YES' if os.getenv('GEMINI_API_KEY') else 'NO'}")

load_dotenv()
# DEBUG — remove after confirming
import logging
print("GEMINI_API_KEY loaded:", "YES" if os.getenv("GEMINI_API_KEY") else "NO")
print("Key starts with:", os.getenv("GEMINI_API_KEY", "")[:8])

from utils.logger import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["UPLOAD_FOLDER"]      = os.getenv("UPLOAD_FOLDER", "./data/raw")
    app.config["VECTOR_DB_PATH"]     = os.getenv("VECTOR_DB_PATH", "./vector_db/chroma_db")
    app.config["GEMINI_API_KEY"]     = os.getenv("GEMINI_API_KEY")
    app.config["EMBEDDING_PROVIDER"] = os.getenv("EMBEDDING_PROVIDER", "local")

    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:3000",
                os.getenv("FRONTEND_URL", ""),
            ],
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Session-ID"],
        }
    })

    # Register blueprints
    from routes.upload    import upload_bp
    from routes.chat      import chat_bp
    from routes.documents import documents_bp
    from routes.history   import history_bp

    app.register_blueprint(upload_bp,    url_prefix="/api")
    app.register_blueprint(chat_bp,      url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")
    app.register_blueprint(history_bp,   url_prefix="/api")

    # Create directories
    os.makedirs(app.config["UPLOAD_FOLDER"],  exist_ok=True)
    os.makedirs(app.config["VECTOR_DB_PATH"], exist_ok=True)

    # ✅ Pre-load the embedding model NOW (at startup, not on first request)
    from routes.upload import init_pipeline
    init_pipeline(app)

    logger.info("Flask application ready.")
    return app


app = create_app()

if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)