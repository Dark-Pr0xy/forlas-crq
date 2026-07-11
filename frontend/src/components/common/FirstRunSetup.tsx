import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { api, apiErrorMessage, setSessionToken } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { useAuth } from "@/store/auth";
import type { SessionStatus, UserPublic } from "@/types/api";
import brand from "@/assets/forlas-brand.png";

interface SetupResponse {
  user: UserPublic;
  session_token: string;
}

export function FirstRunSetup() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const setSession = useAuth((s) => s.setSession);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      setError(null);
      const res = await api.post<SetupResponse>("/api/auth/setup", {
        username: username.trim(),
        password,
      });
      // Store the token so cross-origin (Tauri) requests authenticate by header.
      setSessionToken(res.session_token);
      const status = await api.get<SessionStatus>("/api/auth/session");
      setSession(status);
      qc.invalidateQueries();
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (username.trim().length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    mutation.mutate();
  }

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
          <h1 className="text-lg font-semibold">Create your account</h1>
          <p className="mt-1 text-xs text-muted">
            This is the first run on this machine. Create a local account to begin.
          </p>
          <form onSubmit={submit} className="mt-5 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </div>
            {error && (
              <div className="rounded-sm border border-rose/30 bg-rose-soft px-3 py-2 text-xs text-rose">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating account…" : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-[11px] text-muted">
            Accounts are local to this machine. Passwords cannot be recovered.
          </p>
        </Card>
      </motion.div>
    </div>
  );
}
