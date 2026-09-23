import type { AuthUser } from "../../types/api";
import type { DemoSession } from "../../components/ProductNavigation";

export type AuthRestoreState = "AUTHENTICATED" | "SIGNED_OUT" | "EXPIRED";

const SESSION_MARKER = "local-mrag.auth-session";

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function hasRememberedSession(): boolean {
  return storage()?.getItem(SESSION_MARKER) === "active";
}

export function rememberSession(active: boolean): void {
  const store = storage();
  if (!store) return;
  try {
    if (active) store.setItem(SESSION_MARKER, "active");
    else store.removeItem(SESSION_MARKER);
  } catch {
    // Storage availability must not become an auth fallback or error state.
  }
}

export function authRestoreState(authenticated: boolean, hadRememberedSession: boolean): AuthRestoreState {
  if (authenticated) return "AUTHENTICATED";
  return hadRememberedSession ? "EXPIRED" : "SIGNED_OUT";
}

export function toSession(user: AuthUser): DemoSession {
  return {
    name: user.display_name || user.name || user.email || user.username || "Local researcher",
    email: user.email || user.username || "researcher@local",
    role: String(user.role).toUpperCase() === "ADMIN" ? "admin" : "researcher",
    demo: false,
  };
}
