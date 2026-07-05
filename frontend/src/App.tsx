import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { api, setSessionToken, setUnauthorizedHandler } from "@/lib/api";
import { LoginPanel } from "@/components/common/LoginPanel";
import { UlaGate } from "@/components/common/UlaGate";
import { router } from "@/routes/router";
import { useAuth } from "@/store/auth";
import type { SessionStatus } from "@/types/api";

export function App() {
  const hydrated = useAuth((s) => s.hydrated);
  const authenticated = useAuth((s) => s.authenticated);
  const ulaAcknowledged = useAuth((s) => s.ulaAcknowledged);
  const setSession = useAuth((s) => s.setSession);
  const queryClient = useQueryClient();

  // Any 401 mid-session clears auth + drops back to the login panel.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSessionToken(null);
      useAuth.getState().clear();
      queryClient.clear();
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  const { data, isError, refetch, failureCount } = useQuery<SessionStatus>({
    queryKey: ["session"],
    queryFn: () => api.get<SessionStatus>("/api/auth/session"),
    staleTime: 60_000,
    // The desktop app spawns the backend on launch; it takes a few seconds to
    // cold-start. Keep retrying so the window recovers on its own instead of
    // hanging on "Connecting…" until a manual reopen.
    retry: (count) => count < 60,
    retryDelay: 1000,
  });

  useEffect(() => {
    if (data) setSession(data);
  }, [data, setSession]);

  if (!hydrated) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 text-muted">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-ping rounded-full bg-accent" />
          Connecting to local backend…
        </div>
        {failureCount > 3 && (
          <p className="text-xs">
            The engine is still starting up (this can take a few seconds on first launch).
          </p>
        )}
        {isError && failureCount >= 60 && (
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  if (!authenticated) {
    return <LoginPanel />;
  }

  return (
    <>
      <RouterProvider router={router} />
      {!ulaAcknowledged && <UlaGate />}
    </>
  );
}
