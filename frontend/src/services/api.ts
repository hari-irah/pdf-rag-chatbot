// frontend/src/services/api.ts

import axios from "axios";
import type { UploadResponse, ChatResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s for LLM responses
});

// Inject session ID into every request
apiClient.interceptors.request.use((config) => {
  const sessionId = localStorage.getItem("session_id");
  if (sessionId) {
    config.headers["X-Session-ID"] = sessionId;
  }
  return config;
});

export const uploadPDFs = async (files: File[]): Promise<UploadResponse> => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await apiClient.post<UploadResponse>("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const sendMessage = async (
  question: string,
  sessionId: string,
  sourceFilter?: string
): Promise<ChatResponse> => {
  const response = await apiClient.post<ChatResponse>("/chat", {
    question,
    session_id: sessionId,
    source_filter: sourceFilter,
  });
  return response.data;
};

export const getDocuments = async (sessionId: string) => {
  const response = await apiClient.get(`/documents?session_id=${sessionId}`);
  return response.data;
};

export const deleteDocument = async (filename: string, sessionId: string) => {
  const response = await apiClient.delete(
    `/documents/${encodeURIComponent(filename)}?session_id=${sessionId}`
  );
  return response.data;
};

export const clearHistory = async (sessionId: string) => {
  const response = await apiClient.delete(`/history/${sessionId}`);
  return response.data;
};