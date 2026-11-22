"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ParentShell } from "@/components/ParentShell";
import { WorksheetStatus } from "@/components/WorksheetStatus";
import { WorksheetUploadForm } from "@/components/WorksheetUploadForm";
import { errorMessage, listChildren } from "@/lib/api";
import type { ChildProfile } from "@/lib/types";

function UploadView() {
  const [children, setChildren] = useState<ChildProfile[] | null>(null);
  const [childId, setChildId] = useState("");
  const [worksheetId, setWorksheetId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    listChildren()
      .then((list) => { setChildren(list); setChildId(list[0]?.id ?? ""); })
      .catch((error) => setMessage(errorMessage(error)));
  }, []);

  if (message) return <p role="alert">{message}</p>;
  if (children === null) return <p role="status">Loading…</p>;
  if (children.length === 0) return <p>First <Link className="link" href="/students">add a child profile</Link>, then upload a worksheet.</p>;

  return (
    <>
      <h1>Upload a worksheet</h1>
      <label htmlFor="child">For which child?</label>
      <select id="child" value={childId} onChange={(e) => { setChildId(e.target.value); setWorksheetId(null); }}>
        {children.map((child) => <option key={child.id} value={child.id}>{child.username} ({child.level})</option>)}
      </select>
      {worksheetId
        ? <div className="card"><WorksheetStatus worksheetId={worksheetId} onReupload={() => setWorksheetId(null)} />
            <Link className="link" href="/dashboard">Go to the dashboard</Link></div>
        : <WorksheetUploadForm childId={childId} onUploaded={setWorksheetId} />}
    </>
  );
}

export default function WorksheetsPage() {
  return <ParentShell><UploadView /></ParentShell>;
}
