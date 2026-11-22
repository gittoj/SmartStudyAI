import Link from "next/link";
import type { DashboardWorksheet } from "@/lib/types";

export function RecentWorksheets({ worksheets }: { worksheets: DashboardWorksheet[] }) {
  if (worksheets.length === 0) return null;
  return (
    <section className="card">
      <h2 style={{ marginTop: 0 }}>Recent worksheets</h2>
      <ul className="rows">
        {worksheets.map((worksheet) => {
          const reading = worksheet.status === "uploaded" || worksheet.status === "processing";
          const problem = worksheet.status === "needs_review" || worksheet.status === "failed";
          return (
            <li key={worksheet.id}>
              <span><span className="cap">{worksheet.topic || worksheet.subject}</span><br />
                <span className="muted">{new Date(worksheet.createdAt).toLocaleDateString()}</span>
                {problem && <><br /><span>{worksheet.parentNote}</span></>}</span>
              <span>
                {reading && <span className="badge processing">Reading worksheet</span>}
                {worksheet.status === "ready" && <span className="badge ready">Ready</span>}
                {problem && <Link className="button secondary" style={{ marginTop: 0 }} href="/worksheets">Upload again</Link>}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
