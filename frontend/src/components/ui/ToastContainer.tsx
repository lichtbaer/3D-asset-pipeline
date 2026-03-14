import type { Toast } from "./ToastContext.js";

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.variant}`}>
          <span className="toast__message">{toast.message}</span>
          <button
            type="button"
            className="toast__dismiss"
            onClick={() => onDismiss(toast.id)}
            aria-label="Schließen"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
