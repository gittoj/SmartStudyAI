"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ChildPicker } from "@/components/ChildPicker";
import { PracticeSession } from "@/components/PracticeSession";
import {
  ApiError, childLogout, errorMessage, getPracticeMe, listChildren, listReadyWorksheets, selectChild,
} from "@/lib/api";
import type { ChildProfile, ChildSummary, WorksheetSummary } from "@/lib/types";

type View = "loading" | "picking" | "home" | "session";

export default function LearningPage() {
  const [view, setView] = useState<View>("loading");
  const [child, setChild] = useState<ChildSummary | null>(null);
  const [children, setChildren] = useState<ChildProfile[]>([]);
  const [worksheets, setWorksheets] = useState<WorksheetSummary[]>([]);
  const [worksheetId, setWorksheetId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [needsParent, setNeedsParent] = useState(false);

  // Is a child already selected? 401 means no: show the profile picker instead.
  const enter = useCallback(async () => {
    try {
      setChild(await getPracticeMe());
      setWorksheets(await listReadyWorksheets());
      setView("home");
      return;
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) setMessage(errorMessage(error));
    }
    try {
      setChildren(await listChildren());
      setNeedsParent(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setNeedsParent(true);
      else setMessage(errorMessage(error));
    }
    setView("picking");
  }, []);

  useEffect(() => { void enter(); }, [enter]);

  async function handleSubmitPin(profile: ChildProfile, pin: string): Promise<string | null> {
    try {
      await selectChild(profile.id, pin);
      await enter();
      return null;
    } catch (error) {
      return errorMessage(error);
    }
  }

  async function handleSwitchChild() {
    await childLogout().catch(() => undefined);
    setChild(null);
    setView("loading");
    await enter();
  }

  return (
    <main className="kid">
      {view === "loading" && <p role="status">Loading…</p>}
      {message && <p role="alert">{message}</p>}

      {view === "picking" && (needsParent
        ? <div className="card"><p>Ask a grown-up to log in first.</p><Link className="button" href="/">Parent log in</Link></div>
        : <ChildPicker children={children} onSubmitPin={handleSubmitPin} />)}

      {view === "home" && child && (
        <>
          <h1>Hi, <span className="cap">{child.username}</span>!</h1>
          {worksheets.length === 0
            ? <p>No worksheets yet. Ask a grown-up to upload one.</p>
            : <><h2>Pick a worksheet</h2>
                {worksheets.map((worksheet) => (
                  <button key={worksheet.id} type="button" className="pick"
                    onClick={() => { setWorksheetId(worksheet.id); setView("session"); }}>
                    <span className="cap">{worksheet.topic}</span> <span className="muted cap">· {worksheet.subject}</span>
                  </button>
                ))}</>}
          <p><button type="button" className="secondary" onClick={handleSwitchChild}>This is not me</button></p>
        </>
      )}

      {view === "session" && worksheetId && (
        <PracticeSession worksheetId={worksheetId} onExit={() => { setView("home"); void enter(); }} />
      )}
      {view !== "loading" && (
        <p className="muted"><Link className="link" href="/">Grown-up? Log in here</Link></p>
      )}
    </main>
  );
}
