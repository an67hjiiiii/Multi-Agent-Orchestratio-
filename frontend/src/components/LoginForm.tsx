import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";

interface LoginFormProps {
  onCancel: () => void;
  onCreateAccount: () => void;
  onSignedIn: () => void;
}

export function LoginForm({ onCancel, onCreateAccount, onSignedIn }: LoginFormProps) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.login({ identifier: identifier.trim(), password });
      onSignedIn();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not sign in. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="register-form" onSubmit={(event) => void submit(event)} aria-busy={isSubmitting}>
      <label htmlFor="login-identifier">Email or username</label>
      <input
        id="login-identifier"
        name="identifier"
        autoComplete="username"
        value={identifier}
        onChange={(event) => setIdentifier(event.target.value)}
        required
      />

      <label htmlFor="login-password">Password</label>
      <input
        id="login-password"
        name="password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="form-actions">
        <button type="button" className="button-secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
        <button type="submit" className="button-primary" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </div>
      <p className="form-hint">
        New here? <button type="button" className="text-button" onClick={onCreateAccount}>Create an account</button>
      </p>
    </form>
  );
}
