"use client";
import { useState } from "react";
import { selectChild } from "@/lib/api";
import type { ChildProfile } from "@/lib/types";

interface Props { children: ChildProfile[]; onSelected: (child: ChildProfile) => void }

export function ChildPicker({ children, onSelected }: Props) {
  const [pending, setPending] = useState<ChildProfile | null>(null);
  const [pin, setPin] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleConfirmPin() {
    if (!pending) return;
    try {
      onSelected(await selectChild(pending.id, pin));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <div>
      {children.map((child) => (
        <button key={child.id} type="button" onClick={() => setPending(child)}>{child.username}</button>
      ))}
      {pending && (
        <div>
          <input type="password" inputMode="numeric" maxLength={4} value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} aria-label="PIN" />
          <button type="button" onClick={handleConfirmPin}>Start</button>
        </div>
      )}
      {message && <p role="alert">{message}</p>}
    </div>
  );
}
