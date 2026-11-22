"use client";
import { useEffect, useState } from "react";
import { errorMessage, getWorksheetStatus, retryWorksheet } from "@/lib/api";
import type { WorksheetStatusResponse } from "@/lib/types";

interface Props { worksheetId: string; onReupload: () => void }

export function WorksheetStatus({ worksheetId, onReupload }: Props) {
  const [state, setState] = useState<WorksheetStatusResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [round, setRound] = useState(0); // bumped after a retry to restart polling

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await getWorksheetStatus(worksheetId);
        if (!active) return;
        setState(next);
        if (next.status === "uploaded" || next.status === "processing") timer = setTimeout(poll, 3000);
      } catch (error) {
        if (active) setMessage(errorMessage(error));
      }
    }
    timer = setTimeout(poll, 0);
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [worksheetId, round]);

  async function handleRetry() {
    try {
      await retryWorksheet(worksheetId);
      setState(null);
      setMessage(null);
      setRound(round + 1);
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  if (message) return <p role="alert">{message}</p>;
  if (!state || state.status === "uploaded" || state.status === "processing") return <p role="status">Reading worksheet…</p>;
  if (state.status === "ready") return <p role="status">Worksheet ready for practice.</p>;
  return (
    <div role="alert">
      <p>{state.parentNote}</p>
      {state.canRetry ? <button type="button" onClick={handleRetry}>Try again</button>
                      : <button type="button" onClick={onReupload}>Upload again</button>}
    </div>
  );
}
