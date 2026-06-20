// frontend/src/components/ChatMessage.tsx

import { useState } from "react";
import type { Message } from "../types";

interface Props {
  message: Message;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

  return (
    <div className={`flex gap-3 animate-fade-up ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-[11px] font-semibold
          ${isUser ? "bg-amber-500 text-ink-950" : "bg-teal-500/15 border border-teal-500/30 text-teal-500"}`}
      >
        {isUser ? "Y" : "AI"}
      </div>

      <div className={`max-w-[75%] space-y-2 ${isUser ? "items-end flex flex-col" : ""}`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
            ${
              isUser
                ? "bg-amber-500 text-ink-950 rounded-tr-sm font-medium"
                : "bg-ink-800 border border-ink-700 text-paper-100 rounded-tl-sm"
            }`}
        >
          {message.content}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.sources.map((source, idx) => (
              <button
                key={idx}
                onClick={() =>
                  setExpandedSource(expandedSource === idx ? null : idx)
                }
                className="text-[11px] px-2.5 py-1 rounded-lg bg-teal-500/10
                           border border-teal-500/25 text-teal-500
                           hover:bg-teal-500/20 transition-colors font-mono
                           flex items-center gap-1.5"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 3v5a1 1 0 0 0 1 1h5" />
                  <path d="M5 4a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z" />
                </svg>
                {source.source_file} · p.{source.page_number}
              </button>
            ))}
          </div>
        )}

        {expandedSource !== null && message.sources?.[expandedSource] && (
          <div className="text-xs text-ink-200 bg-ink-900 border border-ink-700 rounded-xl p-3 max-w-md animate-fade-up">
            <p className="font-mono text-ink-400 mb-1">
              {message.sources[expandedSource].source_file} — page{" "}
              {message.sources[expandedSource].page_number}
            </p>
            <p className="leading-relaxed">
              {message.sources[expandedSource].preview}
            </p>
          </div>
        )}

        {message.processingTimeMs !== undefined && (
          <p className="text-[10px] text-ink-600 font-mono px-1">
            {(message.processingTimeMs / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    </div>
  );
}