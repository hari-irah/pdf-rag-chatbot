# backend/list_models.py

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from google import genai

api_key = os.getenv("GEMINI_API_KEY")
print("Key found:", "YES" if api_key else "NO")

client = genai.Client(api_key=api_key)

print("\nAvailable models:\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", "n/a")
    print(f"{m.name}  |  actions: {actions}")