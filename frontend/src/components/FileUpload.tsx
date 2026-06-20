// frontend/src/components/FileUpload.tsx

import { useState, useCallback, useEffect } from "react";
import { uploadPDFs } from "../services/api";
import type { Document } from "../types";

interface Props {
  onUploadComplete: (sessionId: string, docs: Document[]) => void;
}

export function FileUpload({ onUploadComplete }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [fileNames, setFileNames] = useState<string[]>([]);

  useEffect(() => {
    let interval: number;
    if (isUploading) {
      setElapsed(0);
      interval = window.setInterval(() => setElapsed((p) => p + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [isUploading]);

  const handleFiles = useCallback(
    async (files: File[]) => {
      const pdfFiles = files.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
      if (pdfFiles.length === 0) {
        setError("Only PDF files are accepted.");
        return;
      }

      setIsUploading(true);
      setError(null);
      setFileNames(pdfFiles.map((f) => f.name));

      try {
        const result = await uploadPDFs(pdfFiles);
        onUploadComplete(result.session_id, result.documents);
      } catch (err: any) {
        setError(
          err.response?.data?.error ||
            "Upload didn't go through. Check your connection and try again."
        );
      } finally {
        setIsUploading(false);
      }
    },
    [onUploadComplete]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(Array.from(e.dataTransfer.files));
    },
    [handleFiles]
  );

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleFiles(Array.from(e.target.files));
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Ambient backdrop texture */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />

      <div className="max-w-lg w-full relative animate-fade-up">
        {/* Mark + heading */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-amber-500/10 border border-amber-500/30 mb-5">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#d98e3a" strokeWidth="1.6">
              <path d="M14 3v5a1 1 0 0 0 1 1h5" />
              <path d="M5 4a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z" />
              <path d="M9 14h6M9 17h4" />
            </svg>
          </div>
          <h1 className="font-display text-4xl font-semibold text-paper-50 mb-2">
            Inkwell
          </h1>
          <p className="text-ink-200 text-sm">
            Drop in a PDF. Ask it anything. Get answers with the exact page they came from.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onDrop={onDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          className={`
            relative rounded-2xl border-2 border-dashed transition-all duration-200
            ${
              isDragging
                ? "border-amber-500 bg-amber-500/[0.06]"
                : "border-ink-600 hover:border-ink-400 bg-ink-900/40"
            }
            ${isUploading ? "pointer-events-none" : ""}
          `}
        >
          <label
            htmlFor="file-input"
            className="block px-8 py-12 text-center cursor-pointer"
          >
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pdf"
              className="hidden"
              onChange={onFileInput}
              disabled={isUploading}
            />

            {isUploading ? (
              <div className="space-y-4">
                <div className="flex justify-center gap-1.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="w-2 h-2 rounded-full bg-amber-500"
                      style={{
                        animation: "pulse-soft 1.2s ease-in-out infinite",
                        animationDelay: `${i * 0.15}s`,
                      }}
                    />
                  ))}
                </div>
                <div>
                  <p className="text-paper-50 text-sm font-medium">
                    Reading {fileNames.length === 1 ? fileNames[0] : `${fileNames.length} files`}
                  </p>
                  <p className="text-ink-400 text-xs mt-1 font-mono">
                    {elapsed}s elapsed
                    {elapsed > 20 && " — larger PDFs take a couple of minutes"}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <svg
                  className="mx-auto"
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  style={{ color: "var(--ink-400)" }}
                >
                  <path d="M12 3v12m0-12 4 4m-4-4-4 4" />
                  <path d="M5 17v2a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-2" />
                </svg>
                <div>
                  <p className="text-paper-100 text-sm font-medium">
                    Drag a PDF here, or{" "}
                    <span className="text-amber-500">browse files</span>
                  </p>
                  <p className="text-ink-400 text-xs mt-1">
                    Up to 10 files, 50MB each
                  </p>
                </div>
              </div>
            )}
          </label>
        </div>

        {error && (
          <div className="mt-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-200 text-sm flex gap-2.5 items-start animate-fade-up">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 shrink-0">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}