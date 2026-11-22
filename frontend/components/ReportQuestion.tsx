"use client";
import { useState } from "react";
import { errorMessage, reportQuestion } from "@/lib/api";
import type { ReportReason } from "@/lib/types";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "answer_looks_wrong", label: "The answer doesn't look right" },
  { value: "dont_understand", label: "I don't understand it" },
  { value: "something_else", label: "Something else" },
];

export function ReportQuestion({ questionId }: { questionId: string }) {
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function send(reason: ReportReason) {
    try {
      await reportQuestion(questionId, reason);
      setSent(true);
      setMessage(null);
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  if (sent) return <p className="muted" role="status">Thanks! We have told your parent about this question.</p>;
  if (!open) {
    return <button type="button" className="secondary" onClick={() => setOpen(true)}>This question looks odd</button>;
  }
  return (
    <div>
      <p className="muted">What looks odd?</p>
      {REASONS.map((reason) => (
        <button key={reason.value} type="button" className="secondary" onClick={() => void send(reason.value)}>
          {reason.label}
        </button>
      ))}{" "}
      <button type="button" className="secondary" onClick={() => setOpen(false)}>Cancel</button>
      {message && <p role="alert">{message}</p>}
    </div>
  );
}
