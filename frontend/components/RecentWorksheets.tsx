import Link from "next/link";
import type { DashboardWorksheet } from "@/lib/types";

interface Props { worksheets: DashboardWorksheet[]; onRemove: (worksheetId: string) => void }

export function RecentWorksheets({ worksheets, onRemove }: Props) {
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
                <span className="muted">{new Date(worksheet.createdAt).toLocaleDateString("en-SG")}</span>
                {problem && <><br /><span>{worksheet.parentNote}</span></>}</span>
              <span>
                {reading && <span className="badge processing">Reading worksheet</span>}
                {worksheet.status === "ready" && <span className="badge ready">Ready</span>}
                {problem && (
                  <>
                    <Link className="button secondary" style={{ marginTop: 0 }} href="/worksheets">Upload again</Link>{" "}
                    <button type="button" className="secondary" style={{ marginTop: 0 }}
                      onClick={() => onRemove(worksheet.id)}>Remove</button>
                  </>
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
