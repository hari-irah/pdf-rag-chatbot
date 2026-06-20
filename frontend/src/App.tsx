// frontend/src/App.tsx

import { useState } from "react";
import { FileUpload } from "./components/FileUpload";
import { ChatInterface } from "./components/ChatInterface";
import { Sidebar } from "./components/Sidebar";
import { useDocuments } from "./hooks/useDocuments";
import type { Document } from "./types";

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(
    localStorage.getItem("session_id")
  );
  const [showUpload, setShowUpload] = useState(
    !localStorage.getItem("session_id")
  );

  const { documents, addDocuments, removeDocument } = useDocuments(sessionId);

  const handleUploadComplete = (newSessionId: string, docs: Document[]) => {
    localStorage.setItem("session_id", newSessionId);
    setSessionId(newSessionId);
    addDocuments(docs);
    setShowUpload(false);
  };

  const handleRemoveDocument = (filename: string) => {
    removeDocument(filename);
    if (documents.length <= 1) {
      localStorage.removeItem("session_id");
      setSessionId(null);
      setShowUpload(true);
    }
  };

  return (
    <div className="flex h-screen bg-ink-950 text-paper-100 overflow-hidden">
      {sessionId && !showUpload && (
        <Sidebar
          documents={documents}
          onRemoveDocument={handleRemoveDocument}
          onAddMore={() => setShowUpload(true)}
        />
      )}

      <main className="flex-1 flex flex-col overflow-hidden relative">
        {showUpload || !sessionId ? (
          <FileUpload onUploadComplete={handleUploadComplete} />
        ) : (
          <ChatInterface sessionId={sessionId!} />
        )}
      </main>
    </div>
  );
}