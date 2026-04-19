"use client";

/* eslint-disable @next/next/no-img-element */

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import AppShell from "@/components/AppShell";
import { useRoleGuard } from "@/lib/auth";
import { authGetJson, authPostForm, authPostJson, backendUrl, getCookieValue } from "@/lib/backend";

type Attachment = {
  id: number;
  name: string;
  content_type: string;
  url: string;
};

type MessageStatus = "delivered" | "failed" | "thinking" | "streaming";

type ChatMessage = {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  attachments: Attachment[];
  status?: MessageStatus;
};

type ChatSession = {
  id: number;
  title: string;
  language: "en" | "bn";
  updated_at: string;
  generated_complaint_id: number | null;
  complaint_detail_url: string | null;
};

type ValidationReference = {
  title?: string;
  content?: string;
  url?: string;
  source_file?: string;
  category?: string;
};

type ValidationPayload = {
  is_valid?: boolean | null;
  inconsistencies?: string[];
  recommendation?: string;
  references?: ValidationReference[];
  policy_references?: ValidationReference[];
};

type ExtractedData = {
  category: string;
  area: string;
  duration: string;
  keywords: string[];
  inconsistency_score: number;
  policy_reference: string;
  timestamp: string;
  validation?: ValidationPayload;
} | null;

type SessionListResponse = {
  success: boolean;
  sessions: ChatSession[];
};

type SessionDetailResponse = {
  success: boolean;
  session: ChatSession;
  messages: ChatMessage[];
  extracted_data: ExtractedData;
};

type SendMessageResponse = {
  success: boolean;
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  extracted_data: ExtractedData;
};

type FinalizeResponse = {
  success: boolean;
  message: string;
  complaint_detail_url: string | null;
};

type SelectedPhoto = {
  file: File;
  previewUrl: string;
};

const emojiChoices = ["😀", "🙂", "😢", "😡", "🙏", "📍", "🚧", "💧", "⚠️", "🗑️", "🚰", "🛣️", "🚨", "🌧️", "🏥", "💡"];

function formatRoleLabel(role: string) {
  const normalized = (role || "citizen").trim().toLowerCase();
  if (normalized === "admin") {
    return "Admin";
  }
  if (normalized === "authority") {
    return "Authority";
  }
  return "Citizen";
}

function splitForStreaming(text: string): string[] {
  const normalized = (text || "").replace(/\r\n/g, "\n");
  const chunks = normalized.match(/\S+\s*|\n/g);
  if (!chunks || !chunks.length) {
    return [normalized];
  }
  return chunks;
}

