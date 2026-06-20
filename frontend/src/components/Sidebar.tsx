// frontend/src/components/Sidebar.tsx

import { useState } from "react";
import type { Document } from "../types";

interface Props {
  documents: Document[];
  onRemoveDocument: (filename: string) => void;
  onAddMore: () => void;
}

export function Sidebar({ documents, onRemoveDocument, onAddMore }: Props) {
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleRemove = (filename: string) => {
    if (confirmDelete === filename) {
      onRemoveDocument(filename);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(filename);
      setTimeout(() => setConfirmDelete(null), 3000);
    }
  };

  return (
    <aside className="w-72 flex flex-col bg-ink-900 border-r border-ink-700 h-full shrink-0">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-ink-700 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d98e3a" strokeWidth="1.8">
            <path d="M14 3v5a1 1 0 0 0 1 1h5" />
            <path d="M5 4a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z" />
          </svg>
        </div>
        <div>
          <h1 className="font-display text-base font-semibold text-paper-50 leading-none">
            Inkwell
          </h1>
          <p className="text-[11px] text-ink-400 mt-1">RAG document chat</p>
        </div>
      </div>

      {/* Add button */}
      <div className="px-4 pt-4">
        <button
          onClick={onAddMore}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5
                     bg-amber-500 hover:bg-amber-600 active:scale-[0.98]
                     text-ink-950 text-sm font-semibold rounded-xl
                     transition-all duration-150"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add documents
        </button>
      </div>

      {/* Document shelf */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <p className="text-[11px] font-semibold text-ink-400 uppercase tracking-wider mb-3 px-1">
          On the shelf · {documents.length}
        </p>

        {documents.length === 0 ? (
          <div className="text-center py-10 px-3">
            <p className="text-ink-600 text-xs">No documents yet</p>
          </div>
        ) : (
          <ul className="space-y-1.5">
            {documents.map((doc) => (
              <li
                key={doc.filename}
                className="group flex items-start gap-2.5 px-3 py-2.5 rounded-xl
                           bg-ink-800/60 hover:bg-ink-800 border border-transparent
                           hover:border-ink-600 transition-all duration-150"
              >
                <div className="w-7 h-7 rounded-md bg-teal-500/10 border border-teal-500/25 flex items-center justify-center shrink-0 mt-0.5">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#5e8b7e" strokeWidth="2">
                    <path d="M14 3v5a1 1 0 0 0 1 1h5" />
                    <path d="M5 4a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z" />
                  </svg>
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-paper-100 truncate">
                    {doc.filename}
                  </p>
                  <p className="text-[11px] text-ink-400 mt-0.5 font-mono">
                    {doc.pages}p · {doc.chunks} chunks
                  </p>
                </div>

                <button
                  onClick={() => handleRemove(doc.filename)}
                  className={`shrink-0 text-[10px] font-medium px-1.5 py-1 rounded-md
                              transition-colors duration-150
                              ${
                                confirmDelete === doc.filename
                                  ? "bg-red-500 text-white"
                                  : "text-ink-600 hover:text-red-400 opacity-0 group-hover:opacity-100"
                              }`}
                >
                  {confirmDelete === doc.filename ? "sure?" : "✕"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}