// frontend/src/types/index.ts

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  processingTimeMs?: number;
  timestamp: Date;
}

export interface Source {
  source_file: string;
  page_number: number;
  section_title?: string;
  relevance_score: number;
  preview: string;
}

export interface Document {
  filename: string;
  pages: number;
  chunks: number;
  processing_time: number;
}

export interface UploadResponse {
  session_id: string;
  documents: Document[];
  errors: Array<{ filename: string; error: string }>;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  processing_time_ms: number;
}