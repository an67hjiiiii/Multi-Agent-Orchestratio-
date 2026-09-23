import type { AuthUser } from "../../types/api";
import type { DemoSession } from "../../components/ProductNavigation";

export function toSession(user: AuthUser): DemoSession {
  return {
    name: user.display_name || user.name || user.email || user.username || "Local researcher",
    email: user.email || user.username || "researcher@local",
    role: String(user.role).toUpperCase() === "ADMIN" ? "admin" : "researcher",
    demo: false,
  };
}
