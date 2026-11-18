import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { InlineAlert } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { useAuth } from "@/hooks/auth";
import { ApiError } from "@/services/api";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (user) return <Navigate to={from} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-full place-items-center bg-canvas px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-brand-600 text-white shadow-card">
            <svg viewBox="0 0 32 32" className="size-6" aria-hidden>
              <path d="M9 22 16 9l7 13h-4l-3-6-3 6z" fill="currentColor" />
            </svg>
          </span>
          <div>
            <p className="text-lg font-semibold leading-tight text-ink">ACME</p>
            <p className="text-xs text-ink-faint">Salary Management</p>
          </div>
        </div>
        <Card className="p-6">
          <h1 className="text-lg font-semibold text-ink">Sign in</h1>
          <p className="mt-1 text-sm text-ink-soft">Use your HR Manager account.</p>
          <form onSubmit={submit} className="mt-5 space-y-4" noValidate>
            {error && <InlineAlert>{error}</InlineAlert>}
            <Field id="email" label="Email">
              {(p) => (
                <Input {...p} type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
              )}
            </Field>
            <Field id="password" label="Password">
              {(p) => (
                <Input
                  {...p}
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              )}
            </Field>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
