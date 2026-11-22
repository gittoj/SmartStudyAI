"use client";
import { useCallback, useEffect, useState } from "react";
import { ChildForm } from "@/components/ChildForm";
import { ParentShell } from "@/components/ParentShell";
import { createChildProfile, deleteChildProfile, errorMessage, listChildren } from "@/lib/api";
import type { ChildProfile, CreateChildRequest } from "@/lib/types";

const MAX_CHILDREN = 4;

function ChildrenManager() {
  const [children, setChildren] = useState<ChildProfile[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<ChildProfile | null>(null);
  const [confirmText, setConfirmText] = useState("");

  const refresh = useCallback(async () => {
    try { setChildren(await listChildren()); } catch (error) { setMessage(errorMessage(error)); }
  }, []);
  useEffect(() => {
    let active = true; // state is set only when the response arrives, never synchronously in the effect
    listChildren()
      .then((list) => { if (active) setChildren(list); })
      .catch((error) => { if (active) setMessage(errorMessage(error)); });
    return () => { active = false; };
  }, []);

  async function handleCreate(values: CreateChildRequest): Promise<boolean> {
    try {
      await createChildProfile(values);
      setMessage(null);
      await refresh();
      return true;
    } catch (error) {
      setMessage(errorMessage(error));
      return false;
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    try {
      await deleteChildProfile(deleting.id, confirmText);
      setDeleting(null);
      setConfirmText("");
      setMessage(null);
      await refresh();
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  return (
    <>
      <h1>Children</h1>
      {message && <p role="alert">{message}</p>}
      {children.length === 0 && <p>Add a child profile with a username, level and PIN to get started.</p>}
      <ul className="rows card">
        {children.map((child) => (
          <li key={child.id}>
            <span><span className="cap">{child.username}</span> <span className="muted">· {child.level}</span></span>
            <button type="button" className="secondary" style={{ marginTop: 0 }} onClick={() => { setDeleting(child); setConfirmText(""); }}>Delete</button>
          </li>
        ))}
      </ul>
      {deleting && (
        <div className="card" role="group" aria-label="Confirm delete">
          <p>This deletes {deleting.username}&apos;s worksheets, answers and progress. Type <strong>{deleting.username}</strong> to confirm.</p>
          <input aria-label="Type the username" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
          <button type="button" disabled={confirmText.toLowerCase() !== deleting.username} onClick={handleDelete}>Delete permanently</button>{" "}
          <button type="button" className="secondary" onClick={() => setDeleting(null)}>Cancel</button>
        </div>
      )}
      {children.length < MAX_CHILDREN ? <ChildForm onSubmit={handleCreate} /> : <p className="muted">You have added the maximum of four children.</p>}
    </>
  );
}

export default function StudentsPage() {
  return <ParentShell><ChildrenManager /></ParentShell>;
}
