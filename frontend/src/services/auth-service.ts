import type { ConsentRecord, User } from "@/lib/types";
import { request } from "./http";

/** Scopes requested from Google: identity plus read/write access to Calendar. */
export const GOOGLE_OAUTH_SCOPES = [
  "openid",
  "email",
  "profile",
  "https://www.googleapis.com/auth/calendar",
] as const;

export interface AuthSession {
  user: User;
  grantedScopes: string[];
}

export interface AuthService {
  /**
   * Runs the Google OAuth flow. `consent` is the record of what the user accepted
   * in the pre-auth modal and must be stored by the backend with the session.
   */
  signInWithGoogle(consent: ConsentRecord): Promise<AuthSession>;
  signOut(): Promise<void>;
}

/**
 * Expected backend contract:
 *   POST /auth/google/session { consent, scopes } -> AuthSession
 *   POST /auth/logout                             -> 204
 * If the backend uses a redirect flow instead, replace the first call with
 * `window.location.assign(`${API_BASE_URL}/auth/google?...`)` and resolve the
 * session on the callback route.
 */
const httpAuthService: AuthService = {
  signInWithGoogle(consent) {
    return request<AuthSession>("/auth/google/session", {
      method: "POST",
      body: JSON.stringify({ consent, scopes: GOOGLE_OAUTH_SCOPES }),
    });
  },
  signOut() {
    return request<void>("/auth/logout", { method: "POST" });
  },
};

export const authService: AuthService = httpAuthService;
