
"use client";

import { useEffect, useRef, useState } from "react";

type DocumentItem = {
  document_id: string;
  filename: string;
  chunk_count: number;
};

type Source = {
  filename: string;
  page_number: number | null;
  text: string;
  similarity_score: number;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const selectedDocument = documents.find(
    (doc) => doc.document_id === documentId
  );

  useEffect(() => {
    async function loadDocuments() {
      try {
        const response = await fetch(`${API_URL}/documents`);
        if (!response.ok) throw new Error("Could not load documents.");

        const data = await response.json();
        const items: DocumentItem[] = data.documents ?? [];
        setDocuments(items);

        // Restore the selected document when possible.
        const savedId = sessionStorage.getItem("ida-document-id");
        const initial = items.find((doc) => doc.document_id === savedId);
        if (initial) {
          setDocumentId(initial.document_id);
        }
      } catch {
        setError("Could not connect to the backend. Is FastAPI running?");
      } finally {
        setLoadingDocuments(false);
      }
    }

    loadDocuments();
  }, []);

  useEffect(() => {
    if (documentId) {
      sessionStorage.setItem("ida-document-id", documentId);
    } else {
      sessionStorage.removeItem("ida-document-id");
    }
  }, [documentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  function selectDocument(id: string) {
    setDocumentId(id);
    setMessages([]);
    setError("");
    setShowUpload(false);
  }

  function newChat() {
    setMessages([]);
    setQuestion("");
    setError("");
  }

  async function uploadDocument() {
    if (!selectedFile || uploading) return;

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("The file exceeds the 10 MB limit.");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API_URL}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      const newDocument: DocumentItem = {
        document_id: data.document_id,
        filename: data.filename,
        chunk_count: data.chunks_created,
      };

      setDocuments((previous) => [
        newDocument,
        ...previous.filter(
          (doc) => doc.document_id !== newDocument.document_id
        ),
      ]);
      setDocumentId(newDocument.document_id);
      setMessages([]);
      setSelectedFile(null);
      setShowUpload(false);

      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function askQuestion(text = question) {
    const trimmed = text.trim();
    if (!trimmed || !documentId || asking) return;

    setQuestion("");
    setError("");
    setMessages((previous) => [
      ...previous,
      { role: "user", content: trimmed },
    ]);
    setAsking(true);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: documentId,
          question: trimmed,
          top_k: 3,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 502 || response.status === 429) {
          throw new Error(
            "IDA couldn't generate an answer right now. Please try again later."
          );
        }

        throw new Error("Something went wrong. Please try again.");
      }


      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources ?? [],
        },
      ]);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "IDA couldn't generate an answer right now. Please try again later."
      );
    }
    finally {
      setAsking(false);
    }
  }

  return (
    <main className="flex h-dvh overflow-hidden bg-[#212121] text-[#ececec]">
      {/* Sidebar */}
      <aside className="flex w-[270px] shrink-0 flex-col border-r border-white/[0.08] bg-[#181818] max-md:w-[76px]">
        <div className="flex items-center gap-3 px-5 py-5 max-md:justify-center max-md:px-2">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-sm font-bold text-black">
            I
          </div>
          <div className="max-md:hidden">
            <p className="font-semibold tracking-wide">IDA</p>
            <p className="text-[11px] text-[#999]">Document assistant</p>
          </div>
        </div>

        <div className="px-3">
          <button
            onClick={newChat}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm hover:bg-white/[0.08] max-md:justify-center max-md:px-0"
          >
            <span className="text-lg">＋</span>
            <span className="max-md:hidden">New chat</span>
          </button>
          <button
            onClick={() => setShowUpload((value) => !value)}
            className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm text-[#c5c5c5] hover:bg-white/[0.08] max-md:justify-center max-md:px-0"
          >
            <span className="text-lg">↑</span>
            <span className="max-md:hidden">Add document</span>
          </button>
        </div>

        <div className="mt-8 min-h-0 flex-1 overflow-y-auto px-3">
          <p className="mb-3 px-3 text-xs font-medium text-[#858585] max-md:hidden">
            YOUR DOCUMENTS
          </p>

          {loadingDocuments && (
            <p className="px-3 py-2 text-xs text-[#888] max-md:hidden">
              Loading...
            </p>
          )}

          {!loadingDocuments && documents.length === 0 && (
            <p className="px-3 py-2 text-xs leading-5 text-[#888] max-md:hidden">
              No documents yet. Add one to get started.
            </p>
          )}


          {documents.map((doc) => (
            <div
              key={doc.document_id}
              className={`group mb-1 flex items-center gap-1 rounded-lg px-2 transition ${documentId === doc.document_id
                ? "bg-[#303030] text-white"
                : "text-[#b8b8b8] hover:bg-white/[0.06]"
                }`}
            >
              <button
                title={doc.filename}
                onClick={() => selectDocument(doc.document_id)}
                className="flex min-w-0 flex-1 items-start gap-3 py-3 text-left text-sm max-md:justify-center"
              >
                <span className="mt-0.5 shrink-0 text-base">▤</span>

                <span className="min-w-0 max-md:hidden">
                  <span className="block truncate">{doc.filename}</span>
                  <span className="mt-1 block text-[11px] text-[#858585]">
                    {doc.chunk_count} {doc.chunk_count === 1 ? "chunk" : "chunks"}
                  </span>
                </span>
              </button>

              <button
                type="button"
                title={`Delete ${doc.filename}`}
                aria-label={`Delete ${doc.filename}`}
                onClick={async () => {
                  const confirmed = window.confirm(
                    `Delete "${doc.filename}" permanently?`
                  );

                  if (!confirmed) return;

                  setError("");

                  try {
                    const response = await fetch(
                      `${API_URL}/documents/${doc.document_id}`,
                      { method: "DELETE" }
                    );

                    const data = await response.json();

                    if (!response.ok) {
                      throw new Error(data.detail || "Could not delete document.");
                    }

                    setDocuments((previous) =>
                      previous.filter((item) => item.document_id !== doc.document_id)
                    );

                    if (documentId === doc.document_id) {
                      setDocumentId("");
                      setMessages([]);
                      setQuestion("");
                    }
                  } catch (err) {
                    setError(
                      err instanceof Error ? err.message : "Could not delete document."
                    );
                  }
                }}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[#858585] opacity-100 transition hover:bg-red-400/10 hover:text-red-300 md:opacity-0 md:group-hover:opacity-100"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                  aria-hidden="true"
                >
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="m19 6-1 14H6L5 6" />
                  <path d="M10 11v5M14 11v5" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        <div className="border-t border-white/[0.08] p-4 max-md:hidden">
          <p className="text-xs text-[#858585]">
            Answers are generated from your documents.
          </p>
        </div>
      </aside>

      {/* Main chat */}
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[62px] shrink-0 items-center justify-between border-b border-white/[0.07] px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">
              {selectedDocument?.filename || "New conversation"}
            </p>
          </div>
          <span className="ml-3 shrink-0 text-xs text-[#858585]">
            IDA · RAG assistant
          </span>
        </header>

        {showUpload && (
          <div className="border-b border-white/[0.08] bg-[#262626] px-5 py-4">
            <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.docx"
                onChange={(event) =>
                  setSelectedFile(event.target.files?.[0] ?? null)
                }
                className="min-w-0 flex-1 text-sm text-[#ccc] file:mr-3 file:rounded-lg file:border-0 file:bg-[#404040] file:px-3 file:py-2 file:text-sm file:text-white"
              />
              <button
                onClick={uploadDocument}
                disabled={!selectedFile || uploading}
                className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-[#ddd] disabled:opacity-40"
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
              <button
                onClick={() => {
                  setShowUpload(false);
                  setSelectedFile(null);
                }}
                className="rounded-lg px-3 py-2 text-sm text-[#aaa] hover:bg-white/10"
              >
                Cancel
              </button>
            </div>
            <p className="mx-auto mt-2 max-w-3xl text-xs text-[#888]">
              PDF, TXT or DOCX · Maximum 10 MB
            </p>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mx-auto mt-4 w-[calc(100%-32px)] max-w-3xl rounded-lg border border-red-400/20 bg-red-400/[0.08] px-4 py-3 text-sm text-red-200"
          >
            {error}
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex min-h-full flex-col items-center justify-center px-5 py-12">
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-[#2b2b2b] text-xl">
                ▤
              </div>
              <h1 className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
                {selectedDocument
                  ? "What would you like to know?"
                  : "What can I help you understand?"}
              </h1>
              <p className="mt-3 max-w-md text-center text-sm leading-6 text-[#999]">
                {selectedDocument
                  ? `Ask questions about ${selectedDocument.filename}. Answers include supporting source excerpts.`
                  : "Select a document from the sidebar or add a new one to start asking questions."}
              </p>

              {selectedDocument && (
                <div className="mt-8 grid w-full max-w-2xl gap-2 sm:grid-cols-2">
                  {[
                    "Summarize this document",
                    "What are the key findings?",
                    "Explain the main concepts",
                    "What information is missing?",
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => askQuestion(suggestion)}
                      disabled={asking}
                      className="rounded-xl border border-white/[0.1] px-4 py-3 text-left text-sm text-[#c9c9c9] transition hover:bg-white/[0.05] disabled:opacity-40"
                    >
                      {suggestion}
                      <span className="float-right text-[#777]">↗</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="mx-auto max-w-3xl px-5 py-8">
              {messages.map((message, index) => (
                <div key={index} className="mb-8">
                  {message.role === "user" ? (
                    <div className="ml-auto max-w-[85%] rounded-3xl bg-[#303030] px-5 py-3.5 text-sm leading-7 sm:max-w-[75%]">
                      {message.content}
                    </div>
                  ) : (
                    <div className="flex gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/10 bg-[#303030] text-xs font-semibold">
                        I
                      </div>
                      <div className="min-w-0 flex-1 pt-1">
                        <p className="whitespace-pre-wrap text-sm leading-7 text-[#e2e2e2]">
                          {message.content}
                        </p>

                        {/* {message.sources && message.sources.length > 0 && (
                          <details className="mt-5 rounded-xl border border-white/[0.09] bg-white/[0.02]">
                            <summary className="cursor-pointer px-4 py-3 text-sm text-[#bcbcbc] hover:text-white">
                              {message.sources.length} source
                              {message.sources.length === 1 ? "" : "s"}
                            </summary>
                            <div className="space-y-3 border-t border-white/[0.08] p-3">
                              {message.sources.map((source, sourceIndex) => (
                                <div
                                  key={`${source.filename}-${source.page_number}-${sourceIndex}`}
                                  className="rounded-lg bg-white/[0.035] p-3"
                                >
                                  <p className="text-xs font-medium text-[#ddd]">
                                    {source.filename}
                                    {source.page_number !== null
                                      ? ` · Page ${source.page_number}`
                                      : ""}
                                  </p>
                                  <p className="mt-2 whitespace-pre-wrap text-xs leading-6 text-[#a8a8a8]">
                                    {source.text}
                                  </p>
                                  <p className="mt-2 text-[11px] text-[#777]">
                                    Similarity:{" "}
                                    {source.similarity_score.toFixed(4)}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </details>
                        )} */}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {asking && (
                <div className="flex items-center gap-3 text-sm text-[#999]">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-[#303030]">
                    I
                  </div>
                  Thinking...
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Bottom composer */}
        <div className="shrink-0 px-4 pb-5 pt-3 sm:px-6">
          <div className="mx-auto max-w-3xl">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void askQuestion();
              }}
              className="rounded-3xl border border-white/[0.12] bg-[#303030] p-2 transition focus-within:border-white/25"
            >
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault();
                    void askQuestion();
                  }
                }}
                placeholder={
                  selectedDocument
                    ? "Message IDA..."
                    : "Select a document to start asking..."
                }
                disabled={!documentId || asking}
                rows={2}
                className="max-h-36 min-h-[44px] w-full resize-y bg-transparent px-3 py-2 text-sm leading-6 outline-none placeholder:text-[#858585] disabled:opacity-50"
              />
              <div className="flex items-center justify-between px-1 pb-1">
                <button
                  type="button"
                  onClick={() => setShowUpload((value) => !value)}
                  aria-label="Upload document"
                  className="flex h-9 w-9 items-center justify-center rounded-full text-lg text-[#bbb] hover:bg-white/10"
                >
                  +
                </button>
                <button
                  type="submit"
                  disabled={!documentId || !question.trim() || asking}
                  aria-label="Send message"
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-lg font-medium text-black transition hover:bg-[#ddd] disabled:bg-[#555] disabled:text-[#999]"
                >
                  ↑
                </button>
              </div>
            </form>
            <p className="mt-3 text-center text-[11px] text-[#777]">
              IDA can make mistakes. Verify important information using the
              cited sources.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
