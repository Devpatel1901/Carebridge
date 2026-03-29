"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Trash2, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatEasternFromEpochMs } from "@/lib/datetime";

const ACCEPT = ".pdf,.doc,.docx,.txt,.text,.md,.markdown";
const ACCEPT_LABEL = "PDF, DOC, DOCX";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  busy: boolean;
  onComplete: (text: string) => Promise<void>;
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

async function fileToDischargeText(file: File): Promise<string> {
  const name = file.name.toLowerCase();
  const ext = name.split(".").pop() ?? "";
  if (["txt", "md", "markdown", "text"].includes(ext) || file.type === "text/plain") {
    const t = await file.text();
    if (!t.trim()) throw new Error("File is empty.");
    return t;
  }
  if (ext === "pdf" || file.type === "application/pdf") {
    throw new Error(
      "PDF upload is shown in the UI for the demo workflow. Please upload a .txt discharge summary for processing, or export text from your PDF and save as .txt."
    );
  }
  if (ext === "doc" || ext === "docx" || file.type.includes("word") || file.type.includes("document")) {
    throw new Error(
      "Word documents cannot be read in the browser here. Please upload a .txt file, or copy the discharge text into a .txt file and upload that."
    );
  }
  const t = await file.text();
  if (!t.trim()) throw new Error("Could not read usable text from this file. Use a .txt discharge summary.");
  return t;
}

export function DischargeUploadModal({ open, onOpenChange, busy, onComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (!open) {
      setFile(null);
      setError(null);
      setDragOver(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onOpenChange(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onOpenChange]);

  const pick = () => inputRef.current?.click();

  const onFile = useCallback((f: File | undefined) => {
    if (!f) return;
    setError(null);
    setFile(f);
  }, []);

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFile(e.target.files?.[0]);
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFile(f);
  };

  const handleComplete = async () => {
    if (!file || busy) return;
    setError(null);
    try {
      const text = await fileToDischargeText(file);
      await onComplete(text);
      onOpenChange(false);
      setFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    }
  };

  if (!open) return null;

  const dateStr = file ? formatEasternFromEpochMs(file.lastModified) : "";

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onOpenChange(false);
      }}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[1px]" aria-hidden />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="discharge-modal-title"
        className="relative z-[101] flex max-h-[min(92vh,720px)] w-full max-w-[560px] flex-col rounded-xl border border-[#e8e8e8] bg-white shadow-xl"
      >
        <div className="flex items-start justify-between border-b border-[#e8e8e8] px-5 py-4 sm:px-6">
          <h2 id="discharge-modal-title" className="text-lg font-bold text-[#1a1a1a]">
            Upload Discharge Report
          </h2>
          <button
            type="button"
            disabled={busy}
            onClick={() => onOpenChange(false)}
            className="rounded-lg p-1.5 text-[#888] transition-colors hover:bg-[#f5f5f5] hover:text-[#333] disabled:opacity-50"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={onInputChange}
          />

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`flex min-h-[200px] flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-10 transition-colors sm:min-h-[220px] ${
              dragOver ? "border-[#2d6a2e] bg-[#f5faf5]" : "border-[#d0d0d0] bg-[#fafafa]"
            }`}
          >
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#e8f5e9]">
              <Upload className="h-7 w-7 text-[#2d6a2e]" strokeWidth={2} />
            </div>
            <p className="text-center text-sm text-[#555]">
              Drag and drop or{" "}
              <button
                type="button"
                onClick={pick}
                className="font-medium text-[#2d6a2e] underline decoration-[#2d6a2e] underline-offset-2 hover:text-[#245a25]"
              >
                Browse
              </button>{" "}
              to upload
            </p>
            <p className="mt-2 text-center text-xs text-[#888]">Supported formats: {ACCEPT_LABEL}</p>
          </div>

          <a
            href="/discharge-sample-format.txt"
            download="discharge-sample-format.txt"
            className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-[#2d6a2e] hover:underline"
          >
            <FileText className="h-4 w-4 shrink-0" />
            <span>Download sample format</span>
            <span className="font-normal text-[#aaa]">(optional)</span>
          </a>

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

          {file && (
            <div className="mt-5 flex items-start gap-3 rounded-lg border border-[#ddd] bg-white p-3 shadow-sm">
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded text-xs font-bold ${
                  file.name.toLowerCase().endsWith(".pdf")
                    ? "bg-red-50 text-red-600"
                    : file.name.toLowerCase().match(/\.docx?$/)
                      ? "bg-blue-50 text-blue-700"
                      : "bg-[#f0f0f0] text-[#555]"
                }`}
              >
                {file.name.toLowerCase().endsWith(".pdf")
                  ? "PDF"
                  : file.name.toLowerCase().match(/\.docx?$/)
                    ? "DOC"
                    : "TXT"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-[#1a1a1a]">{file.name}</p>
                <p className="mt-0.5 text-xs text-[#888]">
                  Date: {dateStr} · Size: {formatBytes(file.size)}
                </p>
                <p className="mt-1 text-xs text-[#888]">Ready to upload</p>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => setFile(null)}
                className="shrink-0 rounded-lg p-2 text-[#888] hover:bg-[#f5f5f5] hover:text-[#333] disabled:opacity-50"
                aria-label="Remove file"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-[#e8e8e8] px-5 py-4 sm:flex-row sm:justify-end sm:gap-3 sm:px-6">
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => onOpenChange(false)}
            className="h-10 rounded-lg border-[#ddd] bg-white px-5 font-medium text-[#333] hover:bg-[#fafafa]"
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!file || busy}
            onClick={handleComplete}
            className="h-10 rounded-lg bg-[#2d6a2e] px-6 font-semibold text-white hover:bg-[#245a25] disabled:opacity-50"
          >
            {busy ? "Uploading…" : "Complete Upload"}
          </Button>
        </div>
      </div>
    </div>
  );
}
