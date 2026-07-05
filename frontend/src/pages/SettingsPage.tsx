import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Upload, UserPlus } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { fmt } from "@/lib/format";
import { APP_NAME, APP_VERSION } from "@/lib/version";
import { useAuth } from "@/store/auth";
import type { AppSettings, Role, UserPublic } from "@/types/api";

interface BackupEntry {
  filename: string;
  size_bytes: number;
  created_at: string;
}

export function SettingsPage() {
  const currentUser = useAuth((s) => s.user);
  const isOwner = currentUser?.role === "owner";

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {isOwner && <SimulationDefaultsCard />}
      <ImportAlphaCard />
      <PasswordCard userId={currentUser?.id ?? null} />
      {isOwner && <BackupsCard />}
      {isOwner && <UsersCard currentUserId={currentUser?.id ?? null} />}
      <AboutCard />
    </div>
  );
}

// --------------------------------------------------------------- simulation

function SimulationDefaultsCard() {
  const qc = useQueryClient();
  const { data } = useQuery<AppSettings>({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/api/settings"),
  });
  const [iterations, setIterations] = useState<number | null>(null);
  const [seed, setSeed] = useState<number | null>(null);
  const save = useMutation({
    mutationFn: (payload: Partial<AppSettings>) =>
      api.patch<AppSettings>("/api/settings", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Simulation defaults</CardTitle>
        <CardHint>Applied to new runs · Owner only</CardHint>
      </CardHeader>
      <CardBody className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="iter">Iterations</Label>
          <Input
            id="iter"
            type="number"
            value={iterations ?? data.iterations}
            min={1000}
            max={1_000_000}
            onChange={(e) => setIterations(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="seed">Deterministic seed</Label>
          <Input
            id="seed"
            type="number"
            value={seed ?? data.seed}
            onChange={(e) => setSeed(Number(e.target.value))}
          />
        </div>
        <Button
          onClick={() =>
            save.mutate({ iterations: iterations ?? data.iterations, seed: seed ?? data.seed })
          }
          disabled={save.isPending}
        >
          {save.isPending ? "Saving…" : "Save"}
        </Button>
      </CardBody>
    </Card>
  );
}

// --------------------------------------------------------------- import

function ImportAlphaCard() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [note, setNote] = useState<string | null>(null);
  const importAlpha = useMutation({
    mutationFn: (file: File) => api.upload<{ message: string }>("/api/import/alpha", file),
    onSuccess: (res) => {
      setNote(res.message);
      qc.invalidateQueries({ queryKey: ["scenarios"] });
    },
    onError: () => setNote("Import failed — is this an Alpha export JSON?"),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import from Alpha</CardTitle>
        <CardHint>JSON exported from the original HTML tool</CardHint>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-muted">
          Use the Alpha&apos;s &quot;Export all&quot; button, then upload the resulting JSON
          here. Scenarios with invalid inputs are skipped and reported.
        </p>
        <input
          ref={fileRef}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) importAlpha.mutate(file);
          }}
        />
        <Button
          variant="outline"
          onClick={() => fileRef.current?.click()}
          disabled={importAlpha.isPending}
        >
          <Upload className="h-4 w-4" />
          {importAlpha.isPending ? "Importing…" : "Choose Alpha JSON file"}
        </Button>
        {note && <p className="text-xs text-accent">{note}</p>}
      </CardBody>
    </Card>
  );
}

// --------------------------------------------------------------- password

function PasswordCard({ userId }: { userId: number | null }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const change = useMutation({
    mutationFn: () =>
      api.patch(`/api/auth/users/${userId}`, { password }),
    onSuccess: () => {
      setNote("Password updated.");
      setPassword("");
      setConfirm("");
    },
    onError: () => setNote("Update failed."),
  });

  const mismatch = password.length > 0 && password !== confirm;
  const tooShort = password.length > 0 && password.length < 8;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change your password</CardTitle>
        <CardHint>Minimum 8 characters</CardHint>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="space-y-1.5">
          <Label>New password</Label>
          <Input
            type="password"
            value={password}
            autoComplete="new-password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Confirm password</Label>
          <Input
            type="password"
            value={confirm}
            autoComplete="new-password"
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
        {mismatch && <p className="text-xs text-rose">Passwords don&apos;t match.</p>}
        {tooShort && <p className="text-xs text-rose">Password must be at least 8 characters.</p>}
        <Button
          disabled={!userId || tooShort || mismatch || password.length === 0 || change.isPending}
          onClick={() => change.mutate()}
        >
          {change.isPending ? "Updating…" : "Update password"}
        </Button>
        {note && <p className="text-xs text-accent">{note}</p>}
      </CardBody>
    </Card>
  );
}

// --------------------------------------------------------------- backups

