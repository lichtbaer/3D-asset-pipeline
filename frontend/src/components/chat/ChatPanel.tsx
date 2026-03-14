import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useChat } from "../../hooks/useChat.js";
import { useCurrentAssetContext } from "../../hooks/useCurrentAssetContext.js";
import "./ChatPanel.css";
import { usePipelineStore } from "../../store/PipelineStore.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import "./ChatPanel.css";

export function ChatPanel() {
  const navigate = useNavigate();
  const { setPendingPromptFromChat } = usePipelineStore();
  const { assetId, asset } = useCurrentAssetContext();
  const [useAssetContext, setUseAssetContext] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const effectiveAssetId = useAssetContext && assetId ? assetId : null;

  const {
    messages,
    lastResponseMeta,
    sendMessage,
    clearHistory,
    isLoading,
    error,
  } = useChat({ assetId: effectiveAssetId });

  useEscapeKey(() => setIsOpen(false));

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isLoading) return;
    setInputValue("");
    await sendMessage(trimmed);
    scrollToBottom();
  }, [inputValue, isLoading, sendMessage, scrollToBottom]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void handleSend();
      }
    },
    [handleSend]
  );

  const handleSuggestionClick = useCallback(
    (text: string) => {
      void sendMessage(text);
      scrollToBottom();
    },
    [sendMessage, scrollToBottom]
  );

  const handleApplyPrompt = useCallback(
    (prompt: string) => {
      setPendingPromptFromChat(prompt);
      navigate("/pipeline?tab=image");
      setIsOpen(false);
    },
    [setPendingPromptFromChat, navigate]
  );

  const handleNewChat = useCallback(() => {
    clearHistory();
    setInputValue("");
  }, [clearHistory]);

  const stepLabels: Record<string, string> = {
    image: "Image",
    bgremoval: "BgRemoval",
    mesh: "Mesh",
    rigging: "Rig",
    animation: "Anim",
  };
  const stepsSummary =
    asset?.steps &&
    Object.entries(asset.steps)
      .filter(
        ([, v]) => v && typeof v === "object" && "file" in v && (v as { file?: string }).file
      )
      .map(([k]) => stepLabels[k] ?? k)
      .join(" ✓ ");

  return (
    <>
      <button
        type="button"
        className="chat-fab"
        onClick={() => setIsOpen(true)}
        aria-label="KI-Assistent öffnen"
      >
        💬
      </button>

      {isOpen && (
        <div className="chat-panel" role="dialog" aria-label="KI-Assistent">
          <header className="chat-panel__header">
            <h2 className="chat-panel__title">KI-Assistent</h2>
            <div className="chat-panel__actions">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={handleNewChat}
                title="Neuer Chat"
                aria-label="Neuer Chat"
              >
                [+]
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setIsOpen(false)}
                aria-label="Schließen"
              >
                ×
              </button>
            </div>
          </header>

          {assetId && asset && (
            <div className="chat-panel__asset-context">
              <label className="chat-panel__asset-toggle">
                <input
                  type="checkbox"
                  checked={useAssetContext}
                  onChange={(e) => setUseAssetContext(e.target.checked)}
                />
                Asset-Kontext verwenden
              </label>
              <div className="chat-panel__asset-info">
                <span className="chat-panel__asset-name">
                  📦 {asset.name ?? `Asset ${assetId.slice(0, 8)}…`}
                </span>
                {stepsSummary && (
                  <span className="chat-panel__asset-steps">| {stepsSummary}</span>
                )}
              </div>
            </div>
          )}

          <div className="chat-panel__messages">
            {messages.length === 0 && (
              <div className="chat-panel__welcome">
                <p>🤖 Wie kann ich helfen?</p>
                <p className="chat-panel__welcome-hint">
                  Bildideen, Prompt-Optimierung, Pipeline-Entscheidungen…
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={`${msg.timestamp}-${i}`}
                className={`chat-panel__msg chat-panel__msg--${msg.role}`}
              >
                <span className="chat-panel__msg-avatar">
                  {msg.role === "user" ? "👤" : "🤖"}
                </span>
                <div className="chat-panel__msg-body">
                  <p className="chat-panel__msg-content">{msg.content}</p>
                  {msg.role === "assistant" &&
                    i === messages.length - 1 &&
                    lastResponseMeta && (
                      <div className="chat-panel__msg-actions">
                        {lastResponseMeta.promptSuggestion && (
                          <button
                            type="button"
                            className="btn btn--outline btn--sm chat-panel__apply-prompt"
                            onClick={() =>
                              handleApplyPrompt(lastResponseMeta!.promptSuggestion!)
                            }
                          >
                            → Prompt übernehmen
                          </button>
                        )}
                        {lastResponseMeta.suggestions.length > 0 && (
                          <div className="chat-panel__suggestions">
                            {lastResponseMeta.suggestions.map((s, j) => (
                              <button
                                key={j}
                                type="button"
                                className="chat-panel__suggestion-chip"
                                onClick={() => handleSuggestionClick(s)}
                                disabled={isLoading}
                              >
                                {s}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="chat-panel__msg chat-panel__msg--assistant">
                <span className="chat-panel__msg-avatar">🤖</span>
                <div className="chat-panel__typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
            {error && (
              <div className="chat-panel__error" role="alert">
                {error}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-panel__input-area">
            <textarea
              ref={inputRef}
              className="chat-panel__input"
              placeholder="Nachricht eingeben…"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              disabled={isLoading}
            />
            <button
              type="button"
              className="btn btn--primary chat-panel__send"
              onClick={() => void handleSend()}
              disabled={!inputValue.trim() || isLoading}
              aria-label="Senden"
            >
              →
            </button>
          </div>
        </div>
      )}
    </>
  );
}
