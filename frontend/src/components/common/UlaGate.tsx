import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/store/auth";
import type { SessionStatus } from "@/types/api";

const ULA_VERSION = "mit-1.0";

const ULA_SUMMARY = [
  "Free and open source under the MIT License — use, copy, modify, and redistribute freely.",
  "Copyright © 2026 Michael Walker — keep the copyright and licence notice in copies.",
  "Provided AS IS — no warranty and no liability (see LICENCE.md).",
  "Outputs are model estimates; validate with qualified practitioners before relying on them. Not legal, financial, insurance or regulatory advice.",
  "Incorporates concepts from the FAIR methodology; independent and not endorsed by the FAIR Institute.",
  "Bundles third-party open-source components under their own licences (see THIRD-PARTY-NOTICES.md).",
];

export function UlaGate() {
  const setSession = useAuth((s) => s.setSession);
  const [accepted, setAccepted] = useState(false);

  const acknowledge = useMutation({
    mutationFn: async () => {
      await api.post("/api/ula/acknowledge", { version: ULA_VERSION });
      const status = await api.get<SessionStatus>("/api/auth/session");
      setSession(status);
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-6">
      <div className="flex max-h-[88vh] w-full max-w-[760px] flex-col rounded-lg bg-surface shadow-modal">
        <div className="flex items-center gap-4 border-b px-6 py-5">
          <div className="h-9 w-9 rounded-md bg-gradient-to-br from-accent to-plum" />
          <div>
            <h2 className="text-base font-semibold">Welcome to FORLAS CRQ</h2>
            <p className="text-[11.5px] uppercase tracking-wide text-muted">
              Beta · Local first · Offline
            </p>
          </div>
          <span className="ml-auto rounded-full bg-[var(--c-border-2)] px-2.5 py-1 font-mono text-xs text-muted">
            MIT
          </span>
        </div>
        <div className="border-b bg-[var(--c-border-2)]/40 px-6 py-4 text-sm leading-relaxed">
          <p>
            Before you begin, please review and acknowledge the licence and
            disclaimers. A summary appears below; the full MIT License ships in{" "}
            <span className="font-mono">LICENCE.md</span>.
          </p>
          <ul className="mt-3 grid grid-cols-1 gap-1.5 text-xs md:grid-cols-2">
            {ULA_SUMMARY.map((s) => (
              <li key={s} className="relative pl-4 text-muted">
                <span className="absolute left-0 top-1.5 text-accent">●</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex items-center gap-3 border-t px-6 py-4">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              className="h-3.5 w-3.5 accent-[#7A92F4]"
            />
            I have read and accept the MIT License and the disclaimers above
          </label>
          <div className="flex-1" />
          <Button
            disabled={!accepted || acknowledge.isPending}
            onClick={() => acknowledge.mutate()}
          >
            {acknowledge.isPending ? "Confirming…" : "Accept & continue"}
          </Button>
        </div>
      </div>
    </div>
  );
}
