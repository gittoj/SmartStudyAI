import type { WorksheetResult } from "@/lib/types";

interface Props { worksheet: WorksheetResult; onStart: () => void }

export function LessonView({ worksheet, onStart }: Props) {
  const example = worksheet.workedExample;
  return (
    <>
      <h1 className="cap">{worksheet.topic}</h1>
      <section className="card">
        <h2 style={{ marginTop: 0 }}>Let&apos;s learn</h2>
        <p>{worksheet.explanation}</p>
      </section>
      {example && (
        <section className="card">
          <h2 style={{ marginTop: 0 }}>An example</h2>
          <p><strong>{example.prompt}</strong></p>
          <ol className="steps">{example.steps.map((step) => <li key={step}>{step}</li>)}</ol>
          <p>Answer: <strong>{example.answer}</strong></p>
        </section>
      )}
      <button type="button" onClick={onStart}>Start practice</button>
    </>
  );
}
