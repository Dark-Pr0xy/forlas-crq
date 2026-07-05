import { create } from "zustand";
import type { SessionStatus, UserPublic } from "@/types/api";

interface AuthState {
  hydrated: boolean;
  authenticated: boolean;
  ulaAcknowledged: boolean;
  ulaVersion: string | null;
  user: UserPublic | null;
  setSession(status: SessionStatus): void;
  clear(): void;
}

export const useAuth = create<AuthState>((set) => ({
  hydrated: false,
  authenticated: false,
  ulaAcknowledged: false,
  ulaVersion: null,
  user: null,
  setSession(status) {
    set({
      hydrated: true,
      authenticated: status.authenticated,
      ulaAcknowledged: status.ula_acknowledged,
      ulaVersion: status.ula_version,
      user: status.user,
    });
  },
  clear() {
    set({
      hydrated: true,
      authenticated: false,
      ulaAcknowledged: false,
      ulaVersion: null,
      user: null,
    });
  },
}));
