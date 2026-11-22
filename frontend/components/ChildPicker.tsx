"use client";
import { useState, type FormEvent } from "react";
import type { ChildProfile } from "@/lib/types";

interface Props {
  profiles: ChildProfile[];
  /** Returns an error message to show, or null when the PIN was accepted. */
  onSubmitPin: (child: ChildProfile, pin: string) => Promise<string | null>;
}

export function ChildPicker({ profiles, onSubmitPin }: Props) {
  const [pending, setPending] = useState<ChildProfile | null>(null);
  const [pin, setPin] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!pending) return;
    setBusy(true);
    setMessage(await onSubmitPin(pending, pin));
    setPin("");
    setBusy(false);
  }

  if (!pending) {
    return (
      <div className="card">
        <h1>Who is practising?</h1>
        {profiles.length === 0 && <p>Ask a grown-up to add your profile first.</p>}
        <p className="muted">Grown-ups: once a child starts, you will need to log in again to open the dashboard.</p>
        {profiles.map((child) => (
          <button key={child.id} type="button" className="pick" onClick={() => { setPending(child); setMessage(null); }}>
            <span className="cap">{child.username}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h1>Hi, <span className="cap">{pending.username}</span>!</h1>
      <label htmlFor="pin">Type your 4-digit PIN</label>
      <input id="pin" type="password" inputMode="numeric" autoComplete="off" autoFocus required pattern="\d{4}" maxLength={4}
        value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
      {message && <p role="alert">{message}</p>}
      <button type="submit" disabled={busy}>Start</button>{" "}
      <button type="button" className="secondary" onClick={() => { setPending(null); setMessage(null); }}>Back</button>
    </form>
  );
}
