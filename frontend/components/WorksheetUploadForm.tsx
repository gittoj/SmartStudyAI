"use client";
import { useState, type ChangeEvent } from "react";
import { uploadWorksheet } from "@/lib/api";
import type { Subject } from "@/lib/types";

interface Props { childId: string; onUploaded: (worksheetId: string) => void }

export function WorksheetUploadForm({ childId, onUploaded }: Props) {
  const [subject, setSubject] = useState<Subject>("mathematics");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return setMessage("Choose a worksheet photo or PDF.");
    try {
      const result = await uploadWorksheet({ childId, subject, file });
      onUploaded(result.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <div>
      <select value={subject} onChange={(e: ChangeEvent<HTMLSelectElement>) => setSubject(e.target.value as Subject)}>
        <option value="mathematics">Mathematics</option>
        <option value="english">English</option>
      </select>
      <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <button type="button" onClick={handleUpload}>Upload worksheet</button>
      {message && <p role="alert">{message}</p>}
    </div>
  );
}
