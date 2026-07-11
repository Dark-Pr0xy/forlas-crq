import { create } from "zustand";
import type { SessionStatus, UserPublic } from "@/types/api";

interface AuthState {
  hydrated: boolean;
  authenticated: boolean;
  needsSetup: boolean;
  ulaAcknowledged: boolean;
  ulaVersion: string | null;
  user: UserPublic | null;
  setSession(status: SessionStatus): void;
  clear(): void;
}

export const useAuth = create<AuthState>((set) => ({
  hydrated: false,
  authenticated: false,
  needsSetup: false,
  ulaAcknowledged: false,
  ulaVersion: null,
  user: null,
  setSession(status) {
    set({
      hydrated: true,
      authenticated: status.authenticated,
      needsSetup: status.needs_setup,
      ulaAcknowledged: status.ula_acknowledged,
      ulaVersion: status.ula_version,
      user: status.user,
    });
  },
  clear() {
    set({
      hydrated: true,
      authenticated: false,
      needsSetup: false,
      ulaAcknowledged: false,
      ulaVersion: null,
      user: null,
    });
  },
}));
