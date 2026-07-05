import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * App-level error boundary (L2). A render exception now shows a recover panel
 * instead of a blank white screen.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Local-only app: log to the console for diagnostics, no telemetry.
    console.error("Unhandled render error:", error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background p-8 text-center">
          <div className="max-w-md rounded-lg border bg-surface p-6 shadow-card">
            <h1 className="text-lg font-semibold text-ink">Something went wrong</h1>
            <p className="mt-2 text-sm text-muted">
              The interface hit an unexpected error. Your data is safe — reloading usually
              clears it.
            </p>
            <pre className="mt-3 max-h-32 overflow-auto rounded bg-[var(--c-border-2)] p-2 text-left font-mono text-[11px] text-muted">
              {this.state.error.message}
            </pre>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded bg-accent px-4 py-2 text-sm font-medium text-white"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
