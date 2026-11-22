"use client";
import { useEffect, useState } from "react";
import { errorMessage, getPracticeWorksheet, submitPracticeAnswer } from "@/lib/api";
import type { PracticeFeedback, WorksheetResult } from "@/lib/types";
import { LessonView } from "./LessonView";
import { QuestionCard } from "./QuestionCard";

interface Props { worksheetId: string; onExit: () => void }
type Stage = "lesson" | "practice" | "done";

export function PracticeSession({ worksheetId, onExit }: Props) {
  const [worksheet, setWorksheet] = useState<WorksheetResult | null>(null);
  const [stage, setStage] = useState<Stage>("lesson");
  const [index, setIndex] = useState(0);
  const [feedback, setFeedback] = useState<PracticeFeedback | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getPracticeWorksheet(worksheetId).then(setWorksheet).catch((error) => setMessage(errorMessage(error)));
  }, [worksheetId]);

  async function handleSubmit(answer: string) {
    if (!worksheet) return;
    setBusy(true);
    setMessage(null);
    try {
      setFeedback(await submitPracticeAnswer(worksheet.practiceQuestions[index].id, answer));
    } catch (error) {
      setMessage(errorMessage(error));
    }
    setBusy(false);
  }

  function handleNext() {
    setFeedback(null);
    setMessage(null);
    if (worksheet && index + 1 >= worksheet.practiceQuestions.length) setStage("done");
    else setIndex(index + 1);
  }

  const back = <button type="button" className="secondary" onClick={onExit}>Back to my worksheets</button>;
  if (!worksheet) return <>{message ? <p role="alert">{message}</p> : <p role="status">Getting your worksheet…</p>}{back}</>;
  if (stage === "lesson") return <><LessonView worksheet={worksheet} onStart={() => setStage("practice")} />{back}</>;
  if (stage === "done") {
    return (
      <section className="card">
        <h1>All done!</h1>
        <p>Great work today. Come back soon to practise some more.</p>
        {back}
      </section>
    );
  }
  const question = worksheet.practiceQuestions[index];
  return (
    <QuestionCard key={question.id} question={question} number={index + 1} total={worksheet.practiceQuestions.length}
      feedback={feedback} busy={busy} message={message} onSubmit={handleSubmit} onNext={handleNext} />
  );
}
