"use client";
import { useState } from "react";
import type { PracticeFeedback, PracticeQuestion } from "@/lib/types";

interface Props {
  question: PracticeQuestion;
  number: number;
  total: number;
  feedback: PracticeFeedback | null;
  busy: boolean;
  message: string | null;
  onSubmit: (answer: string) => void;
  onNext: () => void;
}

export function QuestionCard({ question, number, total, feedback, busy, message, onSubmit, onNext }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const locked = feedback !== null;

  return (
    <section className="card">
      <p className="muted">Question {number} of {total}</p>
      <h2 style={{ marginTop: 0 }}>{question.prompt}</h2>
      <div role="radiogroup" aria-label="Choices">
        {question.choices.map((choice) => (
          <label key={choice} className={`choice${selected === choice ? " picked" : ""}`}>
            <input type="radio" name={question.id} disabled={locked || busy} checked={selected === choice}
              onChange={() => setSelected(choice)} />
            {choice}
          </label>
        ))}
      </div>
      {message && <p role="alert">{message}</p>}
      {!locked && (
        <button type="button" disabled={busy} onClick={() => (selected ? onSubmit(selected) : undefined)}
          aria-disabled={!selected}>{busy ? "Checking…" : "Check my answer"}</button>
      )}
      {!locked && !selected && <p className="muted">Choose an answer first.</p>}
      {feedback && (
        <>
          <div className={`result ${feedback.isCorrect ? "right" : "retry"}`} role="status">
            <p><strong>{feedback.isCorrect ? "✓ Correct!" : "Not quite."}</strong></p>
            {!feedback.isCorrect && <p>The answer is <strong>{feedback.correctChoice}</strong>.</p>}
            <p>{feedback.feedback}</p>
          </div>
          <button type="button" onClick={onNext}>{number === total ? "Finish" : "Next question"}</button>
        </>
      )}
    </section>
  );
}
