"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { getMe, logout } from "@/lib/api";
import type { ParentAccount } from "@/lib/types";

/** Guards parent pages: redirects to the login screen when there is no parent session. */
export function ParentShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [parent, setParent] = useState<ParentAccount | null>(null);

  useEffect(() => { getMe().then(setParent).catch(() => router.replace("/")); }, [router]);

  async function handleLogout() {
    await logout().catch(() => undefined);
    router.replace("/");
  }

  if (!parent) return <main><p role="status">Loading…</p></main>;
  return (
    <>
      <nav className="nav" aria-label="Main">
        <Link href="/dashboard">Dashboard</Link>
        <Link href="/students">Children</Link>
        <Link href="/worksheets">Upload</Link>
        <Link href="/learning">Child practice</Link>
        <span className="spacer" />
        <span className="muted">{parent.displayName}</span>
        <button type="button" className="secondary" style={{ marginTop: 0 }} onClick={handleLogout}>Log out</button>
      </nav>
      <main>{children}</main>
    </>
  );
}
