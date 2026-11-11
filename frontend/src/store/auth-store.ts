import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ConsentRecord, User } from "@/lib/types";
import { authService } from "@/services/auth-service";

type AuthStatus = "idle" | "loading" | "authenticated" | "error";

interface AuthState {
  user: User | null;
  consent: ConsentRecord | null;
  status: AuthStatus;
  error: string | null;
  /** True once the persisted session has been read from localStorage. */
  hydrated: boolean;
  signIn: (consent: ConsentRecord) => Promise<boolean>;
  signOut: () => Promise<void>;
  clearError: () => void;
  markHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      consent: null,
      status: "idle",
      error: null,
      hydrated: false,

      async signIn(consent) {
        set({ status: "loading", error: null });
        try {
          const session = await authService.signInWithGoogle(consent);
          set({ user: session.user, consent, status: "authenticated" });
          return true;
        } catch {
          set({
            status: "error",
            error: "Não foi possível entrar com o Google. Tente novamente.",
          });
          return false;
        }
      },

      async signOut() {
        try {
          await authService.signOut();
        } finally {
          set({ user: null, consent: null, status: "idle", error: null });
        }
      },

      clearError: () =>
        set((state) => ({ error: null, status: state.user ? "authenticated" : "idle" })),

      markHydrated: () =>
        set((state) => ({ hydrated: true, status: state.user ? "authenticated" : "idle" })),
    }),
    {
      name: "destrava:auth",
      partialize: ({ user, consent }) => ({ user, consent }),
      // Rehydrated by <StoreHydrator /> after mount so server and client markup match.
      skipHydration: true,
      onRehydrateStorage: (state) => () => state.markHydrated(),
    },
  ),
);
