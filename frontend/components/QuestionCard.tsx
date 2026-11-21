"use client";
import { useState } from "react";
import { submitPracticeAnswer } from "@/lib/api";
import type { PracticeFeedback, PracticeQuestion } from "@/lib/types";

interface Props { question: PracticeQuestion; onNext: () => void }

export function QuestionCard({ question, onNext }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<PracticeFeedback | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit() {
    if (!selected) return setMessage("Choose an answer first.");
    try {
      setFeedback(await submitPracticeAnswer(question.id, selected));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <section>
      <h2>{question.prompt}</h2>
      {question.choices.map((choice) => (
        <label key={choice}>
          <input type="radio" name={question.id} disabled={feedback !== null}
            checked={selected === choice} onChange={() => setSelected(choice)} />
          {choice}
        </label>
      ))}
      {!feedback && <button type="button" onClick={handleSubmit}>Check answer</button>}
      {message && <p role="alert">{message}</p>}
      {feedback && (
        <div>
          <p>{feedback.feedback}</p>
          <p>Correct choice: {feedback.correctChoice}</p>
          <button type="button" onClick={onNext}>Next question</button>
        </div>
      )}
    </section>
  );
}