function BackupsCard() {
  const { data, refetch } = useQuery<BackupEntry[]>({
    queryKey: ["backups"],
    queryFn: () => api.get<BackupEntry[]>("/api/backups"),
  });
  const create = useMutation({
    mutationFn: () => api.post<{ message: string }>("/api/backup"),
    onSuccess: () => refetch(),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Backups</CardTitle>
        <CardHint>SQLite snapshots · Owner only</CardHint>
      </CardHeader>
      <CardBody className="space-y-3">
        <Button onClick={() => create.mutate()} disabled={create.isPending}>
          <Database className="h-4 w-4" />
          {create.isPending ? "Creating…" : "Create backup"}
        </Button>
        <div className="max-h-[200px] space-y-1 overflow-auto">
          {(data ?? []).length === 0 ? (
            <p className="text-xs text-muted">No backups yet.</p>
          ) : (
            (data ?? []).map((b) => (
              <div
                key={b.filename}
                className="flex items-center justify-between border-b border-[var(--c-border-2)] py-1.5 text-xs"
              >
                <span className="font-mono">{b.filename}</span>
                <span className="text-muted">
                  {(b.size_bytes / 1_048_576).toFixed(1)} MB · {fmt.date(b.created_at)}
                </span>
              </div>
            ))
          )}
        </div>
        <p className="text-[11px] text-muted">
          Backups are written to the application data directory. Restore by replacing the live
          database file while the app is stopped.
        </p>
      </CardBody>
    </Card>
  );
}

// --------------------------------------------------------------- users

function UsersCard({ currentUserId }: { currentUserId: number | null }) {
  const qc = useQueryClient();
  const { data: users } = useQuery<UserPublic[]>({
    queryKey: ["users"],
    queryFn: () => api.get<UserPublic[]>("/api/auth/users"),
  });
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("reviewer");
  const [note, setNote] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.post<UserPublic>("/api/auth/users", {
        email,
        display_name: name || email,
        password,
        role,
      }),
    onSuccess: () => {
      setNote(`Created ${email}`);
      setEmail("");
      setName("");
      setPassword("");
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => setNote("Create failed — email may already exist."),
  });
  const updateRole = useMutation({
    mutationFn: (vars: { id: number; role: Role }) =>
      api.patch(`/api/auth/users/${vars.id}`, { role: vars.role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const deactivate = useMutation({
    mutationFn: (id: number) => api.delete(`/api/auth/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>Users</CardTitle>
        <CardHint>Owner only · Argon2-hashed local accounts</CardHint>
      </CardHeader>
      <CardBody className="space-y-4">
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pr-2">Email</th>
                <th className="py-2 pr-2">Name</th>
                <th className="py-2 pr-2">Role</th>
                <th className="py-2 pr-2">Status</th>
                <th className="py-2 pr-2"></th>
              </tr>
            </thead>
            <tbody>
              {(users ?? []).map((u) => (
                <tr key={u.id} className="border-b border-[var(--c-border-2)]">
                  <td className="py-1.5 pr-2 font-medium">{u.email}</td>
                  <td className="py-1.5 pr-2 text-muted">{u.display_name}</td>
                  <td className="py-1.5 pr-2">
                    <Select
                      value={u.role}
                      onChange={(e) =>
                        updateRole.mutate({ id: u.id, role: e.target.value as Role })
                      }
                      className="h-7 w-[120px]"
                      disabled={u.id === currentUserId}
                    >
                      <option value="owner">owner</option>
                      <option value="approver">approver</option>
                      <option value="reviewer">reviewer</option>
                      <option value="readonly">readonly</option>
                    </Select>
                  </td>
                  <td className="py-1.5 pr-2">
                    <Badge tone={u.is_active ? "success" : "neutral"}>
                      {u.is_active ? "active" : "inactive"}
                    </Badge>
                  </td>
                  <td className="py-1.5 pr-2 text-right">
                    {u.id !== currentUserId && u.is_active && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          if (confirm(`Deactivate ${u.email}? Their sessions end immediately.`))
                            deactivate.mutate(u.id);
                        }}
                      >
                        Deactivate
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded border bg-[var(--c-border-2)]/30 p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <UserPlus className="h-4 w-4" /> Add user
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
            <Input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Input placeholder="display name" value={name} onChange={(e) => setName(e.target.value)} />
            <Input
              placeholder="password (min 8)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="owner">owner</option>
              <option value="approver">approver</option>
              <option value="reviewer">reviewer</option>
              <option value="readonly">readonly</option>
            </Select>
          </div>
          <Button
            className="mt-2"
            disabled={!email || password.length < 8 || create.isPending}
            onClick={() => create.mutate()}
          >
            {create.isPending ? "Creating…" : "Create user"}
          </Button>
          {note && <p className="mt-1 text-xs text-accent">{note}</p>}
        </div>
      </CardBody>
    </Card>
  );
}

// --------------------------------------------------------------- about

function AboutCard() {
  const { data } = useQuery<AppSettings>({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/api/settings"),
  });
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>About</CardTitle>
      </CardHeader>
      <CardBody className="text-sm leading-relaxed text-muted">
        <p>
          {APP_NAME} Beta · {APP_VERSION} · ULA{" "}
          {data?.ula_acknowledged_version
            ? `v${data.ula_acknowledged_version} acknowledged`
            : "not yet acknowledged"}
          .
        </p>
        <p className="mt-2">
          Copyright © 2026 Michael Walker. All rights reserved. See LICENCE.md.
        </p>
      </CardBody>
    </Card>
  );
}
