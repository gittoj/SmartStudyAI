"use client";
import { useState, type FormEvent } from "react";
import type { CreateChildRequest, Level } from "@/lib/types";

interface Props { onSubmit: (values: CreateChildRequest) => Promise<boolean> }

export function ChildForm({ onSubmit }: Props) {
  const [username, setUsername] = useState("");
  const [level, setLevel] = useState<Level>("P2");
  const [pin, setPin] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (await onSubmit({ username, level, pin })) { setUsername(""); setPin(""); }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Add a child</h2>
      <label htmlFor="username">Username</label>
      <input id="username" required pattern="[A-Za-z0-9_]{3,20}" title="3 to 20 letters, numbers or underscores"
        value={username} onChange={(e) => setUsername(e.target.value)} />
      <p className="muted">Pick a nickname. Please do not use your child&apos;s full name.</p>
      <label htmlFor="level">Level</label>
      <select id="level" value={level} onChange={(e) => setLevel(e.target.value as Level)}>
        <option value="P2">Primary 2</option><option value="P3">Primary 3</option><option value="P4">Primary 4</option>
      </select>
      <label htmlFor="pin">4-digit PIN</label>
      <input id="pin" type="password" inputMode="numeric" required pattern="\d{4}" maxLength={4} title="Exactly four digits"
        value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
      <button type="submit">Add child</button>
    </form>
  );
}