function streamStepDelay(chunk: string): number {
  return Math.min(28 + chunk.length * 7, 120);
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatSessionLabel(timestamp: string) {
  if (!timestamp) {
    return "Just now";
  }

  return new Date(timestamp).toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTime(timestamp: string) {
  if (!timestamp) {
    return "Just now";
  }

  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function toAttachmentUrl(url: string) {
  if (!url) {
    return "#";
  }
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  return backendUrl(url);
}

function getSessionTitle(title: string) {
  const cleaned = (title || "").trim();
  return cleaned || "New Chat";
}

export default function ChatbotPage() {
  const router = useRouter();
  const { ready, role } = useRoleGuard(["citizen"]);

  const [loading, setLoading] = useState(true);
  const [loadingSession, setLoadingSession] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [extractedData, setExtractedData] = useState<ExtractedData>(null);

  const [messageText, setMessageText] = useState("");
  const [selectedPhotos, setSelectedPhotos] = useState<SelectedPhoto[]>([]);
  const [sending, setSending] = useState(false);
  const [assistantPhase, setAssistantPhase] = useState<"idle" | "thinking" | "streaming">("idle");
  const [emojiOpen, setEmojiOpen] = useState(false);

  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const photoInputRef = useRef<HTMLInputElement | null>(null);
  const emojiPickerRef = useRef<HTMLDivElement | null>(null);
  const emojiButtonRef = useRef<HTMLButtonElement | null>(null);
  const selectedPhotosRef = useRef<SelectedPhoto[]>([]);
  const streamRunIdRef = useRef(0);

  const userName = getCookieValue("dhaka_name") || "User";
  const userRole = (getCookieValue("dhaka_role") || "citizen").toLowerCase();
  const userRoleLabel = formatRoleLabel(userRole);
  const userInitial = userName.trim().charAt(0).toUpperCase() || "U";

  const canFinalize = Boolean(currentSession);
  const finalizeLabel = currentSession?.generated_complaint_id ? "Open Complaint" : "Create Complaint";
  const composerState = !currentSession
    ? "Waiting for a session"
    : assistantPhase === "thinking"
      ? "Assistant is thinking..."
      : assistantPhase === "streaming"
        ? "Assistant is generating a reply..."
      : "Ready to send";

  useEffect(() => {
    selectedPhotosRef.current = selectedPhotos;
  }, [selectedPhotos]);

  useEffect(() => {
    return () => {
      selectedPhotosRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    };
  }, []);

  function resizeTextarea() {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = "52px";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
  }

  useEffect(() => {
    resizeTextarea();
  }, [messageText]);

  useEffect(() => {
    if (!messagesContainerRef.current) {
      return;
    }
    messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
  }, [messages, loadingSession]);

  useEffect(() => {
    if (!emojiOpen) {
      return;
    }

    function onDocumentClick(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }

      if (emojiPickerRef.current?.contains(target) || emojiButtonRef.current?.contains(target)) {
        return;
      }
      setEmojiOpen(false);
    }

    document.addEventListener("click", onDocumentClick);
    return () => document.removeEventListener("click", onDocumentClick);
  }, [emojiOpen]);

  function clearSelectedPhotos() {
    setSelectedPhotos((previous) => {
      previous.forEach((item) => URL.revokeObjectURL(item.previewUrl));
      return [];
    });

    if (photoInputRef.current) {
      photoInputRef.current.value = "";
    }
  }

  function upsertSession(session: ChatSession) {
    setSessions((previous) => {
      const filtered = previous.filter((item) => item.id !== session.id);
      return [session, ...filtered];
    });
  }

  async function streamAssistantMessage(tempMessageId: string, assistantMessage: ChatMessage, runId: number) {
    const chunks = splitForStreaming(assistantMessage.content);
    let combined = "";
    setAssistantPhase("streaming");

    for (const chunk of chunks) {
      if (streamRunIdRef.current !== runId) {
        return;
      }

      combined += chunk;
      setMessages((previous) =>
        previous.map((message) =>
          message.id === tempMessageId
            ? {
                ...assistantMessage,
                id: tempMessageId,
                content: combined,
                status: "streaming",
              }
            : message,
        ),
      );

      await wait(streamStepDelay(chunk));
    }

    if (streamRunIdRef.current !== runId) {
      return;
    }

    setMessages((previous) =>
      previous.map((message) =>
        message.id === tempMessageId
          ? {
              ...assistantMessage,
              status: "delivered",
            }
          : message,
      ),
    );
  }

  async function loadSession(sessionId: number) {
    streamRunIdRef.current += 1;
    setAssistantPhase("idle");
    setSending(false);
    setLoadingSession(true);
    setNotice(null);

    try {
      const data = await authGetJson<SessionDetailResponse>(`/api/chatbot/session/${sessionId}/`);
      setCurrentSession(data.session);
      setMessages(data.messages);
      setExtractedData(data.extracted_data);
      upsertSession(data.session);
      sessionStorage.setItem("chat_session_id", String(data.session.id));
    } catch (error) {
      const message = error instanceof Error ? error.message : `Unable to load session ${sessionId}.`;
      setNotice(message);
      sessionStorage.removeItem("chat_session_id");
    } finally {
      setLoadingSession(false);
    }
  }

  async function createSession() {
    streamRunIdRef.current += 1;
    setAssistantPhase("idle");
    setSending(false);
    setNotice(null);
    setLoadingSession(true);

    try {
      const data = await authPostJson<{ success: boolean; session: ChatSession }>("/api/chatbot/session/create/", {
        title: "New Complaint Chat",
        language: "en",
      });

      setCurrentSession(data.session);
      setMessages([]);
      setExtractedData(null);
      setMessageText("");
      clearSelectedPhotos();
      upsertSession(data.session);
      sessionStorage.setItem("chat_session_id", String(data.session.id));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create a new chat session.";
      setNotice(message);
    } finally {
      setLoadingSession(false);
    }
  }

  async function loadInitialState() {
    setLoading(true);
    setNotice(null);

    try {
      const data = await authGetJson<SessionListResponse>("/api/chatbot/sessions/");
      setSessions(data.sessions);

      const storedSessionId = Number(sessionStorage.getItem("chat_session_id") || "");
      const defaultSession = data.sessions.find((session) => session.id === storedSessionId) || data.sessions[0];

      if (defaultSession) {
        await loadSession(defaultSession.id);
      } else {
        await createSession();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load chat sessions.";
      setNotice(message);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currentSession || sending) {
      return;
    }

    const trimmedMessage = messageText.trim();
    if (!trimmedMessage && !selectedPhotos.length) {
      return;
    }

    const outgoingPhotos = [...selectedPhotos];
    const runId = streamRunIdRef.current + 1;
    streamRunIdRef.current = runId;
    const tempUserId = `tmp-user-${Date.now()}`;
    const tempAssistantId = `tmp-assistant-${Date.now()}`;
    const optimisticContent = trimmedMessage || (outgoingPhotos.length === 1 ? "Sent a photo." : `Sent ${outgoingPhotos.length} photos.`);
    const optimisticTimestamp = new Date().toISOString();

    setMessages((previous) => [
      ...previous,
      {
        id: tempUserId,
        role: "user",
        content: optimisticContent,
        timestamp: optimisticTimestamp,
        attachments: [],
        status: "delivered",
      },
      {
        id: tempAssistantId,
        role: "assistant",
        content: "",
        timestamp: optimisticTimestamp,
        attachments: [],
        status: "thinking",
      },
    ]);
    setMessageText("");
    setEmojiOpen(false);
    clearSelectedPhotos();

    setSending(true);
    setAssistantPhase("thinking");
    setNotice(null);

    try {
      let data: SendMessageResponse;

      if (outgoingPhotos.length) {
        const formData = new FormData();
        formData.append("message", trimmedMessage);
        outgoingPhotos.forEach((item) => formData.append("photos", item.file));
        data = await authPostForm<SendMessageResponse>(`/api/chatbot/session/${currentSession.id}/message/`, formData);
      } else {
        data = await authPostJson<SendMessageResponse>(`/api/chatbot/session/${currentSession.id}/message/`, {
          message: trimmedMessage,
        });
      }

      if (streamRunIdRef.current !== runId) {
        return;
      }

      setCurrentSession(data.session);
      upsertSession(data.session);
      setMessages((previous) =>
        previous.map((message) => {
          if (message.id === tempUserId) {
            return {
              ...data.user_message,
              status: "delivered" as MessageStatus,
            };
          }
          if (message.id === tempAssistantId) {
            return {
              ...data.assistant_message,
              id: tempAssistantId,
              content: "",
              status: "thinking" as MessageStatus,
            };
          }
          return message;
        }),
      );
      setExtractedData(data.extracted_data);
      sessionStorage.setItem("chat_session_id", String(data.session.id));
      await streamAssistantMessage(tempAssistantId, data.assistant_message, runId);
    } catch (error) {
      setMessages((previous) =>
        previous
          .map((message) => (message.id === tempUserId ? { ...message, status: "failed" as MessageStatus } : message))
          .filter((message) => message.id !== tempAssistantId),
      );
      const message = error instanceof Error ? error.message : "The assistant could not answer that message.";
      setNotice(message);
    } finally {
      if (streamRunIdRef.current === runId) {
        setSending(false);
        setAssistantPhase("idle");
      }
    }
  }

  async function finalizeComplaint() {
    if (!currentSession) {
      return;
    }

    if (currentSession.generated_complaint_id) {
      router.push(`/complaint/${currentSession.generated_complaint_id}`);
      return;
    }

    setSending(true);
    setNotice(null);

    try {
      const data = await authPostJson<FinalizeResponse>(`/api/chatbot/session/${currentSession.id}/close/`, {});
      setNotice(data.message || "Complaint created successfully.");

      if (data.complaint_detail_url) {
        const match = data.complaint_detail_url.match(/\/complaint\/(\d+)\/?/);
        if (match?.[1]) {
          router.push(`/complaint/${match[1]}`);
        } else {
          window.location.href = data.complaint_detail_url;
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create the complaint from this chat.";
      setNotice(message);
    } finally {
      setSending(false);
    }
  }

  function handlePhotoSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const incomingFiles = Array.from(event.target.files || []);
    if (!incomingFiles.length) {
      return;
    }

    setSelectedPhotos((previous) => {
      const next = [...previous];
      incomingFiles.forEach((file) => {
        if (next.length >= 5) {
          return;
        }
        next.push({
          file,
          previewUrl: URL.createObjectURL(file),
        });
      });
      return next;
    });
  }

  function removePhoto(index: number) {
    setSelectedPhotos((previous) => {
      const next = [...previous];
      const [removed] = next.splice(index, 1);
      if (removed) {
        URL.revokeObjectURL(removed.previewUrl);
      }
      return next;
    });
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  function appendEmoji(emoji: string) {
    setMessageText((previous) => `${previous}${emoji}`);
    setEmojiOpen(false);
    textareaRef.current?.focus();
  }

  useEffect(() => {
    if (!ready || role !== "citizen") {
      return;
    }
    void loadInitialState();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, role]);

  if (!ready || role !== "citizen") {
    return null;
  }

  return (
    <AppShell role="citizen" title="Complaint Assistant" hidePageHeader mainClassName="w-full max-w-none px-0 py-0">
      <div className="chat-shell">
        <div className="chat-layout">
          <aside className="chat-card sidebar-panel">
            <section className="user-panel">
              <div className="user-avatar">{userInitial}</div>
              <p className="user-name">{userName}</p>
              <p className="user-role">{userRoleLabel} account</p>
            </section>

            <section>
              <p className="panel-title">Actions</p>
              <p className="panel-subtitle">Start a new complaint chat or reopen a recent conversation.</p>
              <div className="action-grid mt-3.5">
                <button type="button" className="action-btn" onClick={() => void createSession()} disabled={sending || loadingSession}>
                  Start New Chat <span>+</span>
                </button>
              </div>
            </section>

            <section>
              <p className="panel-title">Recent Sessions</p>
              <p className="panel-subtitle">Your last active complaint discussions.</p>
              <div className="session-list mt-3.5">
                {sessions.length ? (
                  sessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      className={`session-btn ${currentSession?.id === session.id ? "active" : ""}`}
                      disabled={sending || loadingSession}
                      onClick={() => void loadSession(session.id)}
                    >
                      <strong>{getSessionTitle(session.title)}</strong>
                      <span>{formatSessionLabel(session.updated_at)}</span>
                    </button>
                  ))
                ) : (
                  <div className="empty-state">No chat history yet. Start a new session to begin collecting complaint details.</div>
                )}
              </div>
            </section>
          </aside>

          <section className="chat-card chat-panel">
            {notice ? <div className="notice show">{notice}</div> : null}

            <div ref={messagesContainerRef} className="messages-area">
              {loading || loadingSession ? (
                <div className="empty-state">Loading session details...</div>
              ) : messages.length ? (
                messages.map((message) => {
                  const isAssistantThinking = message.role === "assistant" && message.status === "thinking";
                  const isAssistantStreaming = message.role === "assistant" && message.status === "streaming";
                  const isFailedUserMessage = message.role === "user" && message.status === "failed";

                  return (
                    <div key={message.id} className={`message-row ${message.role}`}>
                      <div className="message-stack">
                        <div className="message-meta">
                          <span>{message.role === "user" ? "You" : "Assistant"}</span>
                          <span>{formatTime(message.timestamp)}</span>
                          {message.role === "user" ? (
                            <span className={`message-delivery ${isFailedUserMessage ? "failed" : ""}`}>
                              {isFailedUserMessage ? "Failed" : "Delivered"}
                            </span>
                          ) : isAssistantThinking ? (
                            <span className="message-phase">Thinking</span>
                          ) : isAssistantStreaming ? (
                            <span className="message-phase">Typing</span>
                          ) : null}
                        </div>

                        {isAssistantThinking ? (
                          <div className="message-bubble assistant message-bubble-thinking">
                            <span className="typing-dots" aria-hidden="true">
                              <span />
                              <span />
                              <span />
                            </span>
                            <span>Thinking...</span>
                          </div>
                        ) : message.content ? (
                          <div className={`message-bubble ${message.role}`}>
                            {message.content}
                            {isAssistantStreaming ? <span className="stream-cursor" aria-hidden="true">▋</span> : null}
                          </div>
                        ) : null}

                        {message.attachments?.length ? (
                          <div className="attachment-gallery">
                            {message.attachments.map((attachment) => {
                              const url = toAttachmentUrl(attachment.url);
                              const isImage = (attachment.content_type || "").startsWith("image/");

                              return (
                                <a key={attachment.id} href={url} target="_blank" rel="noreferrer" className="attachment-card">
                                  {isImage ? <img src={url} alt={attachment.name} /> : null}
                                  <span>{attachment.name || "Attachment"}</span>
                                </a>
                              );
                            })}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="welcome-card" id="welcome-card">
                  <h3>Describe the civic problem clearly</h3>
                  <p>
                    Include the category, exact location or thana, and how long the issue has been happening. The assistant will
                    turn that into structured complaint data as the chat progresses.
                  </p>
                </div>
              )}
            </div>

            <div className="composer">
              <form ref={formRef} className="composer-form" onSubmit={sendMessage}>
                <div className="composer-stack">
                  <span className="composer-state" aria-live="polite">
                    {composerState}
                  </span>

                  <div ref={emojiPickerRef} className={`emoji-picker ${emojiOpen ? "show" : ""}`}>
                    {emojiChoices.map((emoji) => (
                      <button key={emoji} type="button" className="emoji-option" onClick={() => appendEmoji(emoji)}>
                        {emoji}
                      </button>
                    ))}
                  </div>

                  <div className="preview-strip">
                    {selectedPhotos.map((item, index) => (
                      <div key={item.previewUrl} className="preview-card">
                        <button type="button" onClick={() => removePhoto(index)}>
                          &times;
                        </button>
                        <img src={item.previewUrl} alt={item.file.name} />
                        <span>{item.file.name}</span>
                      </div>
                    ))}
                  </div>

                  <textarea
                    ref={textareaRef}
                    id="message-input"
                    value={messageText}
                    onChange={(event) => setMessageText(event.target.value)}
                    onKeyDown={onComposerKeyDown}
                    placeholder="Example: There has been a pothole in Dhanmondi 27 for two weeks and it is getting worse."
                  />
                  <p className="composer-note">Dhaka Nagorik AI can make mistakes. Review the complaint details before you create it.</p>
                </div>

                <div className="composer-actions">
                  <button
                    type="button"
                    className="tool-btn"
                    onClick={() => photoInputRef.current?.click()}
                    title="Add photo"
                    aria-label="Add photo"
                  >
                    <i className="fas fa-paperclip" />
                  </button>

                  <button
                    ref={emojiButtonRef}
                    type="button"
                    className="tool-btn"
                    onClick={() => setEmojiOpen((previous) => !previous)}
                    title="Add emoji"
                    aria-label="Add emoji"
                  >
                    <span aria-hidden="true">☺</span>
                  </button>

                  <input
                    ref={photoInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    multiple
                    hidden
                    onChange={handlePhotoSelect}
                  />

                  <button type="submit" className="send-btn" disabled={sending || !currentSession}>
                    {assistantPhase === "thinking" ? "Thinking..." : assistantPhase === "streaming" ? "Generating..." : "Send"}
                  </button>
                </div>
              </form>
            </div>
          </section>

          <aside className="chat-card insight-panel">
            <div className="insight-actions">
              <button type="button" className="secondary-btn" disabled={!canFinalize || sending} onClick={() => void finalizeComplaint()}>
                {finalizeLabel}
              </button>
              <div className="status-chip">{currentSession ? `${(currentSession.language || "en").toUpperCase()} session` : "Session pending"}</div>
            </div>

            <div className="insight-header">
              <p className="panel-title">Complaint Data</p>
              <p className="panel-subtitle">Structured details and validation results appear here after a few exchanges.</p>
            </div>

            {extractedData ? (
              <div className="insight-list">
                {extractedData.category ? (
                  <div className="insight-item">
                    <p className="insight-label">Category</p>
                    <p className="insight-value">{extractedData.category}</p>
                  </div>
                ) : null}

                {extractedData.area ? (
                  <div className="insight-item">
                    <p className="insight-label">Area</p>
                    <p className="insight-value">{extractedData.area}</p>
                  </div>
                ) : null}

                {extractedData.duration ? (
                  <div className="insight-item">
                    <p className="insight-label">Duration</p>
                    <p className="insight-value">{extractedData.duration}</p>
                  </div>
                ) : null}

                {extractedData.keywords?.length ? (
                  <div className="insight-item">
                    <p className="insight-label">Keywords</p>
                    <p className="insight-value">{extractedData.keywords.join(", ")}</p>
                  </div>
                ) : null}

                {typeof extractedData.inconsistency_score === "number" ? (
                  <div className="insight-item">
                    <p className="insight-label">Inconsistency Score</p>
                    <p className="insight-value">{extractedData.inconsistency_score} / 5</p>
                  </div>
                ) : null}

                {extractedData.policy_reference ? (
                  <div className="insight-item">
                    <p className="insight-label">Primary Policy</p>
                    <p className="insight-value">{extractedData.policy_reference}</p>
                  </div>
                ) : null}

                {extractedData.timestamp ? (
                  <div className="insight-item">
                    <p className="insight-label">Captured At</p>
                    <p className="insight-value">{new Date(extractedData.timestamp).toLocaleString()}</p>
                  </div>
                ) : null}

                {extractedData.validation?.recommendation ? (
                  <div className="insight-item">
                    <p className="insight-label">Recommendation</p>
                    <p className="insight-value">{extractedData.validation.recommendation}</p>
                  </div>
                ) : null}

                {extractedData.validation?.inconsistencies?.length ? (
                  <div className="insight-item">
                    <p className="insight-label">Validation Notes</p>
                    <p className="insight-value">{extractedData.validation.inconsistencies.join(" | ")}</p>
                  </div>
                ) : null}

                {extractedData.validation?.references?.length ? (
                  <div className="reference-list">
                    {extractedData.validation.references.map((reference, index) => (
                      <div key={`reference-${index}`} className="reference-item">
                        {reference.url ? (
                          <a href={reference.url} target="_blank" rel="noreferrer">
                            {reference.title || "Reference"}
                          </a>
                        ) : (
                          <strong>{reference.title || "Reference"}</strong>
                        )}
                        {reference.content ? <p>{reference.content}</p> : null}
                      </div>
                    ))}
                  </div>
                ) : null}

                {extractedData.validation?.policy_references?.length ? (
                  <div className="reference-list">
                    {extractedData.validation.policy_references.map((reference, index) => (
                      <div key={`policy-reference-${index}`} className="reference-item">
                        <strong>{reference.title || "Policy Reference"}</strong>
                        {reference.content ? <p>{reference.content}</p> : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="empty-state">
                No extracted complaint details yet. Keep chatting and the assistant will summarize the category, area,
                duration, keywords, and validation notes.
              </div>
            )}
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
