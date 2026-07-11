import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { api, ApiError, setSessionToken } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { useAuth } from "@/store/auth";
import type { SessionStatus, UserPublic } from "@/types/api";
import brand from "@/assets/forlas-brand.png";

interface LoginResponse {
  user: UserPublic;
  session_token: string;
}

export function LoginPanel() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const setSession = useAuth((s) => s.setSession);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      setError(null);
      const res = await api.post<LoginResponse>("/api/auth/login", { email, password });
      // Store the token so cross-origin (Tauri) requests authenticate via header.
      setSessionToken(res.session_token);
      const status = await api.get<SessionStatus>("/api/auth/session");
      setSession(status);
      qc.invalidateQueries();
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        const detail = (err.detail as { detail?: string } | string | null);
        const message =
          typeof detail === "string"
            ? detail
            : detail && "detail" in detail
              ? detail.detail
              : `Sign-in failed (${err.status})`;
        setError(message ?? "Sign-in failed");
      } else {
        setError("Could not reach the backend on http://127.0.0.1:8765.");
      }
    },
  });

  return (
    <div className="flex h-full items-center justify-center bg-background p-8">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="w-full max-w-[400px]"
      >
        <img
          src={brand}
          alt="FORLAS - Forecasting Loss and Operational Risk Assessment"
          className="pointer-events-none mx-auto mb-4 w-full max-w-[240px] select-none"
          draggable={false}
        />
        <Card className="p-7">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && (
              <div className="rounded-sm border border-rose/30 bg-rose-soft px-3 py-2 text-xs text-rose">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? "Signing in…" : "Sign in"}
            </Button>
            <p className="pt-2 text-center text-[11px] text-muted">
              Accounts are local to this machine.
            </p>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
