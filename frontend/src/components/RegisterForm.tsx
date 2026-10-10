import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";

interface RegisterFormProps {
  onCancel: () => void;
  onRegistered: (email: string) => void;
}

export function RegisterForm({ onCancel, onRegistered }: RegisterFormProps) {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.register({
        email: email.trim(),
        username: username.trim() || undefined,
        display_name: displayName.trim() || undefined,
        password,
      });
      onRegistered(email.trim());
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not create the account. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="register-form" onSubmit={(event) => void submit(event)} aria-busy={isSubmitting}>
      <label htmlFor="register-email">Email</label>
      <input
        id="register-email"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      <label htmlFor="register-username">Username <span>(optional)</span></label>
      <input
        id="register-username"
        name="username"
        autoComplete="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />

      <label htmlFor="register-name">Display name <span>(optional)</span></label>
      <input
        id="register-name"
        name="display_name"
        autoComplete="name"
        value={displayName}
        onChange={(event) => setDisplayName(event.target.value)}
      />

      <label htmlFor="register-password">Password</label>
      <input
        id="register-password"
        name="password"
        type="password"
        autoComplete="new-password"
        minLength={8}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />
      <p className="form-hint">Use at least 8 characters.</p>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="form-actions">
        <button type="button" className="button-secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
        <button type="submit" className="button-primary" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
      </div>
    </form>
  );
}
