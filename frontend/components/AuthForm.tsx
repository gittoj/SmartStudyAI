"use client";
import { useState, type ChangeEvent, type FormEvent } from "react";

export type AuthMode = "login" | "register";
export interface AuthValues { email: string; displayName: string; password: string }
interface Props { onSubmit: (mode: AuthMode, values: AuthValues) => Promise<void>; message: string | null }

export function AuthForm({ onSubmit, message }: Props) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [values, setValues] = useState<AuthValues>({ email: "", displayName: "", password: "" });
  const [busy, setBusy] = useState(false);
  const update = (field: keyof AuthValues) => (event: ChangeEvent<HTMLInputElement>) =>
    setValues({ ...values, [field]: event.target.value });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    await onSubmit(mode, values);
    setBusy(false);
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h1>{mode === "login" ? "Parent log in" : "Create your parent account"}</h1>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" required autoComplete="email" value={values.email} onChange={update("email")} />
      {mode === "register" && (<>
        <label htmlFor="name">Your name</label>
        <input id="name" required maxLength={100} value={values.displayName} onChange={update("displayName")} />
      </>)}
      <label htmlFor="password">Password</label>
      <input id="password" type="password" required minLength={mode === "register" ? 10 : 1}
        autoComplete={mode === "login" ? "current-password" : "new-password"} value={values.password} onChange={update("password")} />
      {mode === "register" && <p className="muted">At least 10 characters.</p>}
      {message && <p role="alert">{message}</p>}
      <button type="submit" disabled={busy}>{mode === "login" ? "Log in" : "Create account"}</button>{" "}
      <button type="button" className="secondary" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "New here? Create an account" : "I already have an account"}
      </button>
    </form>
  );
}
