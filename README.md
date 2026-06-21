# 🤖 AI-Powered PDF Chatbot using RAG

> Ask questions about your PDF documents using natural language. 
> Built with Retrieval-Augmented Generation (RAG), Python, Flask, and React.

![Demo](docs/demo.gif)

## ✨ Features

- 📄 Upload multiple PDF documents
- 💬 Ask natural language questions across all documents
- 📍 Get answers with exact page number citations
- 🧠 Maintains conversation history for follow-up questions
- 🌙 Dark mode + mobile responsive UI
- ⚡ Fast semantic search using vector embeddings

## 🏗️ Architecture

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Tailwind CSS |
| Backend | Python, Flask |
| AI/ML | Google Gemini, sentence-transformers |
| Vector DB | ChromaDB |
| PDF Processing | PyMuPDF, pdfplumber |
| Deployment | Vercel (frontend), Render (backend) |

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-rag-chatbot

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
python app.py

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

## 📊 RAG Pipeline

[diagram here]

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| GEMINI_API_KEY | Google Gemini API key | Yes |
| EMBEDDING_PROVIDER | local or gemini | No (default: local) |

## 📝 License
MIT
