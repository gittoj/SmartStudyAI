"use client";
import { useEffect, useState } from "react";
import { getWorksheetStatus, retryWorksheet } from "@/lib/api";
import type { WorksheetStatusResponse } from "@/lib/types";

interface Props { worksheetId: string; onReupload: () => void }

export function WorksheetStatus({ worksheetId, onReupload }: Props) {
  const [state, setState] = useState<WorksheetStatusResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const next = await getWorksheetStatus(worksheetId);
        if (!active) return;
        setState(next);
        if (next.status === "uploaded" || next.status === "processing") setTimeout(poll, 3000);
      } catch (error) {
        if (active) setMessage(error instanceof Error ? error.message : "Something went wrong. Please try again.");
      }
    }
    void poll();
    return () => { active = false; };
  }, [worksheetId]);

  async function handleRetry() {
    try {
      await retryWorksheet(worksheetId);
      setState(null);
      setMessage("Reading worksheet");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    }
  }

  if (message) return <p role="status">{message}</p>;
  if (!state || state.status === "uploaded" || state.status === "processing") return <p role="status">Reading worksheet</p>;
  if (state.status === "ready") return <p role="status">Worksheet ready for practice.</p>;
  return (
    <div role="alert">
      <p>{state.parentNote}</p>
      {state.canRetry ? <button type="button" onClick={handleRetry}>Try again</button>
                      : <button type="button" onClick={onReupload}>Upload again</button>}
    </div>
  );
}
