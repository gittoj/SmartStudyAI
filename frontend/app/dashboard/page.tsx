"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ParentShell } from "@/components/ParentShell";
import { RecentWorksheets } from "@/components/RecentWorksheets";
import { TopicProgressList } from "@/components/TopicProgressList";
import { errorMessage, getDashboard, listChildren, removeWorksheet } from "@/lib/api";
import type { ChildProfile, ParentDashboard } from "@/lib/types";

const LAST_CHILD_KEY = "smartstudy:lastChild"; // a profile id only; nothing sensitive

function readLastChild(): string | null {
  try { return window.localStorage.getItem(LAST_CHILD_KEY); } catch { return null; }
}
function saveLastChild(id: string): void {
  try { window.localStorage.setItem(LAST_CHILD_KEY, id); } catch { /* storage unavailable */ }
}

function DashboardView() {
  const [children, setChildren] = useState<ChildProfile[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<ParentDashboard | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    listChildren()
      .then((list) => {
        setChildren(list);
        setSelectedId((list.find((child) => child.id === readLastChild()) ?? list[0])?.id ?? null);
      })
      .catch((error) => setMessage(errorMessage(error)));
  }, []);

  const load = useCallback(async (id: string) => {
    try { setDashboard(await getDashboard(id)); setMessage(null); } catch (error) { setMessage(errorMessage(error)); }
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    saveLastChild(selectedId);
    setDashboard(null);
    void load(selectedId);
  }, [selectedId, load]);

  // While a worksheet is being read, refresh every few seconds.
  const reading = dashboard?.recentWorksheets.some((w) => w.status === "uploaded" || w.status === "processing") ?? false;
  useEffect(() => {
    if (!reading || !selectedId) return;
    const timer = setTimeout(() => void load(selectedId), 4000);
    return () => clearTimeout(timer);
  }, [reading, selectedId, dashboard, load]);

  async function handleRemove(worksheetId: string) {
    if (!selectedId || !window.confirm("Remove this worksheet? You will not be able to try it again.")) return;
    try {
      await removeWorksheet(worksheetId);
      await load(selectedId);
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  if (message && !dashboard) return <p role="alert">{message}</p>;
  if (children === null) return <p role="status">Loading…</p>;
  if (children.length === 0) return <p>Create a <Link className="link" href="/students">child profile</Link> with a username, level and PIN to begin.</p>;

  return (
    <>
      <h1>Dashboard</h1>
      <label htmlFor="child">Child</label>
      <select id="child" value={selectedId ?? ""} onChange={(e) => setSelectedId(e.target.value)}>
        {children.map((child) => <option key={child.id} value={child.id}>{child.username} ({child.level})</option>)}
      </select>
      {message && <p role="alert">{message}</p>}
      {dashboard && <><TopicProgressList topics={dashboard.topics} /><RecentWorksheets worksheets={dashboard.recentWorksheets} onRemove={handleRemove} /></>}
      <p><Link className="button" href="/worksheets">Upload a worksheet</Link></p>
    </>
  );
}

export default function DashboardPage() {
  return <ParentShell><DashboardView /></ParentShell>;
}
