"use client";
import { useState, type FormEvent } from "react";
import { errorMessage, uploadWorksheet } from "@/lib/api";
import type { Subject } from "@/lib/types";

interface Props { childId: string; onUploaded: (worksheetId: string) => void }

export function WorksheetUploadForm({ childId, onUploaded }: Props) {
  const [subject, setSubject] = useState<Subject>("mathematics");
  const [topicHint, setTopicHint] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return setMessage("Choose a worksheet photo or PDF.");
    setBusy(true);
    setMessage(null);
    try {
      onUploaded((await uploadWorksheet({ childId, subject, topicHint: topicHint.trim() || undefined, file })).id);
    } catch (error) {
      setMessage(errorMessage(error));
    }
    setBusy(false);
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <label htmlFor="subject">Subject</label>
      <select id="subject" value={subject} onChange={(e) => setSubject(e.target.value as Subject)}>
        <option value="mathematics">Mathematics</option><option value="english">English</option>
      </select>
      <label htmlFor="topic">Topic (optional)</label>
      <input id="topic" maxLength={120} value={topicHint} onChange={(e) => setTopicHint(e.target.value)} />
      <label htmlFor="file">Worksheet (PDF, JPG, PNG or WEBP, up to 10 MB)</label>
      <input id="file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      {message && <p role="alert">{message}</p>}
      <button type="submit" disabled={busy}>{busy ? "Uploading…" : "Upload worksheet"}</button>
    </form>
  );
}
