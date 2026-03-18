import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.warn("ErrorBoundary caught:", error, info.componentStack);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", textAlign: "center" }}>
          <h2>Etwas ist schiefgelaufen.</h2>
          <p style={{ color: "var(--color-text-muted, #888)", marginBottom: "1rem" }}>
            {this.state.error?.message ?? "Ein unerwarteter Fehler ist aufgetreten."}
          </p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={this.handleReload}
          >
            Seite neu laden
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
