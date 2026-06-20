// frontend/src/components/ChatInterface.tsx

import { useState, useRef, useEffect } from "react";
import { sendMessage, getDocuments } from "../services/api";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "../types";

interface Props {
  sessionId: string;
}

export function ChatInterface({ sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Your documents are indexed. Ask me anything about them.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [availableDocs, setAvailableDocs] = useState<string[]>([]);
  const [selectedDoc, setSelectedDoc] = useState("all");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    getDocuments(sessionId)
      .then((data) => setAvailableDocs(data.documents || []))
      .catch(() => {});
  }, [sessionId]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await sendMessage(
        userMessage.content,
        sessionId,
        selectedDoc === "all" ? undefined : selectedDoc
      );

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          processingTimeMs: response.processing_time_ms,
          timestamp: new Date(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "Something went wrong reaching the model. Try again in a moment.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-ink-700 bg-ink-900/60 backdrop-blur">
        <div className="flex items-center gap-2 text-sm text-ink-200">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
          Ready
        </div>

        {availableDocs.length > 1 && (
          <select
            value={selectedDoc}
            onChange={(e) => setSelectedDoc(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-lg border border-ink-600
                       bg-ink-800 text-ink-200 focus:border-amber-500
                       outline-none cursor-pointer"
          >
            <option value="all">Search all documents</option>
            {availableDocs.map((doc) => (
              <option key={doc} value={doc}>
                {doc}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        <div className="max-w-3xl mx-auto space-y-5">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {isLoading && (
            <div className="flex items-center gap-3 text-ink-400 text-sm pl-1">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-amber-500"
                    style={{
                      animation: "pulse-soft 1.2s ease-in-out infinite",
                      animationDelay: `${i * 0.15}s`,
                    }}
                  />
                ))}
              </div>
              <span>Searching the document…</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-ink-700 bg-ink-900/60 backdrop-blur px-6 py-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask a question about your documents…"
            disabled={isLoading}
            autoFocus
            className="flex-1 px-4 py-3 rounded-xl border border-ink-600
                       bg-ink-800 text-paper-100 placeholder:text-ink-400
                       focus:border-amber-500 outline-none transition-colors
                       disabled:opacity-50 text-sm"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="px-5 py-3 bg-amber-500 hover:bg-amber-600 active:scale-[0.97]
                       text-ink-950 text-sm font-semibold rounded-xl
                       transition-all duration-150 disabled:opacity-40
                       disabled:pointer-events-none shrink-0"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}