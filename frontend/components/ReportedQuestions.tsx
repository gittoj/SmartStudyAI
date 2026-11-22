import type { ReportedQuestion, ReportReason } from "@/lib/types";

interface Props {
  reports: ReportedQuestion[];
  onResolve: (reportId: string, resolution: "confirmed" | "dismissed") => void;
}

const REASON_TEXT: Record<ReportReason, string> = {
  answer_looks_wrong: "said the answer does not look right",
  dont_understand: "did not understand it",
  something_else: "said something is odd",
};

export function ReportedQuestions({ reports, onResolve }: Props) {
  if (reports.length === 0) return null;
  return (
    <section className="card">
      <h2 style={{ marginTop: 0 }}>Questions to check</h2>
      <p className="muted">
        Your child flagged these. They are left out of the progress below until you decide.
      </p>
      <ul className="rows">
        {reports.map((report) => (
          <li key={report.id}>
            <span>
              <span className="cap">{report.topic}</span><br />
              <strong>{report.prompt}</strong><br />
              <span>Choices: {report.choices.join(", ")}</span><br />
              <span>Marked answer: <strong>{report.correctChoice}</strong></span><br />
              <span className="muted">{report.explanation}</span><br />
              <span className="muted">Your child {REASON_TEXT[report.reason]}.</span>
            </span>
            <span>
              <button type="button" className="secondary" style={{ marginTop: 0 }}
                onClick={() => onResolve(report.id, "confirmed")}>It&apos;s wrong, hide it</button>{" "}
              <button type="button" className="secondary" style={{ marginTop: 0 }}
                onClick={() => onResolve(report.id, "dismissed")}>It&apos;s fine, count it</button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
