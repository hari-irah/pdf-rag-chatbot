// frontend/src/hooks/useDocuments.ts

import { useState } from "react";
import type { Document } from "../types";

export function useDocuments(sessionId: string | null) {
  const [documents, setDocuments] = useState<Document[]>([]);

  const addDocuments = (docs: Document[]) => {
    setDocuments((prev) => {
      // Avoid duplicates — replace if filename already exists
      const existingNames = new Set(prev.map((d) => d.filename));
      const newDocs = docs.filter((d) => !existingNames.has(d.filename));
      return [...prev, ...newDocs];
    });
  };

  const removeDocument = (filename: string) => {
    setDocuments((prev) => prev.filter((d) => d.filename !== filename));
  };

  const clearDocuments = () => {
    setDocuments([]);
  };

  return { documents, addDocuments, removeDocument, clearDocuments };
}